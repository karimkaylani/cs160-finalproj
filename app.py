from flask import Flask, jsonify, redirect, render_template, request, g, session
import os
from supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config.update(SECRET_KEY=os.getenv("FLASK_SECRET_KEY", os.urandom(24)))

@app.route("/")
def home():
    try:
        data = supabase.auth.get_user()
    except:
        return redirect("/login")
    if not data:
        return redirect("/login")
    id = data.user.id
    user = data.user.user_metadata['full_name']
    return render_template("index.html", user=user)

@app.route("/login")
def login():
    return render_template("login.html", url=request.host_url)

@app.route("/login/google", methods=["POST", "GET"])
def google_login():
    res = supabase.auth.sign_in_with_oauth(
        {
            "provider": "google",
            "options": {
	            "redirect_to": f"{request.host_url}callback"
	        },
        }
    )
    return redirect(res.url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    next = request.args.get("next", "/")

    if code:
        res = supabase.auth.exchange_code_for_session({"auth_code": code})
    
    id = res.user.id
    user_metadata = res.user.user_metadata
    name = user_metadata.get("full_name")
    email = user_metadata.get("email")
    avatar = user_metadata.get("avatar_url")
    
    supabase.table("users").upsert(
        {"user_id": id, "name": name, "email": email, "avatar": avatar}
    ).execute()

    return redirect(next)

@app.route("/logout")
def logout():
    supabase.auth.sign_out()
    return redirect("/login")

'''
API Endpoints

/api/preferences:
    POST: set user preferences (preferred_price, max_distance, preferred_cuisine, dietary_restrictions)
    GET: get user preferences

/api/groups:
    POST: create a new group for user (name, members)
    GET: get all groups for user

/api/favorites:
    POST: add a restaurant to user favorites (restaurant_id)
    GET: get all user favorites

/api/user/<id>:
    GET: get user by id (user_id)
'''
@app.route("/api/preferences", methods=["POST"])
def set_preferences():
    data = supabase.auth.get_user()
    if not data:
        return "User not authenticated", 401
    id = data.user.id
    args = request.json
    required_args = ['preferred_price', 'max_distance', 'preferred_cuisine', 'dietary_restrictions']
    if args is None or not all(arg in args for arg in required_args):
        return f"Please supply all required arguments\n{required_args}", 404
    supabase.table("preferences").upsert(
        {"user_id": id, "preferences": args}
    ).execute()
    return "Success"

@app.route("/api/preferences", methods=["GET"])
def get_preferences():
    data = supabase.auth.get_user()
    if not data:
        return "User not authenticated", 401
    id = data.user.id
    prefs = supabase.table("preferences").select("preferences").eq("user_id", id).limit(1).execute()
    prefs = prefs.data[0]
    if prefs is None:
        return "No preferences set", 404
    return jsonify(prefs)

@app.route("/api/groups", methods=["GET"])
def get_groups():
    data = supabase.auth.get_user()
    if not data:
        return "User not authenticated", 401
    id = data.user.id
    groups = supabase.table("groups").select("*").eq("owner_id", id).execute()
    return jsonify(groups.data)

@app.route("/api/groups", methods=["POST"])
def create_group():
    data = supabase.auth.get_user()
    if not data:
        return "User not authenticated", 401
    id = data.user.id
    args = request.json
    required_args = ['name', 'members']
    if args is None or not all(arg in args for arg in required_args):
        return f"Please supply all required arguments\n{required_args}", 404
    group = supabase.table("groups").insert(
        {"name": args['name'], "owner_id": id, "members": args["members"]}
    ).execute()
    return jsonify(group)

@app.route("/api/favorites", methods=["POST"])
def add_favorite():
    data = supabase.auth.get_user()
    if not data:
        return "User not authenticated", 401
    id = data.user.id
    args = request.json
    required_args = ['restaurant_id']
    if args is None or not all(arg in args for arg in required_args):
        return f"Please supply all required arguments\n{required_args}", 404
    favorites = supabase.table("favorites").select("favorites").eq("user_id", id).execute()
    if favorites.data is None:
        favorites = []
    else:
        favorites = favorites.data
    if args['restaurant_id'] in favorites:
        return "Restaurant already in favorites", 400
    favorites.append(args['restaurant_id'])
    favorite = supabase.table("favorites").upsert(
        {"user_id": id, "restaurant_id": favorites}
    ).execute()
    return jsonify(favorite)

@app.route("/api/favorites", methods=["GET"])
def get_favorites():
    data = supabase.auth.get_user()
    if not data:
        return "User not authenticated", 401
    id = data.user.id
    favorites = supabase.table("favorites").select("favorites").eq("user_id", id).execute()
    if favorites.data is None:
        return "No favorites found", 404
    return jsonify(favorites.data)

@app.route("/api/user/<id>", methods=["GET"])
def get_user(id):
    user = supabase.table("users").select("*").eq("user_id", id).limit(1).execute()
    if user.data is None:
        return "User not found", 404
    return jsonify(user.data[0])