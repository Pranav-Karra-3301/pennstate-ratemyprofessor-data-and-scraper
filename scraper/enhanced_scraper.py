"""
Enhanced Penn State RateMyProfessor Scraper
Fetches comprehensive professor data including courses, tags, and detailed ratings
"""

import requests
import json
import re
import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict, field
from bs4 import BeautifulSoup

from .config import *
from .models import JSONLWriter


@dataclass
class EnhancedProfessor:
    """Enhanced professor model with comprehensive data"""
    # Basic info
    id: str
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
    courses: List[Dict[str, Any]] = field(default_factory=list)
    rating_distribution: Dict[str, int] = field(default_factory=dict)
    
    # URLs
    profile_url: Optional[str] = None
    legacy_id: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON string for JSONL format"""
        return json.dumps(asdict(self))


class EnhancedProfessorScraper:
    """Enhanced scraper using RMP's GraphQL API"""
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.professors = []
        self.session = requests.Session()
        self.setup_logging()
        self.setup_session()
        
        # GraphQL endpoint
        self.graphql_url = "https://www.ratemyprofessors.com/graphql"
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('enhanced_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_session(self):
        """Setup requests session with headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json',
            'Origin': 'https://www.ratemyprofessors.com',
            'Referer': 'https://www.ratemyprofessors.com/',
        })
        
    def get_professor_list_query(self, offset: int = 0, limit: int = 20) -> str:
        """GraphQL query to get professor list"""
        return {
            "query": """
                query TeacherSearchResultsPageQuery($query: TeacherSearchQuery!) {
                    search: newSearch {
                        teachers(query: $query) {
                            edges {
                                node {
                                    id
                                    legacyId
                                    firstName
                                    lastName
                                    department
                                    school {
                                        name
                                        id
                                    }
                                    avgRating
                                    numRatings
                                    avgDifficulty
                                    wouldTakeAgainPercent
                                    teacherRatingTags {
                                        tagName
                                        tagCount
                                    }
                                    courseCodes {
                                        courseName
                                        courseCount
                                    }
                                }
                            }
                            pageInfo {
                                hasNextPage
                                endCursor
                            }
                            resultCount
                        }
                    }
                }
            """,
            "variables": {
                "query": {
                    "text": "",
                    "schoolID": "U2Nob29sLTc1OA==",  # Base64 encoded School-758
                    "fallback": True,
                    "offset": offset,
                    "limit": limit
                }
            }
        }
        
    def get_professor_detail_query(self, professor_id: str) -> str:
        """GraphQL query to get detailed professor information"""
        return {
            "query": """
                query TeacherRatingsPageQuery($id: ID!) {
                    node(id: $id) {
                        ... on Teacher {
                            id
                            legacyId
                            firstName
                            lastName
                            department
                            school {
                                name
                                id
                            }
                            avgRating
                            numRatings
                            avgDifficulty
                            wouldTakeAgainPercent
                            teacherRatingTags {
                                tagName
                                tagCount
                            }
                            courseCodes {
                                courseName
                                courseCount
                            }
                            ratingsDistribution {
                                r1
                                r2
                                r3
                                r4
                                r5
                            }
                            relatedTeachers {
                                id
                                firstName
                                lastName
                                avgRating
                            }
                        }
                    }
                }
            """,
            "variables": {
                "id": professor_id
            }
        }
        
    def fetch_professors_batch(self, offset: int = 0, limit: int = 20) -> Dict:
        """Fetch a batch of professors using GraphQL"""
        try:
            query = self.get_professor_list_query(offset, limit)
            
            self.logger.info(f"Fetching professors: offset={offset}, limit={limit}")
            
            response = self.session.post(
                self.graphql_url,
                json=query,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'errors' in data:
                    self.logger.error(f"GraphQL errors: {data['errors']}")
                    return None
                return data
            else:
                self.logger.error(f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching professors batch: {e}")
            return None
            
    def fetch_professor_details(self, professor_id: str) -> Dict:
        """Fetch detailed information for a specific professor"""
        try:
            query = self.get_professor_detail_query(professor_id)
            
            response = self.session.post(
                self.graphql_url,
                json=query,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'errors' in data:
                    self.logger.error(f"GraphQL errors for professor {professor_id}: {data['errors']}")
                    return None
                return data
            else:
                self.logger.error(f"HTTP {response.status_code} for professor {professor_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching professor {professor_id}: {e}")
            return None
            
    def parse_professor_node(self, node: Dict) -> Optional[EnhancedProfessor]:
        """Parse professor data from GraphQL node"""
        try:
            # Extract tags
            tags = []
            if node.get('teacherRatingTags'):
                tags = [tag['tagName'] for tag in node['teacherRatingTags'] if tag.get('tagName')]
                
            # Extract courses
            courses = []
            if node.get('courseCodes'):
                courses = [
                    {
                        'name': course['courseName'],
                        'count': course.get('courseCount', 0)
                    }
                    for course in node['courseCodes']
                    if course.get('courseName')
                ]
                
            # Extract rating distribution if available
            rating_dist = {}
            if node.get('ratingsDistribution'):
                dist = node['ratingsDistribution']
                rating_dist = {
                    '1_star': dist.get('r1', 0),
                    '2_star': dist.get('r2', 0),
                    '3_star': dist.get('r3', 0),
                    '4_star': dist.get('r4', 0),
                    '5_star': dist.get('r5', 0)
                }
                
            # Construct full name from first and last name
            first_name = node.get('firstName', '')
            last_name = node.get('lastName', '')
            full_name = f"{first_name} {last_name}".strip()
                
            professor = EnhancedProfessor(
                id=node['id'],
                legacy_id=str(node.get('legacyId', '')),
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                department=node.get('department', 'Unknown'),
                overall_rating=node.get('avgRating'),
                num_ratings=node.get('numRatings', 0),
                would_take_again_percent=node.get('wouldTakeAgainPercent'),
                level_of_difficulty=node.get('avgDifficulty'),
                tags=tags,
                courses=courses,
                rating_distribution=rating_dist,
                profile_url=f"https://www.ratemyprofessors.com/professor/{node.get('legacyId')}"
            )
            
            return professor
            
        except Exception as e:
            self.logger.error(f"Error parsing professor node: {e}")
            return None
            
    def scrape_all_professors(self, max_professors: Optional[int] = None) -> List[EnhancedProfessor]:
        """Scrape all professors with pagination"""
        self.logger.info(f"Starting to scrape Penn State professors (max: {max_professors or 'all'})")
        
        all_professors = []
        offset = 0
        batch_size = 50  # Fetch 50 at a time for efficiency
        consecutive_empty = 0
        
        while True:
            # Check if we've reached the max
            if max_professors and len(all_professors) >= max_professors:
                all_professors = all_professors[:max_professors]
                self.logger.info(f"Reached max professors limit: {max_professors}")
                break
                
            # Fetch batch
            data = self.fetch_professors_batch(offset, batch_size)
            
            if not data:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    self.logger.warning("Failed to fetch data 3 times, stopping")
                    break
                time.sleep(REQUEST_DELAY * 2)
                continue
                
            # Parse professors from response
            try:
                edges = data['data']['search']['teachers']['edges']
                page_info = data['data']['search']['teachers']['pageInfo']
                result_count = data['data']['search']['teachers'].get('resultCount', 0)
                
                if not edges:
                    self.logger.info("No more professors found")
                    break
                    
                # Process each professor
                batch_professors = []
                for edge in edges:
                    professor = self.parse_professor_node(edge['node'])
                    if professor:
                        batch_professors.append(professor)
                        
                all_professors.extend(batch_professors)
                self.logger.info(f"Scraped {len(batch_professors)} professors (total: {len(all_professors)} of {result_count})")
                
                # Check if there are more pages
                if not page_info.get('hasNextPage', False):
                    self.logger.info("No more pages available")
                    break
                    
                # Update offset
                offset += batch_size
                consecutive_empty = 0
                
                # Rate limiting
                time.sleep(REQUEST_DELAY)
                
                # Test mode limit
                if self.test_mode and len(all_professors) >= 10:
                    self.logger.info("Test mode: stopping at 10 professors")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error processing batch: {e}")
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break
                    
        self.logger.info(f"Total professors scraped: {len(all_professors)}")
        return all_professors
        
    def enhance_with_details(self, professors: List[EnhancedProfessor], sample_size: int = 5) -> List[EnhancedProfessor]:
        """Enhance a sample of professors with detailed information"""
        self.logger.info(f"Enhancing {min(sample_size, len(professors))} professors with detailed info...")
        
        for i, professor in enumerate(professors[:sample_size]):
            try:
                self.logger.info(f"Fetching details for {professor.full_name}")
                
                data = self.fetch_professor_details(professor.id)
                if data and 'data' in data and 'node' in data['data']:
                    enhanced = self.parse_professor_node(data['data']['node'])
                    if enhanced:
                        # Update the professor with enhanced data
                        professor.rating_distribution = enhanced.rating_distribution
                        if enhanced.tags:
                            professor.tags = enhanced.tags
                        if enhanced.courses:
                            professor.courses = enhanced.courses
                            
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                self.logger.error(f"Error enhancing professor {professor.full_name}: {e}")
                continue
                
        return professors
        
    def save_professors(self, professors: List[EnhancedProfessor], filename: Optional[str] = None):
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
    """Main function for testing the enhanced scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Penn State RMP Scraper")
    parser.add_argument("--test", action="store_true", help="Run in test mode (10 professors)")
    parser.add_argument("--max", type=int, help="Maximum number of professors to scrape")
    parser.add_argument("--enhance", type=int, default=0, help="Number of professors to enhance with details")
    
    args = parser.parse_args()
    
    scraper = EnhancedProfessorScraper(test_mode=args.test)
    
    try:
        # Scrape professors
        professors = scraper.scrape_all_professors(max_professors=args.max)
        
        # Optionally enhance some with details
        if args.enhance > 0:
            professors = scraper.enhance_with_details(professors, args.enhance)
            
        # Save results
        scraper.save_professors(professors)
        
        # Print summary
        print(f"\nEnhanced Scraping Results:")
        print(f"Total professors scraped: {len(professors)}")
        
        if professors:
            print(f"\nSample professor data:")
            for i, prof in enumerate(professors[:5]):
                print(f"\n{i+1}. {prof.full_name} ({prof.department})")
                print(f"   ID: {prof.legacy_id}")
                print(f"   Rating: {prof.overall_rating}/5.0, Reviews: {prof.num_ratings}")
                print(f"   Would take again: {prof.would_take_again_percent}%")
                print(f"   Difficulty: {prof.level_of_difficulty}/5.0")
                
                if prof.tags:
                    print(f"   Tags: {', '.join(prof.tags[:5])}")
                    
                if prof.courses:
                    courses_str = ', '.join([f"{c['name']} ({c['count']})" for c in prof.courses[:3]])
                    print(f"   Courses: {courses_str}")
                    
                if prof.rating_distribution:
                    print(f"   Rating distribution: {prof.rating_distribution}")
                    
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()