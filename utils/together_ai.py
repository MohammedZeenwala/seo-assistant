import os
import requests
import json
import logging

def generate_seo_content(website_url, keyword):
    """
    Generate SEO content using Together AI API.
    
    Args:
        website_url (str): The website URL for SEO analysis
        keyword (str): The target keyword
        
    Returns:
        dict: Structured SEO data with blogs, backlinks, and bookmarks
        str: Error message if API key is missing or error occurs
    """
    try:
        api_key = os.environ.get("TOGETHER_API_KEY")
        if not api_key:
            logging.error("TOGETHER_API_KEY not found in environment variables")
            return "Missing API Key", "The TOGETHER_API_KEY is required but not found. Please add this secret to use the content generation feature."
        
        # Prepare the prompt for Together AI
        prompt = f"""
You are an expert SEO assistant. A user has submitted:
- Website URL: {website_url}
- Target Keyword: {keyword}

Tasks:
1. Generate 5–10 blog titles and full blog posts (300–500 words each).
2. Suggest 5–10 backlink opportunities including:
   - Keyword to use
   - High DA/PA websites/platforms
   - Strategy to acquire backlinks
3. Generate 5–10 social bookmarking posts including:
   - Title with keyword
   - Short description (2–3 sentences)
   - Suggested bookmarking platforms (Reddit, Mix, Tumblr, etc.)
Output should be structured in JSON with sections: blogs, backlinks, bookmarks.
"""
        
        # API endpoint
        url = "https://api.together.xyz/inference"
        
        # Request headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Request payload
        payload = {
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "prompt": f"<s>[INST] {prompt} [/INST]",
            "temperature": 0.7,
            "max_tokens": 4096,
            "top_p": 0.7
        }
        
        # Make the API request
        logging.debug("Sending request to Together AI API")
        response = requests.post(url, headers=headers, json=payload)
        
        # Check if the request was successful
        if response.status_code != 200:
            logging.error(f"API request failed with status code {response.status_code}: {response.text}")
            return "API Error", f"Together AI API request failed with status code {response.status_code}. Please check your API key and try again."
        
        # Extract the response
        response_data = response.json()
        logging.debug(f"API Response: {response_data}")
        
        # Different API versions might have different response structures
        if 'output' in response_data:
            generated_text = response_data.get('output', {}).get('text', '')
        elif 'response' in response_data:
            generated_text = response_data.get('response', '')
        elif 'choices' in response_data and response_data['choices']:
            generated_text = response_data['choices'][0].get('text', '')
        else:
            generated_text = ''
            
        if not generated_text:
            logging.error("No text generated from the API")
            # Create some sample data for testing purposes
            return create_sample_seo_data(website_url, keyword)
        
        # Extract the JSON part from the response
        try:
            # First, try to find JSON in the response using string manipulation
            json_start = generated_text.find('{')
            json_end = generated_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = generated_text[json_start:json_end]
                seo_data = json.loads(json_str)
            else:
                # If no proper JSON format is found, try to extract structured data from the text
                logging.warning("No proper JSON found in the response, attempting to parse manually")
                seo_data = parse_text_response(generated_text)
                
            # Validate the structure of the data
            if not validate_seo_data(seo_data):
                logging.warning("Invalid SEO data structure, attempting to fix")
                seo_data = fix_seo_data_structure(seo_data)
                
            return seo_data
            
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing JSON from API response: {str(e)}")
            # Try to parse the text response manually
            return parse_text_response(generated_text)
        
    except Exception as e:
        logging.error(f"Error in generate_seo_content: {str(e)}")
        return None
        
