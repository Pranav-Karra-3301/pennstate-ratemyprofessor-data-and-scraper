"""
Main Penn State RateMyProfessor Scraper
Coordinates professor and review scraping
"""

import os
import argparse
import logging
from datetime import datetime
from typing import Optional

from .simple_scraper import SimpleProfessorScraper
# Note: Reviews require Selenium, which needs browser installation
# from .review_scraper import ReviewScraper
from .models import JSONLWriter
from .config import OUTPUT_DIR


def setup_output_directory():
    """Create output directory if it doesn't exist"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")


def run_full_scrape(test_mode: bool = False, max_professors: Optional[int] = None, 
                   max_reviews_per_prof: Optional[int] = None, skip_reviews: bool = False):
    """Run the complete scraping process"""
    
    setup_output_directory()
    
    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"scraper_run_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    logger.info("=== Penn State RateMyProfessor Scraper Started ===")
    logger.info(f"Test mode: {test_mode}")
    logger.info(f"Max professors: {max_professors}")
    logger.info(f"Max reviews per professor: {max_reviews_per_prof}")
    logger.info(f"Skip reviews: {skip_reviews}")
    
    try:
        # Step 1: Scrape professors
        logger.info("Step 1: Scraping professor information...")
        prof_scraper = SimpleProfessorScraper(test_mode=test_mode)
        professors = prof_scraper.scrape_all_professors(max_professors=max_professors)
        prof_scraper.save_professors(professors)
        
        logger.info(f"Successfully scraped {len(professors)} professors")
        
        if not skip_reviews and professors:
            # Step 2: Scrape reviews (requires browser installation)
            logger.warning("Review scraping requires Chrome or Firefox browser installation.")
            logger.warning("Skipping review scraping for now. Use --skip-reviews to avoid this message.")
            skip_reviews = True
            # TODO: Implement browser-free review scraping or provide browser setup instructions
        
        # Summary
        logger.info("=== Scraping Complete ===")
        logger.info(f"Professors: {len(professors)}")
        
        if not skip_reviews:
            review_count = len(JSONLWriter.read_objects(f"{OUTPUT_DIR}/penn_state_reviews.jsonl"))
            course_count = len(JSONLWriter.read_objects(f"{OUTPUT_DIR}/penn_state_courses.jsonl"))
            logger.info(f"Reviews: {review_count}")
            logger.info(f"Courses: {course_count}")
        
        # Print sample data
        print("\n" + "="*50)
        print("SCRAPING RESULTS SUMMARY")
        print("="*50)
        print(f"Professors scraped: {len(professors)}")
        
        if professors:
            print(f"\nSample professors:")
            for i, prof in enumerate(professors[:5]):
                print(f"  {i+1}. {prof.name} ({prof.department})")
                print(f"     Rating: {prof.rating}, Reviews: {prof.num_ratings}")
        
        if not skip_reviews:
            reviews_data = JSONLWriter.read_objects(f"{OUTPUT_DIR}/penn_state_reviews.jsonl")
            print(f"\nReviews scraped: {len(reviews_data)}")
            
            courses_data = JSONLWriter.read_objects(f"{OUTPUT_DIR}/penn_state_courses.jsonl")
            print(f"Courses identified: {len(courses_data)}")
            
        print("\nOutput files created:")
        print(f"  - {OUTPUT_DIR}/penn_state_professors.jsonl")
        if not skip_reviews:
            print(f"  - {OUTPUT_DIR}/penn_state_reviews.jsonl")
            print(f"  - {OUTPUT_DIR}/penn_state_courses.jsonl")
        
        print(f"\nLog file: {log_filename}")
        print("="*50)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        print(f"\nError during scraping: {e}")
        return False


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Penn State RateMyProfessor Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test mode - scrape 10 professors only
  python -m scraper.main_scraper --test
  
  # Scrape first 100 professors with up to 10 reviews each
  python -m scraper.main_scraper --max-professors 100 --max-reviews 10
  
  # Scrape professors only (no reviews)
  python -m scraper.main_scraper --skip-reviews
  
  # Full scrape (WARNING: This will take a very long time!)
  python -m scraper.main_scraper --full
        """
    )
    
    parser.add_argument(
        "--test", 
        action="store_true",
        help="Run in test mode (scrape only 10 professors with 5 reviews each)"
    )
    
    parser.add_argument(
        "--full",
        action="store_true", 
        help="Run full scrape of all professors (WARNING: Takes many hours!)"
    )
    
    parser.add_argument(
        "--max-professors",
        type=int,
        help="Maximum number of professors to scrape"
    )
    
    parser.add_argument(
        "--max-reviews",
        type=int,
        help="Maximum number of reviews to scrape per professor"
    )
    
    parser.add_argument(
        "--skip-reviews",
        action="store_true",
        help="Skip review scraping, only scrape professor basic info"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.test and args.full:
        print("Error: Cannot use both --test and --full flags")
        return
        
    if args.test:
        max_professors = 10
        max_reviews_per_prof = 5
        test_mode = True
        skip_reviews = False
    elif args.full:
        max_professors = None
        max_reviews_per_prof = None
        test_mode = False
        skip_reviews = False
        
        # Warn user about full scrape
        print("⚠️  WARNING: Full scrape will attempt to scrape all ~7700 professors!")
        print("   This could take 10+ hours and may hit rate limits.")
        print("   Consider using --max-professors to limit the scope.")
        response = input("Do you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return
    else:
        max_professors = args.max_professors
        max_reviews_per_prof = args.max_reviews
        test_mode = False
        skip_reviews = args.skip_reviews
    
    # Display scraping plan
    print("\n" + "="*50)
    print("PENN STATE RATEMYPROFESSOR SCRAPER")
    print("="*50)
    print("⚠️  WARNING: This tool is for personal/educational use only!")
    print("⚠️  It may violate RateMyProfessors.com Terms of Service!")
    print("⚠️  Use responsibly and at your own risk!")
    print("-"*50)
    
    if test_mode:
        print("Mode: TEST (10 professors, 5 reviews each)")
    elif max_professors:
        print(f"Mode: LIMITED ({max_professors} professors max)")
    else:
        print("Mode: FULL SCRAPE (all professors)")
        
    if skip_reviews:
        print("Reviews: SKIPPED")
    elif max_reviews_per_prof:
        print(f"Reviews: Up to {max_reviews_per_prof} per professor")
    else:
        print("Reviews: ALL available")
        
    print("="*50)
    
    # Run the scraper
    success = run_full_scrape(
        test_mode=test_mode,
        max_professors=max_professors,
        max_reviews_per_prof=max_reviews_per_prof,
        skip_reviews=skip_reviews
    )
    
    if success:
        print("\n✅ Scraping completed successfully!")
    else:
        print("\n❌ Scraping failed. Check the log file for details.")


if __name__ == "__main__":
    main()
