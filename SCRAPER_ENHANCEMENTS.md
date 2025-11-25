# Programme Scraper Enhancements

## Overview
The programme scrapers have been completely rewritten to actually extract real programme data from multiple sources. The AI counselor will now use actual scraped data instead of OpenAI's training data.

## Implemented Features

### Option 1: University Website Scraper ✅
The scraper now visits actual university websites and extracts programme information:

**Features:**
- Reads universities from the database (using URLs from Hipolabs API)
- Tries multiple common programme page paths (e.g., `/en/study/programmes`, `/study/programs`)
- Intelligently extracts programme data from HTML pages
- Handles various page structures and formats
- Links programmes to university IDs in the database

**Extracted Data:**
- Programme title
- Degree type (Bachelor/Master/PhD)
- Language of instruction
- Duration (semesters)
- Tuition fees
- University name and ID
- City
- Source URL

**Limits:**
- Scrapes up to 50 universities per run (configurable via `MAX_UNIVERSITIES_TO_SCRAPE`)
- Respects robots.txt
- Includes delays between requests (2 seconds)
- Handles errors gracefully

### Option 2: DAAD Scraper ✅
Enhanced DAAD scraper that extracts programmes from:
- DAAD main programme page
- DAAD International Programmes page
- Study-in-Germany programme finder

**Features:**
- Visits programme detail pages
- Extracts comprehensive programme information
- Handles multiple DAAD subdomains
- Stores source attribution

### Option 3: Hochschulkompass Scraper ✅
Enhanced scraper for Hochschulkompass:
- Searches for programme listings
- Extracts programme details
- Handles various page formats

## How It Works

1. **Main Scraper Function** (`scrape_german_programmes()`):
   - Runs all three scrapers in sequence
   - Combines results
   - Logs statistics
   - Handles errors gracefully

2. **Programme Extraction**:
   - Flexible HTML parsing using BeautifulSoup
   - Tries multiple patterns to find programme data
   - Extracts degree type from titles (Bachelor, Master, PhD)
   - Detects language from page content
   - Parses duration and fees using regex

3. **Data Storage**:
   - Uses `upsert_programme()` to avoid duplicates
   - Unique identifier: title + university + city
   - Updates existing programmes or creates new ones
   - Stores timestamps for tracking

## Usage

### Via Admin Panel
1. Log into admin panel
2. Go to Jobs section
3. Click "Trigger Job"
4. Select `scrape_programmes`
5. Click "Run"

### Via API
```bash
POST /api/admin/jobs/trigger
{
  "job_type": "scrape_programmes"
}
```

### Via Scheduler
The scraper runs automatically based on scheduler configuration (weekly by default).

## Configuration

### Limits
```python
MAX_UNIVERSITIES_TO_SCRAPE = 50  # Limit universities per run
DELAY_BETWEEN_REQUESTS = 2  # Seconds between requests
```

### Programme Paths to Try
The university scraper tries these common paths:
- `/en/study/programmes`
- `/en/study/degree-programs`
- `/en/programs`
- `/study/programmes`
- `/en/studium/studienangebot`
- And more...

## Results

After running the scraper, you'll see:
- Total programmes scraped
- New programmes inserted
- Existing programmes updated
- Any errors encountered

Check the programmes collection in MongoDB:
```javascript
db.programmes.find().count()
db.programmes.find().limit(5)
```

## How AI Counselor Uses This Data

The enhanced counselor now:
1. **Queries real database** - Uses `query_programmes_intelligent()` to search programmes collection
2. **Provides specific details** - Shows actual programme titles, fees, duration, deadlines
3. **Never says "visit website"** - Provides all available information directly
4. **Uses source URLs** - Links to actual programme pages for more info

## Future Enhancements

Potential improvements:
- Add more university website patterns
- Implement Selenium for JavaScript-heavy sites
- Add programme description extraction
- Extract admission requirements
- Parse application deadlines more accurately
- Cache scraping results to reduce load

## Notes

- **Respects robots.txt**: Always checks before scraping
- **Rate limiting**: Includes delays to be respectful
- **Error handling**: Continues even if some universities fail
- **Data validation**: Only stores programmes with required fields
- **Idempotent**: Can run multiple times safely

