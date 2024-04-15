from flask import Flask, redirect, render_template, request, g, session
import os
from supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config.update(SECRET_KEY=os.getenv("FLASK_SECRET_KEY", os.urandom(24)))

@app.route("/")
def home():
    data = supabase.auth.get_user()
    if not data:
        return redirect("/login")
    id = data.user.id
    user = data.user.user_metadata['full_name']
    prefs = supabase.table("preferences").select("preferences").eq("user_id", id).limit(1).execute()
    return render_template("index.html", user=user, prefs=prefs.data)

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
