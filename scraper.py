#!/usr/bin/env python3

import os
import re
import logging
import requests
import datetime
import time
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
FILES_BASE_URL = 'https://www.acea.auto/files/'

# Ensure directories exist
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs('/app/logs/debug', exist_ok=True)

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

def fetch_page(url, retries=3):
    """Fetch a webpage using exact curl parameters that work."""
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Headers from the successful curl command
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    }
    
    # Cookies from the successful curl command
    cookies = {
        'cookielawinfo-checkbox-necessary': 'yes',
        'cookielawinfo-checkbox-functional': 'no',
        'cookielawinfo-checkbox-performance': 'no',
        'cookielawinfo-checkbox-analytics': 'no',
        'cookielawinfo-checkbox-advertisement': 'no',
        'cookielawinfo-checkbox-others': 'no',
        '_ga': 'GA1.1.1790728309.1742674140'
    }
    
    for attempt in range(retries):
        try:
            # Add a delay between retries with increasing backoff
            if attempt > 0:
                sleep_time = 5 * attempt
                logger.info(f"Waiting {sleep_time} seconds before retry")
                time.sleep(sleep_time)
            
            logger.info(f"Fetching {url} (attempt {attempt+1}/{retries})")
            response = session.get(url, headers=headers, cookies=cookies, timeout=30)
            response.raise_for_status()
            
            # Log successful response info
            logger.info(f"Successfully fetched {url} - Status code: {response.status_code}")
            
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url} (attempt {attempt+1}/{retries}): {e}")
            if attempt == retries - 1:
                return None

def download_pdf(pdf_url, filename):
    """Download a PDF file using exact curl parameters that work."""
    session = requests.Session()
    
    # Headers from the successful curl command
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    }
    
    # Cookies from the successful curl command
    cookies = {
        'cookielawinfo-checkbox-necessary': 'yes',
        'cookielawinfo-checkbox-functional': 'no',
        'cookielawinfo-checkbox-performance': 'no',
        'cookielawinfo-checkbox-analytics': 'no',
        'cookielawinfo-checkbox-advertisement': 'no',
        'cookielawinfo-checkbox-others': 'no',
        '_ga': 'GA1.1.1790728309.1742674140'
    }
    
    try:
        logger.info(f"Downloading PDF: {pdf_url}")
        response = session.get(pdf_url, headers=headers, cookies=cookies, timeout=30)
        
        # Check if we got a successful response
        if response.status_code == 404:
            logger.info(f"PDF not found (404): {pdf_url}")
            return None
            
        response.raise_for_status()
        
        # Quick check if it's actually a PDF (should start with %PDF)
        if not response.content.startswith(b'%PDF'):
            logger.warning(f"Retrieved content is not a PDF: {pdf_url}")
            return None
        
        # Save the PDF
        pdf_path = os.path.join(PDF_DIR, filename)
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Successfully downloaded PDF: {filename} to {pdf_path}")
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

