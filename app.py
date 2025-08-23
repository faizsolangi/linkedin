import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# Function to extract chart data from the article
def extract_charts(url):
    try:
        # Set up Selenium with headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        
        driver.get(url)
        time.sleep(3)  # Wait for JavaScript to load
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        
        # Try multiple selectors for article body
        selectors = [
            ('div', {'class': 'post-content'}),
            ('div', {'class': 'content'}),
            ('div', {'class': 'article-body'}),
            ('article', {}),
            ('div', {'id': 'main-content'}),
            ('div', {'class': 'blog-post-content'}),
            ('div', {'class': 'entry-content'}),  # Common for WordPress
            ('div', {'class': 'post-body'})
        ]
        
        article_body = None
        for tag, attrs in selectors:
            article_body = soup.find(tag, **attrs)
            if article_body:
                break
        
        if not article_body:
            return None, [], (
                "Could not find article body. Please inspect the website's HTML to identify the correct container "
                "(e.g., <div class='entry-content'> or <article>). Common classes include 'content', 'article', "
                "'post-body', or 'entry-content'. Provide the correct class to update the script."
            )
        
        # Collect all images for debugging
        all_images = []
        charts = []
        for img in article_body.find_all(['img', 'figure']):
            image_url = None
            alt_text = ''
            tag_name = img.name
            
            if tag_name == 'img':
                image_url = img.get('src')
                alt_text = img.get('alt', '')
            elif tag_name == 'figure':
                img_tag = img.find('img')
                if img_tag:
                    image_url = img_tag.get('src')
                    alt_text = img_tag.get('alt', '')
            
            if not image_url:
                continue
            if not image_url.startswith('http'):
                image_url = requests.compat.urljoin(url, image_url)
            
            # Caption: look for figcaption or next sibling p
            caption = ''
            if tag_name == 'figure':
                cap = img.find('figcaption')
                if cap:
                    caption = cap.get_text(strip=True)
            else:
                next_p = img.find_next('p')
                if next_p:
                    caption = next_p.get_text(strip=True)[:100]
            
            # Context text: previous and next sibling text
            context_text = ''
            prev = img.previous_sibling
            if prev and prev.string:
                context_text += prev.string.strip() + ' '
            next_sib = img.next_sibling
            if next_sib and next_sib.string:
                context_text += next_sib.string.strip()
            if not context_text:
                parent = img.parent
                if parent:
                    context_text = ' '.join(parent.stripped_strings)[:200]
            
            # Store all images for debugging
            all_images.append({
                "image_url": image_url,
                "alt_text": alt_text,
                "caption": caption,
                "context_text": context_text,
                "tag": tag_name
            })
            
            # Filter if it's a chart
            keywords = ['chart', 'graph', 'scatter', 'visualization', 'figure', 'data', 'plot', 'diagram']
            if any(keyword in alt_text.lower() or keyword in caption.lower() or keyword in image_url.lower() 
                   for keyword in keywords):
                charts.append({
                    "image_url": image_url,
                    "caption": caption,
                    "context_text": context_text
                })
        
        return charts, all_images, None
    except Exception as e:
        return None, [], f"Error fetching or parsing article: {str(e)}"

# Streamlit app
st.title("Article Chart Extractor")
st.markdown("Enter the URL of an article to extract chart data (image URLs, captions, and context text).")

# Input form
with st.form("url_form"):
    url = st.text_input("Article URL", value="https://eumatrix.eu/en/blog/Right-wing-grows-on-economic-policy-positioning")
    submit_button = st.form_submit_button("Extract Charts")

if submit_button:
    if not url:
        st.error("Please provide a valid URL")
    else:
        with st.spinner("Extracting charts..."):
            charts, all_images, error = extract_charts(url)
            if error:
                st.error(error)
            elif not charts:
                st.warning(
                    "No charts found in the article. This may occur if images lack chart-related keywords "
                    "(e.g., 'chart', 'graph', 'scatter', 'figure') in alt text, captions, or URLs, "
                    "or if the HTML structure differs from expected."
                )
                # Show all images for debugging
                if all_images:
                    st.subheader("All Detected Images (Debug)")
                    df_images = pd.DataFrame(all_images)
                    st.dataframe(df_images, use_container_width=True, column_config={
                        "image_url": st.column_config.LinkColumn("Image URL", display_text="View Image"),
                        "alt_text": "Alt Text",
                        "caption": "Caption",
                        "context_text": "Context Text",
                        "tag": "HTML Tag"
                    })
            else:
                st.success(f"Found {len(charts)} charts!")
                # Display charts in a table
                df = pd.DataFrame(charts)
                st.dataframe(df, use_container_width=True, column_config={
                    "image_url": st.column_config.LinkColumn("Image URL", display_text="View Image")
                })
                # Optionally display images (uncomment if URLs are valid)
                # for chart in charts:
                #     st.image(chart['image_url'], caption=chart['caption'], use_column_width=True)

st.markdown(
    "**Troubleshooting**: If no charts are found, check the 'All Detected Images' table for clues. "
    "Inspect the website's HTML to confirm chart image tags (e.g., <img> or <figure>) and their attributes. "
    "Share the HTML structure or correct container class for further assistance."
)