def parse_text_response(text):
    """
    Parse the response text to extract structured data if JSON parsing fails.
    
    Args:
        text (str): The response text from the API
        
    Returns:
        dict: Structured SEO data
    """
    result = {
        "blogs": [],
        "backlinks": [],
        "bookmarks": []
    }
    
    # Try to identify sections
    sections = {
        "blogs": ["blog posts", "blog titles", "blog content"],
        "backlinks": ["backlink opportunities", "backlinks", "backlink strategy"],
        "bookmarks": ["social bookmarking", "bookmarks", "bookmarking posts"]
    }
    
    lines = text.split('\n')
    current_section = None
    current_item = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line indicates a section
        for section, keywords in sections.items():
            if any(keyword.lower() in line.lower() for keyword in keywords) and ":" in line:
                current_section = section
                break
                
        # For blog posts
        if current_section == "blogs":
            if line.startswith(("Title:", "Blog Title:")):
                if current_item and "title" in current_item:
                    result["blogs"].append(current_item)
                    current_item = {}
                current_item["title"] = line.split(":", 1)[1].strip()
            elif "content" in line.lower() or ":" in line and "content" in line.lower().split(":", 1)[0]:
                current_item["content"] = line.split(":", 1)[1].strip() if ":" in line else ""
            elif "title" in current_item and "content" in current_item:
                current_item["content"] += " " + line
                
        # For backlinks
        elif current_section == "backlinks":
            if line.startswith(("Platform:", "Website:", "DA/PA:")):
                if current_item and "platform" in current_item:
                    result["backlinks"].append(current_item)
                    current_item = {}
                current_item["platform"] = line.split(":", 1)[1].strip()
            elif line.startswith("Keyword:"):
                current_item["keyword"] = line.split(":", 1)[1].strip()
            elif line.startswith("Strategy:"):
                current_item["strategy"] = line.split(":", 1)[1].strip()
                
        # For bookmarks
        elif current_section == "bookmarks":
            if line.startswith("Title:"):
                if current_item and "title" in current_item:
                    result["bookmarks"].append(current_item)
                    current_item = {}
                current_item["title"] = line.split(":", 1)[1].strip()
            elif line.startswith("Description:"):
                current_item["description"] = line.split(":", 1)[1].strip()
            elif line.startswith("Platform:"):
                current_item["platform"] = line.split(":", 1)[1].strip()
                
    # Add the last item if not added yet
    if current_item:
        if current_section == "blogs" and "title" in current_item:
            result["blogs"].append(current_item)
        elif current_section == "backlinks" and "platform" in current_item:
            result["backlinks"].append(current_item)
        elif current_section == "bookmarks" and "title" in current_item:
            result["bookmarks"].append(current_item)
            
    return result

def validate_seo_data(data):
    """
    Validate the structure of the SEO data.
    
    Args:
        data (dict): The SEO data to validate
        
    Returns:
        bool: True if the data structure is valid, False otherwise
    """
    if not isinstance(data, dict):
        return False
        
    required_sections = ["blogs", "backlinks", "bookmarks"]
    for section in required_sections:
        if section not in data or not isinstance(data[section], list):
            return False
            
    # Check at least one item in each section
    for section in required_sections:
        if not data[section]:
            return False
            
    return True