def is_report_processed(url, filename=None):
    """Check if a report URL or filename has already been processed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if filename:
        # Check if the filename exists in any PDF path
        cursor.execute("SELECT id FROM reports WHERE pdf_url = ? OR url = ? OR pdf_path LIKE ?", 
                      (url, url, f'%{filename}'))
    else:
        cursor.execute("SELECT id FROM reports WHERE pdf_url = ? OR url = ?", (url, url))
    
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

def generate_pc_urls():
    """Generate URLs for PC (passenger car) reports."""
    urls = []
    
    # List of all months
    months = [
        'January', 'February', 'March', 'April', 'May', 'June', 
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    
    # Current year and month
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month
    
    # Generate URLs for current year
    for month_idx, month in enumerate(months, 1):
        # Only include months that have already passed
        if month_idx <= current_month:
            # Regular version
            url = f"{FILES_BASE_URL}Press_release_car_registrations_{month}_{current_year}.pdf"
            urls.append(url)
            
            # With rev suffix
            url_rev = f"{FILES_BASE_URL}Press_release_car_registrations_{month}_{current_year}_rev.pdf"
            urls.append(url_rev)
    
    # Generate URLs for previous year
    prev_year = current_year - 1
    for month in months:
        # Regular version
        url = f"{FILES_BASE_URL}Press_release_car_registrations_{month}_{prev_year}.pdf"
        urls.append(url)
        
        # With rev suffix
        url_rev = f"{FILES_BASE_URL}Press_release_car_registrations_{month}_{prev_year}_rev.pdf"
        urls.append(url_rev)
    
    # Special cases for yearly and half-yearly reports
    url_half_year = f"{FILES_BASE_URL}Press_release_car_registrations_first_half_{current_year}.pdf"
    urls.append(url_half_year)
    
    url_full_year = f"{FILES_BASE_URL}Press_release_car_registrations_{prev_year}.pdf"
    urls.append(url_full_year)
    
    return urls

def generate_cv_urls():
    """Generate URLs for CV (commercial vehicle) reports."""
    urls = []
    
    # Current year
    current_year = datetime.datetime.now().year
    
    # Quarterly reports for current year
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_Q1_{current_year}.pdf")
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_Q1-Q2_{current_year}.pdf")
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_Q1-Q3_{current_year}.pdf")
    
    # Quarterly reports with "rev" suffix
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_Q1_{current_year}_rev.pdf")
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_Q1-Q2_{current_year}_rev.pdf")
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_Q1-Q3_{current_year}_rev.pdf")
    
    # Full year reports 
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_{current_year-1}.pdf")
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_{current_year-1}_rev.pdf")
    
    # January-specific reports (sometimes they use a different format)
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_January_{current_year}.pdf")
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_January_{current_year}_rev.pdf")
    
    # Previous year quarterly reports
    prev_year = current_year - 1
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_Q1_{prev_year}.pdf")
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_Q1-Q2_{prev_year}.pdf")
    urls.append(f"{FILES_BASE_URL}Press_release_commercial_vehicle_registrations_Q1-Q3_{prev_year}.pdf")
    
    return urls

def download_direct_pdfs():
    """Try to download all possible PDF files directly."""
    # Get all URLs
    pc_urls = generate_pc_urls()
    cv_urls = generate_cv_urls()
    
    logger.info(f"Generated {len(pc_urls)} PC URLs and {len(cv_urls)} CV URLs to try")
    
    # Download PC reports
    pc_count = 0
    for url in pc_urls:
        # Extract filename from URL
        filename = os.path.basename(url)
        
        # Check if already processed by URL or filename
        if is_report_processed(url, filename):
            logger.info(f"Already processed PC PDF: {url} or {filename}")
            continue
        
        # Try to download
        pdf_path = download_pdf(url, filename)
        if pdf_path:
            # Generate a title from the filename
            title = f"PC Report - {filename.replace('.pdf', '').replace('_', ' ')}"
            
            # Try to extract month and year from the filename
            try:
                parts = filename.split('_')
                month_year = parts[-2] + ' ' + parts[-1].replace('.pdf', '').replace('rev', '')
                date = datetime.datetime.strptime(month_year, '%B %Y')
                publish_date = date.strftime('%Y-%m-%d')
            except:
                publish_date = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # Use URL as both source URL and PDF URL for simplicity
            save_report('PC', title, url, url, pdf_path, publish_date)
            pc_count += 1
        
        # Add a small delay to avoid being blocked
        time.sleep(1)
    
    # Download CV reports
    cv_count = 0
    for url in cv_urls:
        # Extract filename from URL
        filename = os.path.basename(url)
        
        # Check if already processed by URL or filename
        if is_report_processed(url, filename):
            logger.info(f"Already processed CV PDF: {url} or {filename}")
            continue
        
        # Try to download
        pdf_path = download_pdf(url, filename)
        if pdf_path:
            # Generate a title from the filename
            title = f"CV Report - {filename.replace('.pdf', '').replace('_', ' ')}"
            publish_date = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # Use URL as both source URL and PDF URL for simplicity
            save_report('CV', title, url, url, pdf_path, publish_date)
            cv_count += 1
        
        # Add a small delay to avoid being blocked
        time.sleep(1)
    
    logger.info(f"Successfully downloaded {pc_count} PC PDFs and {cv_count} CV PDFs")
    return pc_count + cv_count

def scan_for_new_reports():
    """Scan for new reports using the direct PDF approach."""
    logger.info("Starting scan for new ACEA reports")
    total_downloaded = download_direct_pdfs()
    logger.info(f"Finished scanning for ACEA reports - Downloaded {total_downloaded} new PDFs")

def main():
    """Main function to initialize the database and scan for new reports."""
    logger.info("Starting ACEA report scraper")
    init_database()
    scan_for_new_reports()
    logger.info("Finished scanning for ACEA reports")

if __name__ == "__main__":
    main()