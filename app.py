import os, re, json
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import markdown2

app = Flask(__name__)
app.secret_key = os.environ.get("RSVCARD_SECRET", "change_this_to_a_random_secret")
UPLOAD_FOLDER = 'static/uploads'
EVENTS_FILE = 'events.json'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME", "yeman7201@gmail.com")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD", "Asdf12@rig")
mail = Mail(app)

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admins")

def load_events():
    if not os.path.exists(EVENTS_FILE):
        return {}
    with open(EVENTS_FILE, 'r') as f:
        return json.load(f)

def save_events(events):
    with open(EVENTS_FILE, 'w') as f:
        json.dump(events, f, indent=2)

def render_md(text):
    return markdown2.markdown(text, extras=["break-on-newline"]) if text else ""

def make_slug(name, date):
    slug = f"{name}-{date}".lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    return slug

@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    events = load_events()
    if not events:
        return "No events configured."
    return render_template("event_selector.html", events=events)

@app.route("/<slug>")
def home(slug):
    events = load_events()
    data = events.get(slug)
    if not data:
        abort(404)
    data_html = {k: render_md(v) if isinstance(v, str) else v for k, v in data.items()}
    return render_template("index.html", slug=slug, data=data, data_html=data_html)

@app.route("/<slug>/rsvp", methods=["POST"])
def rsvp(slug):
    events = load_events()
    data = events.get(slug)
    if not data:
        abort(404)

    name = request.form.get("name")
    attending = request.form.get("attending")
    guests = request.form.get("guests")

    rsvp_file = f"{slug}.txt"
    with open(rsvp_file, "a") as f:
        f.write(f"{name},{attending},{guests}\n")

    email = data.get("rsvp_email")
    if email:
        msg = Message(f"New RSVP for {data.get('names')}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[email])
        msg.body = f"Name: {name}\nAttending: {attending}\nGuests: {guests}\n"
        try:
            mail.send(msg)
            flash("Thank you for your RSVP!", "success")
        except Exception:
            flash("RSVP saved, but email failed.", "warning")
    else:
        flash("Thank you for your RSVP!", "success")

    return redirect(url_for('home', slug=slug) + "#rsvp")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form["username"] == ADMIN_USER and
            request.form["password"] == ADMIN_PASS):
            session["logged_in"] = True
            return redirect(url_for("admin_list"))
        flash("Wrong username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session["logged_in"] = False
    return redirect(url_for("login"))

@app.route("/admin")
def admin_list():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    events = load_events()
    return render_template("admin_list.html", events=events)

@app.route("/admin/new", methods=["GET", "POST"])
def admin_new():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form["names"]
        date = request.form["date"]
        slug = make_slug(name, date)
        events = load_events()

        if slug in events:
            flash("An event with that name/date already exists.", "danger")
            return redirect(url_for("admin_new"))

        events[slug] = {
            "names": name,
            "date": date,
            "invitation": request.form["invitation"],
            "venue": request.form["venue"],
            "venue_map": request.form["venue_map"],
            "gift_message": request.form["gift_message"],
            "rsvp_enabled": "rsvp_enabled" in request.form,
            "rsvp_email": request.form["rsvp_email"],
            "font": request.form.get("font", "Roboto"),
            "home_photo": "",
            "invitation_photo": "",
            "venue_photo": "",
            "gift_photo": "",
            "rsvp_photo": ""
        }

        save_events(events)
        flash("Event created successfully!", "success")
        return redirect(url_for("home", slug=slug))

    return render_template("admin.html", slug=None, data={})

@app.route("/admin/<slug>", methods=["GET", "POST"])
def admin_edit(slug):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    events = load_events()
    data = events.get(slug)
    if not data:
        abort(404)

    if request.method == "POST":
        for key in ["names", "date", "invitation", "venue", "venue_map", "gift_message", "rsvp_email", "font"]:
            data[key] = request.form.get(key, data.get(key))
        data["rsvp_enabled"] = "rsvp_enabled" in request.form

        for field in ["home_photo", "invitation_photo", "venue_photo", "gift_photo", "rsvp_photo"]:
            file = request.files.get(field)
            if file and file.filename:
                filename = secure_filename(file.filename)
                path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(path)
                data[field] = f"/static/uploads/{filename}"

        save_events(events)
        flash("Event updated successfully.", "success")

    return render_template("admin.html", slug=slug, data=data)

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=False, host="0.0.0.0", port=5000)