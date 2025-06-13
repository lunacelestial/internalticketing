from flask import Flask, render_template, request, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

# --- App Configuration ---
app = Flask(__name__)
db_path = os.path.abspath("database.db")
print(f"📂 Working Directory: {os.getcwd()}")
print(f"📁 Database Path: {db_path}")

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Utility: Shift Code Calculation ---
def get_shift_code():
    now = datetime.now()
    hour = now.hour
    day = now.weekday()
    is_day_shift = 6 <= hour < 18

    jan4 = datetime(now.year, 1, 4)
    jan4_offset = (jan4.weekday() + 6) % 7
    week_start = jan4 - timedelta(days=jan4_offset)
    week_no = ((now - week_start).days // 7) + 1
    is_even_week = week_no % 2 == 0

    if day <= 2:  # Sunday–Tuesday
        return "401" if is_day_shift else "402"
    elif day == 3:  # Wednesday
        return "403" if is_day_shift and is_even_week else "404" if not is_day_shift and is_even_week else "401" if is_day_shift else "402"
    else:  # Thursday–Saturday
        return "403" if is_day_shift else "404"

# --- Database Model ---
class FailureReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shift = db.Column(db.String(10))
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)
    date_solved = db.Column(db.DateTime, default=datetime.utcnow)
    location = db.Column(db.String(100), nullable=False)
    asset = db.Column(db.String(100), nullable=False)
    failure_mode = db.Column(db.String(200), nullable=False)
    root_cause = db.Column(db.String(200), nullable=False)
    failure_type = db.Column(db.String(100), nullable=False)
    resolved = db.Column(db.Boolean, default=True)

# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        form_data = request.form.to_dict()
        print("Form data received:", form_data)

        report = FailureReport(
            shift=get_shift_code(),
            location=form_data['location'],
            asset=form_data['asset'],
            failure_mode=form_data['failure_mode'],
            root_cause=form_data['root_cause'],
            failure_type=form_data['failure_type']
        )
        db.session.add(report)
        db.session.commit()
        print("✅ Report committed to database.")
        return redirect('/')

    return render_template('index.html')


# --- Protected GCTD View ---
VIEW_PASSWORD = os.environ.get("VIEW_PASSWORD", "changeme")


@app.route('/gctd')
def gctd_view():
    auth = request.authorization
    if not auth or auth.username != 'gctd' or auth.password != VIEW_PASSWORD:
        return Response(
            'Access denied', 401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'}
        )

    tickets = FailureReport.query.order_by(FailureReport.date_reported.desc()).all()
    return render_template('gctd.html', tickets=tickets)

# --- Resolve Ticket Route ---
@app.route('/resolve/<int:id>')
def resolve_ticket(id):
    ticket = FailureReport.query.get_or_404(id)
    ticket.resolved = True
    ticket.date_solved = datetime.utcnow()
    db.session.commit()
    return redirect('/gctd')

# --- Main ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        from sqlalchemy import inspect
        tables = inspect(db.engine).get_table_names()
        print("✅ DB initialized")
        print("Tables:", tables)
    
    app.run(debug=True)
