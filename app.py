import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- Chart Extraction Logic ---
def extract_charts_with_captions(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    charts = []

    # Look for <figure> blocks
    for fig in soup.find_all("figure"):
        img = fig.find("img")
        if img and img.get("src"):
            img_url = urljoin(url, img["src"])
            caption = ""
            cap_tag = fig.find("figcaption")
            if cap_tag:
                caption = cap_tag.get_text(strip=True)
            else:
                prev_text = fig.find_previous("p")
                next_text = fig.find_next("p")
                caption = (prev_text.get_text(strip=True) if prev_text else "") or \
                          (next_text.get_text(strip=True) if next_text else "")
            charts.append({"image_url": img_url, "caption": caption})

    # Standalone <img>
    for img in soup.find_all("img"):
        if img.get("src"):
            img_url = urljoin(url, img["src"])
            caption = ""
            if img.get("alt"):
                caption = img["alt"].strip()
            else:
                prev_text = img.find_previous("p")
                next_text = img.find_next("p")
                caption = (prev_text.get_text(strip=True) if prev_text else "") or \
                          (next_text.get_text(strip=True) if next_text else "")
            charts.append({"image_url": img_url, "caption": caption})

    return charts


# --- Streamlit UI ---
st.set_page_config(page_title="Chart Extractor", page_icon="📊", layout="wide")

st.title("📊 Article Chart Extractor")
st.write("Provide an article URL and extract all charts with their captions.")

url = st.text_input("Enter Article URL:", "")

if st.button("Extract Charts"):
    if not url.strip():
        st.warning("Please enter a valid URL.")
    else:
        try:
            with st.spinner("Extracting charts..."):
                charts = extract_charts_with_captions(url)

            if not charts:
                st.error("No charts/images found in this article.")
            else:
                st.success(f"Found {len(charts)} charts/images.")
                for i, item in enumerate(charts, 1):
                    st.subheader(f"Chart {i}")
                    st.image(item["image_url"], use_column_width=True)
                    st.caption(item["caption"] if item["caption"] else "⚠️ No caption found")
        except Exception as e:
            st.error(f"Error extracting charts: {str(e)}")
