#!/usr/bin/env python3

import os
import re
import logging
import requests
import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sqlite3
from dateutil import parser

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/app/logs/scraper.log'), logging.StreamHandler()]
)
logger = logging.getLogger('acea_scraper')

# Constants
BASE_URL = 'https://www.acea.auto'
PRESS_RELEASES_URL = 'https://www.acea.auto/nav/?content=press-releases'
DB_PATH = '/app/data/database.db'
PDF_DIR = '/app/data/pdfs'

# Ensure directories exist
os.makedirs(PDF_DIR, exist_ok=True)

def init_database():
    """Initialize the SQLite database if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        pdf_url TEXT,
        pdf_path TEXT,
        publish_date TEXT,
        created_at TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def fetch_page(url):
    """Fetch a webpage and return the BeautifulSoup object."""
    try:
        # Add headers to simulate a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.acea.auto/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

def download_pdf(pdf_url, filename):
    """Download a PDF file and save it to the PDF directory."""
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        pdf_path = os.path.join(PDF_DIR, filename)
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"Downloaded PDF: {filename}")
        return pdf_path
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading PDF {pdf_url}: {e}")
        return None

def extract_date(date_text):
    """Extract and standardize date from text."""
    try:
        return parser.parse(date_text).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        logger.warning(f"Could not parse date: {date_text}")
        return datetime.datetime.now().strftime('%Y-%m-%d')

def is_report_processed(url):
    """Check if a report URL has already been processed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM reports WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def save_report(report_type, title, url, pdf_url, pdf_path, publish_date):
    """Save report information to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reports (type, title, url, pdf_url, pdf_path, publish_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (report_type, title, url, pdf_url, pdf_path, publish_date, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()
    logger.info(f"Saved report: {title}")

def process_report_page(url, report_type):
    """Process a report page to extract and download the PDF."""
    soup = fetch_page(url)
    if not soup:
        return
    
    # Find PDF link container
    pdf_container = soup.find('div', class_='_pdf_ block-container')
    if not pdf_container:
        logger.warning(f"No PDF container found at {url}")
        return
    
    # Find PDF link
    pdf_link = pdf_container.find('a', class_='btn has-file-icon')
    if not pdf_link:
        logger.warning(f"No PDF link found at {url}")
        return
    
    pdf_url = pdf_link.get('href')
    if not pdf_url:
        logger.warning(f"Empty PDF URL at {url}")
        return
    
    # Ensure absolute URL
    if not pdf_url.startswith('http'):
        pdf_url = urljoin(BASE_URL, pdf_url)
    
    # Extract filename from URL or use title as filename
    pdf_filename = os.path.basename(pdf_url)
    if not pdf_filename.endswith('.pdf'):
        pdf_filename = f"{report_type}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
    
    # Download PDF
    pdf_path = download_pdf(pdf_url, pdf_filename)
    if pdf_path:
        title = pdf_link.text.strip()
        publish_date = extract_date(datetime.datetime.now().strftime('%Y-%m-%d'))
        save_report(report_type, title, url, pdf_url, pdf_path, publish_date)

def scan_for_new_reports():
    """Scan the press releases page for new PC and CV reports."""
    logger.info("Starting scan for new ACEA reports")
    
    soup = fetch_page(PRESS_RELEASES_URL)
    if not soup:
        return
    
    # Look for PC (passenger car) reports
    pc_posts = soup.find_all('div', class_='post container pr-pc global-competitive')
    for post in pc_posts:
        link_element = post.find('h2').find('a')
        if not link_element:
            continue
            
        url = link_element.get('href')
        if not url:
            continue
            
        # Check if we've already processed this report
        if is_report_processed(url):
            logger.info(f"Already processed PC report: {url}")
            continue
            
        logger.info(f"Found new PC report: {url}")
        date_span = post.find('span', class_='terms')
        publish_date = extract_date(date_span.text) if date_span else None
        
        # Process the report page
        process_report_page(url, 'PC')
    
    # Look for CV (commercial vehicle) reports
    cv_posts = soup.find_all('div', class_='post container pr-cv global-competitive')
    for post in cv_posts:
        link_element = post.find('h2').find('a')
        if not link_element:
            continue
            
        url = link_element.get('href')
        if not url:
            continue
            
        # Check if we've already processed this report
        if is_report_processed(url):
            logger.info(f"Already processed CV report: {url}")
            continue
            
        logger.info(f"Found new CV report: {url}")
        date_span = post.find('span', class_='terms')
        publish_date = extract_date(date_span.text) if date_span else None
        
        # Process the report page
        process_report_page(url, 'CV')

def main():
    """Main function to initialize the database and scan for new reports."""
    logger.info("Starting ACEA report scraper")
    init_database()
    scan_for_new_reports()
    logger.info("Finished scanning for ACEA reports")

if __name__ == "__main__":
    main()