#!/usr/bin/env python3
# ==============================================================================
# Enhanced Argos Product Data Scraper with EAN and Model Number Support
# ==============================================================================
#
# This version handles both EAN codes and model numbers from a two-column CSV:
# - Column 1: EAN codes (priority)
# - Column 2: Model numbers (fallback)
# - Uses search engines for EAN searches
# - Uses Argos direct search for model numbers (less rate limited)
# - Tracks accessed URLs to prevent duplicate requests
#
# ==============================================================================

import os
import sys
import json
import time
import random
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, quote
import pickle
from typing import Optional, Tuple, Dict, List

# ==============================================================================
# CONFIGURATION
# ==============================================================================

CONFIG = {
    # File paths
    'input_csv': 'input.csv',
    'output_directory': 'scraped_products',
    'success_file': 'successful_products.pkl',
    'not_found_file': 'not_found_products.pkl',
    'blocked_status_file': 'search_blocked_status.json',
    'accessed_urls_file': 'accessed_urls.pkl',

    # Enhanced delay settings with exponential backoff
    'min_delay': 5,
    'max_delay': 10,
    'argos_search_delay': 3,  # Shorter delay for Argos direct search
    'block_cooldown': 1800, 
    'exponential_backoff_base': 2,
    'max_backoff_delay': 300,  # 5 minutes max

    # Retry settings
    'max_retries': 1,
    'retry_delay': 30,

    # Search settings
    'search_timeout': 20,
    'num_results': 3,  # Increased to get more results
    'rotate_backends': True,

    # HTTP request settings
    'request_timeout': 15,

    # User agents for variety
    'user_agents': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    ],

    # Available search backends for text search
    'search_backends': ['google', 'mullvad_google', 'yahoo', 'yandex'],
    
    # Product URL patterns
    'valid_url_patterns': [
        r'/product/\d+',
        r'/product/[a-zA-Z0-9-]+/\d+',
    ],

    # User options
    'rescrape_successful': False,
    'debug_search': True,  # Set to True to see search results
    
    # Logging
    'verbose': True,
    'log_file': 'scraper_log.txt'
}

# ==============================================================================
# GLOBAL VARIABLES
# ==============================================================================

BACKEND_FAILURES = {}  # Track failures per backend
LAST_REQUEST_TIME = {}  # Track last request time per backend
CONSECUTIVE_FAILURES = 0  # Track consecutive failures across all backends
ACCESSED_URLS = set()  # Track all accessed URLs to prevent duplicates

# ==============================================================================
# DEPENDENCY INSTALLATION
# ==============================================================================

