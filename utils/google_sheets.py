import os
import json
import base64
import logging
import tempfile
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

def get_google_credentials():
    """
    Get Google API credentials from environment variables.
    
    Returns:
        Credentials or tuple: Google API credentials if successful,
                             or tuple (None, error_message) if unsuccessful
    """
    try:
        # Try to get the service account info from environment variable
        service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        
        if not service_account_json:
            logging.error("GOOGLE_SERVICE_ACCOUNT_JSON not found in environment variables")
            return None, "The GOOGLE_SERVICE_ACCOUNT_JSON is required but not found. Please add this secret to use the Google Sheets feature."
            
        # Check if the service account JSON is base64 encoded
        try:
            # Try to decode as base64
            service_account_info = json.loads(base64.b64decode(service_account_json))
        except Exception:
            # If not base64, try to use it directly as JSON
            try:
                service_account_info = json.loads(service_account_json)
            except json.JSONDecodeError:
                logging.error("Invalid GOOGLE_SERVICE_ACCOUNT_JSON format")
                return None, "Invalid GOOGLE_SERVICE_ACCOUNT_JSON format. Please ensure it's a valid JSON string or base64 encoded JSON."
        
        # Create a temporary file to store the service account info
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
            json.dump(service_account_info, temp)
            temp_filename = temp.name
            
        # Define the scopes
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        try:
            # Create credentials from the temporary file
            creds = Credentials.from_service_account_file(
                temp_filename, scopes=scopes
            )
            
            # Remove the temporary file
            os.unlink(temp_filename)
            
            return creds
        except Exception as e:
            # Try to remove the temporary file if it exists
            try:
                os.unlink(temp_filename)
            except:
                pass
                
            logging.error(f"Error creating credentials from service account file: {str(e)}")
            return None, "Invalid Google Service Account credentials. Please check your GOOGLE_SERVICE_ACCOUNT_JSON format."
        
    except Exception as e:
        logging.error(f"Error getting Google credentials: {str(e)}")
        return None, f"Error processing Google credentials: {str(e)}"

def save_to_google_sheets(website_url, keyword, seo_data):
    """
    Save SEO data to Google Sheets.
    
    Args:
        website_url (str): The website URL
        keyword (str): The target keyword
        seo_data (dict): The SEO data to save
        
    Returns:
        str or tuple: The URL of the Google Sheet if successful,
                     or tuple (None, error_message) if unsuccessful
    """
    try:
        # Get Google credentials
        credentials_result = get_google_credentials()
        
        # Check if we got an error
        if isinstance(credentials_result, tuple) and credentials_result[0] is None:
            return credentials_result
            
        creds = credentials_result
            
        # Authorize with gspread
        try:
            # Only try to authorize if we have valid credentials (not an error tuple)
            if not isinstance(creds, tuple):
                client = gspread.authorize(creds)
            else:
                # If we have an error tuple, return it
                return creds
        except Exception as e:
            logging.error(f"Error authorizing with Google: {str(e)}")
            return None, "Error connecting to Google Sheets API. Please check your credentials."
        
        # Create a new spreadsheet
        current_date = datetime.now().strftime("%Y-%m-%d")
        spreadsheet_title = f"SEO Automation - {website_url} - {keyword} - {current_date}"
        
        try:
            # Try to create a new spreadsheet
            spreadsheet = client.create(spreadsheet_title)
            
            # Share the spreadsheet with anyone with the link (read-only)
            try:
                spreadsheet.share("", perm_type='anyone', role='reader')
            except Exception as e:
                logging.warning(f"Error sharing spreadsheet: {str(e)}")
                # Continue anyway, as this is not critical
            
            # Get the first sheet
            worksheet = spreadsheet.sheet1
            
            # Rename the first sheet to Summary
            worksheet.update_title("Summary")
            
            # Add summary information
            worksheet.update([
                ["SEO Automation Results"],
                [""],
                ["Website URL:", website_url],
                ["Target Keyword:", keyword],
                ["Generated on:", current_date],
                [""],
                ["Contents:"],
                ["1. Blog Posts"],
                ["2. Backlink Opportunities"],
                ["3. Social Bookmarks"],
                [""]
            ])
            
            # Create a sheet for blog posts
            blog_sheet = spreadsheet.add_worksheet(title="Blog Posts", rows=100, cols=20)
            
            # Add headers
            blog_sheet.update_cell(1, 1, "Blog Title")
            blog_sheet.update_cell(1, 2, "Blog Content")
            
            # Add blog posts
            for i, blog in enumerate(seo_data.get("blogs", []), start=2):
                blog_sheet.update_cell(i, 1, blog.get("title", ""))
                blog_sheet.update_cell(i, 2, blog.get("content", ""))
            
            # Create a sheet for backlink opportunities
            backlink_sheet = spreadsheet.add_worksheet(title="Backlink Opportunities", rows=100, cols=20)
            
            # Add headers
            backlink_sheet.update_cell(1, 1, "Platform/Website")
            backlink_sheet.update_cell(1, 2, "Keyword")
            backlink_sheet.update_cell(1, 3, "Strategy")
            
            # Add backlink opportunities
            for i, backlink in enumerate(seo_data.get("backlinks", []), start=2):
                backlink_sheet.update_cell(i, 1, backlink.get("platform", ""))
                backlink_sheet.update_cell(i, 2, backlink.get("keyword", ""))
                backlink_sheet.update_cell(i, 3, backlink.get("strategy", ""))
            
            # Create a sheet for social bookmarks
            bookmark_sheet = spreadsheet.add_worksheet(title="Social Bookmarks", rows=100, cols=20)
            
            # Add headers
            bookmark_sheet.update_cell(1, 1, "Title")
            bookmark_sheet.update_cell(1, 2, "Description")
            bookmark_sheet.update_cell(1, 3, "Platform")
            
            # Add social bookmarks
            for i, bookmark in enumerate(seo_data.get("bookmarks", []), start=2):
                bookmark_sheet.update_cell(i, 1, bookmark.get("title", ""))
                bookmark_sheet.update_cell(i, 2, bookmark.get("description", ""))
                bookmark_sheet.update_cell(i, 3, bookmark.get("platform", ""))
            
            # Return the spreadsheet URL
            return spreadsheet.url
            
        except Exception as e:
            logging.error(f"Error creating spreadsheet: {str(e)}")
            
            # Try to find an existing spreadsheet with a similar name
            try:
                spreadsheets = client.list_spreadsheet_files()
                for sheet in spreadsheets:
                    if keyword in sheet['name'] and website_url in sheet['name']:
                        # Use the existing spreadsheet
                        return f"https://docs.google.com/spreadsheets/d/{sheet['id']}"
            except Exception as e2:
                logging.error(f"Error finding existing spreadsheet: {str(e2)}")
            
            return None
            
    except Exception as e:
        logging.error(f"Error saving to Google Sheets: {str(e)}")
        return None
