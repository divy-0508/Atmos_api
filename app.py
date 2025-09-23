import os
from flask import Flask, render_template, request, flash, redirect, url_for
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-key-123")

API_KEY = os.getenv("OPENWEATHER_API_KEY", "73c4b8c1219965b4a59b32527bd852b0")


def get_weather_data(city_name):
    """Fetch current weather from OpenWeatherMap (current weather endpoint)."""
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city_name, "appid": API_KEY, "units": "metric"}
    try:
        resp = requests.get(base_url, params=params, timeout=10)
        data = resp.json()
        if resp.status_code == 200:
            weather_obj = data.get("weather", [{}])[0]
            return {
                "city": data.get("name"),
                "country": data.get("sys", {}).get("country"),
                "temperature": round(data.get("main", {}).get("temp", 0), 1),
                "feels_like": round(data.get("main", {}).get("feels_like", 0), 1),
                "description": weather_obj.get("description", "").title(),
                "weather_main": weather_obj.get("main", "").lower(),
                "icon": weather_obj.get("icon", ""),
                "humidity": int(data.get("main", {}).get("humidity", 0)),
                "wind_speed": data.get("wind", {}).get("speed", 0),
                "pressure": data.get("main", {}).get("pressure", 0),
                # Use clouds.all as a proxy for rain chance (0-100)
                "clouds": int(data.get("clouds", {}).get("all", 0)),
            }
        else:
            return {"error": data.get("message", "Unknown error")}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def pick_bg_class_and_rain(weather):
    """Return body_class and rain_chance (0-100) based on API fields."""
    desc = (weather.get("weather_main") or "").lower()
    icon = weather.get("icon", "")
    rain_chance = int(weather.get("clouds", 0))
    if "rain" in desc or "drizzle" in desc:
        body_class = "rain"
    elif "cloud" in desc or "overcast" in desc:
        body_class = "cloudy"
    elif icon.endswith("n"):
        body_class = "night"
    else:
        body_class = "clear"
    return body_class, rain_chance


def time_to_minutes(t):
    """Convert 'HH:MM' string to minutes since midnight; return None if invalid."""
    if not t:
        return None
    try:
        parts = t.split(":")
        hours = int(parts[0])
        mins = int(parts[1])
        return hours * 60 + mins
    except Exception:
        return None


def compute_comfort_score(rain_pct, temp_c, hum_pct, time_str):
    """
    Evaluate comfort score and recommendations using the 15-rule table.
    We'll match rules in order and return the first match; otherwise return a sensible fallback.
    """
    # Helper: create rule entries:
    # each rule is dict with rain_min, rain_max, temp_min, temp_max, hum_min, hum_max, time_start, time_end (minutes),
    # score, game, activities (list)
    # Tolerances: temp +/-1, hum +/-5
    temp_tol = 1
    hum_tol = 5

    def t(hm):
        # hm like "08:00–10:00" or "05:30–07:30" or "17:30–19:30" (unicode en-dash may be used)
        if not hm:
            return None, None
        # normalize dash
        hm = hm.replace("–", "-").replace("—", "-")
        start, end = hm.split("-")
        return time_to_minutes(start.strip()), time_to_minutes(end.strip())

    rules = [
        {"rain": (0, 10),  "temp": (23, 23), "hum": (48, 48), "time": ("08:00-10:00"), "score":95, "game":"Frisbee",
         "acts":["Morning park walk","Light jogging","Outdoor photography"]},
        {"rain": (15,25),  "temp": (25,25), "hum": (55,55), "time": ("15:00-17:00"), "score":88, "game":"Badminton",
         "acts":["Outdoor photography","Cycling in park","Street food exploration"]},
        {"rain": (55,65),  "temp": (18,18), "hum": (70,70), "time": ("14:00-16:00"), "score":65, "game":"Chess",
         "acts":["Reading in a café","Visiting a museum","Indoor sketching"]},
        {"rain": (75,85),  "temp": (21,21), "hum": (85,85), "time": ("18:00-20:00"), "score":50, "game":"Ludo",
         "acts":["Indoor cooking session","Baking cookies","Watching a documentary"]},
        {"rain": (5,15),   "temp": (30,30), "hum": (40,40), "time": ("17:00-19:00"), "score":78, "game":"Volleyball",
         "acts":["Evening cycling","Sunset photography","Ice cream outing"]},
        {"rain": (0,5),    "temp": (15,15), "hum": (45,45), "time": ("07:00-09:00"), "score":90, "game":"Cricket",
         "acts":["Nature trail hike","Birdwatching","Outdoor yoga"]},
        {"rain": (45,55),  "temp": (28,28), "hum": (60,60), "time": ("13:00-15:00"), "score":68, "game":"Carrom",
         "acts":["DIY craft project","Indoor plant care","Listening to podcasts"]},
        {"rain": (90,100), "temp": (19,19), "hum": (95,95), "time": ("20:00-22:00"), "score":35, "game":"Video games (FIFA)",
         "acts":["Movie marathon","Hot chocolate & reading","Puzzle solving"]},
        {"rain": (10,20),  "temp": (22,22), "hum": (50,50), "time": ("05:30-07:30"), "score":96, "game":"Yoga",
         "acts":["Sunrise meditation","Light stretching","Journaling outdoors"]},
        {"rain": (35,45),  "temp": (26,26), "hum": (65,65), "time": ("10:00-12:00"), "score":72, "game":"Table tennis",
         "acts":["Indoor gardening","Organizing workspace","Cooking a new recipe"]},
        {"rain": (0,10),   "temp": (35,35), "hum": (30,30), "time": ("12:00-14:00"), "score":70, "game":"Swimming",
         "acts":["Poolside reading","Cold beverage tasting","Light water aerobics"]},
        {"rain": (65,75),  "temp": (16,16), "hum": (80,80), "time": ("19:00-21:00"), "score":48, "game":"Board games",
         "acts":["Baking bread","Knitting or crochet","Watching a comedy show"]},
        {"rain": (20,30),  "temp": (20,20), "hum": (55,55), "time": ("06:00-08:00"), "score":90, "game":"Jogging",
         "acts":["Birdwatching","Nature photography","Outdoor stretching"]},
        {"rain": (80,90),  "temp": (24,24), "hum": (75,75), "time": ("17:30-19:30"), "score":55, "game":"Puzzle games",
         "acts":["Home karaoke night","Cooking with friends","Indoor dance session"]},
        {"rain": (0,5),    "temp": (12,12), "hum": (40,40), "time": ("14:00-16:00"), "score":88, "game":"Mini-golf",
         "acts":["Outdoor sketching","Visit a botanical garden","Reading in the park"]},
    ]

    # convert input time to minutes
    time_minutes = time_to_minutes(time_str)

    # Try exact-match rules (with tolerances)
    for r in rules:
        r_rmin, r_rmax = r["rain"]
        r_tmin, r_tmax = r["temp"]
        r_hmin, r_hmax = r["hum"]
        tstart, tend = t(r["time"])
        # rain check
        if not (r_rmin <= rain_pct <= r_rmax):
            continue
        # temp check
        if not ((r_tmin - temp_tol) <= temp_c <= (r_tmax + temp_tol)):
            continue
        # hum check
        if not ((r_hmin - hum_tol) <= hum_pct <= (r_hmax + hum_tol)):
            continue
        # time check (if time provided)
        if time_minutes is None:
            # if no time provided, still accept the rule (less strict)
            pass
        else:
            if tstart is None or tend is None:
                # skip time-matching if range invalid
                pass
            else:
                if not (tstart <= time_minutes <= tend):
                    continue

        # matched
        return {
            "score": r["score"],
            "game": r["game"],
            "activities": r["acts"],
            "matched_rule": r
        }

    # Fallback: compute a simple combined comfort score
    # Ideal temp for comfort ~ 22-25; humidity ideal ~ 40-55; rain ideally low.
    temp_score = max(0, 100 - abs(22.5 - temp_c) * 4)  # penalize per deg
    hum_score = max(0, 100 - abs(50 - hum_pct) * 1.2)
    rain_score = max(0, 100 - rain_pct * 1.5)
    combined = round((temp_score * 0.4 + hum_score * 0.3 + rain_score * 0.3))

    # Provide reasonable recommendations based on combined score
    if combined >= 85:
        game = "Frisbee","Badminton", "Mini‑golf"
        activities = ["Morning park walk", "Light jogging", "Outdoor photography"]
    elif combined >= 70:
        game = "Volleyball", "Table-Tennis", "Bedminton"
        activities = ["Evening cycling", "Sunset photography", "Ice cream outing"]
    elif combined >= 50:
        game = "Chess", "Ludo", "Carrom", "Uno"
        activities = ["Baking session", "Indoor sketching", "Reading"]
    else:
        game = "GTA-5", "Clash-Of-clanes", "FreeGuy"
        activities = ["Movie marathon", "Hot chocolate & reading", "Puzzle time"]

    return {
        "score": combined,
        "game": game,
        "activities": activities,
        "matched_rule": None,
    }


