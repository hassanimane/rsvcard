from flask import Flask, render_template, request, redirect, url_for, session, flash
import json, os, re
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import markdown2

app = Flask(__name__)
app.secret_key = 'change_this_to_a_random_secret'  # Set your own secret!
UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = 'data.json'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'yeman7201@gmail.com'   # CHANGE THIS
app.config['MAIL_PASSWORD'] = 'Asdf12@rig'       # Gmail App Password (not your login)
mail = Mail(app)

ADMIN_USER = 'admin'
ADMIN_PASS = 'admins'  # CHANGE THIS

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def render_md(text):
    if text:
        return markdown2.markdown(text, extras=["break-on-newline"])
    return ""

def event_slug(data):
    # Generate a safe file name from event name and date
    name = data.get('names', 'event')
    date = data.get('date', '')
    slug = f"{name}-{date}".lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    return slug

@app.route("/")
def home():
    data = load_data()
    data_html = {k: render_md(v) if isinstance(v, str) else v for k, v in data.items()}
    return render_template("index.html", data=data, data_html=data_html)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    data = load_data()
    if request.method == "POST":
        data["names"] = request.form["names"]
        data["date"] = request.form["date"]
        data["invitation"] = request.form["invitation"]
        data["venue"] = request.form["venue"]
        data["venue_map"] = request.form["venue_map"]
        data["gift_message"] = request.form["gift_message"]
        data["rsvp_enabled"] = "rsvp_enabled" in request.form
        data["rsvp_email"] = request.form["rsvp_email"]
        # Handle image uploads for each section
        for field in ["home_photo", "invitation_photo", "venue_photo", "gift_photo", "rsvp_photo"]:
            if field in request.files:
                f = request.files[field]
                if f and f.filename:
                    filename = secure_filename(f.filename)
                    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    f.save(path)
                    data[field] = f"/static/uploads/{filename}"
        save_data(data)
        flash("Information updated successfully.", "success")
    return render_template("admin.html", data=data)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form["username"] == ADMIN_USER and
            request.form["password"] == ADMIN_PASS):
            session["logged_in"] = True
            return redirect(url_for("admin"))
        else:
            flash("Wrong username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session["logged_in"] = False
    return redirect(url_for("home"))

@app.route("/rsvp", methods=["POST"])
def rsvp():
    name = request.form.get("name")
    attending = request.form.get("attending")
    guests = request.form.get("guests")
    data = load_data()
    email = data.get("rsvp_email", None)
    slug = event_slug(data)
    rsvp_filename = f"{slug}.txt"

    # Save RSVP to event-named file
    with open(rsvp_filename, "a") as f:
        f.write(f"{name},{attending},{guests}\n")

    # Send email notification if enabled
    if email:
        msg = Message("New Wedding RSVP",
                      sender=app.config["MAIL_USERNAME"],
                      recipients=[email])
        msg.body = (
            f"New RSVP for {data.get('names','the event')}!\n"
            f"Name: {name}\n"
            f"Attending: {attending}\n"
            f"Number of guests: {guests}"
        )
        try:
            mail.send(msg)
        except Exception as e:
            print("Mail send error:", e)
            flash("RSVP saved, but failed to send email.", "warning")
        else:
            flash("Thank you for your RSVP!", "success")
    else:
        flash("Thank you for your RSVP!", "success")
    return redirect(url_for("home") + "#rsvp")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    if not os.path.exists("static/uploads"):
        os.makedirs("static/uploads")
    app.run(debug=True, host="0.0.0.0", port=port)