def install_dependencies():
    """Install required libraries if not present."""
    required_packages = {
        'ddgs': 'ddgs',
        'pandas': 'pandas',
        'requests': 'requests',
        'bs4': 'beautifulsoup4'
    }

    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            print(f"Installing {package}...")
            os.system(f"{sys.executable} -m pip install {package} --quiet")

    # Import after installation
    global DDGS
    from ddgs import DDGS

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def log_message(message, level="INFO"):
    """Log messages with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{level}] {message}"

    if CONFIG['verbose']:
        print(formatted_message)

    try:
        with open(CONFIG['log_file'], 'a', encoding='utf-8') as f:
            f.write(formatted_message + '\n')
    except:
        pass

def get_random_headers():
    """Generate headers with random User-Agent."""
    return {
        'User-Agent': random.choice(CONFIG['user_agents']),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }

def adaptive_delay(backend: str = None, is_blocked: bool = False, is_argos_search: bool = False):
    """Implement adaptive delay with exponential backoff."""
    global LAST_REQUEST_TIME, BACKEND_FAILURES
    
    # Calculate base delay
    if is_blocked:
        delay = CONFIG['block_cooldown']
    elif is_argos_search:
        delay = CONFIG['argos_search_delay']
    else:
        # Check if we need exponential backoff for this backend
        if backend and backend in BACKEND_FAILURES:
            failures = BACKEND_FAILURES[backend]
            backoff_delay = min(
                CONFIG['min_delay'] * (CONFIG['exponential_backoff_base'] ** failures),
                CONFIG['max_backoff_delay']
            )
            delay = backoff_delay
        else:
            delay = random.uniform(CONFIG['min_delay'], CONFIG['max_delay'])
    
    # Add jitter to avoid patterns
    delay += random.uniform(0, 2 if is_argos_search else 5)
    
    # Check last request time for this backend
    if backend and backend in LAST_REQUEST_TIME:
        time_since_last = time.time() - LAST_REQUEST_TIME[backend]
        if time_since_last < delay:
            delay = delay - time_since_last
    
    log_message(f"Waiting {delay:.2f} seconds before next request...")
    time.sleep(delay)
    
    # Update last request time
    if backend:
        LAST_REQUEST_TIME[backend] = time.time()

def is_valid_product_url(url):
    """Check if the URL is a valid Argos product page."""
    if not url or 'argos.co.uk' not in url:
        return False

    for pattern in CONFIG['valid_url_patterns']:
        if re.search(pattern, url):
            return True

    exclude_patterns = ['/search/', '/browse/', '/category/', '/c:', '/static/']
    for pattern in exclude_patterns:
        if pattern in url:
            return False

    return False

def has_url_been_accessed(url):
    """Check if URL has been accessed before."""
    return url in ACCESSED_URLS

def mark_url_accessed(url):
    """Mark URL as accessed."""
    ACCESSED_URLS.add(url)

# ==============================================================================
# ENHANCED SEARCH FUNCTIONS
# ==============================================================================

def search_with_ddgs(search_query: str, backend: str = 'auto') -> Tuple[Optional[str], bool, str]:
    """
    Search using ddgs with specific backend.
    Returns: (url, success, backend_used)
    """
    query = f'{search_query} site:argos.co.uk'
    
    try:
        # Initialize DDGS
        ddgs = DDGS(timeout=CONFIG['search_timeout'])
        
        # Perform text search with specific backend
        results = ddgs.text(
            query=query,
            region='uk-en',
            safesearch='off',
            num_results=CONFIG['num_results'],
            backend=backend
        )
        
        if results:
            # Debug logging
            if CONFIG.get('debug_search', False):
                log_message(f"Search query: {query}", "DEBUG")
                log_message(f"Found {len(results)} results", "DEBUG")
                for idx, result in enumerate(results):
                    log_message(f"  Result {idx+1}: {result.get('href', 'No URL')}", "DEBUG")
                    log_message(f"    Title: {result.get('title', 'No title')[:80]}...", "DEBUG")
            
            # Collect all valid Argos product URLs
            argos_urls = []
            for result in results:
                if 'href' in result:
                    url = result['href']
                    # Clean URL - remove tracking parameters
                    if '?' in url:
                        url = url.split('?')[0]
                    
                    if is_valid_product_url(url) and url not in argos_urls:
                        argos_urls.append(url)
            
            # Sequentially check each URL
            if argos_urls:
                log_message(f"Found {len(argos_urls)} Argos product URLs to check", "INFO")
                
                for idx, url in enumerate(argos_urls):
                    # Skip if already accessed
                    if has_url_been_accessed(url):
                        log_message(f"Skipping already accessed URL: {url}", "INFO")
                        continue
                    
                    log_message(f"Checking URL {idx+1}/{len(argos_urls)}: {url}", "INFO")
                    
                    # Check if product exists (not 404)
                    if check_product_exists(url):
                        # Reset failure count for successful backend
                        if backend in BACKEND_FAILURES:
                            BACKEND_FAILURES[backend] = 0
                        log_message(f"Product exists: {url}", "SUCCESS")
                        return url, True, backend
                    else:
                        log_message(f"Product removed (404), trying next URL", "INFO")
                        continue
                
                log_message(f"All {len(argos_urls)} product URLs returned 404 or were already accessed", "INFO")
            else:
                log_message(f"No Argos product URLs found in search results", "INFO")
        else:
            log_message(f"No search results returned", "INFO")
        
        return None, True, backend
    
    except Exception as e:
        error_msg = str(e).lower()
        if 'ratelimit' in error_msg or '202' in error_msg or '429' in error_msg:
            log_message(f"Rate limit hit for backend {backend}", "WARNING")
            BACKEND_FAILURES[backend] = BACKEND_FAILURES.get(backend, 0) + 1
            return None, False, backend
        elif 'timeout' in error_msg:
            log_message(f"Timeout for backend {backend}", "WARNING")
            return None, True, backend
        elif 'no results found' in error_msg:
            log_message(f"No results found", "INFO")
            return None, True, backend
        else:
            log_message(f"Error with backend {backend}: {str(e)}", "ERROR")
            return None, True, backend

def check_product_exists(url: str) -> bool:
    """
    Check if a product URL returns 404 or exists.
    Returns True if product exists, False if 404.
    """
    # Mark as accessed regardless of result
    mark_url_accessed(url)
    
    try:
        headers = get_random_headers()
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        
        if response.status_code == 404:
            log_message(f"Product page returned 404: {url}", "INFO")
            return False
        elif response.status_code == 200:
            return True
        else:
            # For other status codes, try a GET request
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            if response.status_code == 404:
                log_message(f"Product page returned 404: {url}", "INFO")
                return False
            return response.status_code == 200
    except Exception as e:
        log_message(f"Error checking product existence: {str(e)}", "DEBUG")
        return True

def search_argos_direct(model_number: str) -> Optional[str]:
    """
    Search directly on Argos website using model number.
    This is less rate limited than external search engines.
    """
    search_url = f"https://www.argos.co.uk/search/{quote(model_number)}"
    
    # Skip if already accessed
    if has_url_been_accessed(search_url):
        log_message(f"Skipping already accessed search URL: {search_url}", "INFO")
        return None
    
    try:
        headers = get_random_headers()
        
        # Mark as accessed before making request
        mark_url_accessed(search_url)
        
        response = requests.get(
            search_url,
            headers=headers,
            timeout=CONFIG['request_timeout'],
            allow_redirects=True
        )
        
        if response.status_code == 200:
            final_url = response.url
            
            # Check if redirected directly to a product page
            if is_valid_product_url(final_url):
                log_message(f"Direct redirect to product: {final_url}", "SUCCESS")
                return final_url
            
            # Parse the search results page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for product links in search results
            product_links = []
            
            # Method 1: Look for product links with specific patterns
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if re.search(r'/product/\d+', href):
                    if not href.startswith('http'):
                        href = f"https://www.argos.co.uk{href}"
                    if is_valid_product_url(href) and not has_url_been_accessed(href):
                        product_links.append(href)
            
            # Method 2: Look for clickSR parameter in URL (as in your example)
            if not product_links and 'clickSR=' in final_url:
                # Extract the actual product URL from the parameters
                match = re.search(r'/product/\d+', final_url)
                if match:
                    product_url = f"https://www.argos.co.uk{match.group()}"
                    if is_valid_product_url(product_url) and not has_url_been_accessed(product_url):
                        product_links.append(product_url)
            
            if product_links:
                log_message(f"Found {len(product_links)} product link(s) for model {model_number}", "INFO")
                # Return the first valid product link
                return product_links[0]
            else:
                log_message(f"No product links found in Argos search for model {model_number}", "INFO")
        
    except Exception as e:
        log_message(f"Direct Argos search error: {str(e)}", "ERROR")
    
    return None

def find_product_url_enhanced(product_id: str, search_type: str, search_blocked: Dict) -> Tuple[Optional[str], Dict]:
    """
    Enhanced product URL finder.
    search_type: 'ean' or 'model'
    """
    global CONSECUTIVE_FAILURES
    
    log_message(f"Searching for product URL - {search_type.upper()}: {product_id}")
    
    # Strategy 1: For EAN codes, use search engine rotation
    if search_type == 'ean':
        # Get available backends
        available_backends = []
        for backend in CONFIG['search_backends']:
            if backend in search_blocked and search_blocked[backend]:
                # Check if cooldown period has passed
                if 'last_block_time' in search_blocked and backend in search_blocked['last_block_time']:
                    time_since_block = time.time() - search_blocked['last_block_time'][backend]
                    if time_since_block >= CONFIG['block_cooldown']:
                        search_blocked[backend] = False
                        available_backends.append(backend)
                        log_message(f"Backend {backend} cooldown passed, unblocking", "INFO")
                else:
                    continue
            else:
                available_backends.append(backend)
        
        # Shuffle backends
        random.shuffle(available_backends)
        
        if not available_backends:
            log_message("All backends are blocked, waiting for cooldown", "WARNING")
            return None, search_blocked
        
        for backend in available_backends:
            log_message(f"Trying backend: {backend}")
            
            adaptive_delay(backend)
            
            url, success, used_backend = search_with_ddgs(product_id, backend)
            
            if not success:
                # Backend hit rate limit
                search_blocked[backend] = True
                if 'last_block_time' not in search_blocked:
                    search_blocked['last_block_time'] = {}
                search_blocked['last_block_time'][backend] = time.time()
                CONSECUTIVE_FAILURES += 1
                continue
            
            if url:
                log_message(f"Found URL via {used_backend}: {url}", "SUCCESS")
                CONSECUTIVE_FAILURES = 0
                return url, search_blocked
            else:
                # Search completed but no product found
                log_message(f"No results found for EAN {product_id} - product likely not on Argos", "INFO")
                CONSECUTIVE_FAILURES = 0
                return None, search_blocked
    
    # Strategy 2: For model numbers, use Argos direct search
    elif search_type == 'model':
        log_message(f"Using Argos direct search for model: {product_id}")
        
        adaptive_delay('argos', is_argos_search=True)
        
        url = search_argos_direct(product_id)
        
        if url:
            log_message(f"Found URL via Argos search: {url}", "SUCCESS")
            CONSECUTIVE_FAILURES = 0
            return url, search_blocked
        else:
            log_message(f"No results found for model {product_id} on Argos", "INFO")
            CONSECUTIVE_FAILURES = 0
            return None, search_blocked
    
    return None, search_blocked

# ==============================================================================
# PERSISTENCE FUNCTIONS
# ==============================================================================

def load_persistent_data():
    """Load successful and not found product lists from disk."""
    successful_products = set()
    not_found_products = set()
    search_blocked = {}
    accessed_urls = set()
    
    # Initialize backend tracking
    for backend in CONFIG['search_backends']:
        search_blocked[backend] = False

    # Load successful products
    if os.path.exists(CONFIG['success_file']):
        try:
            with open(CONFIG['success_file'], 'rb') as f:
                successful_products = pickle.load(f)
            log_message(f"Loaded {len(successful_products)} previously successful products")
        except Exception as e:
            log_message(f"Error loading successful products: {str(e)}", "WARNING")

    # Load not found products
    if os.path.exists(CONFIG['not_found_file']):
        try:
            with open(CONFIG['not_found_file'], 'rb') as f:
                not_found_products = pickle.load(f)
            log_message(f"Loaded {len(not_found_products)} products not found on Argos")
        except Exception as e:
            log_message(f"Error loading not found products: {str(e)}", "WARNING")

    # Load search blocked status
    if os.path.exists(CONFIG['blocked_status_file']):
        try:
            with open(CONFIG['blocked_status_file'], 'r') as f:
                loaded_blocked = json.load(f)
                for key, value in loaded_blocked.items():
                    if key in search_blocked or key == 'last_block_time':
                        search_blocked[key] = value
        except Exception as e:
            log_message(f"Error loading blocked status: {str(e)}", "WARNING")

    # Load accessed URLs
    if os.path.exists(CONFIG['accessed_urls_file']):
        try:
            with open(CONFIG['accessed_urls_file'], 'rb') as f:
                accessed_urls = pickle.load(f)
            log_message(f"Loaded {len(accessed_urls)} previously accessed URLs")
        except Exception as e:
            log_message(f"Error loading accessed URLs: {str(e)}", "WARNING")
    
    # Update global accessed URLs
    global ACCESSED_URLS
    ACCESSED_URLS = accessed_urls

    return successful_products, not_found_products, search_blocked

def save_persistent_data(successful_products, not_found_products, search_blocked):
    """Save successful and not found product lists to disk."""
    try:
        with open(CONFIG['success_file'], 'wb') as f:
            pickle.dump(successful_products, f)
    except Exception as e:
        log_message(f"Error saving successful products: {str(e)}", "ERROR")

    try:
        with open(CONFIG['not_found_file'], 'wb') as f:
            pickle.dump(not_found_products, f)
    except Exception as e:
        log_message(f"Error saving not found products: {str(e)}", "ERROR")

    try:
        with open(CONFIG['blocked_status_file'], 'w') as f:
            json.dump(search_blocked, f, indent=2)
    except Exception as e:
        log_message(f"Error saving blocked status: {str(e)}", "ERROR")

    try:
        with open(CONFIG['accessed_urls_file'], 'wb') as f:
            pickle.dump(ACCESSED_URLS, f)
    except Exception as e:
        log_message(f"Error saving accessed URLs: {str(e)}", "ERROR")

# ==============================================================================
# ENVIRONMENT AND DATA FUNCTIONS
# ==============================================================================

def setup_environment():
    """Create necessary directories and files."""
    log_message("Setting up environment", "INFO")

    if not os.path.exists(CONFIG['output_directory']):
        os.makedirs(CONFIG['output_directory'])
        log_message(f"Created output directory: {CONFIG['output_directory']}")

    if not os.path.exists(CONFIG['input_csv']):
        log_message(f"Creating sample {CONFIG['input_csv']} file", "WARNING")
        sample_data = [
            ['5028965808078', 'MODEL123'],
            ['5055812226207', ''],
            ['', 'CHP61.100WH'],
            ['0622356316101', 'ABC789']
        ]
        df = pd.DataFrame(sample_data, columns=['EAN', 'Model'])
        df.to_csv(CONFIG['input_csv'], index=False)
        log_message(f"Sample file created with {len(sample_data)} products")

def fetch_page_content(url, retry_count=0):
    """Fetch page content with retry logic."""
    # Skip if already accessed
    if has_url_been_accessed(url):
        log_message(f"Skipping already accessed URL: {url}", "INFO")
        return None
    
    # Mark as accessed
    mark_url_accessed(url)
    
    try:
        headers = get_random_headers()
        
        response = requests.get(
            url,
            headers=headers,
            timeout=CONFIG['request_timeout']
        )
        response.raise_for_status()
        return response.text

    except requests.exceptions.RequestException as e:
        log_message(f"Request failed (attempt {retry_count + 1}): {str(e)}", "ERROR")

        if retry_count < CONFIG['max_retries'] - 1:
            time.sleep(CONFIG['retry_delay'])
            return fetch_page_content(url, retry_count + 1)

        return None

def extract_product_data(html_content):
    """Extract product data from the page HTML."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Try multiple methods to find product data
        script_tag = soup.find('script', string=lambda t: t and 'window.__data' in t)

        if not script_tag:
            script_tag = soup.find('script', string=lambda t: t and 'window.__PRELOADED_STATE__' in t)

        if not script_tag:
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if '@type' in data and data['@type'] == 'Product':
                        log_message("Found product data in JSON-LD format", "INFO")
                        return {'product': data}
                except:
                    continue

        if not script_tag:
            log_message("No product data script found on page", "WARNING")
            return None

        script_content = script_tag.string

        patterns = [
            (r'window\.__data\s*=\s*({.*?});', 1),
            (r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', 1),
            (r'=\s*({.*})\s*;?\s*$', 1)
        ]

        json_string = None
        for pattern, group in patterns:
            match = re.search(pattern, script_content, re.DOTALL)
            if match:
                json_string = match.group(group)
                break

        if not json_string:
            start_index = script_content.find('{')
            end_index = script_content.rfind('}') + 1
            if start_index != -1 and end_index > 0:
                json_string = script_content[start_index:end_index]

        if not json_string:
            log_message("Could not extract JSON from script tag", "ERROR")
            return None

        # Clean and parse JSON
        json_string = json_string.replace(':undefined', ':null')
        json_string = re.sub(r',\s*}', '}', json_string)
        json_string = re.sub(r',\s*]', ']', json_string)

        data = json.loads(json_string)
        log_message("Successfully extracted product data", "SUCCESS")
        return data

    except json.JSONDecodeError as e:
        log_message(f"JSON parsing error: {str(e)}", "ERROR")
    except Exception as e:
        log_message(f"Data extraction error: {str(e)}", "ERROR")

    return None

def scrape_product(product_id, url):
    """Scrape product data from the given URL."""
    log_message(f"Scraping product data from: {url}")

    html_content = fetch_page_content(url)
    if not html_content:
        return None

    product_data = extract_product_data(html_content)
    if not product_data:
        return None

    safe_id = product_id.replace('/', '_').replace('\\', '_')
    output_path = os.path.join(CONFIG['output_directory'], f"{safe_id}.json")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(product_data, f, ensure_ascii=False, indent=4)

        log_message(f"Saved product data to: {output_path}", "SUCCESS")
        return True

    except Exception as e:
        log_message(f"Failed to save data: {str(e)}", "ERROR")
        return False

def load_products():
    """Load products from the CSV file with EAN and Model columns."""
    try:
        # Read CSV with headers
        products_df = pd.read_csv(CONFIG['input_csv'], dtype=str)
        
        # Check if required columns exist
        if 'EAN' not in products_df.columns or 'Model' not in products_df.columns:
            log_message("CSV must have 'EAN' and 'Model' columns", "ERROR")
            return []
        
        # Replace NaN with empty strings
        products_df = products_df.fillna('')
        
        # Create list of tuples (product_id, search_type)
        products = []
        for _, row in products_df.iterrows():
            ean = str(row['EAN']).strip()
            model = str(row['Model']).strip()
            
            # Priority: use EAN if available, otherwise use model
            if ean:
                products.append((ean, 'ean'))
            elif model:
                products.append((model, 'model'))
            else:
                log_message(f"Row {_ + 1} has neither EAN nor Model, skipping", "WARNING")
        
        log_message(f"Loaded {len(products)} products from CSV", "INFO")
        
        # Count by type
        ean_count = sum(1 for _, t in products if t == 'ean')
        model_count = sum(1 for _, t in products if t == 'model')
        log_message(f"  - {ean_count} with EAN codes", "INFO")
        log_message(f"  - {model_count} with model numbers only", "INFO")
        
        return products

    except FileNotFoundError:
        log_message(f"Input file not found: {CONFIG['input_csv']}", "ERROR")
    except Exception as e:
        log_message(f"Error reading CSV: {str(e)}", "ERROR")

    return []

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

def main():
    """Main execution function."""
    global CONSECUTIVE_FAILURES
    
    log_message("=" * 70)
    log_message("Enhanced Argos Product Data Scraper - Starting")
    log_message("Supports both EAN codes and Model numbers")
    log_message("=" * 70)

    # Install dependencies
    install_dependencies()

    # Setup environment
    setup_environment()

    # Load persistent data
    successful_products, not_found_products, search_blocked = load_persistent_data()

    # Load products from CSV
    products = load_products()
    if not products:
        log_message("No products to process", "ERROR")
        return

    # Filter products based on user preferences and previous results
    products_to_process = []
    skipped_successful = 0
    skipped_not_found = 0

    for product_id, search_type in products:
        if product_id in successful_products and not CONFIG['rescrape_successful']:
            skipped_successful += 1
            continue
        if product_id in not_found_products:
            skipped_not_found += 1
            continue
        products_to_process.append((product_id, search_type))

    log_message(f"Products to process: {len(products_to_process)}")
    log_message(f"Skipped (already successful): {skipped_successful}")
    log_message(f"Skipped (not found on Argos): {skipped_not_found}")

    if not products_to_process:
        log_message("No new products to process", "INFO")
        return

    # Process statistics
    successful = 0
    failed = 0
    not_found = 0

    # Process each product
    for i, (product_id, search_type) in enumerate(products_to_process, 1):
        log_message(f"\nProcessing product {i}/{len(products_to_process)}: {product_id} ({search_type})")
        log_message("-" * 50)

        # Check if too many consecutive failures
        if CONSECUTIVE_FAILURES >= 10:
            log_message("Too many consecutive failures, implementing long cooldown...", "WARNING")
            adaptive_delay(None, True)
            CONSECUTIVE_FAILURES = 0

        # Find product URL
        product_url, search_blocked = find_product_url_enhanced(product_id, search_type, search_blocked)

        if not product_url:
            # Check if all backends are blocked (only relevant for EAN searches)
            if search_type == 'ean':
                all_blocked = all(search_blocked.get(backend, False) 
                                for backend in CONFIG['search_backends'])
                if all_blocked:
                    log_message("All search backends are blocked, waiting for cooldown", "ERROR")
                    save_persistent_data(successful_products, not_found_products, search_blocked)
                    
                    # Calculate minimum wait time
                    min_wait_time = float('inf')
                    for backend in CONFIG['search_backends']:
                        if backend in search_blocked.get('last_block_time', {}):
                            time_since_block = time.time() - search_blocked['last_block_time'][backend]
                            time_remaining = CONFIG['block_cooldown'] - time_since_block
                            if time_remaining > 0 and time_remaining < min_wait_time:
                                min_wait_time = time_remaining
                    
                    if min_wait_time < float('inf'):
                        log_message(f"Minimum wait time: {min_wait_time/60:.1f} minutes", "INFO")
                        if min_wait_time > 300:
                            log_message("Consider resuming the script later", "INFO")
                            break
                    continue
            
            # Product not found
            not_found_products.add(product_id)
            not_found += 1
            continue

        # Add delay before scraping
        if i > 1:
            adaptive_delay('scrape', False)

        # Scrape product
        if scrape_product(product_id, product_url):
            successful_products.add(product_id)
            successful += 1
        else:
            failed += 1

        # Save persistent data periodically
        if i % 5 == 0:
            save_persistent_data(successful_products, not_found_products, search_blocked)

    # Final save of persistent data
    save_persistent_data(successful_products, not_found_products, search_blocked)

    # Summary
    log_message("\n" + "=" * 70)
    log_message("Scraping Complete - Summary")
    log_message(f"Total products processed: {len(products_to_process)}")
    log_message(f"Successful: {successful}")
    log_message(f"Failed: {failed}")
    log_message(f"Not found on Argos: {not_found}")
    log_message(f"Total successful (all time): {len(successful_products)}")
    log_message(f"Total not found (all time): {len(not_found_products)}")
    log_message(f"Total URLs accessed: {len(ACCESSED_URLS)}")
    log_message("=" * 70)

    # Backend status report (for EAN searches)
    log_message("\nBackend Status Report (for EAN searches):")
    for backend in CONFIG['search_backends']:
        status = "BLOCKED" if search_blocked.get(backend, False) else "AVAILABLE"
        failures = BACKEND_FAILURES.get(backend, 0)
        
        if status == "BLOCKED" and 'last_block_time' in search_blocked and backend in search_blocked['last_block_time']:
            time_since_block = time.time() - search_blocked['last_block_time'][backend]
            time_remaining = max(0, CONFIG['block_cooldown'] - time_since_block)
            log_message(f"  {backend}: {status} (failures: {failures}, cooldown: {time_remaining/60:.1f} min remaining)")
        else:
            log_message(f"  {backend}: {status} (failures: {failures})")

    # User instructions
    log_message("\nTips for optimal performance:")
    log_message("- EAN codes use search engine rotation (more rate limited)")
    log_message("- Model numbers use Argos direct search (less rate limited)")
    log_message("- Each URL is accessed only once to prevent duplicates")
    log_message("- Progress is saved automatically and can be resumed")
    
    if not CONFIG['rescrape_successful']:
        log_message("\nNote: To re-scrape already successful products, set")
        log_message("CONFIG['rescrape_successful'] = True")

if __name__ == "__main__":
    main()