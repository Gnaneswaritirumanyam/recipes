import json
import re

# ===== Load your recipes file =====
with open("final_data_updated.recipes.json", "r", encoding="utf-8") as f:
    recipes = json.load(f)

# ===== Junk / measurement / descriptive words =====
JUNK_WORDS = {
    "fresh", "dry", "dried", "few", "handful", "mixed", "large", "small", "medium",
    "english", "of", "or", "to", "tablespoon", "teaspoon", "table", "spoon", "cup", "cups",
    "tbsp", "tsp", "gm", "grams", "ml", "kg", "ltr", "litre", "inch", "cm", "piece",
    "pieces", "stick", "stalk", "sticks", "stalks", "stock", "some", "each", "and",
    "with", "without", "optional", "for", "taste", "chopped", "sliced", "crushed",
    "ground", "grated", "paste", "powder","Tablespoon","Tablespoons","a pinch"
}

# ===== Known normalization variants =====
REPLACEMENTS = {
    "chili": "Chili",
    "chilli": "Chili",
    "chilies": "Chili",
    "chillies": "Chili",
    "red chili": "Red Chili",
    "red chillies": "Red Chili",
    "green chili": "Green Chili",
    "green chillies": "Green Chili",
    "green chilli": "Green Chili",
    "green chillie": "Green Chili"
}

# ===== Helper: Normalize known spelling variants =====
def normalize_word(word):
    word = word.lower().strip()
    for k, v in REPLACEMENTS.items():
        if word == k:
            return v
    return word.capitalize()

# ===== Main cleaning logic =====
def clean_ingredient(text):
    # Remove content in parentheses like (Jeera)
    text = re.sub(r"\(.*?\)", "", text)

    # Remove numbers and symbols
    text = re.sub(r"[\d½¼¾/]+", " ", text)

    # Keep only alphabets and spaces
    text = re.sub(r"[^a-zA-Z\s]", " ", text)

    # Split words
    words = [w.strip().lower() for w in text.split() if w.strip()]

    # Remove all leading junk words
    while words and words[0] in JUNK_WORDS:
        words.pop(0)

    # Remove junk words from middle too
    words = [w for w in words if w not in JUNK_WORDS]

    if not words:
        return None

    # Join cleaned words
    text = " ".join(words).strip()

    # Normalize variants (e.g., chillies)
    text = normalize_word(text)

    return text

# ===== Process all recipes =====
ingredients_set = set()

for recipe in recipes:
    main_ing = recipe.get("main_ingredients", [])
    if isinstance(main_ing, list):
        for ing in main_ing:
            cleaned = clean_ingredient(ing)
            if cleaned:
                ingredients_set.add(cleaned)

# ===== Deduplicate ignoring case =====
unique_ingredients = sorted({i.lower(): i.capitalize() for i in ingredients_set}.values())

# ===== Save cleaned list =====
with open("ingredients.json", "w", encoding="utf-8") as f:
    json.dump(unique_ingredients, f, ensure_ascii=False, indent=2)

print(f"✅ Cleaned {len(unique_ingredients)} unique ingredients saved to ingredients.json")
