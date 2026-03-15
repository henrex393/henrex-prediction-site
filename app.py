from flask import Flask, render_template, request, redirect, session
import requests, random, sqlite3
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "henrexsecret"

# ------------------- PAYSTACK CONFIG -------------------
PAYSTACK_PUBLIC_KEY = "pk_test_xxxxx"  # test mode key
PAYSTACK_SECRET_KEY = "sk_test_xxxxx"  # test mode key
PAYSTACK_VERIFIED = False  # flip to True once verified

API_KEY = "cf22c7db329e63d40f7aa98ec8bbb058"  # API-Football
MAJOR_LEAGUES = ["Premier League","La Liga","Serie A","Bundesliga","Ligue 1"]

# ------------------- PREDICTION LOGIC -------------------
def predict_match():
    home_strength = random.uniform(0,3)
    away_strength = random.uniform(0,3)
    result = "Draw"
    if home_strength > away_strength:
        result = "Home Win"
    elif away_strength > home_strength:
        result = "Away Win"
    total_goals = home_strength + away_strength
    over_under = "Over 2.5" if total_goals>2.5 else "Under 2.5"
    btts = "Yes" if home_strength>0.8 and away_strength>0.8 else "No"
    home_corners = random.randint(3,10)
    away_corners = random.randint(3,10)
    corners = f"{home_corners} - {away_corners}"
    adv_pred = f"Expected xG: {home_strength:.1f} - {away_strength:.1f}"
    return result, over_under, btts, corners, adv_pred

# ------------------- HOME ROUTE -------------------
@app.route("/")
def home():
    today = date.today()
    headers = {"x-apisports-key": API_KEY}

    # LIVE MATCHES
    url_live = "https://v3.football.api-sports.io/fixtures?live=all"
    live_data = requests.get(url_live, headers=headers).json()
    live_matches = []
    for match in live_data.get("response", []):
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        home_logo = match["teams"]["home"]["logo"]
        away_logo = match["teams"]["away"]["logo"]
        league_name = match["league"]["name"]
        match_time = match["fixture"]["date"].split("T")[1][:5]

        result, over_under, btts, corners, adv_pred = predict_match()
        affiliate_link = "https://www.examplebet.com/?ref=YOUR_AFFILIATE_ID"
        is_hot = True if random.random() < 0.3 else False

        live_matches.append({
            "home": home, "away": away, "home_logo": home_logo, "away_logo": away_logo,
            "league": league_name, "time": match_time, "status": "Live",
            "result": result, "goals": over_under, "btts": btts, "corners": corners,
            "adv_pred": adv_pred, "affiliate_link": affiliate_link, "is_hot": is_hot
        })

    # MAJOR LEAGUES TODAY
    url_upcoming = f"https://v3.football.api-sports.io/fixtures?date={today}"
    up_data = requests.get(url_upcoming, headers=headers).json()
    major_matches = []
    for match in up_data.get("response", []):
        league_name = match["league"]["name"]
        if league_name in MAJOR_LEAGUES:
            home = match["teams"]["home"]["name"]
            away = match["teams"]["away"]["name"]
            home_logo = match["teams"]["home"]["logo"]
            away_logo = match["teams"]["away"]["logo"]
            match_time = match["fixture"]["date"].split("T")[1][:5]

            result, over_under, btts, corners, adv_pred = predict_match()
            affiliate_link = "https://www.examplebet.com/?ref=YOUR_AFFILIATE_ID"
            is_hot = True if random.random() < 0.3 else False

            major_matches.append({
                "home": home, "away": away, "home_logo": home_logo, "away_logo": away_logo,
                "league": league_name, "time": match_time, "status": "Upcoming",
                "result": result, "goals": over_under, "btts": btts, "corners": corners,
                "adv_pred": adv_pred, "affiliate_link": affiliate_link, "is_hot": is_hot
            })

    # Sort hot matches on top
    live_matches = sorted(live_matches, key=lambda x: x['is_hot'], reverse=True)
    major_matches = sorted(major_matches, key=lambda x: x['is_hot'], reverse=True)

    return render_template("index.html", live_matches=live_matches, major_matches=major_matches, session=session, PAYSTACK_VERIFIED=PAYSTACK_VERIFIED)

# ------------------- LOGIN / REGISTER -------------------
@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        username=request.form["username"]
        password=generate_password_hash(request.form["password"])
        conn=sqlite3.connect("users.db")
        cursor=conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username,password) VALUES (?,?)",(username,password))
        except:
            return "Username exists!"
        conn.commit(); conn.close()
        return redirect("/login")
    return render_template("register.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        username=request.form["username"]
        password=request.form["password"]
        conn=sqlite3.connect("users.db")
        cursor=conn.cursor()
        cursor.execute("SELECT password,is_premium FROM users WHERE username=?",(username,))
        user=cursor.fetchone()
        conn.close()
        if user and check_password_hash(user[0],password):
            session["username"]=username
            session["is_premium"]=user[1]
            return redirect("/")
        return "Invalid login!"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ------------------- PREMIUM SUBSCRIBE -------------------
@app.route("/subscribe/<username>")
def subscribe(username):
    if not PAYSTACK_VERIFIED:
        return "<h3>Premium payments coming soon. Affiliate links are active!</h3><a href='/'>Go Back</a>"

    return f"""
    <html><body style='text-align:center;color:white;background:#0b0b0b;'>
    <h2>Pay 1000 NGN to unlock Premium Predictions</h2>
    <button type="button" onclick="payWithPaystack()">Pay Now</button>
    <script src="https://js.paystack.co/v1/inline.js"></script>
    <script>
    function payWithPaystack(){{
        var handler = PaystackPop.setup({{
            key: '{PAYSTACK_PUBLIC_KEY}',
            email: '{username}@example.com',
            amount: 100000,
            currency: 'NGN',
            ref: ''+Math.floor((Math.random()*1000000000)+1),
            callback: function(response){{
                window.location.href='/verify_payment/'+response.reference+'/{username}';
            }},
            onClose: function(){{
                alert('Payment cancelled');
            }}
        }});
        handler.openIframe();
    }}
    </script>
    </body></html>
    """

@app.route("/verify_payment/<ref>/<username>")
def verify_payment(ref,username):
    if not PAYSTACK_VERIFIED:
        return "<h3>Paystack not verified yet.</h3><a href='/'>Go Back</a>"

    url=f"https://api.paystack.co/transaction/verify/{ref}"
    headers={"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    response = requests.get(url, headers=headers).json()
    if response['data']['status']=='success':
        conn=sqlite3.connect("users.db")
        cursor=conn.cursor()
        cursor.execute("UPDATE users SET is_premium=1 WHERE username=?",(username,))
        conn.commit(); conn.close()
        return "<h2>Payment successful! You are now a premium user.</h2><a href='/'>Go Back</a>"
    return "<h2>Payment verification failed.</h2><a href='/'>Try Again</a>"

if __name__=="__main__":
    app.run(debug=True)