# Argos Product Scraper - User Guide

The Argos Scraper supports both EAN (European Article Number) codes and model numbers as search inputs.

## Table of Contents
1. [What This Tool Does](#what-this-tool-does)
2. [Before You Start](#before-you-start)
3. [Setting Up Your Product List](#setting-up-your-product-list)
4. [Understanding the Configuration](#understanding-the-configuration)
5. [Running the Scraper](#running-the-scraper)
6. [Understanding the Output](#understanding-the-output)
7. [Converting JSON to CSV](#converting-json-to-csv)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)
10. [Technical Documentation](#technical-documentation)

## What This Tool Does

The Argos Product Scraper is a tool that automatically searches for products on the Argos website and downloads their information. It can search using:
- **EAN codes** (the barcode numbers on products)
- **Model numbers** (the manufacturer's product codes)

The tool saves detailed product information including prices, descriptions, and availability.

## Before You Start

### Required Software
- Python 3.6 or newer installed on your computer, or use Google Colab for simpler environment
- A text editor (like Notepad on Windows or TextEdit on Mac)
- Microsoft Excel or any program that can open CSV files

### What You'll Need
- A list of products with their EAN codes and/or model numbers (with headers included)
- About 10 seconds wait time per product

## Setting Up Your Product List

### Creating Your Input File

1. Create a new spreadsheet with exactly these column headers in row 1:
   - Column A: `EAN`
   - Column B: `Model`

2. Fill in your product data:
   - Put EAN codes (barcode numbers) in column A
   - Put model numbers in column B
   - You can have both EAN and Model for a product, or just one of them, EAN will be used if both available.

### Example Input File

| EAN | Model |
|-----|-------|
| 5028965808078 | MODEL123 |
| 5055812226207 |  |
|  | CHP61.100WH |
| 0622356316101 | ABC789 |

**Important Notes:**
- The column headers MUST be exactly `EAN` and `Model` (case-sensitive)
- If you only have an EAN code, leave the Model column empty
- If you only have a model number, leave the EAN column empty
- The tool will use EAN first if both are provided (it's more accurate)

3. Save the file as `input.csv` in the same folder as the scraper
   - In Excel: File → Save As → Choose "CSV (Comma delimited)"
   - Make sure the filename is exactly `input.csv`

## Understanding the Configuration

The scraper has settings you can adjust. Here's what each setting means:

### File Settings
- **input_csv**: The name of your input file (default: `input.csv`)
- **output_directory**: Where product data is saved (default: `scraped_products` folder)

### Timing Settings (in seconds)
- **min_delay**: Minimum wait between searches (default: 5 seconds)
- **max_delay**: Maximum wait between searches (default: 10 seconds)
- **argos_search_delay**: Wait time for direct Argos searches (default: 3 seconds)
- **block_cooldown**: How long to wait if blocked (default: 30 minutes)

### Search Settings
- **num_results**: How many search results to check per product (default: 3)
- **rescrape_successful**: Whether to re-download already found products (default: False)

### Logging
- **verbose**: Show detailed progress messages (default: True)
- **log_file**: Where to save the activity log (default: `scraper_log.txt`)

**For most users, the default settings work perfectly - you don't need to change anything!**

## Running the Scraper

### Step 1: Prepare Your Files
Make sure your `input.csv` file is in the same folder as `argos_scraper.py`

The folder structure should look like:
```
📁 Your Folder
├── argos_scraper.py
└── input.csv
```

### Step 2: Run the Scraper

#### On Windows:
In powershell in vscode

Type: `python argos_scraper.py`

### Step 3: Monitor Progress
The scraper will show you:
- Which product it's currently searching for
- Whether it found the product
- Any errors or issues
- A summary when complete

**Example output:**
```
Processing product 1/10: 5028965808078 (ean)
Found URL via google: https://www.argos.co.uk/product/1234567
Saved product data to: scraped_products/5028965808078.json
```

## Understanding the Output

### Output Files

The scraper creates several files and folders:

1. **scraped_products/** folder
   - Contains one JSON file per successfully found product
   - Files are named using the EAN or model number

2. **successful_products.pkl**
   - Tracks which products were found successfully
   - Allows you to resume if interrupted

3. **not_found_products.pkl**
   - Lists products that weren't found on Argos
   - Prevents re-searching for products not in stock

4. **scraper_log.txt**
   - Detailed log of all activities
   - Useful for troubleshooting

5. **search_blocked_status.json**
   - Tracks if any search methods are temporarily blocked
   - Usually recovers automatically

6. **accessed_urls.pkl**
   - Prevents checking the same URL twice
   - Improves efficiency

### What Gets Saved

For each product found, the tool saves:
- Product name and description
- Current price
- Previous price (if on sale)
- Delivery information
- Product URL
- Part number
- And much more technical data

## Converting JSON to CSV

The scraper saves data in JSON format (technical format). To convert it to Excel-friendly CSV:

### Step 1: Run the Converter
1. Make sure `json_csv_converter.py` is in the same folder
2. Run it the same way as the scraper:
   - Windows: `python json_csv_converter.py`
   - Mac/Linux: `python3 json_csv_converter.py`

### Step 2: Open the CSV
1. Look for `output.csv` in your folder
2. Open it with Excel or any spreadsheet program

### CSV Contents
The CSV file will contain:
- **searchTerm**: The EAN or model number searched
- **timestamp**: When the data was collected
- **productName**: Full product name from Argos
- **description**: Product description
- **partNumber**: Argos part number
- **price_now**: Current price
- **price_was**: Original price (if on sale)
- **flashText**: Sale information
- **Delivery information**: Free delivery, delivery price, etc.
- **url**: Direct link to the product on Argos

## Troubleshooting

### Common Issues and Solutions

#### "No products to process"
- Check that your CSV file is named correctly: `input.csv`
- Ensure your CSV has the correct column headers: `EAN` and `Model`
- Make sure there's data in at least one column

#### "All search backends are blocked"
- The tool is being rate-limited
- Wait 30 minutes and try again
- Increase from 5 sec to 15 in config

#### "Product not found"
- The product might not be sold by Argos
- Check if the EAN/model number is correct
- Try searching manually on Google to verify

#### Script stops unexpectedly
- The script saves progress automatically
- Just run it again - it will continue from where it left off
- Check `scraper_log.txt` for error details

### Reading the Log File

The `scraper_log.txt` file shows:
- `[INFO]` - Normal operations
- `[WARNING]` - Minor issues (usually self-correcting)
- `[ERROR]` - Problems that need attention
- `[SUCCESS]` - Successful operations

## Best Practices

### For Best Results

1. **Start Small**
   - Test with 5-10 products first
   - Make sure everything works before running hundreds

2. **Use EAN Codes When Possible**
   - EAN codes are more accurate than model numbers
   - Model numbers might match multiple products

3. **Be Patient**
   - The tool runs slowly on purpose
   - This prevents getting blocked
   - Expect about 10 seconds per product

4. **Check Your Data**
   - Check input, output names in csv
   - Verify a few products manually
   - Ensure EAN codes are complete (usually 13 digits)
   - Remove any empty lines

## Technical Documentation

### Architecture

#### Core Components
- **Search Engine Integration** - Uses multiple search backends to find product URLs
- **Adaptive Rate Limiting** - Implements exponential backoff and cooldown periods
- **State Persistence** - Maintains progress across runs using pickle files
- **URL Deduplication** - Prevents redundant requests to accessed URLs
- **Data Extraction** - Parses Argos's JavaScript-rendered product data

### File Structure
```
argos_scraper/
├── argos_scraper.py          # Main scraper implementation
├── json_csv_converter.py     # Converts JSON output to CSV
├── user_guide.md            # Non-technical user documentation
├── README.md               # Technical documentation
├── input.csv       # Input file with EAN/Model columns
├── scraped_products/       # Output directory for JSON files
├── successful_products.pkl  # Persistent success tracking
├── not_found_products.pkl  # Persistent not-found tracking
├── search_blocked_status.json # Search backend rate limit status
├── accessed_urls.pkl       # URL access history
└── scraper_log.txt        # Detailed execution log
```

### Technical Details

#### Dependencies
- **pandas**: CSV file handling and data manipulation
- **requests**: HTTP requests with custom headers
- **beautifulsoup4**: HTML parsing for product data extraction
- **ddgs**: DuckDuckGo search API wrapper for product discovery
- Standard library: json, pickle, os, sys, time, random, re, datetime, urllib

#### Configuration Structure

The `CONFIG` dictionary controls all scraper behavior:

```python
CONFIG = {
    # File paths
    'input_csv': 'input.csv',              # Input CSV filename
    'output_directory': 'scraped_products',         # JSON output directory
    'success_file': 'successful_products.pkl',      # Success tracking
    'not_found_file': 'not_found_products.pkl',     # Not found tracking
    'blocked_status_file': 'search_blocked_status.json',  # Rate limit status
    'accessed_urls_file': 'accessed_urls.pkl',      # URL history
    
    # Timing parameters
    'min_delay': 5,                    # Minimum delay between requests
    'max_delay': 10,                   # Maximum delay between requests
    'argos_search_delay': 3,           # Delay for direct Argos searches
    'block_cooldown': 1800,            # 30-minute cooldown when blocked
    'exponential_backoff_base': 2,     # Backoff multiplier
    'max_backoff_delay': 300,          # Maximum 5-minute backoff
    
    # Search settings
    'num_results': 3,                  # Search results to check per query
    'search_backends': ['google', 'mullvad_google', 'yahoo', 'yandex'],
    'rotate_backends': True,           # Rotate between search providers
    
    # HTTP settings
    'request_timeout': 15,             # Request timeout in seconds
    'user_agents': [...],              # List of browser user agents
    
    # User options
    'rescrape_successful': False,      # Skip already scraped products
    'debug_search': True,              # Enable search result debugging
    'verbose': True,                   # Enable verbose logging
    'log_file': 'scraper_log.txt'     # Log file path
}
```

### Core Functions

#### 1. Dependency Management

**`install_dependencies()`** (lines 103-122)
- **Purpose**: Automatically installs required Python packages if not present
- **Packages installed**: ddgs, pandas, requests, beautifulsoup4
- **Usage**: Called automatically at startup

#### 2. Utility Functions

**`log_message(message, level="INFO")`** (lines 127-139)
- **Purpose**: Centralized logging with timestamps
- **Parameters**:
  - `message`: Log message content
  - `level`: Log level (INFO, WARNING, ERROR, SUCCESS, DEBUG)
- **Output**: Console and file logging based on verbose setting

**`get_random_headers()`** (lines 141-156)
- **Purpose**: Generates browser-like HTTP headers with random User-Agent
- **Returns**: Dictionary of HTTP headers
- **Features**: Includes modern browser headers for stealth

**`adaptive_delay(backend=None, is_blocked=False, is_argos_search=False)`** (lines 158-193)
- **Purpose**: Implements intelligent rate limiting with exponential backoff
- **Parameters**:
  - `backend`: Search backend identifier
  - `is_blocked`: Whether the backend is currently blocked
  - `is_argos_search`: Whether this is a direct Argos search
- **Algorithm**:
  - Base delay with jitter
  - Exponential backoff on failures
  - Separate timing for different backends
  - Tracks last request time per backend

**`is_valid_product_url(url)`** (lines 195-209)
- **Purpose**: Validates if a URL is an Argos product page
- **Returns**: Boolean indicating validity
- **Validation**: Checks URL patterns and excludes non-product pages

**`has_url_been_accessed(url)` / `mark_url_accessed(url)`** (lines 211-218)
- **Purpose**: URL deduplication to prevent redundant requests
- **Implementation**: Uses global set for O(1) lookup

#### 3. Search Functions

**`search_with_ddgs(search_query, backend='auto')`** (lines 223-309)
- **Purpose**: Search for products using DuckDuckGo search API
- **Parameters**:
  - `search_query`: Product identifier (EAN/model)
  - `backend`: Search provider (google, yahoo, etc.)
- **Returns**: Tuple of (url, success, backend_used)
- **Features**:
  - Site-restricted search (site:argos.co.uk)
  - Multiple result checking
  - 404 detection for removed products
  - Debug logging for search results

**`check_product_exists(url)`** (lines 311-337)
- **Purpose**: Verifies if a product URL is still valid (not 404)
- **Method**: HEAD request followed by GET if needed
- **Returns**: Boolean indicating product existence

**`search_argos_direct(model_number)`** (lines 339-406)
- **Purpose**: Direct search on Argos website (less rate-limited)
- **Process**:
  1. Constructs Argos search URL
  2. Checks for direct redirect to product
  3. Parses search results page
  4. Extracts product links
- **Returns**: First valid product URL or None

**`find_product_url_enhanced(product_id, search_type, search_blocked)`** (lines 408-485)
- **Purpose**: Main product discovery orchestrator
- **Parameters**:
  - `product_id`: EAN or model number
  - `search_type`: 'ean' or 'model'
  - `search_blocked`: Backend availability status
- **Strategy**:
  - EAN: Uses search engine rotation
  - Model: Uses direct Argos search
- **Features**: Backend rotation, failure tracking, cooldown management

#### 4. Persistence Functions

**`load_persistent_data()`** (lines 491-544)
- **Purpose**: Restores scraper state from disk
- **Loads**:
  - Successful products set
  - Not found products set
  - Search backend status
  - Accessed URLs history
- **Error handling**: Graceful degradation on corrupt files

**`save_persistent_data(successful_products, not_found_products, search_blocked)`** (lines 546-570)
- **Purpose**: Persists scraper state to disk
- **Saves**: All tracking data for resume capability
- **Format**: Pickle for sets, JSON for status

#### 5. Environment and Data Functions

**`setup_environment()`** (lines 576-595)
- **Purpose**: Creates necessary directories and sample files
- **Creates**:
  - Output directory
  - Sample CSV if missing
- **Sample data**: Demonstrates both EAN and model formats

**`fetch_page_content(url, retry_count=0)`** (lines 596-624)
- **Purpose**: Fetches HTML content with retry logic
- **Features**:
  - URL deduplication check
  - Retry on failure
  - Random headers
- **Returns**: HTML content or None

**`extract_product_data(html_content)`** (lines 626-691)
- **Purpose**: Extracts structured data from Argos product pages
- **Methods tried (in order)**:
  1. window.__data script tag
  2. window.__PRELOADED_STATE__ script tag
  3. JSON-LD structured data
  4. Regex patterns for JavaScript objects
- **Data cleaning**: Handles undefined values, trailing commas
- **Returns**: Parsed JSON data or None

**`scrape_product(product_id, url)`** (lines 693-717)
- **Purpose**: Complete scraping pipeline for a single product
- **Process**:
  1. Fetch page content
  2. Extract product data
  3. Save to JSON file
- **File naming**: Sanitizes product ID for filesystem

**`load_products()`** (lines 719-762)
- **Purpose**: Loads product list from CSV input file
- **Requirements**: 'EAN' and 'Model' column headers
- **Priority**: EAN preferred over model when both present
- **Returns**: List of (product_id, search_type) tuples

#### 6. Main Execution

**`main()`** (lines 768-917)
- **Purpose**: Main program orchestrator
- **Workflow**:
  1. Environment setup and dependency installation
  2. Load persistent state
  3. Load and filter product list
  4. Process each product:
     - Find URL using appropriate strategy
     - Handle rate limiting and blocks
     - Scrape product data
     - Update persistence
  5. Generate summary report
- **Features**:
  - Progress tracking
  - Automatic state saving
  - Backend status reporting
  - User-friendly summary

### Data Flow

1. **Input Processing**
   ```
   CSV File → load_products() → [(product_id, search_type), ...]
   ```

2. **Product Discovery**
   ```
   Product ID → find_product_url_enhanced() → Product URL
                    ├── EAN: search_with_ddgs() → Multiple backends
                    └── Model: search_argos_direct() → Direct search
   ```

3. **Data Extraction**
   ```
   Product URL → fetch_page_content() → HTML
                       ↓
                 extract_product_data() → JSON data
                       ↓
                 Save to scraped_products/
   ```

4. **State Management**
   ```
   Runtime State ←→ Pickle/JSON Files
   ```

### Error Handling

#### Rate Limiting
- Exponential backoff per backend
- 30-minute cooldown on rate limit detection
- Automatic backend rotation for EAN searches

#### Network Errors
- Configurable retry attempts
- Timeout handling
- Graceful degradation

#### Data Errors
- Multiple extraction methods
- JSON parsing error recovery
- Validation of URLs before processing

### Performance Considerations

1. **Adaptive Delays**: Prevents detection and blocking
2. **URL Deduplication**: Avoids redundant requests
3. **State Persistence**: Enables efficient resumption
4. **Backend Rotation**: Distributes load across search providers
5. **Direct Search**: Lower rate limits for model numbers

### Security Considerations

1. **User Agent Rotation**: Mimics real browser behavior
2. **Request Headers**: Full browser header set
3. **Rate Limiting**: Respects server resources
4. **No Authentication**: Accesses only public data

### JSON to CSV Converter (json_csv_converter.py)

#### Purpose
Converts scraped JSON files into a single CSV file for analysis in Excel or other tools.

#### Key Functions

**`parse_json_file(file_path, file_name)`** (lines 41-94)
- **Purpose**: Extracts relevant fields from Argos JSON structure
- **Extracted fields**:
  - searchTerm (from filename)
  - timestamp
  - productName
  - description
  - partNumber
  - price_now, price_was
  - flashText (sale info)
  - Delivery details
  - Product URL
- **Error handling**: Graceful handling of missing fields

**`main()`** (lines 97-154)
- **Purpose**: Orchestrates the conversion process
- **Process**:
  1. Scans scraped_products directory
  2. Parses each JSON file
  3. Aggregates data into DataFrame
  4. Exports to CSV with ordered columns

### Best Practices for Development

1. **Adding New Search Backends**
   - Add to CONFIG['search_backends']
   - Ensure ddgs supports the backend
   - Test rate limiting behavior

2. **Modifying Delays**
   - Consider server load
   - Test with small batches first
   - Monitor for blocking

3. **Extending Data Extraction**
   - Add new patterns to extract_product_data()
   - Update json_csv_converter.py accordingly
   - Maintain backward compatibility

4. **Error Recovery**
   - Always update persistence files
   - Log errors with context
   - Implement graceful degradation

### Maintenance Notes

- **Log Rotation**: Implement log file rotation for long-running instances
- **Cache Cleanup**: Accessed URLs set grows unbounded
- **Backend Health**: Monitor search backend availability
- **Data Validation**: Periodically verify extraction accuracy