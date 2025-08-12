"""
Penn State RateMyProfessor Professor Scraper
Scrapes basic professor information from the professors listing page
"""

import time
import logging
import re
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, 
    StaleElementReferenceException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.firefox.service import Service as FirefoxService

from .config import *
from .models import Professor, JSONLWriter


class ProfessorScraper:
    """Scrapes professor data from Penn State RateMyProfessors page"""
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.professors = []
        self.driver = None
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log'),
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
                    
                # Use webdriver-manager to handle ChromeDriver
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
                self.logger.info("Chrome driver initialized successfully")
                return
                
            except Exception as chrome_error:
                self.logger.warning(f"Chrome initialization failed: {chrome_error}")
                self.logger.info("Trying Firefox as fallback...")
                
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
                self.logger.info("Firefox driver initialized successfully")
                return
            
        except Exception as e:
            self.logger.error(f"Failed to initialize any webdriver: {e}")
            raise
            
    def close_driver(self):
        """Close the webdriver"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Chrome driver closed")
            
    def get_total_professors_count(self) -> int:
        """Extract total number of professors from the search results header"""
        try:
            # Look for the header with professor count
            header_xpath = "//h1[contains(text(), 'professors at')]"
            header_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, header_xpath))
            )
            header_text = header_element.text
            
            # Extract number from text like "7703 professors at Penn State University"
            match = re.search(r'(\d+)\s+professors', header_text)
            if match:
                count = int(match.group(1))
                self.logger.info(f"Found {count} professors total")
                return count
            else:
                self.logger.warning("Could not parse professor count from header")
                return 0
                
        except TimeoutException:
            self.logger.warning("Could not find professor count header")
            return 0
            
    def wait_for_professors_to_load(self):
        """Wait for professor cards to load on the page"""
        try:
            # Wait for at least one professor card to be present
            professor_xpath = "//a[contains(@href, '/professor/')]"
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, professor_xpath))
            )
            time.sleep(2)  # Additional wait for dynamic content
            
        except TimeoutException:
            self.logger.warning("Timeout waiting for professors to load")
            
    def extract_professor_data(self, professor_element) -> Optional[Professor]:
        """Extract professor data from a professor card element"""
        try:
            # Get professor URL and ID
            url = professor_element.get_attribute('href')
            professor_id = None
            if url:
                match = re.search(r'/professor/(\d+)', url)
                if match:
                    professor_id = match.group(1)
            
            # Extract text content and parse it
            professor_text = professor_element.text.strip()
            if not professor_text:
                return None
                
            lines = [line.strip() for line in professor_text.split('\n') if line.strip()]
            
            if len(lines) < 4:
                self.logger.debug(f"Insufficient data in professor card: {lines}")
                return None
                
            # Parse the professor data based on the card structure
            # Expected format: [QUALITY, rating, number ratings, name, department, school, %, would take again, level, level of difficulty]
            try:
                name = None
                department = None
                rating = None
                num_ratings = None
                would_take_again_pct = None
                level_of_difficulty = None
                
                # Find name (usually appears after QUALITY and rating info)
                for i, line in enumerate(lines):
                    # Name is typically the longest non-numeric line that's not a keyword
                    if (not any(word in line.upper() for word in ['QUALITY', 'RATING', 'WOULD', 'TAKE', 'AGAIN', 'LEVEL', 'DIFFICULTY', 'PENN STATE']) 
                        and not re.match(r'^\d+\.?\d*%?$', line)
                        and len(line) > 3):
                        if name is None:  # Take the first qualifying line as name
                            name = line
                        elif department is None and line != name:  # Next qualifying line as department
                            department = line
                            
                # Extract rating (first decimal number found)
                for line in lines:
                    if re.match(r'^\d+\.?\d*$', line):
                        try:
                            rating = float(line)
                            break
                        except ValueError:
                            continue
                            
                # Extract number of ratings (look for pattern like "284 ratings")
                for line in lines:
                    if 'rating' in line.lower():
                        match = re.search(r'(\d+)', line)
                        if match:
                            num_ratings = int(match.group(1))
                            break
                            
                # Extract would take again percentage
                for line in lines:
                    if '%' in line and 'would' in ' '.join(lines).lower():
                        match = re.search(r'(\d+)%', line)
                        if match:
                            would_take_again_pct = float(match.group(1))
                            break
                            
                # Extract level of difficulty (usually the last decimal number)
                for line in reversed(lines):
                    if re.match(r'^\d+\.?\d*$', line):
                        try:
                            level_of_difficulty = float(line)
                            break
                        except ValueError:
                            continue
                            
                if not name:
                    self.logger.debug(f"Could not extract name from: {lines}")
                    return None
                    
                professor = Professor(
                    name=name,
                    department=department or "Unknown",
                    rating=rating,
                    num_ratings=num_ratings,
                    would_take_again_pct=would_take_again_pct,
                    level_of_difficulty=level_of_difficulty,
                    url=url,
                    professor_id=professor_id
                )
                
                return professor
                
            except Exception as e:
                self.logger.debug(f"Error parsing professor data: {e}, Lines: {lines}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting professor data: {e}")
            return None
            
    def load_more_professors(self) -> bool:
        """Click the 'Show More' button to load additional professors"""
        try:
            # Look for the show more button
            show_more_xpath = "//button[contains(text(), 'Show More') or contains(text(), 'Load More')]"
            show_more_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, show_more_xpath))
            )
            
            # Scroll to button and click
            self.driver.execute_script("arguments[0].scrollIntoView(true);", show_more_button)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", show_more_button)
            
            # Wait for new content to load
            time.sleep(3)
            self.logger.info("Clicked 'Show More' button")
            return True
            
        except (TimeoutException, NoSuchElementException):
            self.logger.info("No 'Show More' button found - reached end of list")
            return False
        except Exception as e:
            self.logger.warning(f"Error clicking 'Show More' button: {e}")
            return False
            
    def scrape_professors(self, max_professors: Optional[int] = None) -> List[Professor]:
        """Main method to scrape professor data"""
        try:
            self.init_driver()
            self.logger.info(f"Starting to scrape Penn State professors from: {PROFESSORS_SEARCH_URL}")
            
            # Navigate to the professors page
            self.driver.get(PROFESSORS_SEARCH_URL)
            self.wait_for_professors_to_load()
            
            # Get total count for tracking progress
            total_count = self.get_total_professors_count()
            
            professors_scraped = 0
            consecutive_no_new_professors = 0
            
            while True:
                # Find all professor card elements
                professor_xpath = "//a[contains(@href, '/professor/')]"
                professor_elements = self.driver.find_elements(By.XPATH, professor_xpath)
                
                self.logger.info(f"Found {len(professor_elements)} professor elements on page")
                
                new_professors_count = 0
                
                # Process each professor element
                for element in professor_elements:
                    try:
                        professor = self.extract_professor_data(element)
                        if professor and professor.name:
                            # Check if we already have this professor (avoid duplicates)
                            if not any(p.name == professor.name and p.department == professor.department 
                                     for p in self.professors):
                                self.professors.append(professor)
                                new_professors_count += 1
                                professors_scraped += 1
                                
                                if professors_scraped % 10 == 0:
                                    self.logger.info(f"Scraped {professors_scraped} professors so far...")
                                    
                                # Stop if we've reached the test limit
                                if self.test_mode and professors_scraped >= BATCH_SIZE:
                                    self.logger.info(f"Test mode: stopping at {professors_scraped} professors")
                                    return self.professors
                                    
                                # Stop if we've reached the specified max
                                if max_professors and professors_scraped >= max_professors:
                                    self.logger.info(f"Reached max professors limit: {max_professors}")
                                    return self.professors
                                    
                    except Exception as e:
                        self.logger.debug(f"Error processing professor element: {e}")
                        continue
                
                self.logger.info(f"Added {new_professors_count} new professors in this batch")
                
                # If no new professors were found, increment counter
                if new_professors_count == 0:
                    consecutive_no_new_professors += 1
                else:
                    consecutive_no_new_professors = 0
                    
                # If we haven't found new professors in multiple attempts, stop
                if consecutive_no_new_professors >= 3:
                    self.logger.info("No new professors found in multiple attempts, stopping")
                    break
                    
                # Try to load more professors
                if not self.load_more_professors():
                    self.logger.info("Cannot load more professors, scraping complete")
                    break
                    
                # Wait between requests
                time.sleep(REQUEST_DELAY)
                
            self.logger.info(f"Scraping complete! Total professors scraped: {len(self.professors)}")
            return self.professors
            
        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
            raise
        finally:
            self.close_driver()
            
    def save_professors(self, filename: Optional[str] = None):
        """Save scraped professors to JSONL file"""
        if not filename:
            filename = PROFESSORS_FILE
            
        try:
            JSONLWriter.write_objects(filename, self.professors)
            self.logger.info(f"Saved {len(self.professors)} professors to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving professors: {e}")
            raise


def main():
    """Main function for testing the professor scraper"""
    scraper = ProfessorScraper(test_mode=True)
    
    try:
        professors = scraper.scrape_professors()
        scraper.save_professors()
        
        print(f"\nScraping Results:")
        print(f"Total professors scraped: {len(professors)}")
        
        if professors:
            print(f"\nSample professor data:")
            for i, prof in enumerate(professors[:3]):
                print(f"{i+1}. {prof.name} - {prof.department}")
                print(f"   Rating: {prof.rating}, Reviews: {prof.num_ratings}")
                print(f"   Would take again: {prof.would_take_again_pct}%")
                print(f"   Difficulty: {prof.level_of_difficulty}")
                print()
                
    except Exception as e:
        print(f"Error during scraping: {e}")
        

if __name__ == "__main__":
    main()
