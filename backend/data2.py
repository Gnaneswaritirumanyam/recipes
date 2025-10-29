import json
import os

# ---------------- FILE PATHS ----------------
FINAL_DATA_JSON = r"C:\Users\tirum\OneDrive\Desktop\AIRecipes\final_data.recipes.json"
SEPARATED_ING_JSON = r"C:\Users\tirum\OneDrive\Desktop\AIRecipes\separted_ing.json"
IMAGE_FOLDER = "recipes_images"  # relative path for FastAPI static folder

# ---------------- LOAD FILES ----------------
with open(FINAL_DATA_JSON, "r", encoding="utf-8") as f:
    final_data = json.load(f)

with open(SEPARATED_ING_JSON, "r", encoding="utf-8") as f:
    separated_ing = json.load(f)

# ---------------- HELPER ----------------
def normalize_name(name):
    """Lowercase and strip extra spaces for matching"""
    return name.strip().lower()

# Create a lookup dict from separated_ing
lookup_ing = {}
for r in separated_ing:
    lookup_ing[normalize_name(r["TranslatedRecipeName"])] = r.get("main_ingredients", [])

# ---------------- UPDATE FINAL DATA ----------------
updated_count = 0
for r in final_data:
    norm_name = normalize_name(r["TranslatedRecipeName"])
    if norm_name in lookup_ing:
        r["main_ingredients"] = lookup_ing[norm_name]

    # Update image_path to be relative to /static folder
    if "image_path" in r and r["image_path"]:
        filename = os.path.basename(r["image_path"])
        r["image_path"] = os.path.join(IMAGE_FOLDER, filename)
    else:
        r["image_path"] = os.path.join(IMAGE_FOLDER, "default.jpg")
    
    updated_count += 1

# ---------------- SAVE NEW JSON ----------------
OUTPUT_JSON = r"C:\Users\tirum\OneDrive\Desktop\AIRecipes\final_data_updated.recipes.json"
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"✅ Updated {updated_count} recipes!")
print(f"✅ Saved updated JSON to: {OUTPUT_JSON}")