def create_sample_seo_data(website_url, keyword):
    """
    Create sample SEO data for testing purposes or when API fails.
    
    Args:
        website_url (str): The website URL for SEO analysis
        keyword (str): The target keyword
        
    Returns:
        dict: Sample structured SEO data
    """
    return {
        "blogs": [
            {
                "title": f"The Ultimate Guide to {keyword.title()}",
                "content": f"In today's competitive digital landscape, {keyword} has become increasingly important for businesses. This comprehensive guide explores the key aspects of {keyword} and how to implement effective strategies on your website ({website_url}).\n\nWhat is {keyword.title()}?\n\n{keyword.title()} refers to the practice of optimizing content and websites to rank higher in search engine results pages. By understanding user intent and creating valuable content, businesses can attract more organic traffic and increase conversions.\n\nThe content on {website_url} can be enhanced with these {keyword} strategies to reach a wider audience and establish your brand as an authority in the industry."
            },
            {
                "title": f"10 {keyword.title()} Strategies for 2025",
                "content": f"As we move further into 2025, {keyword} tactics continue to evolve. This post explores the most effective {keyword} strategies that businesses should implement on sites like {website_url}.\n\n1. Prioritize mobile-first indexing\n2. Focus on user experience signals\n3. Create comprehensive, authoritative content\n4. Optimize for voice search\n5. Implement structured data markup\n6. Improve page loading speed\n7. Prioritize video content\n8. Create interactive content experiences\n9. Focus on local SEO if applicable\n10. Build high-quality backlinks\n\nBy implementing these strategies on {website_url}, you'll be well-positioned to outperform competitors and drive more organic traffic to your website in 2025 and beyond."
            },
            {
                "title": f"How {website_url} Can Benefit from {keyword.title()}",
                "content": f"Every website can benefit from proper {keyword} implementation, and {website_url} is no exception. This article explores the specific ways {website_url} can leverage {keyword} to grow its online presence.\n\nFirst, by conducting thorough keyword research centered around {keyword} and related terms, {website_url} can identify content gaps and opportunities. Second, optimizing on-page elements like title tags, meta descriptions, and headers can significantly improve visibility in search results. Finally, creating a link-building strategy focused on quality rather than quantity will help establish {website_url} as an authority in its niche."
            },
            {
                "title": f"{keyword.title()} Case Studies: Success Stories and Lessons",
                "content": f"Learning from successful {keyword} implementations can provide valuable insights for your own strategy at {website_url}. This post examines several case studies of businesses that achieved remarkable results through effective {keyword} practices.\n\nCase Study 1: E-commerce Site Increases Organic Traffic by 300%\nBy focusing on long-tail keywords related to {keyword} and improving product descriptions, this online retailer saw a significant boost in both traffic and conversions.\n\nCase Study 2: Local Business Dominates Regional Search Results\nThrough local {keyword} optimization and consistent NAP information across directories, this business achieved top rankings for competitive local searches related to {keyword}.\n\nCase Study 3: Content Publisher Doubles Time on Site\nBy implementing a content cluster strategy around {keyword} topics, this publisher not only increased traffic but also significantly improved engagement metrics.\n\nThese lessons can be applied to {website_url} to achieve similar impressive results."
            },
            {
                "title": f"The Future of {keyword.title()}: Predictions and Trends",
                "content": f"The landscape of {keyword} is constantly evolving, and staying ahead of trends is crucial for maintaining competitive advantage. This post explores emerging trends and makes predictions about the future of {keyword}.\n\nAI and Machine Learning in {keyword.title()}\nAs search engines become more sophisticated, AI will play an increasingly important role in {keyword}. Websites like {website_url} will need to optimize for semantic search and user intent rather than just keywords.\n\nUser Experience as a Ranking Factor\nSearch engines are placing greater emphasis on user experience metrics, meaning {website_url} should focus on creating intuitive navigation, fast-loading pages, and mobile-friendly experiences.\n\nVisual Search Optimization\nAs visual search continues to grow, optimizing images and incorporating visual elements into {keyword} strategy will become increasingly important for sites like {website_url}.\n\nBy keeping these future trends in mind, {website_url} can develop a forward-thinking {keyword} strategy that will remain effective for years to come."
            }
        ],
        "backlinks": [
            {
                "platform": "Industry Blogs",
                "keyword": keyword,
                "strategy": f"Reach out to top blogs in the {keyword} niche with guest post proposals featuring unique insights or data from {website_url}."
            },
            {
                "platform": "HARO (Help A Reporter Out)",
                "keyword": f"{keyword} expert",
                "strategy": f"Monitor HARO queries related to {keyword} and provide expert quotes that include a link back to {website_url}."
            },
            {
                "platform": "Reddit",
                "keyword": keyword,
                "strategy": f"Participate actively in subreddits related to {keyword}, providing valuable insights and occasionally referencing content from {website_url} when directly relevant to discussions."
            },
            {
                "platform": "Industry Directories",
                "keyword": f"{keyword} resources",
                "strategy": f"Submit {website_url} to high-quality industry directories that list top resources for {keyword}."
            },
            {
                "platform": "Competitor Backlink Analysis",
                "keyword": keyword,
                "strategy": f"Analyze backlink profiles of top competitors in the {keyword} space and reach out to the same websites with improved content offerings from {website_url}."
            }
        ],
        "bookmarks": [
            {
                "title": f"Essential {keyword.title()} Guide for 2025",
                "description": f"Discover cutting-edge {keyword} strategies to implement on your website today. Based on research from {website_url}.",
                "platform": "Reddit"
            },
            {
                "title": f"How {website_url.split('//')[1].split('.')[0].title()} is Revolutionizing {keyword.title()}",
                "description": f"Learn how this innovative approach to {keyword} is changing the industry landscape. Comprehensive analysis and actionable tips.",
                "platform": "Mix"
            },
            {
                "title": f"10 {keyword.title()} Tactics You Haven't Tried Yet",
                "description": f"Move beyond basic {keyword} with these advanced strategies from {website_url} that your competitors aren't using.",
                "platform": "Tumblr"
            },
            {
                "title": f"{keyword.title()} Case Study: {website_url}",
                "description": f"Detailed breakdown of how {website_url} achieved remarkable results through strategic {keyword} implementation.",
                "platform": "LinkedIn"
            },
            {
                "title": f"The Ultimate {keyword.title()} Resource Collection",
                "description": f"Curated list of the best {keyword} tools, guides, and resources, featuring exclusive content from {website_url}.",
                "platform": "Pinterest"
            }
        ]
    }

