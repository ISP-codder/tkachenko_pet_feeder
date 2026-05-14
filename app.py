from flask import Flask, Response, render_template, redirect, request, session, url_for, jsonify
from helpers import cam_connect, generate_frames, flash, send_feed_command, start_schedule, stop_schedule, schedule_is_running

app = Flask(__name__)
app.secret_key = 'daniil_super_secret_key_777'

ADMIN_USERNAME = "daniil"
ADMIN_PASSWORD = "347042Daniil"

settings = {
    "portion": "SMALL",
    "schedule_mode": "off",       # "off" | "interval" | "timed"
    "interval_seconds": 3600,
    "feed_times": [],             # список строк "HH:MM"
    "schedule_portion": "SMALL",
    "pet_id": 16,
    "accuracy": 0.65,
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
        generate_frames(settings["pet_id"], settings["accuracy"]),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route("/settings", methods=["GET", "POST"])
def handle_settings():
    if request.method == "POST":
        # Порция для ручной подачи
        portion_input = request.form.get("portion", "smallPortion")
        settings["portion"] = (
            'LARGE' if portion_input == 'largePortion'
            else 'MED' if portion_input == 'medPortion'
            else 'SMALL'
        )

        # Режим расписания
        schedule_mode = request.form.get("schedule_mode", "off")
        settings["schedule_mode"] = schedule_mode

        # Порция для расписания
        sp_input = request.form.get("schedule_portion", "smallPortion")
        settings["schedule_portion"] = (
            'LARGE' if sp_input == 'largePortion'
            else 'MED' if sp_input == 'medPortion'
            else 'SMALL'
        )

        if schedule_mode == "interval":
            h = int(request.form.get("interval_hours", 0) or 0)
            m = int(request.form.get("interval_minutes", 0) or 0)
            s = int(request.form.get("interval_seconds", 0) or 0)
            settings["interval_seconds"] = h * 3600 + m * 60 + s
            settings["feed_times"] = []

        elif schedule_mode == "timed":
            times = []
            for i in range(8):
                t = request.form.get(f"time_{i}", "").strip()
                if t:
                    times.append(t)
            settings["feed_times"] = times
            settings["interval_seconds"] = 0

        else:
            settings["feed_times"] = []
            settings["interval_seconds"] = 0

        start_schedule(settings)
        return redirect("/")

    return render_template('settings.html', settings=settings, schedule_running=schedule_is_running())


@app.route('/schedule/stop', methods=['POST'])
def schedule_stop():
    stop_schedule()
    settings["schedule_mode"] = "off"
    return jsonify({"status": "stopped"})


@app.route('/schedule/status')
def schedule_status():
    return jsonify({
        "running": schedule_is_running(),
        "mode": settings["schedule_mode"],
        "interval_seconds": settings.get("interval_seconds", 0),
        "feed_times": settings.get("feed_times", []),
        "schedule_portion": settings.get("schedule_portion", "SMALL"),
    })


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