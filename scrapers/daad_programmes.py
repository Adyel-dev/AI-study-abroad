"""
DAAD and Hochschulkompass programme scraper
Scrapes German study programmes from various sources and stores in MongoDB
Enhanced implementation to actually extract programme data
"""
import requests
from bs4 import BeautifulSoup
import time
import logging
import re
from datetime import datetime
from models.mongo import get_db
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from bson import ObjectId

logger = logging.getLogger(__name__)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
DELAY_BETWEEN_REQUESTS = 2  # seconds
MAX_UNIVERSITIES_TO_SCRAPE = 50  # Limit for initial scraping

def check_robots_txt(url):
    """Check if URL is allowed by robots.txt"""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception as e:
        logger.warning(f"Could not check robots.txt for {url}: {e}")
        return True  # Allow by default if check fails

def scrape_german_programmes():
    """
    Scrape German programmes from various sources
    Returns dict with scraping statistics
    """
    try:
        logger.info("Starting German programmes scraping")
        db = get_db()
        
        total_scraped = 0
        total_inserted = 0
        total_updated = 0
        errors = 0
        
        # Scrape from multiple sources
        # Note: University websites scraper is more comprehensive but slower
        # DAAD and Hochschulkompass are faster but may have less detail
        sources = [
            scrape_daad_basic,
            scrape_hochschulkompass,
            scrape_from_university_websites,  # Put last as it's slower
        ]
        
        for scraper_func in sources:
            try:
                result = scraper_func(db)
                total_scraped += result.get('scraped', 0)
                total_inserted += result.get('inserted', 0)
                total_updated += result.get('updated', 0)
                errors += result.get('errors', 0)
                time.sleep(DELAY_BETWEEN_REQUESTS)
            except Exception as e:
                logger.error(f"Error in scraper {scraper_func.__name__}: {e}")
                errors += 1
                continue
        
        result = {
            'total_scraped': total_scraped,
            'inserted': total_inserted,
            'updated': total_updated,
            'errors': errors,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Programme scraping completed: {result}")
        
        # Log job
        db.jobs_log.insert_one({
            'job_type': 'scrape_programmes',
            'status': 'success' if errors == 0 else 'partial',
            'result': result,
            'created_at': datetime.utcnow()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error during programme scraping: {e}")
        db = get_db()
        db.jobs_log.insert_one({
            'job_type': 'scrape_programmes',
            'status': 'error',
            'error': str(e),
            'created_at': datetime.utcnow()
        })
        raise

def scrape_from_university_websites(db):
    """
    Option 1: Scrape programmes from university websites
    Uses university URLs from the database and looks for programme pages
    """
    scraped = 0
    inserted = 0
    updated = 0
    errors = 0
    
    try:
        # Get universities from database
        universities = list(db.universities.find({'country': 'Germany'}).limit(MAX_UNIVERSITIES_TO_SCRAPE))
        logger.info(f"Found {len(universities)} universities to scrape programmes from")
        
        for uni in universities:
            try:
                uni_name = uni.get('name', 'Unknown')
                uni_id = str(uni['_id'])
                web_pages = uni.get('web_pages', [])
                city = uni.get('state-province', '')
                
                if not web_pages:
                    continue
                
                # Try the first web page
                base_url = web_pages[0] if isinstance(web_pages, list) else web_pages
                
                if not base_url or not base_url.startswith('http'):
                    continue
                
                logger.info(f"Scraping programmes from {uni_name}: {base_url}")
                
                # Common programme page paths to try
                programme_paths = [
                    '/en/study/programmes',
                    '/en/study/degree-programs',
                    '/en/programs',
                    '/en/degree-programs',
                    '/study/programmes',
                    '/study/programs',
                    '/en/studium/studienangebot',
                    '/studium/studienangebot',
                    '/en/courses',
                    '/courses',
                ]
                
                found_programmes = False
                
                for path in programme_paths:
                    try:
                        url = urljoin(base_url, path)
                        
                        if not check_robots_txt(url):
                            continue
                        
                        headers = {'User-Agent': USER_AGENT}
                        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                        
                        if response.status_code != 200:
                            continue
                        
                        soup = BeautifulSoup(response.content, 'html.parser')
                        programmes = extract_programmes_from_html(soup, uni_name, uni_id, city, url)
                        
                        if programmes:
                            found_programmes = True
                            for prog_data in programmes:
                                is_inserted, is_updated = upsert_programme(db, prog_data)
                                if is_inserted:
                                    inserted += 1
                                    scraped += 1
                                elif is_updated:
                                    updated += 1
                                    scraped += 1
                            
                            # Found programmes, no need to try other paths
                            break
                    
                    except Exception as e:
                        logger.debug(f"Error trying path {path} for {uni_name}: {e}")
                        continue
                
                if not found_programmes:
                    # Try scraping from main page if it contains programme links
                    try:
                        if check_robots_txt(base_url):
                            headers = {'User-Agent': USER_AGENT}
                            response = requests.get(base_url, headers=headers, timeout=15)
                            if response.status_code == 200:
                                soup = BeautifulSoup(response.content, 'html.parser')
                                # Look for links to programme pages
                                programme_links = soup.find_all('a', href=re.compile(r'programm|program|studiengang|course|degree', re.I))
                                
                                for link in programme_links[:5]:  # Try first 5 links
                                    try:
                                        href = link.get('href', '')
                                        if href:
                                            full_url = urljoin(base_url, href)
                                            if full_url.startswith('http') and uni_name.lower() in full_url.lower():
                                                if check_robots_txt(full_url):
                                                    response2 = requests.get(full_url, headers=headers, timeout=15)
                                                    if response2.status_code == 200:
                                                        soup2 = BeautifulSoup(response2.content, 'html.parser')
                                                        programmes = extract_programmes_from_html(soup2, uni_name, uni_id, city, full_url)
                                                        
                                                        for prog_data in programmes[:3]:  # Limit per page
                                                            is_inserted, is_updated = upsert_programme(db, prog_data)
                                                            if is_inserted:
                                                                inserted += 1
                                                                scraped += 1
                                                            elif is_updated:
                                                                updated += 1
                                                                scraped += 1
                                    except:
                                        continue
                    except:
                        pass
                
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
            except Exception as e:
                logger.error(f"Error scraping programmes from university {uni.get('name', 'Unknown')}: {e}")
                errors += 1
                continue
        
        logger.info(f"University websites scraper: scraped={scraped}, inserted={inserted}, updated={updated}, errors={errors}")
        
    except Exception as e:
        logger.error(f"Error in scrape_from_university_websites: {e}")
        errors += 1
    
    return {'scraped': scraped, 'inserted': inserted, 'updated': updated, 'errors': errors}

def extract_programmes_from_html(soup, university_name, university_id, city, source_url):
    """
    Extract programme data from HTML soup
    This is a flexible parser that tries multiple patterns
    """
    programmes = []
    
    try:
        # Pattern 1: Look for common programme container classes
        programme_containers = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'program|course|degree|studiengang', re.I))
        
        if not programme_containers:
            # Pattern 2: Look for tables or lists with programme info
            programme_containers = soup.find_all(['tr', 'li'], string=re.compile(r'bachelor|master|phd|b\.?sc|m\.?sc|m\.?a|b\.?a', re.I))
        
        for container in programme_containers[:20]:  # Limit to 20 per page
            try:
                prog_data = {}
                
                # Extract title
                title_elem = container.find(['h1', 'h2', 'h3', 'h4', 'a', 'strong'], class_=re.compile(r'title|name|heading', re.I))
                if not title_elem:
                    title_elem = container.find(['h1', 'h2', 'h3', 'h4'])
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 5 and len(title) < 200:
                        prog_data['title'] = title
                
                if not prog_data.get('title'):
                    # Try getting text from container itself
                    text = container.get_text(strip=True)
                    if len(text) > 10 and len(text) < 200:
                        # Extract first line or meaningful text
                        lines = text.split('\n')
                        for line in lines[:3]:
                            line = line.strip()
                            if len(line) > 10 and any(word in line.lower() for word in ['bachelor', 'master', 'phd', 'degree', 'program']):
                                prog_data['title'] = line
                                break
                
                if not prog_data.get('title'):
                    continue
                
                # Extract degree type
                title_lower = prog_data['title'].lower()
                if 'master' in title_lower or 'm.sc' in title_lower or 'm.a' in title_lower or 'm.eng' in title_lower:
                    prog_data['degree_type'] = 'Master'
                elif 'bachelor' in title_lower or 'b.sc' in title_lower or 'b.a' in title_lower or 'b.eng' in title_lower:
                    prog_data['degree_type'] = 'Bachelor'
                elif 'phd' in title_lower or 'doctorate' in title_lower or 'promotion' in title_lower:
                    prog_data['degree_type'] = 'PhD'
                else:
                    prog_data['degree_type'] = 'Master'  # Default
                
                # Extract language
                text_content = container.get_text().lower()
                languages = []
                if 'english' in text_content:
                    languages.append('English')
                if 'german' in text_content or 'deutsch' in text_content:
                    languages.append('German')
                if not languages:
                    languages = ['English']  # Default assumption
                prog_data['language'] = languages
                
                # Extract duration
                duration_match = re.search(r'(\d+)\s*(semester|semesters|years?|jahr)', text_content, re.I)
                if duration_match:
                    num = int(duration_match.group(1))
                    unit = duration_match.group(2).lower()
                    if 'semester' in unit:
                        prog_data['duration_semesters'] = num
                    elif 'year' in unit or 'jahr' in unit:
                        prog_data['duration_semesters'] = num * 2
                
                # Extract tuition
                tuition_match = re.search(r'(\d+[,.]?\d*)\s*(€|euro|eur)', text_content, re.I)
                if tuition_match:
                    try:
                        fee = float(tuition_match.group(1).replace(',', '.'))
                        prog_data['tuition_fee_eur_per_semester'] = int(fee)
                    except:
                        pass
                
                # Check for "free" or "no tuition"
                if 'free' in text_content or 'no tuition' in text_content or 'keine gebühren' in text_content:
                    prog_data['tuition_fee_eur_per_semester'] = 0
                
                # Extract link
                link_elem = container.find('a', href=True)
                if link_elem:
                    href = link_elem.get('href', '')
                    if href:
                        prog_data['source_url'] = urljoin(source_url, href)
                else:
                    prog_data['source_url'] = source_url
                
                # Fill required fields
                prog_data['university_name'] = university_name
                prog_data['university_id'] = university_id
                prog_data['city'] = city or ''
                prog_data['source'] = 'university_website'
                
                programmes.append(prog_data)
                
            except Exception as e:
                logger.debug(f"Error extracting programme from container: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error in extract_programmes_from_html: {e}")
    
    return programmes

def scrape_daad_basic(db):
    """
    Option 2: Enhanced DAAD scraper
    Scrapes programmes from DAAD website
    """
    scraped = 0
    inserted = 0
    updated = 0
    errors = 0
    
    try:
        # DAAD programme search pages
        base_urls = [
            "https://www.daad.de/en/studying-in-germany/universities/all-degree-programmes/",
            "https://www2.daad.de/deutschland/studienangebote/international-programmes/en/",
            "https://www.study-in-germany.com/en/plan-your-studies/study-options/programme/",
        ]
        
        for base_url in base_urls:
            try:
                if not check_robots_txt(base_url):
                    logger.warning(f"robots.txt disallows scraping from {base_url}")
                    continue
                
                headers = {'User-Agent': USER_AGENT}
                response = requests.get(base_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for programme links or listings
                programme_links = soup.find_all('a', href=re.compile(r'program|course|degree|studienangebot', re.I))
                
                for link in programme_links[:30]:  # Limit to 30 per page
                    try:
                        href = link.get('href', '')
                        if not href:
                            continue
                        
                        full_url = urljoin(base_url, href)
                        
                        if not check_robots_txt(full_url):
                            continue
                        
                        # Visit programme detail page
                        response2 = requests.get(full_url, headers=headers, timeout=15)
                        if response2.status_code != 200:
                            continue
                        
                        soup2 = BeautifulSoup(response2.content, 'html.parser')
                        
                        # Extract programme info
                        prog_data = {}
                        
                        # Title
                        title_elem = soup2.find(['h1', 'h2'], class_=re.compile(r'title|heading', re.I))
                        if not title_elem:
                            title_elem = soup2.find('h1')
                        if title_elem:
                            prog_data['title'] = title_elem.get_text(strip=True)
                        
                        if not prog_data.get('title'):
                            continue
                        
                        # University name
                        uni_elem = soup2.find(string=re.compile(r'university|hochschule', re.I))
                        if uni_elem:
                            prog_data['university_name'] = uni_elem.find_parent().get_text(strip=True) if hasattr(uni_elem, 'find_parent') else str(uni_elem)
                        else:
                            prog_data['university_name'] = 'Unknown'
                        
                        # Degree type from title
                        title_lower = prog_data['title'].lower()
                        if 'master' in title_lower:
                            prog_data['degree_type'] = 'Master'
                        elif 'bachelor' in title_lower:
                            prog_data['degree_type'] = 'Bachelor'
                        elif 'phd' in title_lower:
                            prog_data['degree_type'] = 'PhD'
                        else:
                            prog_data['degree_type'] = 'Master'
                        
                        # Language
                        text = soup2.get_text().lower()
                        languages = []
                        if 'english' in text:
                            languages.append('English')
                        if 'german' in text:
                            languages.append('German')
                        if not languages:
                            languages = ['English']
                        prog_data['language'] = languages
                        
                        prog_data['city'] = ''
                        prog_data['source'] = 'DAAD'
                        prog_data['source_url'] = full_url
                        
                        is_inserted, is_updated = upsert_programme(db, prog_data)
                        if is_inserted:
                            inserted += 1
                            scraped += 1
                        elif is_updated:
                            updated += 1
                            scraped += 1
                        
                        time.sleep(1)  # Be respectful
                        
                    except Exception as e:
                        logger.debug(f"Error processing DAAD programme link: {e}")
                        continue
                
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
            except Exception as e:
                logger.error(f"Error scraping DAAD URL {base_url}: {e}")
                errors += 1
                continue
        
        logger.info(f"DAAD scraper: scraped={scraped}, inserted={inserted}, updated={updated}, errors={errors}")
        
    except Exception as e:
        logger.error(f"Error in scrape_daad_basic: {e}")
        errors += 1
    
    return {'scraped': scraped, 'inserted': inserted, 'updated': updated, 'errors': errors}

def scrape_hochschulkompass(db):
    """
    Option 2: Enhanced Hochschulkompass scraper
    Scrapes programmes from Hochschulkompass website
    """
    scraped = 0
    inserted = 0
    updated = 0
    errors = 0
    
    try:
        base_url = "https://www.hochschulkompass.de/en/degree-programmes.html"
        
        if not check_robots_txt(base_url):
            logger.warning(f"robots.txt disallows scraping from {base_url}")
            return {'scraped': 0, 'inserted': 0, 'updated': 0, 'errors': 0}
        
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for programme listings or search form
        # Hochschulkompass might have a search interface, try to find programme links
        programme_links = soup.find_all('a', href=re.compile(r'studiengang|programm|program', re.I))
        
        if not programme_links:
            # Try alternative approach - look for search results or listings
            programme_containers = soup.find_all(['div', 'li', 'article'], class_=re.compile(r'program|course|study', re.I))
            
            # Extract programmes from the full soup
            programmes = extract_programmes_from_html(soup, 'Unknown University', '', '', base_url)
            
            for prog_data in programmes[:20]:  # Limit to 20
                try:
                    prog_data['source'] = 'Hochschulkompass'
                    if not prog_data.get('source_url'):
                        prog_data['source_url'] = base_url
                    
                    is_inserted, is_updated = upsert_programme(db, prog_data)
                    if is_inserted:
                        inserted += 1
                        scraped += 1
                    elif is_updated:
                        updated += 1
                        scraped += 1
                
                except Exception as e:
                    logger.debug(f"Error processing Hochschulkompass programme: {e}")
                    continue
        
        logger.info(f"Hochschulkompass scraper: scraped={scraped}, inserted={inserted}, updated={updated}, errors={errors}")
        
    except Exception as e:
        logger.error(f"Error scraping Hochschulkompass: {e}")
        errors += 1
    
    return {'scraped': scraped, 'inserted': inserted, 'updated': updated, 'errors': errors}

def upsert_programme(db, programme_data):
    """
    Upsert a programme into the database
    Returns tuple (inserted, updated)
    """
    try:
        # Validate required fields
        if not programme_data.get('title') or not programme_data.get('university_name'):
            return (False, False)
        
        # Create unique identifier from title + university + city
        query = {
            'title': programme_data.get('title'),
            'university_name': programme_data.get('university_name'),
            'city': programme_data.get('city', '')
        }
        
        existing = db.programmes.find_one(query)
        
        # Ensure all required fields exist
        programme_doc = {
            'title': programme_data.get('title'),
            'degree_type': programme_data.get('degree_type', 'Master'),
            'language': programme_data.get('language', ['English']),
            'university_name': programme_data.get('university_name'),
            'university_id': programme_data.get('university_id', ''),
            'city': programme_data.get('city', ''),
            'tuition_fee_eur_per_semester': programme_data.get('tuition_fee_eur_per_semester'),
            'duration_semesters': programme_data.get('duration_semesters'),
            'application_deadline': programme_data.get('application_deadline'),
            'source': programme_data.get('source', 'unknown'),
            'source_url': programme_data.get('source_url', ''),
            'last_seen_at': datetime.utcnow(),
        }
        
        if existing:
            db.programmes.update_one(
                {'_id': existing['_id']},
                {'$set': programme_doc}
            )
            return (False, True)
        else:
            programme_doc['created_at'] = datetime.utcnow()
            db.programmes.insert_one(programme_doc)
            return (True, False)
            
    except Exception as e:
        logger.error(f"Error upserting programme: {e}")
        return (False, False)