@app.route("/")
def root():
    # return render_template("index.html")
    return redirect(url_for("animate"))

@app.route("/animate")
def animate():
    return render_template("animate.html")


@app.route("/home")
def index():
    return render_template("index.html")



@app.route("/weather", methods=["POST"])
def weather():
    city = request.form.get("city", "").strip()
    time_input = request.form.get("time", "").strip() or None

    if not city:
        flash("Please enter a city name", "error")
        return redirect(url_for("index"))

    weather = get_weather_data(city)
    if "error" in weather:
        flash(f"Could not fetch weather: {weather['error']}", "error")
        return redirect(url_for("index"))

    body_class, rain_chance = pick_bg_class_and_rain(weather)

    # prediction = rain_chance (proxy)
    prediction = int(rain_chance)

    # recommendation generated in comfort route too, but keep simple here
    recommendation = (
        "High chance of rain — consider taking an umbrella."
        if prediction >= 50
        else "Low chance of rain — enjoy your day!"
    )

    return render_template(
        "weather.html",
        weather=weather,
        time=time_input,
        body_class=body_class,
        prediction=prediction,
        recommendation=recommendation,
    )


@app.route("/comfort_score")
def comfort_score():
    # expects query params: city, temperature, humidity, rain, time
    city = request.args.get("city") or request.args.get("location") or ""
    try:
        temp = float(request.args.get("temperature") or request.args.get("temp") or 0)
    except Exception:
        temp = 0.0
    try:
        hum = int(float(request.args.get("humidity") or request.args.get("hum") or 0))
    except Exception:
        hum = 0
    try:
        rain = int(float(request.args.get("rain") or request.args.get("prediction") or 0))
    except Exception:
        rain = 0
    time_in = request.args.get("time") or ""

    result = compute_comfort_score(rain_pct=rain, temp_c=temp, hum_pct=hum, time_str=time_in)

    return render_template(
        "comfort_score.html",
        city=city,
        temperature=temp,
        humidity=hum,
        rain=rain,
        time=time_in,
        score=result["score"],
        game=result["game"],
        activities=result["activities"],
        matched_rule=result.get("matched_rule"),
    )


# Footer pages
@app.route("/mission")
def mission():
    return render_template("mission.html")


@app.route("/technology")
def tech():
    return render_template("technology.html")


@app.route("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=True)
