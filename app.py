import os
import logging
import json
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from dotenv import load_dotenv
from utils.together_ai import generate_seo_content, create_sample_seo_data
from utils.google_sheets import save_to_google_sheets

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")

# Make sure the app can run correctly in different environments
is_production = os.environ.get('RENDER', False)

if is_production:
    # In production (e.g., Render), prioritize stability over everything
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    
    # Set a very long session lifetime to prevent unexpected logouts
    app.config['PERMANENT_SESSION_LIFETIME'] = 60 * 60 * 24 * 30  # 30 days
    app.config['SESSION_PERMANENT'] = True
else:
    # Local development
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flask_session')
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

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
        
        logging.debug(f"Form submission: website_url={website_url}, keyword={keyword}")
        
        if not website_url or not keyword:
            flash('Please provide both website URL and target keyword', 'danger')
            return redirect(url_for('index'))
        
        # Generate SEO content using Together AI
        logging.debug("Calling generate_seo_content")
        result = generate_seo_content(website_url, keyword)
        logging.debug(f"generate_seo_content returned type: {type(result)}")
        
        # Check if we got an error message instead of data
        if isinstance(result, tuple) and len(result) == 2:
            error_type, error_msg = result
            logging.error(f"Error from Together AI: {error_type} - {error_msg}")
            flash(f"{error_type}: {error_msg}", 'danger')
            return redirect(url_for('index'))
        
        # If we got valid SEO data
        seo_data = result
        
        # Log seo_data keys and structure for debugging
        logging.debug(f"SEO data keys: {seo_data.keys() if isinstance(seo_data, dict) else 'Not a dictionary'}")
        for key in seo_data.keys() if isinstance(seo_data, dict) else []:
            logging.debug(f"Items in {key}: {len(seo_data.get(key, []))}")
        
        try:
            # Try to save to Google Sheets
            logging.debug("Calling save_to_google_sheets")
            sheet_result = save_to_google_sheets(website_url, keyword, seo_data)
            
            # Check if we got an error from Google Sheets
            if isinstance(sheet_result, tuple) and len(sheet_result) == 2:
                # We still want to proceed, but inform the user about the sheets error
                sheet_url = None
                error_type, error_msg = sheet_result
                logging.warning(f"Google Sheets error: {error_type} - {error_msg}")
                flash(f"Google Sheets: {error_msg}", 'warning')
            else:
                sheet_url = sheet_result
        except Exception as sheets_error:
            logging.error(f"Error with Google Sheets: {str(sheets_error)}")
            sheet_url = None
            flash(f"Google Sheets error: {str(sheets_error)}", 'warning')
        
        # Store data in session for display and download
        try:
            # Make sure seo_data is JSON serializable by creating a simplified version
            simplified_data = {"blogs": [], "backlinks": [], "bookmarks": []}
            
            # Process blogs
            if isinstance(seo_data, dict) and "blogs" in seo_data and isinstance(seo_data["blogs"], list):
                for blog in seo_data["blogs"]:
                    if not isinstance(blog, dict):
                        continue
                        
                    blog_item = {}
                    
                    # Get title
                    if "title" in blog:
                        blog_item["title"] = str(blog["title"])
                    else:
                        blog_item["title"] = f"Blog Post {len(simplified_data['blogs']) + 1}"
                    
                    # Get content from various possible fields
                    content = None
                    for field in ["content", "post", "blog_post"]:
                        if field in blog and blog[field]:
                            content = str(blog[field])
                            break
                    
                    blog_item["content"] = content or "No content available for this blog post."
                    simplified_data["blogs"].append(blog_item)
            
            # Process backlinks
            if isinstance(seo_data, dict) and "backlinks" in seo_data and isinstance(seo_data["backlinks"], list):
                for backlink in seo_data["backlinks"]:
                    if not isinstance(backlink, dict):
                        continue
                        
                    backlink_item = {}
                    
                    # Map common field names
                    backlink_item["platform"] = str(backlink.get("platform", backlink.get("website", "Unknown Platform")))
                    backlink_item["keyword"] = str(backlink.get("keyword", ""))
                    backlink_item["strategy"] = str(backlink.get("strategy", ""))
                    
                    simplified_data["backlinks"].append(backlink_item)
            
            # Process bookmarks
            if isinstance(seo_data, dict) and "bookmarks" in seo_data and isinstance(seo_data["bookmarks"], list):
                for bookmark in seo_data["bookmarks"]:
                    if not isinstance(bookmark, dict):
                        continue
                        
                    bookmark_item = {}
                    
                    # Map common field names
                    bookmark_item["title"] = str(bookmark.get("title", ""))
                    bookmark_item["description"] = str(bookmark.get("description", ""))
                    bookmark_item["platform"] = str(bookmark.get("platform", ""))
                    
                    simplified_data["bookmarks"].append(bookmark_item)
            
            # If we have empty sections, add at least one sample item
            if not simplified_data["blogs"]:
                simplified_data["blogs"] = [{"title": "Sample Blog Title", "content": "Sample blog content would appear here."}]
                
            if not simplified_data["backlinks"]:
                simplified_data["backlinks"] = [{"platform": "Sample Platform", "keyword": keyword, "strategy": "Sample strategy for backlinks."}]
                
            if not simplified_data["bookmarks"]:
                simplified_data["bookmarks"] = [{"title": "Sample Bookmark", "description": "Sample bookmark description.", "platform": "Sample Platform"}]
            
            # Store the simplified data in the session
            session['seo_data'] = simplified_data
            session['website_url'] = website_url
            session['keyword'] = keyword
            session['sheet_url'] = sheet_url
            
            logging.debug("Data stored in session successfully")
            
            # Redirect to results page
            return redirect(url_for('results'))
        except Exception as session_error:
            logging.error(f"Error storing data in session: {str(session_error)}")
            import traceback
            logging.error(traceback.format_exc())
            
            # As a final fallback, create a new sample dataset and show that
            try:
                sample_data = create_sample_seo_data(website_url, keyword)
                session['seo_data'] = sample_data
                session['website_url'] = website_url
                session['keyword'] = keyword
                session['sheet_url'] = None
                flash("We encountered an issue processing your request, but we've generated sample content for you.", 'warning')
                return redirect(url_for('results'))
            except:
                flash(f"Error storing results: {str(session_error)}", 'danger')
                return redirect(url_for('index'))
        
    except Exception as e:
        logging.error(f"Error in generate function: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
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
    import traceback
    logging.error(f"Server error: {str(e)}")
    logging.error(traceback.format_exc())
    
    # Create a new session if needed - this is useful for Render deployment
    try:
        # Clear the session and create a new one
        session.clear()
        session['initialized'] = True
    except Exception as session_error:
        logging.error(f"Error managing session: {session_error}")
    
    # More robust error handling for production environments
    try:
        # Only redirect to index with a message (don't try to generate sample data)
        flash('An unexpected error occurred. Please try again with a different URL or keyword.', 'danger')
        return redirect(url_for('index'))
    except:
        # If redirect fails, render the template directly
        return render_template('index.html', error_message='An unexpected error occurred. Please try again.'), 500
