"""
API-based Penn State RateMyProfessor Scraper
Uses the actual RMP API endpoints for reliable data extraction
"""

import requests
import json
import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict, field

from .config import *
from .models import JSONLWriter


@dataclass  
class APIProfessor:
    """Professor data from API"""
    id: str
    legacy_id: int
    first_name: str
    last_name: str
    full_name: str
    department: str
    school: str = "Penn State University"
    school_id: str = "758"
    
    # Ratings
    overall_rating: Optional[float] = None
    num_ratings: Optional[int] = None
    would_take_again_percent: Optional[float] = None
    level_of_difficulty: Optional[float] = None
    
    # Additional details
    tags: List[str] = field(default_factory=list)
    courses: List[str] = field(default_factory=list)
    
    # URLs
    profile_url: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON string for JSONL format"""
        return json.dumps(asdict(self))


class APIProfessorScraper:
    """Scraper using RMP's actual API endpoints"""
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.professors = []
        self.session = requests.Session()
        self.setup_logging()
        self.setup_session()
        
        # API endpoints
        self.graphql_url = "https://www.ratemyprofessors.com/graphql"
        self.school_id_encoded = "U2Nob29sLTc1OA=="  # Base64 encoded School-758
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('api_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_session(self):
        """Setup requests session with headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Origin': 'https://www.ratemyprofessors.com',
            'Referer': 'https://www.ratemyprofessors.com/search/professors/758',
        })
        
    def search_professors(self, search_text: str = "", cursor: Optional[str] = None) -> Dict:
        """Search for professors using the API"""
        query = """
            query NewSearchTeachersQuery($text: String!, $schoolID: ID!, $after: String) {
                newSearch {
                    teachers(query: {text: $text, schoolID: $schoolID}, first: 100, after: $after) {
                        edges {
                            cursor
                            node {
                                id
                                legacyId
                                firstName
                                lastName
                                department
                                avgRating
                                numRatings
                                avgDifficulty
                                wouldTakeAgainPercent
                            }
                        }
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                    }
                }
            }
        """
        
        variables = {
            "text": search_text,
            "schoolID": self.school_id_encoded,
            "after": cursor
        }
        
        try:
            response = self.session.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'errors' in data:
                    self.logger.error(f"GraphQL errors: {data['errors']}")
                    return None
                return data
            else:
                self.logger.error(f"HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error searching professors: {e}")
            return None
            
    def get_professor_details(self, legacy_id: int) -> Dict:
        """Get detailed information for a specific professor"""
        query = """
            query TeacherRatingsPageQuery($id: ID!) {
                node(id: $id) {
                    ... on Teacher {
                        id
                        legacyId
                        firstName
                        lastName
                        department
                        avgRating
                        numRatings
                        avgDifficulty
                        wouldTakeAgainPercent
                        teacherRatingTags {
                            tagName
                        }
                        courseCodes {
                            courseName
                        }
                    }
                }
            }
        """
        
        # Convert legacy ID to GraphQL ID format
        graphql_id = f"VGVhY2hlci0{legacy_id}"  # Teacher-{id} in base64
        
        variables = {"id": graphql_id}
        
        try:
            response = self.session.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting professor details: {e}")
            return None
            
    def parse_professor(self, node: Dict) -> Optional[APIProfessor]:
        """Parse professor data from API response"""
        try:
            first_name = node.get('firstName', '')
            last_name = node.get('lastName', '')
            full_name = f"{first_name} {last_name}".strip()
            
            professor = APIProfessor(
                id=node['id'],
                legacy_id=node.get('legacyId', 0),
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                department=node.get('department', 'Unknown'),
                overall_rating=node.get('avgRating'),
                num_ratings=node.get('numRatings', 0),
                would_take_again_percent=node.get('wouldTakeAgainPercent'),
                level_of_difficulty=node.get('avgDifficulty'),
                profile_url=f"https://www.ratemyprofessors.com/professor/{node.get('legacyId')}"
            )
            
            # Add tags if available
            if 'teacherRatingTags' in node:
                professor.tags = [tag['tagName'] for tag in node['teacherRatingTags']]
                
            # Add courses if available
            if 'courseCodes' in node:
                professor.courses = [course['courseName'] for course in node['courseCodes']]
                
            return professor
            
        except Exception as e:
            self.logger.error(f"Error parsing professor: {e}")
            return None
            
    def scrape_all_professors(self, max_professors: Optional[int] = None) -> List[APIProfessor]:
        """Scrape all professors using pagination"""
        self.logger.info(f"Starting to scrape Penn State professors (max: {max_professors or 'all'})")
        
        all_professors = []
        search_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        # Try searching by each letter to get more results
        for letter in search_letters:
            if max_professors and len(all_professors) >= max_professors:
                break
                
            self.logger.info(f"Searching for professors starting with '{letter}'")
            cursor = None
            consecutive_empty = 0
            
            while True:
                if max_professors and len(all_professors) >= max_professors:
                    break
                    
                # Search for professors
                data = self.search_professors(search_text=letter, cursor=cursor)
                
                if not data:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        break
                    time.sleep(REQUEST_DELAY)
                    continue
                    
                try:
                    teachers = data['data']['newSearch']['teachers']
                    edges = teachers.get('edges', [])
                    page_info = teachers.get('pageInfo', {})
                    
                    if not edges:
                        self.logger.info(f"No professors found for '{letter}'")
                        break
                        
                    # Process professors
                    new_professors = []
                    for edge in edges:
                        professor = self.parse_professor(edge['node'])
                        if professor:
                            # Check for duplicates
                            if not any(p.legacy_id == professor.legacy_id for p in all_professors):
                                new_professors.append(professor)
                                
                    all_professors.extend(new_professors)
                    self.logger.info(f"Found {len(new_professors)} new professors (total: {len(all_professors)})")
                    
                    # Check for next page
                    if page_info.get('hasNextPage'):
                        cursor = page_info.get('endCursor')
                        time.sleep(REQUEST_DELAY)
                    else:
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error processing search results: {e}")
                    break
                    
            # Small delay between letters
            time.sleep(REQUEST_DELAY)
            
            # Test mode limit
            if self.test_mode and len(all_professors) >= 10:
                break
                
        # If we didn't get enough professors with letter search, try blank search
        if len(all_professors) < (max_professors or 100):
            self.logger.info("Trying blank search for additional professors")
            data = self.search_professors(search_text="")
            
            if data:
                try:
                    edges = data['data']['newSearch']['teachers'].get('edges', [])
                    for edge in edges:
                        professor = self.parse_professor(edge['node'])
                        if professor and not any(p.legacy_id == professor.legacy_id for p in all_professors):
                            all_professors.append(professor)
                            if max_professors and len(all_professors) >= max_professors:
                                break
                except Exception as e:
                    self.logger.error(f"Error processing blank search: {e}")
                    
        # Trim to max if needed
        if max_professors and len(all_professors) > max_professors:
            all_professors = all_professors[:max_professors]
            
        self.logger.info(f"Total professors scraped: {len(all_professors)}")
        return all_professors
        
    def enhance_with_details(self, professors: List[APIProfessor], sample_size: int = 5) -> List[APIProfessor]:
        """Enhance professors with detailed information including tags and courses"""
        self.logger.info(f"Enhancing {min(sample_size, len(professors))} professors with details...")
        
        for i, professor in enumerate(professors[:sample_size]):
            try:
                self.logger.info(f"Fetching details for {professor.full_name}")
                
                data = self.get_professor_details(professor.legacy_id)
                if data and 'data' in data and 'node' in data['data']:
                    node = data['data']['node']
                    if node:
                        # Update tags
                        if 'teacherRatingTags' in node:
                            professor.tags = [tag['tagName'] for tag in node['teacherRatingTags']]
                            
                        # Update courses
                        if 'courseCodes' in node:
                            professor.courses = [course['courseName'] for course in node['courseCodes']]
                            
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                self.logger.error(f"Error enhancing professor {professor.full_name}: {e}")
                continue
                
        return professors
        
    def save_professors(self, professors: List[APIProfessor], filename: Optional[str] = None):
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
    """Main function for testing the API scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description="API-based Penn State RMP Scraper")
    parser.add_argument("--test", action="store_true", help="Run in test mode (10 professors)")
    parser.add_argument("--max", type=int, help="Maximum number of professors to scrape")
    parser.add_argument("--enhance", type=int, default=0, help="Number of professors to enhance with details")
    
    args = parser.parse_args()
    
    scraper = APIProfessorScraper(test_mode=args.test)
    
    try:
        # Scrape professors
        professors = scraper.scrape_all_professors(max_professors=args.max)
        
        # Optionally enhance some with details
        if args.enhance > 0:
            professors = scraper.enhance_with_details(professors, args.enhance)
            
        # Save results
        scraper.save_professors(professors)
        
        # Print summary
        print(f"\nAPI Scraping Results:")
        print(f"Total professors scraped: {len(professors)}")
        
        if professors:
            print(f"\nSample professor data:")
            for i, prof in enumerate(professors[:5]):
                print(f"\n{i+1}. {prof.full_name} ({prof.department})")
                print(f"   Legacy ID: {prof.legacy_id}")
                print(f"   Rating: {prof.overall_rating}/5.0, Reviews: {prof.num_ratings}")
                print(f"   Would take again: {prof.would_take_again_percent}%")
                print(f"   Difficulty: {prof.level_of_difficulty}/5.0")
                
                if prof.tags:
                    print(f"   Tags: {', '.join(prof.tags[:5])}")
                    
                if prof.courses:
                    print(f"   Courses: {', '.join(prof.courses[:5])}")
                    
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()