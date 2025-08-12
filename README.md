# Penn State RateMyProfessor Data Scraper

⚠️ **WARNING: This repository and its scraping scripts are designed for personal use and educational purposes only!**

⚠️ **IMPORTANT LEGAL NOTICE:** This tool likely violates the Terms of Service of both RateMyProfessors.com and potentially Penn State University policies. Use at your own risk and responsibility.

⚠️ **DISCLAIMER:** The maintainers of this repository are not responsible for any misuse of this tool or any consequences arising from its use.

---

## Overview

This repository contains Python scripts to scrape professor data from RateMyProfessors.com specifically for Penn State University (School ID: 758). The scraper collects professor ratings, departments, difficulty levels, and other available metrics.

**Students gotta do what they gotta do** - but please use this responsibly and ethically!

## Inspiration and Attribution

This project is improved and scoped specifically for Penn State University, inspired by the original [RateMyProfessor.com-Web-Scraper](https://github.com/highlyavailable/RateMyProfessor.com-Web-Scraper) repository. Our implementation focuses on Penn State data with enhanced features and better organization.

## Features

- ✅ Scrapes all professor data from Penn State University (~7,703 professors)
- ✅ Extracts ratings, number of reviews, "would take again" percentages, and difficulty levels
- ✅ Outputs data in JSON Lines (.jsonl) format for easy processing
- ✅ Test mode for safe experimentation with small data batches
- ✅ Automated data updates via GitHub Actions (every 4 months)
- ⚠️ Individual review scraping (requires browser installation - coming soon)

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

**Test Mode (Recommended for first run):**
```bash
python -m scraper.main_scraper --test
```
*Scrapes only 10 professors for testing*

**Scrape First 100 Professors:**
```bash
python -m scraper.main_scraper --max-professors 100
```

**Professors Only (No Reviews):**
```bash
python -m scraper.main_scraper --skip-reviews
```

**Full Scrape (WARNING: Takes hours!):**
```bash
python -m scraper.main_scraper --full
```
*⚠️ This will attempt to scrape all ~7,700 professors and may take 10+ hours*

## Output Files

All scraped data is stored in the `data/` directory:

- `data/penn_state_professors.jsonl` - Professor information (ratings, departments, etc.)
- `data/penn_state_reviews.jsonl` - Individual student reviews (requires browser setup)
- `data/penn_state_courses.jsonl` - Course-specific data extracted from reviews

### Sample Data Format

```json
{
  "name": "Jeff Love",
  "department": "Psychology", 
  "school": "Penn State University",
  "rating": 4.5,
  "num_ratings": 284,
  "would_take_again_pct": 90.625,
  "level_of_difficulty": 2.6,
  "url": null,
  "professor_id": null
}
```

## Automated Updates

This repository includes a GitHub Actions workflow that automatically updates the professor data every 4 months:

- **August 1st** - Fall semester update
- **January 1st** - Spring semester update  
- **May 1st** - Summer semester update

This ensures the data stays current across academic terms.

## Technical Details

### Architecture

- **Simple Scraper** (`scraper/simple_scraper.py`) - Uses requests + BeautifulSoup (no browser required)
- **Models** (`scraper/models.py`) - Data structures for professors, reviews, and courses
- **Configuration** (`scraper/config.py`) - All settings and Penn State specific parameters

### Penn State Specific Settings

- School ID: 758
- Base URL: `https://www.ratemyprofessors.com/search/professors/758?q=*`
- Total Professors: ~7,703 (as of last update)

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
