import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Function to extract chart data from the article
def extract_charts(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return None, f"Failed to fetch article: {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Assuming article content is in a div with class 'post-content' (adjust based on site inspection)
        article_body = soup.find('div', class_='post-content')  # Replace with actual class/id if different
        
        if not article_body:
            return None, "Could not find article body"
        
        # Charts: find img tags that look like charts
        charts = []
        for img in article_body.find_all('img'):
            image_url = img.get('src')
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
            if any(keyword in alt_text.lower() or keyword in caption.lower() or keyword in image_url.lower() for keyword in ['chart', 'graph', 'scatter', 'visualization']):
                charts.append({
                    "image_url": image_url,
                    "caption": caption,
                    "context_text": context_text
                })
        
        return charts, None
    except Exception as e:
        return None, f"Error: {str(e)}"

# Streamlit app
st.title("Article Chart Extractor")
st.markdown("Enter the URL of an article to extract chart data.")

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
                st.warning("No charts found in the article")
            else:
                st.success(f"Found {len(charts)} charts!")
                # Display charts in a table
                df = pd.DataFrame(charts)
                st.dataframe(df, use_container_width=True)
                # Optionally display images (commented out to avoid broken image links since URLs are null in example)
                # for chart in charts:
                #     st.image(chart['image_url'], caption=chart['caption'])