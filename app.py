import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI

# --- Initialize OpenAI client (use env var for API key) ---
client = OpenAI()

# --- Chart Extraction Logic ---
def extract_charts_with_captions(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    charts = []

    for fig in soup.find_all("figure"):
        img = fig.find("img")
        if img and img.get("src"):
            img_url = urljoin(url, img["src"])
            cap_tag = fig.find("figcaption")
            caption = cap_tag.get_text(strip=True) if cap_tag else ""
            charts.append({"image_url": img_url, "caption": caption})

    for img in soup.find_all("img"):
        if img.get("src"):
            img_url = urljoin(url, img["src"])
            caption = img.get("alt", "").strip()
            charts.append({"image_url": img_url, "caption": caption})

    return charts

# --- Convert image URL to binary (bytes) ---
def image_to_binary(image_url):
    response = requests.get(image_url)
    response.raise_for_status()
    return response.content  # raw bytes

# --- Interpret chart with OpenAI ---
def interpret_chart(image_bytes, caption=""):
    # Encode image to base64
    img_base64 = base64.b64encode(image_bytes).decode("utf-8")

    # Call GPT-4o-mini with vision
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # vision-capable model
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Interpret this chart. Caption: {caption}"},
                    {"type": "image_url", "image_url": f"data:image/png;base64,{img_base64}"}
                ]
            }
        ],
        max_tokens=300
    )
    return response.choices[0].message.content


# --- Streamlit UI ---
st.set_page_config(page_title="Chart Extractor & Interpreter", page_icon="📊", layout="wide")

st.title("📊 Chart Extractor + AI Interpreter")

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

                    if st.button(f"Interpret Chart {i} with AI", key=f"ai_{i}"):
                        image_bytes = image_to_binary(item["image_url"])
                        interpretation = interpret_chart(image_bytes, item["caption"])
                        st.write("**AI Interpretation:**")
                        st.info(interpretation)

        except Exception as e:
            st.error(f"Error extracting charts: {str(e)}")
