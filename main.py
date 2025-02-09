#!/usr/bin/env python3
import asyncio
import aiohttp
import async_timeout
import argparse
import logging
import re
import sys
import socket
import time
import os
import json
import csv

from bs4 import BeautifulSoup
import defusedxml.ElementTree as ET
from tqdm import tqdm
import pyfiglet

# ==============================
# Global configuration defaults
# ==============================
DEFAULT_CONCURRENCY = 10
DEFAULT_TIMEOUT = 10  # seconds
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 1  # initial backoff in seconds

# ==============================
# Utility functions
# ==============================
def validate_domain(domain: str) -> str:
    """Ensure that the domain has a proper protocol.
    Try HTTPS first, and fallback to HTTP if needed."""
    domain = domain.strip()
    if not domain.startswith("http://") and not domain.startswith("https://"):
        test_url = "https://" + domain
        try:
            # A quick synchronous check before scanning
            requests_timeout = 5
            import requests  # using requests here only for a quick test
            r = requests.get(test_url, timeout=requests_timeout)
            if r.status_code < 400:
                return "https://" + domain
        except Exception:
            pass
        # Fallback to HTTP
        return "http://" + domain
    return domain

def check_internet_connection() -> bool:
    """Perform a simple connectivity check."""
    try:
        import requests
        requests.get("https://www.google.com", timeout=5)
        return True
    except Exception:
        return False

