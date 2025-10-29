from fastapi import FastAPI, Request, Response, HTTPException,status,Form,UploadFile, File,Depends
from fastapi.responses import HTMLResponse,FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from passlib.context import CryptContext
from dotenv import load_dotenv
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os, requests, json, re
from rapidfuzz import process, fuzz
import networkx as nx
from fastapi.templating import Jinja2Templates
import requests 
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
ALGORITHM = "HS256"
STATIC_DIR = os.getenv("STATIC_DIR", r"C:/Users/tirum/OneDrive/Desktop/AIRecipes")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
MAX_BCRYPT_LEN = 72  
origins = os.getenv("FRONTEND_ORIGINS","http://127.0.0.1:8000" ).split(",")


client = MongoClient(MONGO_URI)
auth_db = client["myapp"]
users_col = auth_db["users"]
history_col=auth_db["History"]


app = FastAPI(title="Recipe Suggestion + Auth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class History(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    action_type = Column(String)  # "searched" or "viewed"
    data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
templates = Jinja2Templates(directory="templates")
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None  
    
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---------------- HTML ROUTES ----------------
@app.get("/", response_class=HTMLResponse)
async def signup_page():
    path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Signup page not found")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    path = os.path.join(STATIC_DIR, "login.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Login page not found")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    path = os.path.join(STATIC_DIR, "dashboard.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Dashboard not found")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
    
@app.get("/cuisine", response_class=HTMLResponse)
async def cuisine_page():
    path = os.path.join(STATIC_DIR,"cuisine.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Cuisine not found")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/items", response_class=HTMLResponse)
async def items_page(request: Request, cuisine: str):
    return templates.TemplateResponse("items.html", {"request": request, "cuisine": cuisine})

# ---------------- MODELS ----------------
class SignupModel(BaseModel):
    name: str
    email: EmailStr
    password: str
    recaptcha: str

class LoginModel(BaseModel):
    email: EmailStr
    password: str

class IngredientsInput(BaseModel):
    ingredients: list[str]

class ForgotPasswordRequest(BaseModel):
    email: str

# ============ GLOBAL SEARCH & VIEW HISTORY ============
search_history = []
view_history = []

@app.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    try:
        email = req.email.strip().lower()
        user = users_col.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Here you would send an actual email (for now we simulate)
        return {"message": f"Password reset link sent to {email}!"}
    except Exception as e:
        print("Forgot password error:", e)
        raise HTTPException(status_code=500, detail=str(e))

# ---------------- SIGNUP ----------------
@app.post("/index")
async def signup(data: SignupModel):
    try:
        # Verify reCAPTCHA
        if not RECAPTCHA_SECRET:
            raise HTTPException(status_code=500, detail="reCAPTCHA secret not configured")
        resp = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET, "response": data.recaptcha}
        )
        if not resp.ok or not resp.json().get("success"):
            raise HTTPException(status_code=400, detail="reCAPTCHA verification failed")

        # Check if email exists
        if users_col.find_one({"email": data.email}):
            raise HTTPException(status_code=400, detail="Email already exists")

        # Hash password
        hashed_pw = pwd_context.hash(data.password[:MAX_BCRYPT_LEN])

        # Save user
        users_col.insert_one({
            "name": data.name,
            "email": data.email,
            "password": hashed_pw,
            "createdAt": datetime.utcnow()
        })
        return {"message": "Signup successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------- LOGIN ----------------
@app.post("/login")
async def login(data: LoginModel, response: Response):
    try:
        user = users_col.find_one({"email": data.email})
        if not user or not pwd_context.verify(data.password[:MAX_BCRYPT_LEN], user.get("password", "")):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token({"sub": data.email})
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="lax",
            secure=COOKIE_SECURE,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60,
            path="/"
        )
        return {"message": "Login successful", "name": user["name"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- SESSION CHECK ----------
@app.get("/api/session")
async def get_session(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return {"active": False}
    payload = verify_token(token)
    if not payload:
        return {"active": False}
    
    user_email = payload.get("sub")  # or whatever you store
    return {"active": True, "email": user_email}
# ---------------- LOGOUT ----------------

@app.post("/api/logout")
async def api_logout(response: Response):
    response.delete_cookie(
        "access_token",
        path="/",
        samesite="lax"
    )
    return {"message": "Logged out successfully"}

# ---------------- PROTECTED DASHBOARD API ----------------
@app.get("/api/dashboard")
async def api_dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expired, please log in again.")

    email = payload.get("sub")
    user = users_col.find_one({"email": email}, {"password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    return {"message": f"Welcome, {user.get('name', email)}!", "user": user}

# ---------------- LOAD RECIPE DATA ----------------
RECIPES_FILE = os.path.join(STATIC_DIR, "final_data_updated.recipes.json")
if not os.path.exists(RECIPES_FILE):
    raise FileNotFoundError(f"{RECIPES_FILE} not found")

with open(RECIPES_FILE, "r", encoding="utf-8") as f:
    RECIPES = json.load(f)

# Build graph
G = nx.Graph()
all_ingredients_set = set()
recipe_info_map = {}

def preprocess_ingredient(ing):
    synonyms = re.findall(r'([^\(\)]+)', ing.lower().strip())
    return [s.strip() for s in synonyms]

for r in RECIPES:
    recipe_name = r["TranslatedRecipeName"]
    recipe_info_map[recipe_name] = r
    G.add_node(recipe_name, type="recipe")
    main_ings = r.get("main_ingredients", [])
    for ing in main_ings:
        for i in preprocess_ingredient(ing):
            all_ingredients_set.add(i)
            G.add_node(i, type="ingredient")
            G.add_edge(recipe_name, i)

all_ingredients_list = list(all_ingredients_set)

def correct_ingredient(user_ing):
    match, score, _ = process.extractOne(user_ing.lower(), all_ingredients_list, scorer=fuzz.WRatio)
    return match
# ---------------- SUGGEST RECIPES ----------------
@app.post("/suggest_recipes")
def get_recipe_suggestions(data: IngredientsInput):
    if not data.ingredients:
        return {"message": "Please provide at least one ingredient."}

    corrected_ings = [correct_ingredient(ing) for ing in data.ingredients]
      # ✅ Save search history (keep only latest 10)
    search_history.append({
        "ingredients": corrected_ings,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    if len(search_history) > 10:
        search_history.pop(0)

    recipe_scores = []
    for recipe in [n for n, d in G.nodes(data=True) if d['type'] == 'recipe']:
        main_ing_neighbors = set(G.neighbors(recipe))
        matched = main_ing_neighbors & set(corrected_ings)
        if not matched:
            continue

        r = recipe_info_map[recipe]

        # Get image filename from JSON path
        img_path = r.get("image_path", "")
        if not img_path:
            continue  # skip recipes without image
        img_filename = os.path.basename(img_path).replace("\\", "/")
        full_img_path = os.path.join(STATIC_DIR, "recipes_images", img_filename)
        if not os.path.isfile(full_img_path):
            print(f"Image not found for recipe {recipe}: {full_img_path}")
            continue  # skip recipes with missing image file

        recipe_scores.append((recipe, matched, img_filename))

    # Sort by number of matched ingredients (descending)
    recipe_scores.sort(key=lambda x: len(x[1]), reverse=True)

    # Prepare results (max 9)
    results = []
    for recipe_name, matched_set, img_filename in recipe_scores[:9]:
        r = recipe_info_map[recipe_name]
        results.append({
            "TranslatedRecipeName": r.get("TranslatedRecipeName"),
            "main_ingredients": r.get("main_ingredients", []),
            "common_ingredients": r.get("common_ingredients", []),
            "matched_ingredients": list(matched_set),
            "matched_count": len(matched_set),
            "image": f"/static/recipes_images/{img_filename}"
        })

    if not results:
        return {"message": "No recipes found."}

    return {"user_input": data.ingredients, "suggested_recipes": results}


# ---------------- GET RECIPE DETAILS ----------------
@app.get("/get_recipe")
def get_recipe(name: str):
    # Normalize the input (handle case, spaces, encoding)
    normalized_name = name.strip().lower().replace("%20", " ")

    # Find matching recipe (case-insensitive)
    matched_recipe = None
    for key in recipe_info_map.keys():
        if key.strip().lower() == normalized_name:
            matched_recipe = recipe_info_map[key]
            break

    if not matched_recipe:
        raise HTTPException(status_code=404, detail=f"Recipe '{name}' not found")
    
    # ✅ Save viewed recipe to history
    view_history.append({
        "recipe_name": matched_recipe.get("TranslatedRecipeName", name),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    if len(view_history) > 10:
        view_history.pop(0)
    img_path = matched_recipe.get("image_path", "default.jpg")
    img_filename = os.path.basename(img_path).replace("\\", "/")

    return {
        "TranslatedRecipeName": matched_recipe.get("TranslatedRecipeName"),
        "TranslatedIngredients": matched_recipe.get("TranslatedIngredients", []),
        "TranslatedInstructions": matched_recipe.get("TranslatedInstructions", []),
        "PrepTimeInMins": matched_recipe.get("PrepTimeInMins", ""),
        "CookTimeInMins": matched_recipe.get("CookTimeInMins", ""),
        "Servings": matched_recipe.get("Servings", ""),
        "Course": matched_recipe.get("Course", ""),
        "Cuisine": matched_recipe.get("Cuisine", ""),
        "Diet": matched_recipe.get("Diet", ""),
        "image": f"/static/recipes_images/{img_filename}"
    }

@app.get("/get_history")
def get_history():
    return {
        "searched": search_history[::-1],  # latest first
        "viewed": view_history[::-1]
    }


reviews_col = auth_db["reviews"]

# ---------------- REVIEW MODEL ----------------
class Review(BaseModel):
    name: str
    email: EmailStr
    rating: int
    review: str

@app.get("/reviews", response_class=HTMLResponse)
async def reviews_page():
    """
    Serves the main reviews UI (reviews.html)
    """
    path = os.path.join(STATIC_DIR, "reviews.html")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="reviews.html not found")
    return FileResponse(path)

# GET all reviews
@app.get("/api/reviews")
def get_reviews():
    reviews = list(reviews_col.find().sort("createdAt",-1))
    for r in reviews:
        r["_id"]=str(r["_id"])
        if isinstance(r.get("createdAt"), datetime):
            r["createdAt"]=r["createdAt"].isoformat()
    return reviews

# POST new review
@app.post("/api/reviews")
def post_review(r: Review):
    if r.rating<1 or r.rating>5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")
    data=r.dict()
    data["createdAt"]=datetime.utcnow()
    res=reviews_col.insert_one(data)
    return {"status":"success","id":str(res.inserted_id)}
# ==============================
# 📦 USER DATA COLLECTION
# ==============================
userdata_col = auth_db["userdata"]

class UserData(BaseModel):
    name: str
    email: EmailStr
    address: str = ""
    profilePic: str = ""
    favorites: list = []
    activity: list = []
    timeSpent: str = "0m"


# ---------------- PROFILE PAGE ----------------
@app.get("/profile", response_class=HTMLResponse)
async def profile_page():
    path = os.path.join(STATIC_DIR, "profile.html")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="profile.html not found")
    return FileResponse(path)


# ---------------- FETCH USER PROFILE ----------------
@app.get("/api/profile")
async def get_user_profile(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = payload.get("sub")

    # Base user info
    user = users_col.find_one({"email": email}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Extended data
    userdata = userdata_col.find_one({"email": email}, {"_id": 0}) or {}

    return {
        "name": user.get("name", ""),
        "email": email,
        "address": userdata.get("address", "Add your address"),
        "profilePic": userdata.get("profilePic", "/static/recipes_images/icon.png"),
        "favorites": userdata.get("favorites", []),
        "activity": userdata.get("activity", []),
        "timeSpent": userdata.get("timeSpent", "0m"),
    }


# ---------------- UPLOAD PROFILE PIC ----------------
@app.post("/api/upload_profile_pic")
async def upload_profile_pic(request: Request, file: UploadFile = File(...)):
    token = request.cookies.get("access_token")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = payload.get("sub")

    upload_dir = os.path.join(STATIC_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{email}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(await file.read())

    file_url = "/" + file_path.replace("\\", "/")
    userdata_col.update_one({"email": email}, {"$set": {"profilePic": file_url}}, upsert=True)
    return {"success": True, "profilePic": file_url}


# ---------------- FAVORITES ----------------
@app.post("/api/add_favorite")
async def add_favorite(request: Request, title: str = Form(...), image: str = Form(...)):
    token = request.cookies.get("access_token")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = payload.get("sub")
    userdata_col.update_one(
        {"email": email},
        {"$addToSet": {"favorites": {"title": title, "image": image}}},
        upsert=True
    )
    return {"success": True, "message": "Added to favorites"}


@app.post("/api/remove_favorite")
async def remove_favorite(request: Request, title: str = Form(...)):
    token = request.cookies.get("access_token")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = payload.get("sub")
    userdata_col.update_one(
        {"email": email},
        {"$pull": {"favorites": {"title": title}}}
    )
    return {"success": True, "message": "Removed from favorites"}


@app.get("/api/get_favorites")
async def get_favorites(request: Request):
    token = request.cookies.get("access_token")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = payload.get("sub")
    user = userdata_col.find_one({"email": email}, {"_id": 0, "favorites": 1})
    favorites = user.get("favorites", []) if user else []
    return {"favorites": favorites}


# ---------------- ACTIVITY LOG ----------------
@app.post("/api/add_activity")
async def add_activity(request: Request, activity: str = Form(...)):
    token = request.cookies.get("access_token")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = payload.get("sub")
    userdata_col.update_one(
        {"email": email},
        {"$push": {"activity": {"$each": [activity], "$position": 0}}},
        upsert=True
    )
    return {"success": True, "message": "Activity added"}


@app.delete("/api/clear_activity")
async def clear_activity(request: Request):
    token = request.cookies.get("access_token")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = payload.get("sub")
    userdata_col.update_one({"email": email}, {"$set": {"activity": []}})
    return {"success": True, "message": "Activity cleared"}


# ---------------- ADDRESS ----------------
@app.post("/api/update_address")
async def update_address(request: Request, address: str = Form(...)):
    token = request.cookies.get("access_token")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = payload.get("sub")
    userdata_col.update_one({"email": email}, {"$set": {"address": address}}, upsert=True)
    return {"success": True, "message": "Address updated"}
