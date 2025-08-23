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
        time.sleep(5)  # Increased wait for dynamic content
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
            ('div', {'class': 'entry-content'}),
            ('div', {'class': 'post-body'}),
            ('section', {'class': 'content'})
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
                "'post-body', 'entry-content', or 'blog-post-content'. Provide the HTML snippet for assistance."
            )
        
        # Collect all potential chart elements
        all_elements = []
        charts = []
        chart_keywords = ['chart', 'graph', 'scatter', 'visualization', 'figure', 'data', 'plot', 'diagram', 'infographic', 'statistic']
        
        # Check <img>, <figure>, <canvas>, <svg>, and <iframe>
        for element in article_body.find_all(['img', 'figure', 'canvas', 'svg', 'iframe']):
            element_type = element.name
            image_url = None
            alt_text = ''
            class_attr = element.get('class', [])
            class_str = ' '.join(class_attr) if class_attr else ''
            
            if element_type == 'img':
                image_url = element.get('src')
                alt_text = element.get('alt', '')
            elif element_type == 'figure':
                img_tag = element.find('img')
                if img_tag:
                    image_url = img_tag.get('src')
                    alt_text = img_tag.get('alt', '')
            elif element_type in ['canvas', 'svg', 'iframe']:
                image_url = element.get('src', '') or element.get('data-src', '') or f"{element_type}_element_{id(element)}"
            
            if not image_url and element_type not in ['canvas', 'svg']:
                continue
            if image_url and not image_url.startswith('http'):
                image_url = requests.compat.urljoin(url, image_url)
            
            # Caption: look for figcaption, nearby p, or preceding h3/h4
            caption = ''
            if element_type == 'figure':
                cap = element.find('figcaption')
                if cap:
                    caption = cap.get_text(strip=True)
            if not caption:
                next_p = element.find_next('p')
                if next_p:
                    caption = next_p.get_text(strip=True)[:100]
                else:
                    prev_h = element.find_previous(['h3', 'h4'])
                    if prev_h:
                        caption = prev_h.get_text(strip=True)[:100]
            
            # Context text: broader context from surrounding elements
            context_text = ''
            for sibling in [element.previous_sibling, element.next_sibling]:
                if sibling and sibling.string:
                    context_text += sibling.string.strip() + ' '
            if not context_text:
                parent = element.parent
                if parent:
                    context_text = ' '.join(parent.stripped_strings)[:200]
            
            # Store all elements for debugging
            all_elements.append({
                "element_type": element_type,
                "image_url": image_url or f"{element_type}_no_url",
                "alt_text": alt_text,
                "caption": caption,
                "context_text": context_text,
                "class": class_str
            })
            
            # Filter if it's a chart
            if any(keyword in (alt_text.lower() + caption.lower() + image_url.lower() + class_str.lower()) 
                   for keyword in chart_keywords):
                charts.append({
                    "image_url": image_url or f"{element_type}_element",
                    "caption": caption,
                    "context_text": context_text
                })
            # Fallback: check context text for JSON captions
            elif any(keyword in context_text.lower() for keyword in chart_keywords):
                charts.append({
                    "image_url": image_url or f"{element_type}_element",
                    "caption": caption,
                    "context_text": context_text
                })
        
        return charts, all_elements, None
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
            charts, all_elements, error = extract_charts(url)
            if error:
                st.error(error)
            elif not charts:
                st.warning(
                    "No charts found in the article. This may occur if images or elements lack chart-related keywords "
                    "(e.g., 'chart', 'graph', 'scatter', 'figure', 'data', 'plot', 'diagram', 'infographic', 'statistic') "
                    "in alt text, captions, URLs, or classes, or if charts use non-standard HTML (e.g., <canvas>, SVG)."
                )
                # Show all detected elements for debugging
                if all_elements:
                    st.subheader("All Detected Elements (Debug)")
                    df_elements = pd.DataFrame(all_elements)
                    st.dataframe(df_elements, use_container_width=True, column_config={
                        "image_url": st.column_config.LinkColumn("Image URL", display_text="View"),
                        "element_type": "Element Type",
                        "alt_text": "Alt Text",
                        "caption": "Caption",
                        "context_text": "Context Text",
                        "class": "Class"
                    })
            else:
                st.success(f"Found {len(charts)} charts!")
                # Display charts in a table
                df = pd.DataFrame(charts)
                st.dataframe(df, use_container_width=True, column_config={
                    "image_url": st.column_config.LinkColumn("Image URL", display_text="View")
                })
                # Optionally display images (uncomment if URLs are valid)
                # for chart in charts:
                #     if chart['image_url'].startswith('http'):
                #         st.image(chart['image_url'], caption=chart['caption'], use_column_width=True)

st.markdown(
    "**Troubleshooting**: If no charts are found, check the 'All Detected Elements' table for clues. "
    "Inspect the website's HTML (right-click a chart, select 'Inspect') to confirm chart elements (e.g., <img>, <figure>, <canvas>, SVG). "
    "Share the HTML snippet, including tags, classes, or attributes, for precise adjustments. "
    "Contact support at [email@example.com] for assistance."
)