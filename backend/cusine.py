import json
import re
import os

# Function to check if text is English
def is_english(text):
    if not text:
        return False
    return bool(re.match(r'^[\x00-\x7F\s\d.,!?"\'()-]*$', text))

# Path to your JSON file
json_file = r"C:\Users\tirum\OneDrive\Desktop\AIRecipes\final_data_updated.recipes.json"

with open(json_file, "r", encoding="utf-8") as f:
    all_recipes = json.load(f)

cuisine_dict = {}

for r in all_recipes:
    # Convert list fields to string
    name = r.get("TranslatedRecipeName", "")
    if isinstance(name, list):
        name = " ".join(name)
    name = name.strip()

    instructions = r.get("TranslatedInstructions", "")
    if isinstance(instructions, list):
        instructions = " ".join(instructions)
    instructions = instructions.strip()

    ingredients = r.get("TranslatedIngredients", "")
    if isinstance(ingredients, list):
        ingredients = " ".join(ingredients)
    ingredients = ingredients.strip()

    # Skip if any key field is missing or not English
    if not (is_english(name) and is_english(instructions) and is_english(ingredients)):
        continue

    cuisine = r.get("Cuisine", "Other")

    # Convert image_path to web-friendly URL
    raw_image = r.get("image_path", "")
    image_url = "/static/" + raw_image.replace("\\", "/") if raw_image else "/static/recipes_images/icon.png"

    recipe_item = {
        "name": name,
        "instructions": instructions,
        "ingredients": ingredients,
        "cook_time": r.get("CookTimeInMins", ""),
        "prep_time": r.get("PrepTimeInMins", ""),
        "total_time": r.get("TotalTimeInMins", ""),
        "servings": r.get("Servings", ""),
        "course": r.get("Course", ""),
        "cuisine": r.get("Cuisine", ""),
        "diet": r.get("Diet", ""),
        "image": image_url
    }

    if cuisine not in cuisine_dict:
        cuisine_dict[cuisine] = []
    cuisine_dict[cuisine].append(recipe_item)

# Save filtered JSON
output_file = r"C:\Users\tirum\OneDrive\Desktop\AIRecipes\filtered_recipes_by_cuisine.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(cuisine_dict, f, ensure_ascii=False, indent=2)

# Print cuisine summary
cuisines = list(cuisine_dict.keys())
print(f"Filtered recipes saved successfully to {output_file}")
print(f"Total cuisines found: {len(cuisines)}")
print("Cuisine list:")
for c in cuisines:
    print(f"- {c}")
