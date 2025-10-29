import json
import re

def remove_duplicates_keep_order(seq):
    seen = set()
    result = []
    for item in seq:
        if item.lower() not in seen:  
            seen.add(item.lower())
            result.append(item)
    return result

# Load your existing recipes JSON
with open(r"C:\Users\tirum\OneDrive\Desktop\codes\ingredients.New recipes.json", "r", encoding="utf-8") as f:
    recipes = json.load(f)

common_ingredients_list = [
    "salt","water","oil","turmeric powder","garlic","chilli powder","red chilli powder",
    "curry leaves","coriander powder","dry red chilli","dry red chillies",
    "cumin seeds","mustard","mustard seeds","tomato","onion","green chillis","green onion","red onion"
]

new_recipes = []

for recipe in recipes:
    ingredients = recipe.get("TranslatedIngredients", [])
    common_items = []
    main_items = []

    for ing in ingredients:
        if isinstance(ing, dict):
            item = ing.get("item", "").strip()
        else:
            item = str(ing).strip()

        item_lower = item.lower()
        if any(common in item_lower for common in common_ingredients_list):
            common_items.append(item)
        else:
            main_items.append(item)

    # Remove duplicates but preserve order
    common_items = remove_duplicates_keep_order(common_items)
    main_items = remove_duplicates_keep_order(main_items)

    # Build new recipe dict with only required fields
    new_recipe = {
        "_id": recipe.get("_id"),
        "Srno": recipe.get("Srno"),
        "TranslatedRecipeName": recipe.get("TranslatedRecipeName"),
        "PrepTimeInMins": recipe.get("PrepTimeInMins"),
        "CookTimeInMins": recipe.get("CookTimeInMins"),
        "TotalTimeInMins": recipe.get("TotalTimeInMins"),
        "Servings": recipe.get("Servings"),
        "Cuisine": recipe.get("Cuisine"),
        "Course": recipe.get("Course"),
        "Diet": recipe.get("Diet"),
        "TranslatedInstructions": recipe.get("TranslatedInstructions"),
        "URL": recipe.get("URL"),
        "common_ingredients": common_items,
        "main_ingredients": main_items
    }

    new_recipes.append(new_recipe)

# Save processed JSON
with open(r"C:\Users\tirum\OneDrive\Desktop\separted_ingredient.json", "w", encoding="utf-8") as f:
    json.dump(new_recipes, f, indent=4, ensure_ascii=False)

print("✅ Done – new JSON created with required fields")
