import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Function to extract chart data from the article
def extract_charts(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None, f"Failed to fetch article: HTTP {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try multiple selectors for article body
        selectors = [
            ('div', {'class': 'post-content'}),
            ('div', {'class': 'content'}),
            ('div', {'class': 'article-body'}),
            ('article', {}),
            ('div', {'id': 'main-content'}),
            ('div', {'class': 'blog-post-content'})
        ]
        
        article_body = None
        for tag, attrs in selectors:
            article_body = soup.find(tag, **attrs)
            if article_body:
                break
        
        if not article_body:
            return None, (
                "Could not find article body. Please inspect the website's HTML to identify the correct container "
                "(e.g., <div class='content'> or <article>). Common classes include 'content', 'article', "
                "'post-body', or 'blog-post-content'. Provide the correct class to update the script."
            )
        
        # Charts: find img tags that look like charts
        charts = []
        for img in article_body.find_all('img'):
            image_url = img.get('src')
            if not image_url:
                continue
            if not image_url.startswith('http'):
                image_url = requests.compat.urljoin(url, image_url)  # Make absolute
            
            alt_text = img.get('alt', '')
            
            # Caption: look for figcaption or next sibling p
            caption = ''
            figcaption = img.find_parent('figure')
            if figcaption:
                cap = figcaption.find('figcaption')
                if cap:
                    caption = cap.get_text(strip=True)
            else:
                next_p = img.find_next('p')
                if next_p:
                    caption = next_p.get_text(strip=True)[:100]  # Truncate if too long
            
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
            
            # Filter if it's a chart
            if any(keyword in alt_text.lower() or keyword in caption.lower() or keyword in image_url.lower() 
                   for keyword in ['chart', 'graph', 'scatter', 'visualization']):
                charts.append({
                    "image_url": image_url,
                    "caption": caption,
                    "context_text": context_text
                })
        
        return charts, None
    except Exception as e:
        return None, f"Error fetching or parsing article: {str(e)}"

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
            charts, error = extract_charts(url)
            if error:
                st.error(error)
            elif not charts:
                st.warning("No charts found in the article. This may occur if the article has no images tagged as charts or if the HTML structure differs from expected.")
            else:
                st.success(f"Found {len(charts)} charts!")
                # Display charts in a table
                df = pd.DataFrame(charts)
                st.dataframe(df, use_container_width=True, column_config={
                    "image_url": st.column_config.LinkColumn("Image URL", display_text="View Image")
                })
                # Optionally display images (uncomment if image URLs are valid)
                # for chart in charts:
                #     st.image(chart['image_url'], caption=chart['caption'], use_column_width=True)

st.markdown("**Note**: If no charts are found or an error occurs, inspect the website's HTML to confirm the article body container class or tag. Contact support for assistance.")