#!/usr/bin/env python3

import os
import sqlite3
import datetime
import logging
import sys
from flask import Flask, render_template, send_from_directory, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
import scraper

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/app/logs/app.log'), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('acea_webapp')

# Constants
DB_PATH = '/app/data/database.db'
PDF_DIR = '/app/data/pdfs'
LOG_FILE = '/app/logs/scraper.log'

# Get the absolute path to the templates directory
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
logger.info(f"Template directory path: {template_dir}")

# List files in the templates directory to verify
try:
    template_files = os.listdir(template_dir)
    logger.info(f"Template files found: {template_files}")
except Exception as e:
    logger.error(f"Error listing template files: {e}")
    template_files = []

# Create Flask app with explicit template folder
app = Flask(__name__, template_folder=template_dir)

# Add debug routes
@app.route('/health')
def health_check():
    """Simple health check endpoint that doesn't require templates."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.datetime.now().isoformat(),
        'template_dir': template_dir,
        'template_files': template_files,
        'db_exists': os.path.exists(DB_PATH),
        'pdf_dir_exists': os.path.exists(PDF_DIR)
    })

@app.route('/debug')
def debug_info():
    """Return debug information about the environment."""
    env_vars = {k: v for k, v in os.environ.items()}
    dirs = {
        'current': os.listdir('.'),
        'app': os.listdir('/app') if os.path.exists('/app') else [],
        'templates': template_files,
        'data': os.listdir('/app/data') if os.path.exists('/app/data') else []
    }
    
    return jsonify({
        'environment': env_vars,
        'directories': dirs,
        'python_path': sys.path
    })

def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def run_scraper():
    """Run the scraper from the scheduler."""
    logger.info("Running scheduled scraper job")
    try:
        scraper.main()
    except Exception as e:
        logger.error(f"Error in scheduled scraper job: {e}")

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(run_scraper, 'interval', hours=12)
scheduler.start()

@app.route('/')
def index():
    """Render the homepage with latest reports."""
    conn = get_db_connection()
    
    # Get PC reports
    pc_reports = conn.execute(
        'SELECT * FROM reports WHERE type = "PC" ORDER BY publish_date DESC LIMIT 10'
    ).fetchall()
    
    # Get CV reports
    cv_reports = conn.execute(
        'SELECT * FROM reports WHERE type = "CV" ORDER BY publish_date DESC LIMIT 10'
    ).fetchall()
    
    conn.close()
    
    # Check when the last successful scan happened
    last_scan = "Unknown"
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                for line in reversed(f.readlines()):
                    if "Finished scanning for ACEA reports" in line:
                        last_scan = line.split(" - ")[0]
                        break
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
    
    return render_template(
        'index.html', 
        pc_reports=pc_reports, 
        cv_reports=cv_reports,
        last_scan=last_scan
    )

@app.route('/reports/<report_type>')
def reports(report_type):
    """Show all reports of a specific type."""
    if report_type not in ['PC', 'CV']:
        return jsonify({'error': 'Invalid report type'}), 400
        
    conn = get_db_connection()
    reports = conn.execute(
        'SELECT * FROM reports WHERE type = ? ORDER BY publish_date DESC',
        (report_type,)
    ).fetchall()
    conn.close()
    
    return render_template(
        'reports.html', 
        reports=reports, 
        report_type=report_type
    )

@app.route('/pdf/<path:filename>')
def serve_pdf(filename):
    """Serve a PDF file."""
    return send_from_directory(PDF_DIR, filename)

@app.route('/api/stats')
def stats():
    """Return statistics about the reports."""
    conn = get_db_connection()
    
    pc_count = conn.execute('SELECT COUNT(*) FROM reports WHERE type = "PC"').fetchone()[0]
    cv_count = conn.execute('SELECT COUNT(*) FROM reports WHERE type = "CV"').fetchone()[0]
    
    latest_pc = conn.execute(
        'SELECT publish_date FROM reports WHERE type = "PC" ORDER BY publish_date DESC LIMIT 1'
    ).fetchone()
    
    latest_cv = conn.execute(
        'SELECT publish_date FROM reports WHERE type = "CV" ORDER BY publish_date DESC LIMIT 1'
    ).fetchone()
    
    conn.close()
    
    return jsonify({
        'total_reports': pc_count + cv_count,
        'pc_reports': pc_count,
        'cv_reports': cv_count,
        'latest_pc': latest_pc[0] if latest_pc else None,
        'latest_cv': latest_cv[0] if latest_cv else None
    })

@app.route('/run-scan', methods=['POST'])
def run_scan():
    """Manually trigger a scan."""
    try:
        scraper.main()
        return jsonify({'success': True, 'message': 'Scan completed successfully'})
    except Exception as e:
        logger.error(f"Error in manual scan: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/logs')
def view_logs():
    """View the application logs."""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                logs = f.readlines()
                # Return only the last 100 lines
                logs = logs[-100:]
        else:
            logs = ["No logs found"]
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        logs = [f"Error reading logs: {e}"]
    
    return render_template('logs.html', logs=logs)

if __name__ == '__main__':
    # Initialize database if it doesn't exist
    if not os.path.exists(DB_PATH):
        scraper.init_database()
    
    # Run the Flask app with debug enabled for troubleshooting
    app.run(host='0.0.0.0', port=9734, debug=True)