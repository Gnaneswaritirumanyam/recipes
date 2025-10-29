from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union
import json, re
from rapidfuzz import fuzz, process
from sentence_transformers import SentenceTransformer, util
from spellchecker import SpellChecker

app = FastAPI(title="Hybrid Recipe Suggestion API")

with open(r"C:\Users\tirum\OneDrive\Desktop\AIRecipes\separted_ing.json", "r", encoding="utf-8") as f:
    RECIPES = json.load(f)

model = SentenceTransformer('all-MiniLM-L6-v2')

for r in RECIPES:
    main_text = " ".join(r.get("main_ingredients", []))
    r["embedding"] = model.encode(main_text)

spell = SpellChecker()
def normalize_word(word: str) -> str:
    w = word.strip().lower()
    w = re.sub(r"[^a-z0-9\s()]", "", w)
    if w.endswith("es"):
        w = w[:-2]
    elif w.endswith("s"):
        w = w[:-1]
    return w

def extract_all_words(text: str):
    """Return normalized words including bracketed words"""
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

def correct_terms(terms):
    """Auto-correct user input using spellchecker"""
    corrected = []
    for t in terms:
        t_lower = t.lower()
        c = spell.correction(t_lower)  
        corrected.append(c)
    return corrected

def fuzzy_match_count(recipe, user_terms, threshold=80):
    """Count how many user terms match recipe ingredients (including bracket words)"""
    all_ingredients = recipe.get("main_ingredients", [])
    all_words = set()
    for ing in all_ingredients:
        all_words.update(extract_all_words(ing))

    matched_terms = set()
    for term in user_terms:
        match_tuple = process.extractOne(term, all_words, scorer=fuzz.ratio)
        if match_tuple:
            match_word, score, _ = match_tuple
            if score >= threshold:
                matched_terms.add(term)
    return len(matched_terms)

class IngredientsInput(BaseModel):
    ingredients: Union[List[str], str]

@app.post("/recipes/suggestions_hybrid")
def recipe_suggestions_hybrid(payload: IngredientsInput, top_n: int = 5):
    if isinstance(payload.ingredients, str):
        raw_terms = [x.strip() for x in payload.ingredients.split(",") if x.strip()]
        user_input_text = " ".join(raw_terms)
    else:
        raw_terms = [x.strip() for x in payload.ingredients if x.strip()]
        user_input_text = " ".join(raw_terms)

    corrected_terms = correct_terms(raw_terms)
    user_terms = list(set(normalize_word(term) for term in corrected_terms))
    
    user_emb = model.encode(user_input_text)
    scored_recipes = []
    for r in RECIPES:
        emb_score = float(util.cos_sim(user_emb, r["embedding"])[0][0].item())
        fuzzy_count = fuzzy_match_count(r, user_terms)
        max_main_ing = max(len(r.get("main_ingredients", [])), 1)
        fuzzy_score = fuzzy_count / max_main_ing
        combined_score = 0.7 * emb_score + 0.3 * fuzzy_score

        if combined_score > 0:
            scored_recipes.append((combined_score, r))
    scored_recipes.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, r in scored_recipes[:top_n]:
        results.append({
            "TranslatedRecipeName": r.get("TranslatedRecipeName") or r.get("RecipeName"),
            "combined_score": round(score, 3),
            "main_ingredients": list(set(r.get("main_ingredients", []))),
            "common_ingredients": list(set(r.get("common_ingredients", [])))
        })

    return {"matched_recipes": results}
