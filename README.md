# Tracebound - Asynchronous Web Phrase Scanner

## Overview
Tracebound is a highly optimized, asynchronous web scanner designed to efficiently search for specific phrases within domain-based web content. It leverages modern concurrency techniques, structured logging, and robust error handling to ensure high performance, scalability, and reliability. The scanner is capable of processing thousands of URLs in parallel while maintaining accuracy and security.

## Features
### 🚀 Performance & Speed Enhancements
- **Asynchronous networking** using `aiohttp` to eliminate blocking calls
- **Multi-threaded URL scanning** for parallel execution
- **Connection pooling** to reduce network latency

### ⚙️ Robust Error Handling & Logging
- **Centralized error handling** with structured logging
- **Retry logic with exponential backoff** for transient network errors
- **Logging verbosity control** (silent mode, minimal logs, debug mode)

### 🔍 Advanced Web Scraping
- **Recursive sitemap parsing** to discover hidden URLs
- **Structured data extraction** for better accuracy
- **Optimized HTML parsing** using `BeautifulSoup`

### 🛡️ Security & Compliance
- **Secure request headers** to minimize detection by anti-scraping mechanisms
- **Rate-limiting & request throttling** to prevent being blocked
- **Defensive coding** with safe XML parsing using `defusedxml`

### 📊 Efficient Data Storage & Output Options
- **Supports multiple output formats**: TXT, JSON, CSV
- **Batch file I/O operations** to minimize disk usage
- **Database storage support (future release)**

### 🛠️ Configurability & Ease of Use
- **Command-line arguments** for flexible scanning options
- **Real-time progress tracking** with a progress bar (`tqdm`)
- **Automatic domain protocol detection**

## Installation
### Prerequisites
Ensure you have Python 3.7+ installed. You can install the required dependencies using:
```sh
pip install -r requirements.txt
```

### Required Dependencies
- `aiohttp` (Asynchronous HTTP requests)
- `async_timeout` (Timeout management for async requests)
- `beautifulsoup4` (HTML parsing)
- `defusedxml` (Secure XML parsing)
- `tqdm` (Progress tracking)
- `pyfiglet` (Fancy ASCII banner, optional)

## Usage
### Basic Command
```sh
python tracebound.py <domain> <phrase>
```

### Example
```sh
python tracebound.py example.com "contact us"
```
This will scan `example.com` for occurrences of "contact us" across all indexed pages.

### Advanced Options
| Option | Description |
|--------|-------------|
| `--regex` | Enable regex pattern matching instead of simple text search |
| `--concurrency N` | Set the number of concurrent requests (default: 10) |
| `--timeout N` | Set request timeout in seconds (default: 10) |
| `--output txt/json/csv` | Specify the output format (default: TXT) |
| `--debug` | Enable verbose logging for debugging |

Example with advanced options:
```sh
python tracebound.py example.com "data privacy" --regex --concurrency 20 --output json
```

## How It Works
1. **Domain Validation**: Ensures a valid URL and auto-detects HTTP/HTTPS.
2. **Sitemap Discovery**: Extracts all indexed URLs via `/sitemap.xml`.
3. **Asynchronous Scanning**: Fetches and scans pages concurrently.
4. **Phrase Matching**: Performs case-insensitive or regex-based search.
5. **Logging & Output**: Saves results in TXT, JSON, or CSV format.

## Contribution
Want to contribute? Open a pull request! Feel free to improve performance, add new features, or fix bugs.

## License
This project is licensed under the MIT License.

## Author
Tracebound is developed and maintained by fled-dev.

