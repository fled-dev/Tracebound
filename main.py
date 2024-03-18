import requests
from bs4 import BeautifulSoup
import re
import pyfiglet
import defusedxml.ElementTree as ET
import concurrent.futures
from termcolor import colored
import time
import os

os.system('cls' if os.name == 'nt' else 'clear')
ascii_logo = pyfiglet.figlet_format("Tracebound v1.0")
print(ascii_logo)
time.sleep(2)

def generate_sitemap_urls(base_url):
    common_locations = ['/sitemap.xml']
    sitemap_urls = [base_url + location for location in common_locations]
    return sitemap_urls

def parse_sitemap(session, sitemap_url):
    response = session.get(sitemap_url)
    page_urls = []
    if response.status_code == 200:
        try:
            root = ET.fromstring(response.content)
            urls = [element.text for element in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
            for url in urls:
                if 'sitemap' in url:
                    page_urls.extend(parse_sitemap(session, url))
                else:
                    page_urls.append(url)
        except ET.ParseError:
            print(f"Error: Unable to parse XML at {sitemap_url}")
    return page_urls

found_count = 0

def scan_page(session, page_url, phrase):
    global found_count
    response = session.get(page_url)
    if response.status_code == 200:
        content = response.content
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        if re.search(phrase, text, re.IGNORECASE):
            found_count += 1
            print(colored(f"\rDiscovered in [{found_count}] pages", 'green'), end="")

def verify_log_file(phrase, page_urls):
    print()
    print()
    print(colored("Success: All URLs were logged to /"+phrase+".txt", 'blue'))

def scan_website(base_url, phrase):
    sitemap_urls = generate_sitemap_urls(base_url)
    session = requests.Session()
    session.headers.update({'User-Agent': 'Tracebound/1.0 Beta (https://tracebound.fled.dev)'})
    all_page_urls = []
    for sitemap_url in sitemap_urls:
        print(colored(f"Looking for sitemaps at {sitemap_url}", 'yellow'))
        page_urls = parse_sitemap(session, sitemap_url)
        all_page_urls.extend(page_urls)
        print(colored(f"Found {len(page_urls)} page URLs in the sitemap", 'yellow'))
        print()
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            executor.map(scan_page, [session]*len(page_urls), page_urls, [phrase]*len(page_urls))
    verify_log_file(phrase, page_urls)


scan_website('http://blockchaininsider.org', 'proof')