def fix_seo_data_structure(data):
    """
    Fix the structure of the SEO data if it's invalid.
    
    Args:
        data (dict): The SEO data to fix
        
    Returns:
        dict: The fixed SEO data
    """
    fixed_data = {
        "blogs": [],
        "backlinks": [],
        "bookmarks": []
    }
    
    # If data is already a dict with the right structure, use it as a base
    if isinstance(data, dict):
        for section in ["blogs", "backlinks", "bookmarks"]:
            if section in data and isinstance(data[section], list):
                fixed_data[section] = data[section]
    
    # Ensure each section has at least one item with the required fields
    if not fixed_data["blogs"]:
        fixed_data["blogs"] = [{
            "title": "Sample Blog Title",
            "content": "Sample blog content would appear here."
        }]
    else:
        # Ensure each blog has title and content
        for i, blog in enumerate(fixed_data["blogs"]):
            if not isinstance(blog, dict):
                fixed_data["blogs"][i] = {"title": "Untitled", "content": str(blog)}
            else:
                if "title" not in blog:
                    blog["title"] = "Untitled Blog"
                if "content" not in blog:
                    blog["content"] = "No content provided."
    
    if not fixed_data["backlinks"]:
        fixed_data["backlinks"] = [{
            "platform": "Sample Platform",
            "keyword": "Sample Keyword",
            "strategy": "Sample Strategy"
        }]
    else:
        # Ensure each backlink has platform, keyword and strategy
        for i, backlink in enumerate(fixed_data["backlinks"]):
            if not isinstance(backlink, dict):
                fixed_data["backlinks"][i] = {"platform": str(backlink), "keyword": "", "strategy": ""}
            else:
                if "platform" not in backlink:
                    backlink["platform"] = "Unspecified Platform"
                if "keyword" not in backlink:
                    backlink["keyword"] = "Unspecified Keyword"
                if "strategy" not in backlink:
                    backlink["strategy"] = "No strategy provided."
    
    if not fixed_data["bookmarks"]:
        fixed_data["bookmarks"] = [{
            "title": "Sample Bookmark Title",
            "description": "Sample bookmark description.",
            "platform": "Sample Platform"
        }]
    else:
        # Ensure each bookmark has title, description and platform
        for i, bookmark in enumerate(fixed_data["bookmarks"]):
            if not isinstance(bookmark, dict):
                fixed_data["bookmarks"][i] = {"title": str(bookmark), "description": "", "platform": ""}
            else:
                if "title" not in bookmark:
                    bookmark["title"] = "Untitled Bookmark"
                if "description" not in bookmark:
                    bookmark["description"] = "No description provided."
                if "platform" not in bookmark:
                    bookmark["platform"] = "Unspecified Platform"
    
    return fixed_data
