import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from playwright.sync_api import sync_playwright
import re

# Function to extract chart data from the article
def extract_charts(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            # Simulate scrolling to trigger lazy-loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)  # Wait after scroll
            # Wait for Flourish embeds or timeout after 20s
            page.wait_for_selector("iframe[src*='flourish.studio'], div[class*='flourish'], script[src*='flourish.studio']", timeout=20000)
            soup = BeautifulSoup(page.content(), 'html.parser')
            browser.close()
        
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
            return None, [], [], (
                "Could not find article body. Please inspect the website's HTML to identify the correct container "
                "(e.g., <div class='entry-content'> or <article>). Common classes include 'content', 'article', "
                "'post-body', 'entry-content', or 'blog-post-content'. Provide the HTML snippet for assistance."
            )
        
        # Collect all potential chart elements and HTML snippets
        all_elements = []
        charts = []
        html_snippets = []
        chart_keywords = [
            'chart', 'graph', 'scatter', 'visualization', 'visualisation', 'figure', 'data', 'plot', 
            'diagram', 'infographic', 'statistic', 'flourish', 'eurobarometer', 'seat projection', 
            'issues facing', 'climate vs', 'most important issues'
        ]
        
        # Check <img>, <figure>, <canvas>, <svg>, <iframe>, <div>, <script>
        for element in article_body.find_all(['img', 'figure', 'canvas', 'svg', 'iframe', 'div', 'script']):
            element_type = element.name
            image_url = None
            alt_text = ''
            class_attr = element.get('class', [])
            class_str = ' '.join(class_attr) if class_attr else ''
            data_attrs = ' '.join(f"{k}={v}" for k, v in element.attrs.items() if k.startswith('data-'))
            
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
            elif element_type == 'div' and any(c in class_str.lower() for c in ['flourish', 'chart', 'graph', 'visualization', 'visualisation']):
                image_url = element.get('data-src', '') or f"div_element_{id(element)}"
            elif element_type == 'script' and 'flourish.studio' in str(element):
                # Extract Flourish URL from script content or src
                image_url = re.search(r'(https://public\.flourish\.studio/[^\'"\s]+)', str(element))
                image_url = image_url.group(1) if image_url else element.get('src', f"script_element_{id(element)}")
            
            if not image_url and element_type not in ['canvas', 'svg', 'iframe', 'div', 'script']:
                continue
            if image_url and not image_url.startswith('http') and element_type != 'iframe':
                image_url = requests.compat.urljoin(url, image_url)
            
            # Caption: broader search including nearby headings and divs
            caption = ''
            for tag in ['figcaption', 'p', 'h3', 'h4', 'h5', 'h6', 'div']:
                for i in range(1, 4):  # Check up to 3 elements away
                    next_elem = element
                    prev_elem = element
                    for _ in range(i):
                        if next_elem:
                            next_elem = next_elem.find_next(tag)
                        if prev_elem:
                            prev_elem = prev_elem.find_previous(tag)
                    if next_elem and next_elem.get_text(strip=True):
                        caption = next_elem.get_text(strip=True)[:150]
                        break
                    if prev_elem and prev_elem.get_text(strip=True):
                        caption = prev_elem.get_text(strip=True)[:150]
                        break
                if caption:
                    break
            
            # Context text: include broader range and parent/grandparent text
            context_text = ''
            for i in range(1, 5):  # Check 4 elements before/after
                prev_sib = element
                next_sib = element
                for _ in range(i):
                    if prev_sib:
                        prev_sib = prev_sib.previous_sibling
                    if next_sib:
                        next_sib = next_sib.next_sibling
                if prev_sib and prev_sib.string:
                    context_text += prev_sib.string.strip() + ' '
                if next_sib and next_sib.string:
                    context_text += next_sib.string.strip() + ' '
            if not context_text:
                parent = element.parent
                if parent:
                    context_text = ' '.join(parent.stripped_strings)[:500]
                grandparent = parent.parent if parent else None
                if grandparent:
                    context_text += ' ' + ' '.join(grandparent.stripped_strings)[:500]
            
            # Store HTML snippet with broader context
            html_context = element.parent if element.parent else element
            html_snippet = str(html_context)[:1500]  # Include parent context
            if len(str(html_context)) > 1500:
                html_snippet += '...'
            
            # Store all elements for debugging
            all_elements.append({
                "element_type": element_type,
                "image_url": image_url or f"{element_type}_no_url",
                "alt_text": alt_text,
                "caption": caption,
                "context_text": context_text,
                "class": class_str,
                "data_attrs": data_attrs,
                "html_snippet": html_snippet
            })
            
            # Filter if it's a chart
            text_to_check = (alt_text.lower() + caption.lower() + image_url.lower() + 
                            class_str.lower() + context_text.lower() + data_attrs.lower())
            if (any(keyword in text_to_check for keyword in chart_keywords) or 
                'flourish.studio' in image_url.lower()):
                charts.append({
                    "image_url": image_url or f"{element_type}_element",
                    "caption": caption,
                    "context_text": context_text
                })
        
        return charts, all_elements, html_snippets, None
    except Exception as e:
        return None, [], [], f"Error fetching or parsing article: {str(e)}"

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
            charts, all_elements, html_snippets, error = extract_charts(url)
            if error:
                st.error(error)
            elif not charts:
                st.warning(
                    "No charts found in the article. This may occur if elements lack chart-related keywords "
                    "(e.g., 'chart', 'graph', 'scatter', 'visualization', 'visualisation', 'figure', 'data', 'plot', "
                    "'diagram', 'infographic', 'statistic', 'flourish', 'eurobarometer', 'seat projection', "
                    "'issues facing', 'climate vs', 'most important issues') in alt text, captions, URLs, classes, "
                    "or data attributes, or if charts use non-standard HTML (e.g., <iframe>, <div>, or <script> for "
                    "Flourish visualizations)."
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
                        "class": "Class",
                        "data_attrs": "Data Attributes",
                        "html_snippet": "HTML Snippet"
                    })
                # Show HTML snippets
                if html_snippets:
                    st.subheader("HTML Snippets of Detected Elements")
                    for i, snippet in enumerate(html_snippets, 1):
                        st.code(f"Element {i}:\n{snippet}", language="html")
            else:
                st.success(f"Found {len(charts)} charts!")
                # Display charts in a table
                df = pd.DataFrame(charts)
                st.dataframe(df, use_container_width=True, column_config={
                    "image_url": st.column_config.LinkColumn("Image URL", display_text="View")
                })
                # Display images for valid URLs
                for chart in charts:
                    if chart['image_url'].startswith('http'):
                        st.image(chart['image_url'], caption=chart['caption'], use_column_width=True)

st.markdown(
    "**Troubleshooting**: Check the 'All Detected Elements' table and 'HTML Snippets' section. "
    "Inspect the website's HTML (right-click a chart, select 'Inspect') to confirm chart elements "
    "(e.g., <iframe src='https://public.flourish.studio/...'>, <div class='flourish-embed'>, or <script>). "
    "Share the HTML snippet, debug table output, or contact support at [email@example.com] for assistance."
)