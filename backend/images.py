import os
import json
import time
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import re


JSON_FILE = r"C:\Users\tirum\OneDrive\Desktop\AIRecipes\separted_ing.json"        
URL_KEY = "URL"                     
NAME_KEY = "TranslatedRecipeName"   
OUTPUT_DIR = r"C:\Users\tirum\OneDrive\Desktop\AIRecipes\recipes_images"       
DELAY = 1                           

# --- Setup ---
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Load JSON ---
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# --- Loop over all URLs ---
for i, item in enumerate(tqdm(data, desc="Scraping images")):
    url = item.get(URL_KEY)
    if not url:
        continue

    recipe_name = item.get(NAME_KEY, f"recipe_{i+1}")
    # Clean recipe name for file name
    recipe_name_clean = re.sub(r'[^A-Za-z0-9]+', '_', recipe_name).strip('_')

    try:
        resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            print(f"Skipping {url} — status {resp.status_code}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1️⃣ Try og:image first
        meta_img = soup.find("meta", property="og:image")
        if meta_img and meta_img.get("content"):
            img_url = meta_img.get("content")
        else:
            # 2️⃣ Fallback: first <img> tag
            image_tag = soup.find("img")
            img_url = image_tag.get("src") if image_tag else None

        if not img_url:
            print(f"No image found at {url}")
            continue

        if img_url.startswith("//"):  # fix protocol-relative URLs
            img_url = "https:" + img_url

        # Download image
        img_data = requests.get(img_url, timeout=15).content
        img_ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
        img_path = os.path.join(OUTPUT_DIR, f"{recipe_name_clean}{img_ext}")

        with open(img_path, "wb") as f:
            f.write(img_data)

        time.sleep(DELAY)  # be polite to the server

    except Exception as e:
        print(f"Error scraping {url}: {e}")
