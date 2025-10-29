from fastapi import FastAPI
from pydantic import BaseModel
import json
import re
import networkx as nx
from rapidfuzz import process, fuzz
from fastapi.middleware.cors import CORSMiddleware
import os

# ---------------- FASTAPI APP ----------------
app = FastAPI(title="Graph-Based Recipe Suggestion API")

# Enable CORS for dashboard frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ---------------- MODEL ----------------
class IngredientsInput(BaseModel):
    ingredients: list[str]

# ---------------- LOAD RECIPES ----------------
STATIC_DIR = r"C:\Users\tirum\OneDrive\Desktop\AIRecipes"
RECIPES_FILE = os.path.join(STATIC_DIR, "final_data_updated.recipes.json")

with open(RECIPES_FILE, "r", encoding="utf-8") as f:
    RECIPES = json.load(f)

# ---------------- GRAPH CONSTRUCTION ----------------
def preprocess_ingredient(ing):
    ing = ing.lower().strip()
    synonyms = re.findall(r'([^\(\)]+)', ing)
    return [s.strip() for s in synonyms]

G = nx.Graph()
all_ingredients_set = set()
recipe_info_map = {}

for r in RECIPES:
    recipe_name = r["TranslatedRecipeName"]
    recipe_info_map[recipe_name] = r
    G.add_node(recipe_name, type='recipe')

    main_ings = r.get("main_ingredients", [])
    for ing in main_ings:
        ing_list = preprocess_ingredient(ing)
        for i in ing_list:
            all_ingredients_set.add(i)
            G.add_node(i, type='ingredient')
            G.add_edge(recipe_name, i)

all_ingredients_list = list(all_ingredients_set)

# ---------------- UTILITY FUNCTIONS ----------------
def correct_ingredient(user_ing):
    if not all_ingredients_list:
        return user_ing
    match, score, _ = process.extractOne(user_ing.lower(), all_ingredients_list, scorer=fuzz.WRatio)
    return match

def suggest_recipes(user_ingredients, top_n=9):
    corrected_ings = [correct_ingredient(ing) for ing in user_ingredients]

    recipe_scores = []
    for recipe in [n for n, d in G.nodes(data=True) if d['type'] == 'recipe']:
        main_ing_neighbors = set(G.neighbors(recipe))
        matched = main_ing_neighbors & set(corrected_ings)
        if matched:
            recipe_scores.append((recipe, matched))

    recipe_scores.sort(key=lambda x: len(x[1]), reverse=True)

    results = []
    for recipe_name, matched_set in recipe_scores[:top_n]:
        r = recipe_info_map[recipe_name]
        img_path = r.get("image_path", "default.jpg")
        img_filename = os.path.basename(img_path)  # Extract filename
        results.append({
            "TranslatedRecipeName": r.get("TranslatedRecipeName"),
            "main_ingredients": r.get("main_ingredients", []),
            "common_ingredients": r.get("common_ingredients", []),
            "matched_ingredients": list(matched_set),
            "matched_count": len(matched_set),
            "image": f"/static/recipes_images/{img_filename}"
        })
    return results

# ---------------- API ENDPOINT ----------------
@app.post("/suggest_recipes")
def get_recipe_suggestions(data: IngredientsInput):
    if not data.ingredients:
        return {"message": "Please provide at least one ingredient."}
    suggestions = suggest_recipes(data.ingredients)
    if not suggestions:
        return {"message": "No recipes found."}
    return {"user_input": data.ingredients, "suggested_recipes": suggestions}

# ---------------- STATIC FILES ----------------
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=os.path.join(STATIC_DIR, "recipes_images")), name="static")
