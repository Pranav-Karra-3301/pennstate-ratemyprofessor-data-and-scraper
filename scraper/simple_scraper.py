"""
Simple Penn State RateMyProfessor Scraper using requests (no Selenium)
Works with server-side rendered content
"""

import requests
import json
import re
import time
import logging
from typing import List, Optional, Dict
from bs4 import BeautifulSoup

from .config import *
from .models import Professor, JSONLWriter


class SimpleProfessorScraper:
    """Scrapes professor data using requests and BeautifulSoup"""
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.professors = []
        self.session = requests.Session()
        self.setup_logging()
        self.setup_session()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('simple_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_session(self):
        """Setup requests session with headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def get_page_content(self, url: str) -> Optional[str]:
        """Get page content with retry logic"""
        for attempt in range(MAX_RETRIES):
            try:
                self.logger.info(f"Fetching: {url} (attempt {attempt + 1})")
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.warning(f"HTTP {response.status_code} for {url}")
                    
            except Exception as e:
                self.logger.error(f"Error fetching {url}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(REQUEST_DELAY * (attempt + 1))
                    
        return None
        
    def extract_professor_cards(self, html_content: str) -> List[Dict]:
        """Extract professor card data from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find professor card links
        professor_links = soup.find_all('a', href=re.compile(r'/professor/\d+'))
        
        professors_data = []
        for link in professor_links:
            try:
                # Extract URL and ID
                url = BASE_RMP_URL + link.get('href')
                professor_id = re.search(r'/professor/(\d+)', link.get('href')).group(1)
                
                # Extract text content from the card
                card_text = link.get_text().strip()
                if not card_text:
                    continue
                    
                # Parse the card text
                professor_data = self.parse_professor_card_text(card_text, url, professor_id)
                if professor_data:
                    professors_data.append(professor_data)
                    
            except Exception as e:
                self.logger.debug(f"Error processing professor card: {e}")
                continue
                
        return professors_data
        
    def parse_professor_card_text(self, card_text: str, url: str, professor_id: str) -> Optional[Dict]:
        """Parse professor card text to extract structured data"""
        try:
            # Split into lines and clean
            lines = [line.strip() for line in card_text.split('\n') if line.strip()]
            
            if len(lines) < 4:
                return None
                
            # Initialize data
            data = {
                'url': url,
                'professor_id': professor_id,
                'name': None,
                'department': None,
                'rating': None,
                'num_ratings': None,
                'would_take_again_pct': None,
                'level_of_difficulty': None
            }
            
            # Look for patterns in the text
            full_text = ' '.join(lines)
            
            # Extract rating (first decimal number)
            rating_match = re.search(r'(\d+\.\d+)', full_text)
            if rating_match:
                try:
                    data['rating'] = float(rating_match.group(1))
                except ValueError:
                    pass
                    
            # Extract number of ratings
            ratings_match = re.search(r'(\d+) ratings?', full_text)
            if ratings_match:
                data['num_ratings'] = int(ratings_match.group(1))
                
            # Extract would take again percentage
            take_again_match = re.search(r'(\d+)% would take again', full_text)
            if take_again_match:
                data['would_take_again_pct'] = float(take_again_match.group(1))
                
            # Extract level of difficulty (look for pattern like "2.6 level of difficulty")
            difficulty_match = re.search(r'(\d+\.\d+) level of difficulty', full_text)
            if difficulty_match:
                data['level_of_difficulty'] = float(difficulty_match.group(1))
                
            # Extract name and department (heuristic approach)
            # Remove known keywords and numbers to find name and department
            cleaned_lines = []
            for line in lines:
                # Skip lines that are clearly not names/departments
                if (not re.match(r'^[\d\.]+$', line) and  # Not just numbers
                    'quality' not in line.lower() and
                    'rating' not in line.lower() and
                    'would take' not in line.lower() and
                    'level of' not in line.lower() and
                    'penn state' not in line.lower() and
                    len(line) > 2):
                    cleaned_lines.append(line)
                    
            # First reasonable line is likely the name
            if cleaned_lines:
                data['name'] = cleaned_lines[0]
                
            # Second reasonable line is likely the department
            if len(cleaned_lines) > 1:
                data['department'] = cleaned_lines[1]
                
            # Fallback: try to extract name from the original lines
            if not data['name']:
                for line in lines:
                    # Look for lines that look like names (2-3 words, title case)
                    if (re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+( [A-Z][a-z]+)?$', line) and
                        len(line) > 5):
                        data['name'] = line
                        break
                        
            if data['name']:
                return data
            else:
                self.logger.debug(f"Could not extract name from card: {lines}")
                return None
                
        except Exception as e:
            self.logger.debug(f"Error parsing professor card: {e}")
            return None
            
    def extract_relay_store_data(self, html_content: str) -> List[Dict]:
        """Try to extract professor data from window.__RELAY_STORE__"""
        try:
            # Look for the RELAY_STORE data
            relay_match = re.search(r'window\.__RELAY_STORE__\s*=\s*({.*?});', html_content, re.DOTALL)
            if not relay_match:
                self.logger.info("No RELAY_STORE found")
                return []
                
            store_data = json.loads(relay_match.group(1))
            professors_data = []
            
            # Navigate the store structure to find teacher data
            for key, value in store_data.items():
                if isinstance(value, dict) and 'teacher' in str(value).lower():
                    # This might contain teacher data
                    if '__typename' in value and 'teacher' in value['__typename'].lower():
                        # Extract relevant data
                        professor_data = {}
                        
                        # Map known fields
                        field_mapping = {
                            'firstName': 'first_name',
                            'lastName': 'last_name', 
                            'department': 'department',
                            'avgRating': 'rating',
                            'numRatings': 'num_ratings',
                            'wouldTakeAgainPercent': 'would_take_again_pct',
                            'avgDifficulty': 'level_of_difficulty'
                        }
                        
                        for rmp_field, our_field in field_mapping.items():
                            if rmp_field in value:
                                professor_data[our_field] = value[rmp_field]
                                
                        if 'first_name' in professor_data and 'last_name' in professor_data:
                            professor_data['name'] = f"{professor_data['first_name']} {professor_data['last_name']}"
                            professors_data.append(professor_data)
                            
            self.logger.info(f"Extracted {len(professors_data)} professors from RELAY_STORE")
            return professors_data
            
        except Exception as e:
            self.logger.debug(f"Error extracting RELAY_STORE data: {e}")
            return []
            
    def scrape_professors_page(self, page_url: str) -> List[Professor]:
        """Scrape a single page of professors"""
        html_content = self.get_page_content(page_url)
        if not html_content:
            return []
            
        professors = []
        
        # Try both methods
        # Method 1: Extract from RELAY_STORE
        relay_data = self.extract_relay_store_data(html_content)
        for data in relay_data:
            professor = Professor(
                name=data.get('name', 'Unknown'),
                department=data.get('department', 'Unknown'),
                rating=data.get('rating'),
                num_ratings=data.get('num_ratings'),
                would_take_again_pct=data.get('would_take_again_pct'),
                level_of_difficulty=data.get('level_of_difficulty'),
                url=data.get('url'),
                professor_id=data.get('professor_id')
            )
            professors.append(professor)
            
        # Method 2: Extract from professor cards
        if not professors:  # Fallback if RELAY_STORE method didn't work
            card_data = self.extract_professor_cards(html_content)
            for data in card_data:
                professor = Professor(
                    name=data.get('name', 'Unknown'),
                    department=data.get('department', 'Unknown'),
                    rating=data.get('rating'),
                    num_ratings=data.get('num_ratings'),
                    would_take_again_pct=data.get('would_take_again_pct'),
                    level_of_difficulty=data.get('level_of_difficulty'),
                    url=data.get('url'),
                    professor_id=data.get('professor_id')
                )
                professors.append(professor)
                
        return professors
        
    def scrape_all_professors(self, max_professors: Optional[int] = None) -> List[Professor]:
        """Scrape all professors from Penn State"""
        self.logger.info(f"Starting to scrape Penn State professors")
        
        # Start with the first page
        base_url = PROFESSORS_SEARCH_URL
        all_professors = []
        
        # Get the first page
        professors = self.scrape_professors_page(base_url)
        all_professors.extend(professors)
        
        self.logger.info(f"Scraped {len(professors)} professors from initial page")
        
        if self.test_mode:
            # In test mode, just return the first batch
            return all_professors[:BATCH_SIZE]
            
        # For now, we'll work with what we can get from the first page
        # RMP likely uses pagination that requires JavaScript or API calls
        # This could be extended to handle pagination if needed
        
        if max_professors:
            all_professors = all_professors[:max_professors]
            
        self.logger.info(f"Total professors scraped: {len(all_professors)}")
        return all_professors
        
    def save_professors(self, professors: List[Professor], filename: Optional[str] = None):
        """Save scraped professors to JSONL file"""
        if not filename:
            filename = PROFESSORS_FILE
            
        try:
            JSONLWriter.write_objects(filename, professors)
            self.logger.info(f"Saved {len(professors)} professors to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving professors: {e}")
            raise


def main():
    """Main function for testing the simple scraper"""
    scraper = SimpleProfessorScraper(test_mode=True)
    
    try:
        professors = scraper.scrape_all_professors()
        scraper.save_professors(professors)
        
        print(f"\nSimple Scraping Results:")
        print(f"Total professors scraped: {len(professors)}")
        
        if professors:
            print(f"\nSample professor data:")
            for i, prof in enumerate(professors[:5]):
                print(f"{i+1}. {prof.name} - {prof.department}")
                print(f"   Rating: {prof.rating}, Reviews: {prof.num_ratings}")
                print(f"   Would take again: {prof.would_take_again_pct}%")
                print(f"   Difficulty: {prof.level_of_difficulty}")
                print(f"   URL: {prof.url}")
                print()
                
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
