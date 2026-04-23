import io
import os
import sqlite3
import pickle
import pandas as pd
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'replace-this-with-a-secure-secret-key'

DATABASE = os.path.join(os.path.dirname(__file__), 'users.db')
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model.pkl')

ADMIN_EMAILS = {
    'yusafsonu30@gmail.com',
    'musananjireddy2006@gmail.com',
    'muthyalanikhilreddy1@gmail.com',
    'chettigaricharantejagoud@gmail.com'
}

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'error'
login_manager.login_message = 'Please log in to continue.'

# Load the trained model from model.pkl once at startup.
model = None
if os.path.exists(MODEL_PATH):
    try:
        with open(MODEL_PATH, 'rb') as model_file:
            model = pickle.load(model_file)
    except Exception:
        model = None


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def init_db():
    db = get_db()
    db.execute(
        '''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )'''
    )
    db.commit()


class User(UserMixin):
    def __init__(self, user_id, name, email, role):
        self.id = user_id
        self.name = name
        self.email = email
        self.role = role

    @property
    def is_admin(self):
        return self.role == 'admin'


@login_manager.user_loader
def load_user(user_id):
    user = query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)
    if user:
        return User(user['id'], user['name'], user['email'], user['role'])
    return None


@app.before_request
def before_request():
    init_db()


@app.context_processor
def inject_user():
    return {
        'logged_in': current_user.is_authenticated
    }


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to continue.', 'error')
            return redirect(url_for('login'))
        if current_user.role != 'admin':
            flash('Access denied. Admins only.', 'error')
            return redirect(url_for('predict'))
        return view(*args, **kwargs)
    return wrapped_view


def parse_int(value, default=0):
    try:
        return round(float(value))
    except (TypeError, ValueError):
        return default


def parse_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def predict_risk(attendance, avg_marks, study_hours, backlogs):
    score = 0
    if attendance < 75:
        score += 1
    if avg_marks < 60:
        score += 1
    if study_hours < 4:
        score += 1
    if backlogs > 0:
        score += 1
    return 1 if score >= 2 else 0


def risk_label(prediction, attendance, avg_marks, study_hours, backlogs):
    if prediction == 1:
        return 'High'
    if attendance < 60 or avg_marks < 55 or study_hours < 3 or backlogs == 2:
        return 'Medium'
    return 'Low'


def suggestion_for_risk(risk):
    if risk == 'High':
        return 'Improve study habits and clear backlogs.'
    if risk == 'Medium':
        return 'Stay consistent and improve focus.'
    return 'Keep up the good work.'


def classify_student(attendance, avg_marks, study_hours, backlogs):
    if model is not None:
        try:
            prediction = int(model.predict([[attendance, avg_marks, study_hours, backlogs]])[0])
        except Exception:
            prediction = predict_risk(attendance, avg_marks, study_hours, backlogs)
    else:
        prediction = predict_risk(attendance, avg_marks, study_hours, backlogs)

    risk = risk_label(prediction, attendance, avg_marks, study_hours, backlogs)
    suggestion = suggestion_for_risk(risk)
    return {
        'attendance': attendance,
        'avg_marks': avg_marks,
        'study_hours': study_hours,
        'backlogs': backlogs,
        'risk': risk,
        'suggestion': suggestion
    }


def compute_summary(results):
    high = sum(1 for row in results if row.get('risk') == 'High')
    medium = sum(1 for row in results if row.get('risk') == 'Medium')
    low = sum(1 for row in results if row.get('risk') == 'Low')
    return len(results), high, medium, low


def compute_analytics(results):
    groups = {'High': [], 'Medium': [], 'Low': []}
    for row in results:
        groups.get(row.get('risk', 'Low'), []).append(row)

    def average(key, rows, default):
        return round(sum(r.get(key, 0) for r in rows) / len(rows), 2) if rows else default

    return {
        'attendance_high': average('attendance', groups['High'], 40),
        'attendance_medium': average('attendance', groups['Medium'], 65),
        'attendance_low': average('attendance', groups['Low'], 88),
        'backlogs_high': average('backlogs', groups['High'], 3.2),
        'backlogs_medium': average('backlogs', groups['Medium'], 1.3),
        'backlogs_low': average('backlogs', groups['Low'], 0.4),
        'study_high': average('study_hours', groups['High'], 2.4),
        'study_medium': average('study_hours', groups['Medium'], 4.6),
        'study_low': average('study_hours', groups['Low'], 6.8)
    }


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user_row = query_db('SELECT * FROM users WHERE email = ?', [email], one=True)

        if user_row and check_password_hash(user_row['password'], password):
            user = User(user_row['id'], user_row['name'], user_row['email'], user_row['role'])
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('dashboard'))
            return redirect(url_for('predict'))

        flash('Invalid email or password.', 'error')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard') if current_user.role == 'admin' else url_for('predict'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('signup'))

        if query_db('SELECT * FROM users WHERE email = ?', [email], one=True):
            flash('Email is already registered.', 'error')
            return redirect(url_for('signup'))

        requested_role = request.form.get('role', 'user').strip().lower()
        if requested_role == 'admin':
            if email not in ADMIN_EMAILS:
                flash('Admin registration is restricted to authorized email addresses.', 'error')
                return redirect(url_for('signup'))
            role = 'admin'
        else:
            role = 'user'

        hashed_password = generate_password_hash(password)
        db = get_db()
        db.execute(
            'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
            (name, email, hashed_password, role)
        )
        db.commit()

        flash('Account created successfully. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    if request.method == 'POST':
        attendance = parse_float(request.form.get('attendance', 0))
        avg_marks = parse_float(request.form.get('avg_marks', 0))
        study_hours = parse_float(request.form.get('study_hours', 0))
        backlogs = parse_int(request.form.get('backlogs', 0))

        # Server-side validation
        errors = []
        if not (0 <= attendance <= 100):
            errors.append("Attendance must be between 0 and 100.")
        if not (0 <= avg_marks <= 100):
            errors.append("Average marks must be between 0 and 100.")
        if study_hours < 0:
            errors.append("Study hours must be 0 or more.")
        if backlogs < 0:
            errors.append("Backlogs must be 0 or more.")

        if errors:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('predict'))

        student = classify_student(attendance, avg_marks, study_hours, backlogs)
        results = [student]
        total, high, medium, low = compute_summary(results)

        session['students'] = results
        session['total'] = total
        session['high'] = high
        session['medium'] = medium
        session['low'] = low

        return render_template(
            'results.html',
            data=results,
            total=total,
            high=high,
            medium=medium,
            low=low
        )

    return render_template('predict.html')


