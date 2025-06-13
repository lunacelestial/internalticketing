from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Shift Code Calculation Logic ---
def get_shift_code():
    now = datetime.now()
    hour = now.hour
    day = now.weekday()  # Monday=0, Sunday=6
    is_day_shift = 6 <= hour < 18

    # Calculate ISO week number (same as ExcelScript logic)
    jan4 = datetime(now.year, 1, 4)
    jan4_offset = (jan4.weekday() + 6) % 7
    week_start = jan4 - timedelta(days=jan4_offset)
    week_no = ((now - week_start).days // 7) + 1
    is_even_week = week_no % 2 == 0

    if day <= 2:  # Sunday–Tuesday
        return "401" if is_day_shift else "402"
    elif day == 3:  # Wednesday
        if is_even_week:
            return "403" if is_day_shift else "404"
        else:
            return "401" if is_day_shift else "402"
    else:  # Thursday–Saturday
        return "403" if is_day_shift else "404"

# --- SQLAlchemy Model ---
class FailureReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shift = db.Column(db.String(10))
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)
    date_solved = db.Column(db.DateTime, default=datetime.utcnow)  # for now, same as reported
    location = db.Column(db.String(100), nullable=False)
    asset = db.Column(db.String(100), nullable=False)
    failure_mode = db.Column(db.String(200), nullable=False)
    root_cause = db.Column(db.String(200), nullable=False)
    failure_type = db.Column(db.String(100), nullable=False)
    resolved = db.Column(db.Boolean, default=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        print("Form data received:", request.form.to_dict())

        report = FailureReport(
            shift=get_shift_code(),
            location=request.form['location'],
            asset=request.form['asset'],
            failure_mode=request.form['failure_mode'],
            root_cause=request.form['root_cause'],
            failure_type=request.form['failure_type']
        )
        db.session.add(report)
        db.session.commit()
        return redirect('/')
    return render_template('index.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
