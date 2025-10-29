import pandas as pd
import json
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI not found in .env file!")

# Load Excel
xl_path = r"C:\Users\tirum\Downloads\testing.xlsx"
df = pd.read_excel(xl_path)

required_columns = [
    "TranslatedRecipeName",
    "TranslatedInstructions",
    "CookTimeInMins",
    "PrepTimeInMins",
    "TotalTimeInMins",
    "Servings",
    "Course",
    "Cuisine",
    "Diet",
    "TranslatedIngredients"
]
df = df[required_columns]

# Load image JSON
with open(r"C:\Users\tirum\OneDrive\Desktop\AIRecipes\ingredients.images.json", "r", encoding="utf-8") as f:
    image_data = json.load(f)
df_images = pd.DataFrame(image_data)

# Normalize names for merging
df["TranslatedRecipeName"] = df["TranslatedRecipeName"].str.strip().str.lower()
df_images["TranslatedRecipeName"] = df_images["TranslatedRecipeName"].str.strip().str.lower()

# Merge image paths
df = df.merge(df_images[["TranslatedRecipeName", "image_path"]], on="TranslatedRecipeName", how="left")

# Split ingredients and instructions into lists
df["TranslatedIngredients"] = df["TranslatedIngredients"].apply(lambda x: [i.strip() for i in str(x).split(',') if i.strip()])
df["TranslatedInstructions"] = df["TranslatedInstructions"].apply(lambda x: [i.strip() for i in str(x).split('.') if i.strip()])

# Convert to dict for MongoDB
recipes_dict = df.to_dict(orient="records")
print(f"Total recipes processed: {len(recipes_dict)} ✅")

# Insert into MongoDB
client = MongoClient(MONGO_URI)
db = client["final_data"]
collection = db["recipes"]

collection.drop()  # reset collection
collection.insert_many(recipes_dict)
print("✅ All recipes inserted into MongoDB with ingredients and instructions as lists!")