@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(url_for('predict'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('predict'))

    try:
        try:
            df = pd.read_csv(file, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file, encoding='latin1')
        df.columns = df.columns.str.strip().str.lower()
    except Exception as exc:
        flash(f'Could not read CSV file: {exc}', 'error')
        return redirect(url_for('predict'))

    required_columns = {'attendance', 'avg_marks', 'study_hours', 'backlogs'}
    if not required_columns.issubset(df.columns):
        flash(f'CSV must contain columns: {", ".join(required_columns)}', 'error')
        return redirect(url_for('predict'))

    results = []
    for _, row in df.iterrows():
        attendance = parse_float(row.get('attendance', 0))
        avg_marks = parse_float(row.get('avg_marks', 0))
        study_hours = parse_float(row.get('study_hours', 0))
        backlogs = parse_int(row.get('backlogs', 0))

        # Validate each row
        if not (0 <= attendance <= 100) or not (0 <= avg_marks <= 100) or study_hours < 0 or backlogs < 0:
            continue  # Skip invalid rows
        results.append(classify_student(attendance, avg_marks, study_hours, backlogs))

    if not results:
        flash('No valid student rows were found in the uploaded file.', 'error')
        return redirect(url_for('predict'))

    total, high, medium, low = compute_summary(results)
    session['students'] = results
    session['total'] = total
    session['high'] = high
    session['medium'] = medium
    session['low'] = low

    return render_template(
        'results.html',
        data=results,
        total=total,
        high=high,
        medium=medium,
        low=low
    )


@app.route('/results')
@login_required
def results():
    results = session.get('students', [])
    if not results:
        flash('No prediction results available yet.', 'error')
        return redirect(url_for('predict'))

    total, high, medium, low = compute_summary(results)
    return render_template(
        'results.html',
        data=results,
        total=total,
        high=high,
        medium=medium,
        low=low
    )


@app.route('/dashboard')
@admin_required
def dashboard():
    total = session.get('total', 0)
    high = session.get('high', 0)
    medium = session.get('medium', 0)
    low = session.get('low', 0)
    return render_template(
        'dashboard.html',
        user=current_user,
        total=total,
        high=high,
        medium=medium,
        low=low
    )


@app.route('/counselling')
@admin_required
def counselling():
    students = session.get('students', [])
    high_students = [student for student in students if student.get('risk') == 'High']
    medium_students = [student for student in students if student.get('risk') == 'Medium']
    low_students = [student for student in students if student.get('risk') == 'Low']
    return render_template(
        'counselling.html',
        user=current_user,
        high_students=high_students,
        medium_students=medium_students,
        low_students=low_students
    )


@app.route('/analytics')
@login_required
def analytics():
    metrics = compute_analytics(session.get('students', []))
    return render_template('analytics.html', **metrics)


@app.route('/user_dashboard')
@login_required
def user_dashboard():
    results = session.get('students', [])
    if not results:
        flash('No prediction data available. Please make a prediction first.', 'error')
        return redirect(url_for('predict'))
    total, high, medium, low = compute_summary(results)
    
    # Calculate averages
    attendance_avg = sum(s.get('attendance', 0) for s in results) / len(results) if results else 0
    marks_avg = sum(s.get('avg_marks', 0) for s in results) / len(results) if results else 0
    study_hours_avg = sum(s.get('study_hours', 0) for s in results) / len(results) if results else 0
    backlogs_avg = sum(s.get('backlogs', 0) for s in results) / len(results) if results else 0
    
    return render_template(
        'user_dashboard.html',
        data=results,
        total=total,
        high=high,
        medium=medium,
        low=low,
        attendance_avg=round(attendance_avg, 2),
        marks_avg=round(marks_avg, 2),
        study_hours_avg=round(study_hours_avg, 2),
        backlogs_avg=round(backlogs_avg, 2)
    )


@app.route('/user_counselling')
@login_required
def user_counselling():
    results = session.get('students', [])
    if not results:
        flash('No prediction data available. Please make a prediction first.', 'error')
        return redirect(url_for('predict'))
    high_students = [student for student in results if student.get('risk') == 'High']
    medium_students = [student for student in results if student.get('risk') == 'Medium']
    low_students = [student for student in results if student.get('risk') == 'Low']
    return render_template(
        'user_counselling.html',
        high_students=high_students,
        medium_students=medium_students,
        low_students=low_students
    )


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/resources')
def resources():
    return render_template('learn.html')


@app.route('/download')
@login_required
def download():
    students = session.get('students', [])
    if not students:
        flash('No student results available for download.', 'error')
        return redirect(url_for('predict'))

    df = pd.DataFrame(students)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return send_file(
        io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='student_report.csv'
    )


if __name__ == '__main__':
    app.run(debug=True)