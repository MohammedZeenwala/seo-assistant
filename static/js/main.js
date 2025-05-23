/**
 * Main JavaScript for SEO Automation Tool
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Form validation for the SEO form
    const seoForm = document.getElementById('seo-form');
    if (seoForm) {
        seoForm.addEventListener('submit', function(e) {
            const websiteUrl = document.getElementById('website_url').value;
            const keyword = document.getElementById('keyword').value;
            
            // Basic validation
            if (!websiteUrl || !keyword) {
                e.preventDefault();
                alert('Please fill in all required fields');
                return;
            }
            
            // URL validation
            if (!isValidUrl(websiteUrl)) {
                e.preventDefault();
                alert('Please enter a valid URL (including https:// or http://)');
                return;
            }
            
            // Hide the form and show loading animation
            seoForm.classList.add('d-none');
            const loadingAnimation = document.getElementById('loading-animation');
            loadingAnimation.classList.remove('d-none');
            
            // Update loading status with different messages
            const loadingStatus = document.getElementById('loading-status');
            const loadingMessages = [
                `Analyzing ${websiteUrl} for ${keyword} optimization...`,
                `Researching current ${keyword} trends...`,
                `Generating blog post ideas related to ${keyword}...`,
                `Finding high-quality backlink opportunities...`,
                `Creating social bookmarking strategies...`,
                `Optimizing content for search engines...`,
                `Almost there! Finalizing your SEO content...`
            ];
            
            let messageIndex = 0;
            
            // Change loading message every 3 seconds
            const messageInterval = setInterval(function() {
                messageIndex = (messageIndex + 1) % loadingMessages.length;
                loadingStatus.textContent = loadingMessages[messageIndex];
            }, 3000);
            
            // Store the interval ID in the form data to clear it when the page unloads
            window.loadingMessageInterval = messageInterval;
            
            // Continue with form submission
            return true;
        });
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Function to validate URL
    function isValidUrl(url) {
        try {
            new URL(url);
            return true;
        } catch (e) {
            return false;
        }
    }
    
    // Auto-collapse long content sections on results page
    const resultSections = document.querySelectorAll('.collapse.show');
    if (resultSections.length > 3) {
        // Keep only the first section expanded if there are many sections
        for (let i = 1; i < resultSections.length; i++) {
            resultSections[i].classList.remove('show');
        }
    }
    
    // Copy blog content functionality
    const copyBlogButtons = document.querySelectorAll('.copy-blog-btn');
    copyBlogButtons.forEach(button => {
        button.addEventListener('click', function() {
            const blogId = this.getAttribute('data-blog-id');
            // Get all the text content from the blog content div (will include whatever field was rendered)
            const blogContent = document.querySelector(`#blog${blogId} .blog-content`).innerText;
            
            // Remove the "No content available for this blog post." message if present
            const cleanedContent = blogContent.replace('No content available for this blog post.', '').trim();
            
            // Only copy if there's actual content
            if (cleanedContent) {
                copyToClipboard(cleanedContent, this);
            } else {
                alert('No content available to copy');
            }
        });
    });
    
    // Copy backlink strategy functionality
    const copyStrategyButtons = document.querySelectorAll('.copy-strategy-btn');
    copyStrategyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const backlinkId = this.getAttribute('data-backlink-id');
            const backlinkStrategy = document.querySelector(`.backlink-card:nth-child(${backlinkId}) p`).innerText;
            
            copyToClipboard(backlinkStrategy, this);
        });
    });
    
    // Copy social bookmark functionality
    const copyBookmarkButtons = document.querySelectorAll('.copy-bookmark-btn');
    copyBookmarkButtons.forEach(button => {
        button.addEventListener('click', function() {
            const bookmarkId = this.getAttribute('data-bookmark-id');
            const bookmarkTitle = document.querySelector(`.bookmark-card:nth-of-type(${bookmarkId}) h5`).innerText.replace(/^\d+\s+/, '');
            const bookmarkDescription = document.querySelector(`.bookmark-card:nth-of-type(${bookmarkId}) .card-text`).innerText;
            const bookmarkPlatform = document.querySelector(`.bookmark-card:nth-of-type(${bookmarkId}) .platform-badge`).innerText;
            
            const bookmarkContent = `Title: ${bookmarkTitle}\nDescription: ${bookmarkDescription}\nPlatform: ${bookmarkPlatform}`;
            
            copyToClipboard(bookmarkContent, this);
        });
    });
    
    // Helper function to copy content to clipboard
    function copyToClipboard(content, button) {
        // Create a temporary textarea to copy the content
        const textarea = document.createElement('textarea');
        textarea.value = content;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        
        // Change button text temporarily
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check me-1"></i> Copied!';
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-success');
        
        // Reset button after 2 seconds
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-primary');
        }, 2000);
    }
    
    // Add styling for blog content 
    const blogContents = document.querySelectorAll('.blog-content');
    blogContents.forEach(content => {
        content.style.lineHeight = '1.6';
        content.style.fontSize = '1rem';
    });
});
