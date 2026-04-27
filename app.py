from flask import Flask, Response, render_template, redirect, request, session, url_for
from helpers import cam_connect, generate_frames, calc_delay, flash, send_feed_command

app = Flask(__name__)

app.secret_key = 'daniil_super_secret_key_777'

ADMIN_USERNAME = "daniil"
ADMIN_PASSWORD = "347042Daniil"

settings = {
    "timer_running": False,
    "feed_delay": 30,
    "pet_id": 16,
    "auto_feed": False,
    "seconds": 30,
    "minutes": 0,
    "hours": 0,
    "accuracy": 0.65,
    "portion": 'SMALL'
}
cam_connect()
@app.before_request
def check_login():
    allowed_routes = ['login', 'static']
    if request.endpoint not in allowed_routes and not session.get('logged_in'):
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = "Неверный логин или пароль!"
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/")
def index(): 
    return render_template('index.html')

@app.route("/stream", methods=["GET", "POST"])
def stream():
    return render_template('stream.html')

@app.route('/video_feed')
def video_feed():
    
    return Response(
        generate_frames(
            settings["feed_delay"], 
            settings["pet_id"], 
            settings["accuracy"], 
            settings["auto_feed"], 
            settings["portion"]
        ), 
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route("/settings", methods=["GET", "POST"])
def handle_settings():
    if request.method == "POST":
        settings["seconds"] = request.form.get("seconds")
        settings["minutes"] = request.form.get("minutes")
        settings["hours"] = request.form.get("hours")
        settings["feed_delay"] = calc_delay(settings["seconds"], settings["minutes"], settings["hours"])

        petSelection = request.form.get("petSelection")
        settings["pet_id"] = 15 if petSelection == 'detectCats' else 14 if petSelection == 'detectBirds' else 16

        accuracyInput = request.form.get("accuracy")
        settings["accuracy"] = 0.5 if accuracyInput == 'lowAccuracy' else 0.8 if accuracyInput == 'highAccuracy' else 0.65

        portionInput = request.form.get("portion")
        settings["portion"] = 'LARGE' if portionInput == 'largePortion' else 'MED' if portionInput == 'medPortion' else 'SMALL'

        settings["auto_feed"] = True if request.form.get("auto_feed") == 'on' else False

        return redirect("/")
    
    return render_template('settings.html', settings=settings)

@app.route('/feed', methods=['POST'])
def feed():
    if request.form.get('feed') == 'button_click':
        send_feed_command(settings["portion"])
        return "OK", 200
    return "Error", 400

@app.route('/flash_on', methods=['POST'])
def flash_on():
    if request.form.get('flash_on') == 'button_click':
        flash('on')
        return "OK", 200
    return "Error", 400

@app.route('/flash_off', methods=['POST'])
def flash_off():
    if request.form.get('flash_off') == 'button_click':
        flash('off')
        return "OK", 200
    return "Error", 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=False)