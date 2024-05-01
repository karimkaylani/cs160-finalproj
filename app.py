from flask import Flask, jsonify, redirect, render_template, request, g, session
import os
import requests
from supabase_client import supabase
from dotenv import load_dotenv
import json

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
    return render_template("index.html")

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

@app.route("/preferences")
def preferences():
    return render_template("preferences.html")

@app.route("/groups")
def groups():
    return render_template("groups.html")

@app.route("/favorites")
def favorites():
    return render_template("favorites.html")

'''
API Endpoints

/api/preferences:
    POST: set/update user preferences (preferred_price, max_distance, preferred_cuisine, dietary_restrictions)
    GET: get user preferences
/api/preferences/<user_id>:
    GET: get user preferences by id (user_id)

/api/groups:
    POST: create a new group for user (name, members)
    GET: get all groups for user
    DELETE: delete a group (group_id)
/api/groups/<group_id>:
    GET: get group by id (group_id)

/api/favorites:
    POST: add a restaurant to user favorites (restaurant_id)
    GET: get all user favorites
    DELETE: remove a restaurant from user favorites (restaurant_id)

/api/user:
    GET: get current user
/api/user/<id>:
    GET: get user by id (user_id)
/api/user/search/<name>:
    GET: search for user by name (query)

/api/yelp_search:
    POST: save yelp search (url, results)
/api/yelp_search/<url>:
    GET: get yelp search by url

/api/restaurants/<id>:
    GET: get restaurant by id (restaurant_id)
    POST: save restaurant to database (restaurant_id, name, image_url, url, location, phone, rating, price, categories)

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

@app.route("/api/preferences/<user_id>", methods=["GET"])
def get_user_preferences(user_id):
    prefs = supabase.table("preferences").select("preferences").eq("user_id", user_id).limit(1).execute()
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
    print(args['members'])
    required_args = ['name', 'members']
    if args is None or not all(arg in args for arg in required_args):
        return f"Please supply all required arguments\n{required_args}", 404
    if ('group_id' not in args):
        group = supabase.table("groups").upsert(
            {"name": args['name'], "owner_id": id, "members": json.dumps(args["members"])}
        ).execute()
    else:
        group = supabase.table("groups").upsert(
            {"id": args['group_id'], "name": args['name'], "owner_id": id, "members": json.dumps(args["members"])}
        ).execute()
    return jsonify(group.data)

@app.route("/api/groups/<group_id>", methods=["DELETE"])
def delete_group(group_id):
    data = supabase.auth.get_user()
    if not data:
        return "User not authenticated", 401
    group = supabase.table("groups").delete().eq("id", group_id).execute()
    return jsonify(group.data)

@app.route("/api/groups/<group_id>", methods=["GET"])
def get_group(group_id):
    group = supabase.table("groups").select("*").eq("id", group_id).limit(1).execute()
    if group.data is None:
        return "Group not found", 404
    return jsonify(group.data[0])

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
    favorites = supabase.table("favorites").select("favorites").eq("user_id", id).limit(1).execute()
    if not favorites.data:
        favorites = []
    else:
        favorites = json.loads(favorites.data[0]['favorites'])
    if args['restaurant_id'] in favorites:
        return "Restaurant already in favorites", 400
    favorites.append(args['restaurant_id'])
    favorite = supabase.table("favorites").upsert(
        {"user_id": id, "favorites": json.dumps(favorites)}
    ).execute()
    return jsonify(favorites)

@app.route("/api/favorites", methods=["GET"])
def get_favorites():
    data = supabase.auth.get_user()
    if not data:
        return "User not authenticated", 401
    id = data.user.id
    favorites = supabase.table("favorites").select("favorites").eq("user_id", id).limit(1).execute()
    if not favorites.count:
        return jsonify([])
    id_list = json.loads(favorites.data[0]['favorites'])
    res = []
    for id in id_list:
        restaurant = supabase.table("restaurants").select("*").eq("id", id).limit(1).execute()
        res.append(restaurant.data[0])
    return jsonify(res)

@app.route("/api/favorites", methods=["DELETE"])
def remove_favorite():
    data = supabase.auth.get_user()
    if not data:
        return "User not authenticated", 401
    id = data.user.id
    args = request.json
    required_args = ['restaurant_id']
    if args is None or not all(arg in args for arg in required_args):
        return f"Please supply all required arguments\n{required_args}", 404
    favorites = supabase.table("favorites").select("favorites").eq("user_id", id).execute()
    if not favorites.count:
        return "No favorites found", 404
    favorites = json.loads(favorites.data[0]['favorites'])
    if args['restaurant_id'] not in favorites:
        return "Restaurant not in favorites", 400
    favorites.remove(args['restaurant_id'])
    favorite = supabase.table("favorites").upsert(
        {"user_id": id, "favorites": json.dumps(favorites)}
    ).execute()
    return jsonify(favorites)

@app.route("/api/user", methods=["GET"])
def get_current_user():
    user = supabase.auth.get_user()
    if user is None:
        return "User not found", 404
    id = user.user.id
    user = supabase.table("users").select("*").eq("user_id", id).limit(1).execute()
    return jsonify(user.data[0])

@app.route("/api/user/<id>", methods=["GET"])
def get_user(id):
    user = supabase.table("users").select("*").eq("user_id", id).limit(1).execute()
    if user.data is None:
        return "User not found", 404
    return jsonify(user.data[0])

@app.route("/api/user/search/<name>", methods=["GET"])
def search_user(name):
    # get all users
    users = supabase.table("users").select("*").execute()
    users = users.data
    # find users with name like name, case-sensitive
    users = [user for user in users if name.lower() in user['name'].lower()]
    if not users.count:
        return "No users found", 404
    return jsonify(users)

def save_search(url, results):
    supabase.table("yelp_search").upsert(
        {"url": url, "yelp_response": results}
    ).execute()

@app.route("/api/yelp_search", methods=["GET"])
def get_search():
    url = request.args.get('url', '')
    search = supabase.table("yelp_search").select("yelp_response").eq("url", url).limit(1).execute()
    if search.data:
        print('Loaded from cache!')
        return jsonify(search.data[0]['yelp_response'])
    response = requests.get(url, headers={"Authorization": os.getenv('YELP_API_KEY'),"accept": "application/json"})
    if response.status_code != 200:
        return "Error fetching data", 400
    response = response.json()
    response = response['businesses']
    save_search(url, response)
    return response

@app.route("/api/restaurants/<id>", methods=["GET"])
def get_restaurant(id):
    restaurant = supabase.table("restaurants").select("*").eq("restaurant_id", id).limit(1).execute()
    if not restaurant.count:
        return "Restaurant not found", 404
    return jsonify(restaurant.data[0])

@app.route("/api/restaurants", methods=["POST"])
def save_restaurant():
    data = request.json
    required_args = ['id', 'name', 'address', 'url', 'imgurl', 'rating', 'rcount', 'reason']
    if data is None or not all(arg in data for arg in required_args):
        return f"Please supply all required arguments\n{required_args}", 404
    restaurant = supabase.table("restaurants").upsert(
        {"id": data['id'], "name": data['name'], "address": data['address'], "url": data['url'], "img_url": data['imgurl'], "rating": data['rating'], "num_reviews": data['rcount'], "reason": data['reason']}
    ).execute()
    return jsonify(restaurant.data)