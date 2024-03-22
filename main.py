import requests
from bs4 import BeautifulSoup
import pyfiglet
import defusedxml.ElementTree as ET
from termcolor import colored
import time
import os
import socket

DEBUG = False
WARNINGS = True

class Tracebound:
    def welcome(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        ascii_logo = pyfiglet.figlet_format("Tracebound v1.0")
        print(ascii_logo)
        time.sleep(1)

    def log(message, color):
        if DEBUG == True:
            print(colored(message, color))

    def warning(message):
        if WARNINGS == True:
            print(colored(message, 'yellow'))

    def is_online(self):
        try:
            requests.get('https://google.com')
            Tracebound.log("Success: Internet connection is available", 'green')
        except requests.ConnectionError:
            print(colored("Error: No internet connection", 'red'))
        
    def collect_domain(self):
        domain = input("Enter the domain you want to scan: ")
        # Check if the domain resolves to an IP address
        try:
            ip = socket.gethostbyname(domain)
            Tracebound.log(f"Success: The domain resolves to {ip}", 'green')
        except socket.gaierror:
            print(colored("Error: The domain does not resolve to an IP address", 'red'))
        # Check if the protocol is defined
        if "http://" not in domain and "https://" not in domain:
            # Check whether the domain is using HTTP or HTTPS
            try:
                requests.get('https://' + domain)
                domain = "https://" + domain
            except requests.ConnectionError:
                Tracebound.warning('The domain does not have a valid SSL certificate, falling back to HTTP')
                domain = "http://" + domain
        return domain

    def collect_phrase(self):
        phrase = input("Enter the phrase you want to search for: ")
        return phrase

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
                        page_urls.extend(Tracebound.parse_sitemap(session, url))
                    else:
                        page_urls.append(url)
            except ET.ParseError:
                print(f"Error: Unable to parse XML at {sitemap_url}")
        return page_urls

    found_count = 0

    def scan_page(session, page_url, phrase):
        # Check the page for the phrase
        response = session.get(page_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            if phrase in soup.get_text():
                Tracebound.found_count += 1
                print(colored(f"Found the phrase '{phrase}' at {page_url}", 'green'))
                # Log the URL to a file
                with open(phrase + ".txt", "a") as log_file:
                    log_file.write(page_url + "\n")
            else:
                print(colored(f"Did not find the phrase '{phrase}' at {page_url}", 'red'))
        else:
            print(colored(f"Error: Unable to access {page_url}", 'red'))

    def verify_log_file(phrase):
        # Soon: Function to verify the log file
        # For now, just print a success message
        print(colored("Success: All URLs were logged to /"+phrase+".txt", 'blue'))

    def scan_website(base_url, phrase):
        sitemap_urls = Tracebound.generate_sitemap_urls(base_url)
        session = requests.Session()
        session.headers.update({'User-Agent': 'Tracebound/1.0 Beta (https://tracebound.fled.dev)'})
        all_page_urls = []
        for sitemap_url in sitemap_urls:
            print(colored(f"Looking for sitemaps at {sitemap_url}", 'yellow'))
            sitemap_content = Tracebound.parse_sitemap(session, sitemap_url)
            all_page_urls.extend(sitemap_content)
            print(colored(f"Found [{len(sitemap_content)}] page URLs in the sitemap", 'yellow'))
            print()
            # Create a thread pool to scan the pages
            for page_url in all_page_urls:
                Tracebound.scan_page(session, page_url, phrase)

Tracebound.welcome()
Tracebound.is_online()
domain = Tracebound.collect_domain()
phrase = Tracebound.collect_phrase()
Tracebound.scan_website(domain, phrase)