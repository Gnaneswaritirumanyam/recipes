from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union
import json, re
from rapidfuzz import fuzz

app = FastAPI()
with open(r"C:\Users\tirum\OneDrive\Desktop\separted_ing.json", "r", encoding="utf-8") as f:
    RECIPES = json.load(f)

def normalize_word(word: str) -> str:
    w = word.strip().lower()
    w = re.sub(r"[^a-z0-9\s()]", "", w)  
    if w.endswith("es"):
        w = w[:-2]
    elif w.endswith("s"):
        w = w[:-1]
    return w

def extract_all_words(text: str):
    words = []
    normalized = normalize_word(text)
    words.append(normalized)
    
    no_brackets = re.sub(r"\(.*?\)", "", normalized).strip()
    if no_brackets != normalized:
        words.append(no_brackets)
    
    bracket_match = re.findall(r"\((.*?)\)", text)
    for m in bracket_match:
        words.append(normalize_word(m))
    
    return set(words)

def recipe_match_count(recipe, user_terms, threshold=80):
    all_ingredients = recipe.get("main_ingredients", [])
    matched_terms = set()
    
    for ing in all_ingredients:
        ing_words = extract_all_words(ing)
        for term in user_terms:
            if any(fuzz.ratio(term, w) >= threshold for w in ing_words):
                matched_terms.add(term)
    return len(matched_terms)

class IngredientsInput(BaseModel):
    ingredients: Union[List[str], str]

@app.post("/recipes/suggestions")
def recipe_suggestions(payload: IngredientsInput):
    if isinstance(payload.ingredients, str):
        raw_terms = [x.strip() for x in payload.ingredients.split(",") if x.strip()]
    else:
        raw_terms = [x.strip() for x in payload.ingredients if x.strip()]
    
    user_terms = list(set(normalize_word(term) for term in raw_terms))
    
    scored_recipes = []
    for recipe in RECIPES:
        count = recipe_match_count(recipe, user_terms)
        if count > 0:
            scored_recipes.append((count, recipe))
    
    scored_recipes.sort(key=lambda x: x[0], reverse=True)
    
    results = []
    for count, r in scored_recipes:
        results.append({
            "TranslatedRecipeName": r.get("TranslatedRecipeName") or r.get("RecipeName"),
            "matched_ingredients_count": count,
            "main_ingredients": list(set(r.get("main_ingredients", []))),
            "common_ingredients": list(set(r.get("common_ingredients", [])))  # info only
        })
    
    return {"matched_recipes": results}



