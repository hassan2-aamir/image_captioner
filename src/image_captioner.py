import requests
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from transformers import AutoProcessor, BlipForConditionalGeneration
from urllib.parse import urljoin
import time

# Load the pretrained processor and model
processor = AutoProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

def download_image(url, max_retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            return img
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(1)  # Wait before retrying

# URL of the page to scrape
url = "https://en.wikipedia.org/wiki/Animal"

# Download the page
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Find all img elements
img_elements = soup.find_all('img')

# Open a file to write the captions
with open("captions.txt", "w", encoding='utf-8') as caption_file:
    for img_element in img_elements:
        img_url = img_element.get('src')
        
        # Skip if no source URL found
        if not img_url:
            continue

        # Skip if the image is an SVG or too small (likely an icon)
        if 'svg' in img_url or '1x1' in img_url:
            continue

        # Correct the URL if it's malformed
        if img_url.startswith('//'):
            img_url = 'https:' + img_url
        elif not img_url.startswith(('http://', 'https://')):
            img_url = urljoin('https://en.wikipedia.org', img_url)

        try:
            # Download and process the image
            raw_image = download_image(img_url)
            
            # Skip small images
            if raw_image.size[0] * raw_image.size[1] < 400:
                continue

            # Convert to RGB (handles PNG with transparency)
            if raw_image.mode in ('RGBA', 'P'):
                raw_image = raw_image.convert('RGB')

            # Process the image
            inputs = processor(raw_image, return_tensors="pt")
            out = model.generate(**inputs, max_new_tokens=50)
            caption = processor.decode(out[0], skip_special_tokens=True)

            # Write the caption to the file
            caption_file.write(f"{img_url}: {caption}\n")
            print(f"Successfully processed: {img_url}")
            
        except Exception as e:
            print(f"Error processing image {img_url}: {str(e)}")
            continue