# ==============================
# The core scanner class
# ==============================
class TraceboundScanner:
    def __init__(self, base_url: str, phrase: str, *,
                 regex: bool = False,
                 concurrency: int = DEFAULT_CONCURRENCY,
                 timeout: int = DEFAULT_TIMEOUT,
                 output_format: str = "txt",
                 debug: bool = False):
        self.base_url = base_url.rstrip('/')
        self.phrase = phrase
        self.regex = regex
        self.concurrency = concurrency
        self.timeout = timeout
        self.output_format = output_format.lower()
        self.debug = debug

        # Compile regex or prepare plain-text search
        if self.regex:
            self.phrase_pattern = re.compile(phrase, re.IGNORECASE)
        else:
            self.phrase_lower = phrase.lower()

        # Containers for results and state
        self.found_urls = []
        self.visited_sitemaps = set()  # avoid re-parsing the same sitemap

        # Setup logger for structured logging
        self.logger = logging.getLogger("TraceboundScanner")
        self.logger.debug("Initialized TraceboundScanner")

    async def fetch(self, url: str, session: aiohttp.ClientSession,
                    retries: int = RETRY_ATTEMPTS) -> str:
        """Fetch a URL with exponential backoff retry."""
        for attempt in range(1, retries + 1):
            try:
                async with async_timeout.timeout(self.timeout), session.get(url) as response:
                    if response.status == 200:
                        self.logger.debug(f"Fetched {url} successfully.")
                        return await response.text()
                    else:
                        self.logger.warning(f"{url} returned status {response.status}")
                        return ""
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self.logger.error(f"Attempt {attempt}: Error fetching {url}: {e}")
                await asyncio.sleep(RETRY_BACKOFF * (2 ** (attempt - 1)))
        self.logger.error(f"Failed to fetch {url} after {retries} attempts.")
        return ""

    async def parse_sitemap(self, sitemap_url: str, session: aiohttp.ClientSession) -> list:
        """Recursively parse a sitemap to extract page URLs."""
        if sitemap_url in self.visited_sitemaps:
            self.logger.debug(f"Already visited sitemap: {sitemap_url}")
            return []
        self.visited_sitemaps.add(sitemap_url)
        self.logger.info(f"Parsing sitemap: {sitemap_url}")
        content = await self.fetch(sitemap_url, session)
        if not content:
            return []
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            self.logger.error(f"XML parse error at {sitemap_url}: {e}")
            return []
        # Namespace for sitemaps
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = []
        for loc in root.findall(".//s:loc", ns):
            url_text = loc.text.strip()
            if "sitemap" in url_text.lower():
                # Nested sitemap – recurse
                nested_urls = await self.parse_sitemap(url_text, session)
                urls.extend(nested_urls)
            else:
                urls.append(url_text)
        return urls

    async def get_all_page_urls(self, session: aiohttp.ClientSession) -> list:
        """Attempt to locate common sitemap files and return all page URLs."""
        sitemap_paths = ['/sitemap.xml', '/sitemap_index.xml']
        tasks = []
        for path in sitemap_paths:
            sitemap_url = f"{self.base_url}{path}"
            self.logger.info(f"Looking for sitemap at: {sitemap_url}")
            tasks.append(self.parse_sitemap(sitemap_url, session))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        page_urls = []
        for result in results:
            if isinstance(result, list):
                page_urls.extend(result)
            else:
                self.logger.error(f"Error retrieving sitemap: {result}")
        unique_urls = list(set(page_urls))
        self.logger.info(f"Found {len(unique_urls)} unique page URLs in sitemaps.")
        return unique_urls

    async def scan_page(self, page_url: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> None:
        """Scan a single page for the phrase."""
        async with semaphore:
            content = await self.fetch(page_url, session)
        if not content:
            return
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text(separator=" ", strip=True)
        found = False
        if self.regex:
            if self.phrase_pattern.search(text):
                found = True
        else:
            if self.phrase_lower in text.lower():
                found = True
        if found:
            self.logger.info(f"Phrase found at: {page_url}")
            self.found_urls.append(page_url)
        else:
            self.logger.debug(f"Phrase not found at: {page_url}")

    async def run(self) -> None:
        """Run the full scan: retrieve sitemaps, scan pages concurrently, and write results."""
        connector = aiohttp.TCPConnector(limit=self.concurrency)
        headers = {
            "User-Agent": "Tracebound/2.0 (https://tracebound.example.com)",
            "Accept": "text/html,application/xhtml+xml,application/xml"
        }
        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            # Get all page URLs from sitemap(s)
            page_urls = await self.get_all_page_urls(session)
            if not page_urls:
                self.logger.error("No page URLs found. Exiting scan.")
                return

            self.logger.info("Beginning page scan...")
            semaphore = asyncio.Semaphore(self.concurrency)
            tasks = [self.scan_page(url, session, semaphore) for url in page_urls]

            # Use tqdm to display progress
            for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Scanning pages"):
                try:
                    await f
                except Exception as e:
                    self.logger.error(f"Error scanning a page: {e}")

            self.logger.info(f"Scan complete. Found phrase on {len(self.found_urls)} pages.")
            await self.write_results()

    async def write_results(self) -> None:
        """Write found URLs to file in the chosen output format."""
        timestamp = int(time.time())
        if self.output_format == "json":
            filename = f"results_{timestamp}.json"
            data = {"found_urls": self.found_urls}
            with open(filename, "w") as f:
                json.dump(data, f, indent=4)
        elif self.output_format == "csv":
            filename = f"results_{timestamp}.csv"
            with open(filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["URL"])
                for url in self.found_urls:
                    writer.writerow([url])
        else:
            # Default to plain text
            filename = f"results_{timestamp}.txt"
            with open(filename, "w") as f:
                for url in self.found_urls:
                    f.write(url + "\n")
        self.logger.info(f"Results written to {filename}")

# ==============================
# Main entry point
# ==============================
def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Tracebound - A scalable, asynchronous domain-based phrase scanner."
    )
    parser.add_argument("domain", nargs="?", help="Domain to scan (e.g. example.com)")
    parser.add_argument("phrase", nargs="?", help="Phrase to search for")
    parser.add_argument("--regex", action="store_true", help="Interpret the phrase as a regular expression")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Number of concurrent requests")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout in seconds")
    parser.add_argument("--output", choices=["txt", "json", "csv"], default="txt", help="Output format for results")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging output")
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("Tracebound")

    # Clear screen and print ASCII art welcome message
    os.system('cls' if os.name == 'nt' else 'clear')
    try:
        ascii_logo = pyfiglet.figlet_format("Tracebound v2.0")
        print(ascii_logo)
    except Exception:
        print("Tracebound v2.0")

    # Check internet connectivity
    if not check_internet_connection():
        logger.error("No internet connection detected. Exiting.")
        sys.exit(1)

    # Interactive input if not provided as arguments
    if not args.domain:
        domain_input = input("Enter the domain you want to scan (e.g. example.com): ").strip()
    else:
        domain_input = args.domain.strip()
    if not args.phrase:
        phrase_input = input("Enter the phrase you want to search for: ").strip()
    else:
        phrase_input = args.phrase.strip()

    # Validate and prepare the domain URL
    domain_url = validate_domain(domain_input)
    logger.info(f"Scanning domain: {domain_url}")
    logger.info(f"Searching for phrase: {phrase_input}")

    # Optionally, check that the domain resolves to an IP address
    try:
        resolved_ip = socket.gethostbyname(domain_input)
        logger.debug(f"Domain {domain_input} resolves to {resolved_ip}")
    except socket.gaierror:
        logger.warning(f"Warning: The domain '{domain_input}' did not resolve to an IP address.")

    # Create and run the scanner
    scanner = TraceboundScanner(
        base_url=domain_url,
        phrase=phrase_input,
        regex=args.regex,
        concurrency=args.concurrency,
        timeout=args.timeout,
        output_format=args.output,
        debug=args.debug
    )

    try:
        asyncio.run(scanner.run())
    except KeyboardInterrupt:
        logger.info("Scan interrupted by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()