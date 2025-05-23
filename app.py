import os
import logging
import json
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from dotenv import load_dotenv
from utils.together_ai import generate_seo_content
from utils.google_sheets import save_to_google_sheets

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("q!9V^kF9z#AeE@dS2&nP1$Wz")

@app.route('/')
def index():
    """Render the home page with the SEO form."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Process the form submission and generate SEO content."""
    try:
        # Get form data
        website_url = request.form.get('website_url')
        keyword = request.form.get('keyword')
        
        if not website_url or not keyword:
            flash('Please provide both website URL and target keyword', 'danger')
            return redirect(url_for('index'))
        
        # Generate SEO content using Together AI
        result = generate_seo_content(website_url, keyword)
        
        # Check if we got an error message instead of data
        if isinstance(result, tuple) and len(result) == 2:
            error_type, error_msg = result
            flash(f"{error_type}: {error_msg}", 'danger')
            return redirect(url_for('index'))
        
        # If we got valid SEO data
        seo_data = result
        
        # Try to save to Google Sheets
        sheet_result = save_to_google_sheets(website_url, keyword, seo_data)
        
        # Check if we got an error from Google Sheets
        if isinstance(sheet_result, tuple) and len(sheet_result) == 2:
            # We still want to proceed, but inform the user about the sheets error
            sheet_url = None
            error_type, error_msg = sheet_result
            flash(f"Google Sheets: {error_msg}", 'warning')
        else:
            sheet_url = sheet_result
        
        # Store data in session for display and download
        session['seo_data'] = seo_data
        session['website_url'] = website_url
        session['keyword'] = keyword
        session['sheet_url'] = sheet_url
        
        # Redirect to results page
        return redirect(url_for('results'))
        
    except Exception as e:
        logging.error(f"Error generating SEO content: {str(e)}")
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/results')
def results():
    """Display the generated SEO content."""
    # Check if we have data in the session
    if 'seo_data' not in session:
        flash('No SEO data available. Please submit the form first.', 'warning')
        return redirect(url_for('index'))
    
    # Get data from session
    seo_data = session['seo_data']
    website_url = session['website_url']
    keyword = session['keyword']
    sheet_url = session.get('sheet_url', None)
    
    return render_template(
        'results.html',
        website_url=website_url,
        keyword=keyword,
        blogs=seo_data.get('blogs', []),
        backlinks=seo_data.get('backlinks', []),
        bookmarks=seo_data.get('bookmarks', []),
        sheet_url=sheet_url
    )

@app.route('/download_csv')
def download_csv():
    """Generate and download the SEO data as a CSV file."""
    if 'seo_data' not in session:
        flash('No SEO data available. Please submit the form first.', 'warning')
        return redirect(url_for('index'))
    
    # Get data from session
    seo_data = session['seo_data']
    website_url = session['website_url']
    keyword = session['keyword']
    
    # Create a string IO object for the CSV data
    si = io.StringIO()
    writer = csv.writer(si)
    
    # Write header
    writer.writerow(['Type', 'Title', 'Content', 'Additional Info'])
    
    # Write blog data
    for blog in seo_data.get('blogs', []):
        writer.writerow(['Blog', blog.get('title', ''), blog.get('content', ''), ''])
    
    # Write backlink data
    for backlink in seo_data.get('backlinks', []):
        writer.writerow([
            'Backlink', 
            backlink.get('keyword', ''), 
            backlink.get('strategy', ''), 
            backlink.get('platform', '')
        ])
    
    # Write bookmark data
    for bookmark in seo_data.get('bookmarks', []):
        writer.writerow([
            'Bookmark', 
            bookmark.get('title', ''), 
            bookmark.get('description', ''), 
            bookmark.get('platform', '')
        ])
    
    # Reset the pointer to the beginning
    si.seek(0)
    
    # Create the response
    output = si.getvalue()
    
    # Create a string buffer
    buf = io.BytesIO()
    buf.write(output.encode('utf-8'))
    buf.seek(0)
    
    # Send the file
    filename = f"seo_data_{website_url.replace('https://', '').replace('http://', '').replace('/', '_')}_{keyword}.csv"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logging.error(f"Server error: {str(e)}")
    flash('An unexpected error occurred. Please try again later.', 'danger')
    return render_template('index.html'), 500
