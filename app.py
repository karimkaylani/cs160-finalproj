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

    return redirect(next)

@app.route("/logout")
def logout():
    supabase.auth.sign_out()
    return redirect("/login")

@app.route("/preferences", methods=["POST"])
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

@app.route("/preferences", methods=["GET"])
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