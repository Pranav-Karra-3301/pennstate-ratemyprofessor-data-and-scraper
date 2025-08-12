"""
Penn State RateMyProfessor Review Scraper
Scrapes individual professor reviews and course information
"""

import time
import re
import logging
from typing import List, Optional, Dict
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, 
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.firefox.service import Service as FirefoxService

from .config import *
from .models import Professor, Review, Course, JSONLWriter


class ReviewScraper:
    """Scrapes individual reviews from professor pages"""
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.reviews = []
        self.courses = []
        self.driver = None
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('review_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def init_driver(self):
        """Initialize webdriver with options, try Chrome first, then Firefox"""
        try:
            # Try Chrome first
            try:
                chrome_options = webdriver.ChromeOptions()
                for option in CHROME_OPTIONS:
                    chrome_options.add_argument(option)
                    
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
                self.logger.info("Chrome driver initialized for review scraping")
                return
                
            except Exception as chrome_error:
                self.logger.warning(f"Chrome initialization failed: {chrome_error}")
                self.logger.info("Trying Firefox as fallback for review scraping...")
                
                # Try Firefox as fallback
                firefox_options = webdriver.FirefoxOptions()
                for option in CHROME_OPTIONS:
                    if option.startswith('--'):
                        # Convert Chrome options to Firefox format
                        if option == '--headless':
                            firefox_options.add_argument('-headless')
                        elif option == '--no-sandbox':
                            continue  # Firefox doesn't have this option
                        elif option == '--disable-dev-shm-usage':
                            continue  # Firefox doesn't have this option
                        else:
                            firefox_options.add_argument(option)
                
                service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=firefox_options)
                self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
                self.logger.info("Firefox driver initialized for review scraping")
                return
            
        except Exception as e:
            self.logger.error(f"Failed to initialize any webdriver: {e}")
            raise
            
    def close_driver(self):
        """Close the webdriver"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Chrome driver closed")
            
    def scrape_professor_reviews(self, professor: Professor, max_reviews: Optional[int] = None) -> List[Review]:
        """Scrape all reviews for a specific professor"""
        if not professor.url:
            self.logger.warning(f"No URL available for professor {professor.name}")
            return []
            
        try:
            self.logger.info(f"Scraping reviews for {professor.name}")
            self.driver.get(professor.url)
            
            # Wait for page to load
            time.sleep(3)
            
            reviews = []
            
            # Try to load more reviews by clicking "Load More" buttons
            self.load_all_reviews()
            
            # Find all review elements
            review_elements = self.find_review_elements()
            
            for i, review_element in enumerate(review_elements):
                if max_reviews and i >= max_reviews:
                    break
                    
                try:
                    review = self.extract_review_data(review_element, professor)
                    if review:
                        reviews.append(review)
                        
                except Exception as e:
                    self.logger.debug(f"Error extracting review {i+1}: {e}")
                    continue
                    
            self.logger.info(f"Scraped {len(reviews)} reviews for {professor.name}")
            return reviews
            
        except Exception as e:
            self.logger.error(f"Error scraping reviews for {professor.name}: {e}")
            return []
            
    def load_all_reviews(self):
        """Click 'Load More' buttons to load all available reviews"""
        max_attempts = 10  # Prevent infinite loops
        attempts = 0
        
        while attempts < max_attempts:
            try:
                # Look for "Load More" or "Show More" button
                load_more_xpath = "//button[contains(text(), 'Load More') or contains(text(), 'Show More')]"
                load_more_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, load_more_xpath))
                )
                
                # Scroll to button and click
                self.driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", load_more_button)
                
                # Wait for new content to load
                time.sleep(2)
                attempts += 1
                
            except (TimeoutException, NoSuchElementException):
                # No more "Load More" buttons found
                break
            except Exception as e:
                self.logger.debug(f"Error loading more reviews: {e}")
                break
                
    def find_review_elements(self) -> List:
        """Find all review elements on the page"""
        # Common selectors for review cards
        review_selectors = [
            "//div[contains(@class, 'Rating__RatingBody')]",
            "//div[contains(@class, 'review')]",
            "//div[contains(@class, 'Comment')]",
            "//div[contains(@data-testid, 'review')]"
        ]
        
        for selector in review_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements:
                    self.logger.info(f"Found {len(elements)} review elements using selector: {selector}")
                    return elements
            except Exception as e:
                continue
                
        # Fallback: try to find any div that might contain review data
        try:
            elements = self.driver.find_elements(By.XPATH, "//div[contains(text(), 'For Credit') or contains(text(), 'Attendance') or contains(text(), 'Textbook')]")
            if elements:
                self.logger.info(f"Found {len(elements)} review elements using fallback selector")
                return elements
        except Exception:
            pass
            
        self.logger.warning("No review elements found")
        return []
        
    def extract_review_data(self, review_element, professor: Professor) -> Optional[Review]:
        """Extract review data from a review element"""
        try:
            review_text = review_element.text.strip()
            if not review_text:
                return None
                
            # Initialize review object
            review = Review(
                professor_id=professor.professor_id or "",
                professor_name=professor.name
            )
            
            # Extract course information
            course_match = re.search(r'([A-Z]+\s*\d+[A-Z]*)', review_text)
            if course_match:
                review.course = course_match.group(1)
                
            # Extract rating (look for patterns like "5.0" or "Quality 4.0")
            rating_match = re.search(r'(?:Quality|Rating)?\s*(\d+\.?\d*)\s*(?:/5)?', review_text)
            if rating_match:
                try:
                    review.rating = float(rating_match.group(1))
                except ValueError:
                    pass
                    
            # Extract difficulty
            difficulty_match = re.search(r'(?:Difficulty|Level of Difficulty)\s*(\d+\.?\d*)', review_text)
            if difficulty_match:
                try:
                    review.difficulty = float(difficulty_match.group(1))
                except ValueError:
                    pass
                    
            # Extract would take again
            if 'Yes' in review_text and 'Would Take Again' in review_text:
                review.would_take_again = True
            elif 'No' in review_text and 'Would Take Again' in review_text:
                review.would_take_again = False
                
            # Extract for credit
            if 'Yes' in review_text and 'For Credit' in review_text:
                review.for_credit = True
            elif 'No' in review_text and 'For Credit' in review_text:
                review.for_credit = False
                
            # Extract attendance
            if 'Mandatory' in review_text and 'Attendance' in review_text:
                review.attendance = 'Mandatory'
            elif 'Not Mandatory' in review_text and 'Attendance' in review_text:
                review.attendance = 'Not Mandatory'
                
            # Extract grade
            grade_match = re.search(r'Grade Received\s*([A-F][+-]?)', review_text)
            if grade_match:
                review.grade = grade_match.group(1)
                
            # Extract textbook usage
            if 'Yes' in review_text and 'Textbook' in review_text:
                review.textbook = True
            elif 'No' in review_text and 'Textbook' in review_text:
                review.textbook = False
                
            # Extract review text (try to find the main comment)
            lines = review_text.split('\n')
            for line in lines:
                # Look for lines that seem like comments (longer text, not just labels)
                if (len(line) > 20 and 
                    not any(keyword in line for keyword in ['Quality', 'Difficulty', 'Would Take Again', 'For Credit', 'Attendance', 'Textbook', 'Grade']) and
                    not re.match(r'^\d+\.?\d*$', line.strip())):
                    review.review_text = line.strip()
                    break
                    
            # Extract date
            date_match = re.search(r'(\w+ \d{1,2}, \d{4})', review_text)
            if date_match:
                review.date = date_match.group(1)
                
            # Extract thumbs up/down
            thumbs_up_match = re.search(r'(\d+)\s*👍', review_text)
            if thumbs_up_match:
                review.thumbs_up = int(thumbs_up_match.group(1))
                
            thumbs_down_match = re.search(r'(\d+)\s*👎', review_text)
            if thumbs_down_match:
                review.thumbs_down = int(thumbs_down_match.group(1))
                
            return review
            
        except Exception as e:
            self.logger.debug(f"Error extracting review data: {e}")
            return None
            
    def scrape_reviews_for_professors(self, professors: List[Professor], max_reviews_per_prof: Optional[int] = None) -> List[Review]:
        """Scrape reviews for a list of professors"""
        try:
            self.init_driver()
            all_reviews = []
            
            for i, professor in enumerate(professors):
                if self.test_mode and i >= 3:  # Limit to 3 professors in test mode
                    break
                    
                try:
                    reviews = self.scrape_professor_reviews(professor, max_reviews_per_prof)
                    all_reviews.extend(reviews)
                    self.reviews.extend(reviews)
                    
                    # Extract course information from reviews
                    self.extract_courses_from_reviews(reviews, professor)
                    
                    # Wait between professor pages
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    self.logger.error(f"Error scraping reviews for {professor.name}: {e}")
                    continue
                    
            self.logger.info(f"Total reviews scraped: {len(all_reviews)}")
            return all_reviews
            
        except Exception as e:
            self.logger.error(f"Error during review scraping: {e}")
            raise
        finally:
            self.close_driver()
            
    def extract_courses_from_reviews(self, reviews: List[Review], professor: Professor):
        """Extract unique course information from reviews"""
        course_stats = {}
        
        for review in reviews:
            if review.course:
                course_key = f"{review.course}_{professor.professor_id}"
                
                if course_key not in course_stats:
                    course_stats[course_key] = {
                        'course_code': review.course,
                        'professor_id': professor.professor_id or "",
                        'professor_name': professor.name,
                        'department': professor.department,
                        'ratings': [],
                        'difficulties': []
                    }
                    
                if review.rating:
                    course_stats[course_key]['ratings'].append(review.rating)
                if review.difficulty:
                    course_stats[course_key]['difficulties'].append(review.difficulty)
                    
        # Create Course objects
        for course_data in course_stats.values():
            ratings = course_data['ratings']
            difficulties = course_data['difficulties']
            
            course = Course(
                course_code=course_data['course_code'],
                professor_id=course_data['professor_id'],
                professor_name=course_data['professor_name'],
                department=course_data['department'],
                avg_rating=sum(ratings) / len(ratings) if ratings else None,
                avg_difficulty=sum(difficulties) / len(difficulties) if difficulties else None,
                num_reviews=len(ratings)
            )
            
            self.courses.append(course)
            
    def save_reviews(self, filename: Optional[str] = None):
        """Save scraped reviews to JSONL file"""
        if not filename:
            filename = REVIEWS_FILE
            
        try:
            JSONLWriter.write_objects(filename, self.reviews)
            self.logger.info(f"Saved {len(self.reviews)} reviews to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving reviews: {e}")
            raise
            
    def save_courses(self, filename: Optional[str] = None):
        """Save extracted courses to JSONL file"""
        if not filename:
            filename = COURSES_FILE
            
        try:
            JSONLWriter.write_objects(filename, self.courses)
            self.logger.info(f"Saved {len(self.courses)} courses to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving courses: {e}")
            raise


def main():
    """Main function for testing the review scraper"""
    # Load some professors to test with
    try:
        professor_data = JSONLWriter.read_objects(PROFESSORS_FILE)
        if not professor_data:
            print("No professor data found. Run professor_scraper.py first.")
            return
            
        # Convert back to Professor objects
        professors = [
            Professor(
                name=p['name'],
                department=p['department'],
                rating=p.get('rating'),
                num_ratings=p.get('num_ratings'),
                would_take_again_pct=p.get('would_take_again_pct'),
                level_of_difficulty=p.get('level_of_difficulty'),
                url=p.get('url'),
                professor_id=p.get('professor_id')
            )
            for p in professor_data[:3]  # Test with first 3 professors
        ]
        
        scraper = ReviewScraper(test_mode=True)
        reviews = scraper.scrape_reviews_for_professors(professors, max_reviews_per_prof=5)
        
        scraper.save_reviews()
        scraper.save_courses()
        
        print(f"\nReview Scraping Results:")
        print(f"Total reviews scraped: {len(reviews)}")
        print(f"Total courses identified: {len(scraper.courses)}")
        
        if reviews:
            print(f"\nSample review data:")
            for i, review in enumerate(reviews[:2]):
                print(f"{i+1}. {review.professor_name} - {review.course or 'Unknown Course'}")
                print(f"   Rating: {review.rating}, Difficulty: {review.difficulty}")
                print(f"   Would take again: {review.would_take_again}")
                print(f"   Review: {review.review_text[:100] if review.review_text else 'No text'}...")
                print()
                
    except Exception as e:
        print(f"Error during review scraping: {e}")


if __name__ == "__main__":
    main()
