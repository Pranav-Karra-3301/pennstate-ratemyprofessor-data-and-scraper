# Penn State RateMyProfessor Data Scraper

⚠️ **Warning**: This project is mostly vibecoded and made for personal use. It may contain experimental features, incomplete implementations, and unconventional approaches. Use at your own risk and discretion. Production use is not recommended without thorough testing.

⚠️ **WARNING**: This scraper was mainly vibecoded for personal use and is provided as-is. Use at your own risk. This tool likely violates RateMyProfessors.com Terms of Service and Penn State University policies. However, students gotta do what they gotta do. The maintainers are not responsible for any consequences of using this tool.

---

## Overview

This repository contains Python scripts to scrape professor data from RateMyProfessors.com specifically for Penn State University (School ID: 758). The scraper collects professor ratings, departments, difficulty levels, and other available metrics.

**Students gotta do what they gotta do** - but please use this responsibly and ethically!

## Inspiration and Attribution

This project is improved and scoped specifically for Penn State University, inspired by the original [RateMyProfessor.com-Web-Scraper](https://github.com/highlyavailable/RateMyProfessor.com-Web-Scraper) repository. Our implementation focuses on Penn State data with enhanced features and better organization.

## Features

- ✅ Scrapes all professor data from Penn State University (1000+ professors)
- ✅ Extracts comprehensive data including:
  - 📊 Ratings, difficulty levels, and "would take again" percentages
  - 📚 Course codes and teaching history
  - 🏷️ Teaching style tags and characteristics
  - 👥 Number of ratings and department information
- ✅ Multiple scraper modes:
  - **API Scraper**: Most reliable, uses GraphQL API
  - **Enhanced Scraper**: Includes detailed course and tag data
  - **Simple Scraper**: Basic HTML scraping
- ✅ Outputs data in JSON Lines (.jsonl) format for easy processing
- ✅ Test mode for safe experimentation with small data batches
- ✅ Automated monthly data updates via GitHub Actions
- ✅ Data validation and quality checks

## Quick Start

### Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd pennstate-ratemyprofessor-data-and-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage Examples

**API Scraper (Recommended - Most Reliable):**
```bash
# Test mode - scrape 10 professors
python -m scraper.api_scraper --test

# Scrape 500 professors
python -m scraper.api_scraper --max 500

# Scrape 1000 professors and enhance 200 with detailed data
python -m scraper.api_scraper --max 1000 --enhance 200
```

**Enhanced Scraper (Includes Course Data):**
```bash
# Run enhanced scraper with course and tag extraction
python -m scraper.enhanced_scraper --max 500 --enhance 100
```

**Simple Scraper (Basic HTML Scraping):**
```bash
# Basic scraping without API
python -m scraper.simple_scraper --test
```

## Output Files

All scraped data is stored in the `data/` directory:

- `data/penn_state_professors.jsonl` - Professor information (ratings, departments, etc.)
- `data/penn_state_reviews.jsonl` - Individual student reviews (requires browser setup)
- `data/penn_state_courses.jsonl` - Course-specific data extracted from reviews

### Sample Data Format

```json
{
  "id": "VGVhY2hlci0yNzUwNjgy",
  "legacy_id": 2750682,
  "first_name": "Ashley",
  "last_name": "Pallone",
  "full_name": "Ashley Pallone",
  "department": "Mathematics",
  "school": "Penn State University",
  "school_id": "758",
  "overall_rating": 4.8,
  "num_ratings": 23,
  "would_take_again_percent": 95.65,
  "level_of_difficulty": 2.7,
  "tags": [
    "Amazing lectures",
    "Clear grading criteria",
    "Accessible outside class",
    "Caring",
    "EXTRA CREDIT"
  ],
  "courses": [
    "MATH140",
    "MATH140B",
    "MATH141",
    "MATH141B"
  ],
  "profile_url": "https://www.ratemyprofessors.com/professor/2750682"
}
```

## Automated Updates

This repository includes a GitHub Actions workflow that automatically updates the professor data monthly:

- **Schedule**: Runs on the 1st of every month at 3 AM EST
- **Manual Trigger**: Can be manually triggered from the Actions tab
- **Pull Request**: Creates a PR with the updated data for review
- **Validation**: Automatically validates data format and completeness

### Manual Update
To manually trigger an update:
1. Go to the [Actions tab](../../actions)
2. Select "Monthly Data Update"
3. Click "Run workflow"

The workflow will:
- Scrape up to 2000 professors
- Enhance 500 with detailed course/tag data
- Validate the data format
- Create a pull request with the changes

## Technical Details

### Architecture

- **API Scraper** (`scraper/api_scraper.py`) - Uses GraphQL API for reliable data extraction
- **Enhanced Scraper** (`scraper/enhanced_scraper.py`) - Comprehensive data with courses and tags
- **Simple Scraper** (`scraper/simple_scraper.py`) - Basic HTML scraping with BeautifulSoup
- **Models** (`scraper/models.py`) - Data structures for professors, reviews, and courses
- **Configuration** (`scraper/config.py`) - All settings and Penn State specific parameters
- **GitHub Actions** (`.github/workflows/`) - Automated CI/CD and monthly updates

### Penn State Specific Settings

- School ID: 758
- School ID (Base64): U2Nob29sLTc1OA==
- GraphQL Endpoint: `https://www.ratemyprofessors.com/graphql`
- Base URL: `https://www.ratemyprofessors.com/search/professors/758`
- Total Professors: 1000+ active professors with ratings

### Rate Limiting

The scraper includes built-in rate limiting and retry logic to be respectful to RateMyProfessors.com servers:

- 1 second delay between requests
- Exponential backoff on failures
- Maximum 3 retry attempts

## Limitations

1. **Review Scraping**: Individual professor reviews require a web browser (Chrome/Firefox) installation for JavaScript execution
2. **Pagination**: Currently extracts data from the initial page load (~5 professors at a time)
3. **Rate Limits**: RateMyProfessors may implement rate limiting or blocking
4. **Legal Restrictions**: Usage may violate Terms of Service

## Future Enhancements

- [ ] Pagination support for full professor list
- [ ] Browser-free review scraping
- [ ] Course schedule integration
- [ ] Grade distribution correlation
- [ ] Advanced analytics and visualizations

## Legal and Ethical Considerations

### ⚠️ Terms of Service

This tool likely violates RateMyProfessors.com Terms of Service. The website's robots.txt and terms explicitly discourage automated data collection.

### 🎓 Educational Use Only

This repository is intended for:
- Personal academic research
- Educational projects and learning
- Non-commercial analysis

### 🚫 Prohibited Uses

DO NOT use this tool for:
- Commercial purposes
- Harassment or targeting of professors
- Publication or redistribution of scraped data
- Any activity that could harm individuals or institutions

## Contributors

- **Main Contributors**: Cursor AI and Claude Sonnet 4
- **Inspiration**: [RateMyProfessor.com-Web-Scraper](https://github.com/highlyavailable/RateMyProfessor.com-Web-Scraper)

## Troubleshooting

### Common Issues

**1. "No browser found" error:**
```bash
# Install Chrome or Firefox, then run:
python -m scraper.main_scraper --skip-reviews
```

**2. Rate limiting/blocking:**
```bash
# Use test mode and be patient:
python -m scraper.main_scraper --test
```

**3. Empty results:**
- Check internet connection
- Verify Penn State school ID (758) is still valid
- Run in test mode first

### Getting Help

1. Check the log files (created during each run)
2. Try test mode first
3. Review the troubleshooting section above
4. Open an issue if problems persist

## License and Disclaimer

This project is provided "as-is" for educational purposes. Users assume all responsibility for compliance with applicable laws and terms of service. The authors disclaim any liability for misuse or legal consequences.

---

**Remember**: Be ethical, be respectful, and use this tool responsibly! 🎓
