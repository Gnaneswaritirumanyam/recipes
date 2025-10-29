import pandas as pd
from pymongo import MongoClient
import re
import time
from dotenv import load_dotenv
import os

# Load .env file
env_path = r"C:\Users\tirum\OneDrive\Desktop\Ai Recipes\.env"
load_dotenv(dotenv_path=env_path)

# Read Mongo URL from .env
MONGO_URI = os.getenv("MONGO_URI")

EXCEL_PATH = r"C:\Users\tirum\Downloads\testing.xlsx"
DB_NAME2 = "ingredients"      
COLLECTION_NAME2 = "New recipes"

UNITS = {
    "cup","cups","tablespoon","tablespoons","tbsp","tbsp.","teaspoon","teaspoons","tsp","tsp.","1/2 tablespoon","1/2 tablespoons",
    "gram","grams","g","gm","kg","kgs","kilogram","kilograms","kl","ml","l","litre","liter","pinch","inch","inches","a pinch",
    "bunch","clove","cloves","slice","slices","piece","pieces","packet","packets","can","cans","optional","roasting",
    "stick","sticks","ounce","oz","lb","pound","pkg"
}

def normalize_fraction_string(q: str) -> str:
    """
    Normalize mixed fractions anywhere in the string.c
    Example: '2 1 / 2' -> '2-1/2'
    """
    if not q:
        return q
    s = str(q).strip()
    s = re.sub(r'\s*/\s*', '/', s)                
    s = re.sub(r'(\d+)\s+(\d+/\d+)', r'\1-\2', s) 
    s = re.sub(r'\s*-\s*', '-', s)                
    return s.strip()

def split_item_and_note(text):
    """Split item and note at the first dash if present."""
    parts = re.split(r"\s*-\s*", text, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    else:
        return text.strip(), ""

def parse_ingredients(ingredient_str):
    """Parse ingredients into dicts with only item, quantity, note if present."""
    if pd.isna(ingredient_str) or str(ingredient_str).strip() == "":
        return []

    parsed = []
    for raw in str(ingredient_str).split(","):
        s = raw.strip()
        if not s:
            continue

        # normalize mixed fractions BEFORE splitting
        s = normalize_fraction_string(s)
        lower = s.lower()

        # Handle "to taste", "as required", "as per taste"
        taste_match = None
        if re.search(r"\bto taste\b", lower):
            taste_match = "to taste"
        elif re.search(r"\bas required\b", lower):
            taste_match = "as required"
        elif re.search(r"\bas per taste\b", lower):
            taste_match = "as per taste"
        
        if taste_match:
            name = re.split(r"-|"+taste_match, s, flags=re.I)[0].strip().strip("- ").strip()
            parsed.append({"quantity": taste_match, "item": name})
            continue

        tokens = s.split()
        # Check if starts with number/fraction, including mixed like 2-1/2
        if tokens and re.match(r"^\d+(-\d+/\d+)?$|^\d+/\d+$|^\d+(\.\d+)?$", tokens[0]):
            qty = tokens[0]
            qty_display = qty
            idx = 1
            # Include unit if next token is known
            if idx < len(tokens):
                t1 = tokens[1].lower().rstrip(".,")
                if t1 in UNITS:
                    qty_display = f"{qty} {tokens[1]}"
                    idx += 1
            item_part = " ".join(tokens[idx:]).strip()
            if not item_part:
                item_part = s[len(str(qty_display)):].strip()
            item_main, note_part = split_item_and_note(item_part)
            ingredient_data = {"item": item_main}
            if qty_display:
                ingredient_data["quantity"] = qty_display
            if note_part:
                ingredient_data["note"] = note_part
            parsed.append(ingredient_data)
            continue

        # No numeric quantity present
        item_main, note_part = split_item_and_note(s)
        ingredient_data = {"item": item_main}
        if note_part:
            ingredient_data["note"] = note_part
        parsed.append(ingredient_data)

    return parsed

def main():
    print("Loading Excel...")
    df = pd.read_excel(EXCEL_PATH)

    client = MongoClient(MONGO_URI,
                         serverSelectionTimeoutMS=30000,
                         socketTimeoutMS=30000,
                         connectTimeoutMS=30000)
    db = client[DB_NAME2]
    col = db[COLLECTION_NAME2]

    records = []
    print("Parsing rows...")
    for _, row in df.iterrows():
        rec = row.to_dict()
        raw_ingredients = rec.get("TranslatedIngredients", "") or rec.get("Ingredients", "")
        rec["TranslatedIngredients"] = parse_ingredients(raw_ingredients)
        records.append(rec)

    print(f"Inserting {len(records)} records in batches...")
    batch_size = 500
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        if batch:
            col.insert_many(batch)
        time.sleep(0.1)

    print("✅ Ingredients stored as list of dicts with item, quantity, note if present.")

if __name__ == "__main__":
    main()
