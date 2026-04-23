import io
import os
import sqlite3
import pickle
import smtplib
import pandas as pd
from functools import wraps
from datetime import datetime, timedelta
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

DATABASE = os.path.join(os.path.dirname(__file__), 'users.db')
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model.pkl')
ENV_PATH = os.path.join(os.path.dirname(__file__), '.env')


def load_env_file(env_path):
    """Load simple KEY=VALUE pairs from a local .env file without extra dependencies."""
    if not os.path.exists(env_path):
        return

    with open(env_path, 'r', encoding='utf-8') as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()

            if not key:
                continue

            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]

            os.environ.setdefault(key, value)


load_env_file(ENV_PATH)

app = Flask(__name__)
app.secret_key = 'replace-this-with-a-secure-secret-key'

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
    db.execute(
        '''CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            attendance REAL NOT NULL,
            avg_marks REAL NOT NULL,
            study_hours REAL NOT NULL,
            backlogs INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
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
        # Convert to float first to handle decimal strings, then to int
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_float(value, default=0.0):
    try:
        # Preserve the original format - if it was an integer input, keep it as float but display appropriately
        val = float(value)
        return val
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


def parse_prediction_timestamp(value):
    if not value:
        return None

    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def format_prediction_timestamp(value):
    parsed = parse_prediction_timestamp(value)
    return parsed.strftime('%Y-%m-%d %H:%M:%S') if parsed else (value or 'N/A')


def build_risk_summary(predictions):
    summary = {'High': 0, 'Medium': 0, 'Low': 0}
    for prediction in predictions:
        if isinstance(prediction, dict):
            risk_level = prediction.get('risk_level') or prediction.get('risk')
        else:
            risk_level = prediction['risk_level'] if 'risk_level' in prediction.keys() else prediction['risk']
        if risk_level in summary:
            summary[risk_level] += 1
    return summary


def smtp_is_configured():
    required_settings = [
        'SMTP_HOST',
        'SMTP_PORT',
        'SMTP_USERNAME',
        'SMTP_PASSWORD',
        'SMTP_FROM_EMAIL'
    ]
    return all(os.getenv(setting) for setting in required_settings)


def send_bulk_notifications(recipients, subject, message):
    if not smtp_is_configured():
        return False, 'SMTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM_EMAIL to enable email delivery.'

    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    from_email = os.getenv('SMTP_FROM_EMAIL')
    use_tls = os.getenv('SMTP_USE_TLS', 'true').strip().lower() not in {'0', 'false', 'no'}

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        if use_tls:
            server.starttls()
        server.login(smtp_username, smtp_password)

        for recipient in recipients:
            email_message = EmailMessage()
            email_message['Subject'] = subject
            email_message['From'] = from_email
            email_message['To'] = recipient['email']
            email_message.set_content(
                f"Hello {recipient['name']},\n\n{message}\n\nRegards,\nDropoutAI Admin Team"
            )
            server.send_message(email_message)

    return True, f'Notification email sent to {len(recipients)} student(s).'


def get_report_styles():
    styles = getSampleStyleSheet()
    return {
        'title': ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=23,
            leading=28,
            textColor=colors.HexColor('#0f172a'),
            alignment=TA_CENTER,
            spaceAfter=8
        ),
        'subtitle': ParagraphStyle(
            'ReportSubtitle',
            parent=styles['BodyText'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#475569'),
            alignment=TA_CENTER,
            spaceAfter=18
        ),
        'section': ParagraphStyle(
            'ReportSection',
            parent=styles['Heading2'],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#0f172a'),
            spaceBefore=12,
            spaceAfter=8
        ),
        'body': ParagraphStyle(
            'ReportBody',
            parent=styles['BodyText'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=6
        ),
        'bullet': ParagraphStyle(
            'ReportBullet',
            parent=styles['BodyText'],
            fontSize=10,
            leading=14,
            leftIndent=12,
            bulletIndent=0,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=4
        ),
        'small': ParagraphStyle(
            'ReportSmall',
            parent=styles['BodyText'],
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#475569'),
            spaceAfter=4
        ),
    }


def get_metric_reference_ranges():
    return {
        'attendance': {
            'label': 'Attendance',
            'unit': '%',
            'ideal': '85% or above',
            'healthy_threshold': 85,
            'warning_threshold': 75,
            'description': 'Attendance reflects class engagement and consistency. Lower attendance usually increases academic gaps and dropout probability.',
            'improvement': 'Improve attendance with a weekly routine, class reminders, and early communication with faculty when issues arise.'
        },
        'avg_marks': {
            'label': 'Average Marks',
            'unit': '%',
            'ideal': '75% or above',
            'healthy_threshold': 75,
            'warning_threshold': 60,
            'description': 'Marks indicate current academic mastery. Scores below the safe range suggest that concepts need revision and support.',
            'improvement': 'Use targeted revision blocks, practice tests, and subject-specific mentoring to raise marks steadily.'
        },
        'study_hours': {
            'label': 'Study Hours',
            'unit': ' hrs/day',
            'ideal': '5 or more hours/day',
            'healthy_threshold': 5,
            'warning_threshold': 3,
            'description': 'Daily study hours show preparation discipline. Very low study time often leads to weak performance and growing backlog pressure.',
            'improvement': 'Adopt a fixed daily study timetable with short revision sessions and one focused practice block each evening.'
        },
        'backlogs': {
            'label': 'Backlogs',
            'unit': '',
            'ideal': '0 backlog',
            'healthy_threshold': 0,
            'warning_threshold': 2,
            'description': 'Backlogs represent unresolved academic carryover. More backlogs sharply raise stress and future dropout risk.',
            'improvement': 'Prioritize one or two backlog subjects at a time and follow a weekly clearing strategy with faculty support.'
        }
    }


def get_risk_color(risk_level):
    return {
        'High': colors.HexColor('#dc2626'),
        'Medium': colors.HexColor('#d97706'),
        'Low': colors.HexColor('#16a34a')
    }.get(risk_level, colors.HexColor('#475569'))


def color_to_hex(color_value):
    red = int(round(color_value.red * 255))
    green = int(round(color_value.green * 255))
    blue = int(round(color_value.blue * 255))
    return f"#{red:02x}{green:02x}{blue:02x}"


def evaluate_metric(metric_key, value):
    metric = get_metric_reference_ranges()[metric_key]

    if metric_key == 'backlogs':
        if value <= metric['healthy_threshold']:
            status = 'Good'
            color = colors.HexColor('#16a34a')
            progress = 'Excellent'
        elif value <= metric['warning_threshold']:
            status = 'Average'
            color = colors.HexColor('#d97706')
            progress = 'Watch'
        else:
            status = 'Poor'
            color = colors.HexColor('#dc2626')
            progress = 'Critical'
    else:
        if value >= metric['healthy_threshold']:
            status = 'Good'
            color = colors.HexColor('#16a34a')
            progress = 'Healthy'
        elif value >= metric['warning_threshold']:
            status = 'Average'
            color = colors.HexColor('#d97706')
            progress = 'Needs attention'
        else:
            status = 'Poor'
            color = colors.HexColor('#dc2626')
            progress = 'At risk'

    return {
        'status': status,
        'color': color,
        'progress': progress,
        'ideal': metric['ideal'],
        'label': metric['label'],
        'description': metric['description'],
        'improvement': metric['improvement']
    }


def build_metric_analysis(prediction):
    metric_keys = ['attendance', 'avg_marks', 'study_hours', 'backlogs']
    analysis = []
    reference = get_metric_reference_ranges()

    for key in metric_keys:
        value = prediction[key]
        assessment = evaluate_metric(key, value)
        unit = reference[key]['unit']
        analysis.append({
            'key': key,
            'label': assessment['label'],
            'value': f"{value}{unit}",
            'ideal': assessment['ideal'],
            'status': assessment['status'],
            'color': assessment['color'],
            'progress': assessment['progress'],
            'description': assessment['description'],
            'issue': assessment['improvement']
        })
    return analysis


def build_risk_reasons(prediction):
    reasons = []
    attendance = prediction['attendance']
    avg_marks = prediction['avg_marks']
    study_hours = prediction['study_hours']
    backlogs = prediction['backlogs']
    risk = prediction['risk_level']

    if attendance < 75:
        reasons.append(f"Attendance is {attendance}%, below the safe engagement zone of 75%+.")
    elif attendance < 85:
        reasons.append(f"Attendance is {attendance}%, acceptable but still below the ideal 85%+ target.")

    if avg_marks < 60:
        reasons.append(f"Average marks are {avg_marks}%, indicating current academic difficulty.")
    elif avg_marks < 75:
        reasons.append(f"Average marks are {avg_marks}%, which is moderate but below the preferred 75%+ range.")

    if study_hours < 3:
        reasons.append(f"Study time is only {study_hours} hours/day, which is too low for stable academic performance.")
    elif study_hours < 5:
        reasons.append(f"Study time is {study_hours} hours/day, below the ideal consistency level.")

    if backlogs > 2:
        reasons.append(f"The student has {backlogs} backlogs, creating strong pressure on future progress.")
    elif backlogs > 0:
        reasons.append(f"The student has {backlogs} backlog(s), which should be cleared early to avoid risk escalation.")

    if risk == 'Low' and not reasons:
        reasons.append('Current metrics are largely within healthy ranges, which supports a low dropout risk profile.')
    elif risk == 'Medium' and len(reasons) < 2:
        reasons.append('The student shows mixed performance signals, so moderate supervision is recommended.')
    elif risk == 'High' and len(reasons) < 3:
        reasons.append('Multiple academic and engagement indicators combine to create a high-risk profile that requires immediate support.')

    return reasons


def build_strengths_and_weaknesses(prediction):
    strengths = []
    weaknesses = []

    if prediction['attendance'] >= 85:
        strengths.append('Strong attendance shows dependable classroom engagement.')
    if prediction['avg_marks'] >= 75:
        strengths.append('Academic scores are in a strong range and indicate solid concept understanding.')
    if prediction['study_hours'] >= 5:
        strengths.append('Study discipline is healthy and supports exam readiness.')
    if prediction['backlogs'] == 0:
        strengths.append('No active backlogs reduce academic pressure and future risk.')

    if prediction['attendance'] < 75:
        weaknesses.append('Attendance is low and may be limiting classroom learning continuity.')
    if prediction['avg_marks'] < 60:
        weaknesses.append('Marks are below the safe range and need structured improvement.')
    if prediction['study_hours'] < 3:
        weaknesses.append('Study hours are too low for stable progress.')
    if prediction['backlogs'] > 0:
        weaknesses.append('Existing backlogs are increasing academic burden.')

    if not strengths:
        strengths.append('The student still has recovery potential if guided with a structured support plan.')
    if not weaknesses:
        weaknesses.append('No major weaknesses are visible right now; the priority is maintaining consistency.')

    return strengths, weaknesses


def build_personalized_counselling_plan(prediction):
    plan = []

    if prediction['study_hours'] < 5:
        plan.append('Create a fixed daily study schedule with one core subject block, one revision block, and one short practice session.')
    if prediction['attendance'] < 85:
        plan.append('Track attendance every week and set a recovery target to attend all scheduled classes for the next 30 days.')
    if prediction['avg_marks'] < 75:
        plan.append('Review weak subjects with faculty or a mentor and complete topic-wise practice after each class.')
    if prediction['backlogs'] > 0:
        plan.append('Prepare a backlog-clearing calendar by prioritizing the most critical subjects first and assigning weekly problem-solving hours.')

    risk = prediction['risk_level']
    if risk == 'High':
        plan.append('Arrange immediate counselling, weekly academic review meetings, and a parent or mentor progress check if appropriate.')
    elif risk == 'Medium':
        plan.append('Schedule bi-weekly counselling check-ins to prevent further decline and reinforce consistency.')
    else:
        plan.append('Maintain current momentum through monthly self-review and early action if any metric drops.')

    return plan


def build_improvement_roadmap(prediction):
    roadmap = [
        'Week 1: Review the latest result, identify two weakest subjects, and create a fixed study timetable.',
        'Week 2: Improve class attendance consistency and complete one revision cycle for the weakest subject.',
        'Week 3: Solve practice problems or past questions and monitor daily study hours in a tracker.',
        'Week 4: Evaluate progress with a mentor, adjust the plan, and set next-month performance targets.'
    ]

    if prediction['backlogs'] > 0:
        roadmap.append('Backlog Strategy: Focus on clearing one backlog at a time with dedicated weekend revision and mock practice.')
    if prediction['attendance'] < 75:
        roadmap.append('Attendance Recovery: Use alarms, transport planning, and a peer accountability partner to reduce absences.')
    if prediction['study_hours'] < 3:
        roadmap.append('Study Habit Recovery: Start with 2 focused sessions daily and increase duration gradually over 2 weeks.')

    return roadmap


def build_future_risk_prediction_suggestions(prediction):
    suggestions = []

    if prediction['risk_level'] == 'High':
        suggestions.append('If the current pattern continues, the student may face compounding academic stress and deeper disengagement.')
        suggestions.append('Reducing backlogs and increasing attendance should be treated as immediate preventive actions.')
    elif prediction['risk_level'] == 'Medium':
        suggestions.append('The student is recoverable, but inconsistency could shift the profile into high risk without follow-up support.')
        suggestions.append('Regular monitoring over the next 4 to 6 weeks is recommended.')
    else:
        suggestions.append('The current performance suggests a stable trajectory if present habits are maintained.')
        suggestions.append('Preventive monitoring is still important during exams, project deadlines, or attendance drops.')

    suggestions.append('Re-run the prediction after measurable improvements in attendance, marks, or study hours to monitor trend direction.')
    return suggestions


def append_bullet_section(story, items, styles):
    for item in items:
        story.append(Paragraph(item, styles['bullet'], bulletText='-'))


def append_metric_table(story, prediction):
    metric_rows = [['Metric', 'Current Value', 'Ideal Range', 'Indicator']]
    metric_styles = [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
                     ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                     ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                     ('GRID', (0, 0), (-1, -1), 0.6, colors.HexColor('#cbd5e1')),
                     ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                     ('TOPPADDING', (0, 0), (-1, -1), 7),
                     ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]

    for row_index, metric in enumerate(build_metric_analysis(prediction), start=1):
        metric_rows.append([
            metric['label'],
            metric['value'],
            metric['ideal'],
            metric['progress']
        ])
        metric_styles.append(('BACKGROUND', (3, row_index), (3, row_index), metric['color']))
        metric_styles.append(('TEXTCOLOR', (3, row_index), (3, row_index), colors.white))
        metric_styles.append(('FONTNAME', (3, row_index), (3, row_index), 'Helvetica-Bold'))
        metric_styles.append(('ROWBACKGROUNDS', (0, row_index), (2, row_index), [colors.white, colors.HexColor('#f8fafc')]))

    metric_table = Table(metric_rows, colWidths=[1.55 * inch, 1.25 * inch, 1.95 * inch, 1.3 * inch])
    metric_table.setStyle(TableStyle(metric_styles))
    story.append(metric_table)


def append_report_header(story, styles, user_row, latest_prediction, prediction_count):
    risk_color = get_risk_color(latest_prediction['risk_level'])
    story.append(Paragraph('Academic Performance & Dropout Risk Report', styles['title']))
    story.append(Paragraph(
        f"{user_row['name']} | {user_row['email']} | Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles['subtitle']
    ))

    overview_rows = [
        ['Current Risk Level', latest_prediction['risk_level']],
        ['Prediction Date', format_prediction_timestamp(latest_prediction['prediction_date'])],
        ['Predictions Recorded', str(prediction_count)],
        ['Primary Recommendation', suggestion_for_risk(latest_prediction['risk_level'])]
    ]
    overview_table = Table(overview_rows, colWidths=[2.0 * inch, 4.5 * inch])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (1, 0), (1, 0), risk_color),
        ('TEXTCOLOR', (1, 0), (1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 0.18 * inch))


def append_student_report_sections(story, styles, user_row, prediction, predictions):
    story.append(Paragraph('Student Overview', styles['section']))
    summary = build_risk_summary(predictions)
    overview_text = (
        f"This report summarizes the student's present academic condition using attendance, average marks, study habits, and backlog data. "
        f"The current profile is classified as <b><font color='{color_to_hex(get_risk_color(prediction['risk_level']))}'>{prediction['risk_level']}</font></b> risk. "
        f"Historical records show {summary['High']} high-risk, {summary['Medium']} medium-risk, and {summary['Low']} low-risk predictions."
    )
    story.append(Paragraph(overview_text, styles['body']))

    story.append(Paragraph('Performance Analysis', styles['section']))
    story.append(Paragraph(
        'Each academic metric below is compared with an ideal range so issues can be identified quickly and action can be prioritized.',
        styles['body']
    ))
    append_metric_table(story, prediction)
    story.append(Spacer(1, 0.12 * inch))
    for metric in build_metric_analysis(prediction):
        story.append(Paragraph(
            f"<b>{metric['label']}:</b> {metric['description']} Current reading is <b>{metric['value']}</b> compared with the ideal <b>{metric['ideal']}</b>. "
            f"This area is currently rated <b><font color='{color_to_hex(metric['color'])}'>{metric['status']}</font></b>. {metric['issue']}",
            styles['body']
        ))

    story.append(Paragraph('Risk Analysis', styles['section']))
    story.append(Paragraph(
        f"The system marked this student as <b><font color='{color_to_hex(get_risk_color(prediction['risk_level']))}'>{prediction['risk_level']}</font></b> risk for the following reasons:",
        styles['body']
    ))
    append_bullet_section(story, build_risk_reasons(prediction), styles)

    strengths, weaknesses = build_strengths_and_weaknesses(prediction)
    story.append(Paragraph('Strengths & Weaknesses', styles['section']))
    story.append(Paragraph('<b>Strengths</b>', styles['body']))
    append_bullet_section(story, strengths, styles)
    story.append(Paragraph('<b>Weaknesses</b>', styles['body']))
    append_bullet_section(story, weaknesses, styles)

    story.append(Paragraph('Personalized Counselling Plan', styles['section']))
    append_bullet_section(story, build_personalized_counselling_plan(prediction), styles)

    story.append(Paragraph('Improvement Roadmap', styles['section']))
    append_bullet_section(story, build_improvement_roadmap(prediction), styles)

    story.append(Paragraph('Future Risk Prediction Suggestions', styles['section']))
    append_bullet_section(story, build_future_risk_prediction_suggestions(prediction), styles)

    story.append(Paragraph('Recent Prediction History', styles['section']))
    history_rows = [['Date', 'Risk', 'Attendance', 'Marks', 'Study Hours', 'Backlogs']]
    for item in predictions[:5]:
        history_rows.append([
            format_prediction_timestamp(item['prediction_date']),
            item['risk_level'],
            f"{item['attendance']}%",
            str(item['avg_marks']),
            str(item['study_hours']),
            str(item['backlogs'])
        ])
    history_table = Table(history_rows, colWidths=[1.45 * inch, 0.8 * inch, 1.0 * inch, 0.9 * inch, 1.0 * inch, 0.8 * inch])
    history_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.6, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.append(history_table)


def build_professional_student_report(story, user_row, predictions, include_page_break=False):
    if include_page_break:
        story.append(PageBreak())

    styles = get_report_styles()
    latest_prediction = predictions[0]
    append_report_header(story, styles, user_row, latest_prediction, len(predictions))
    append_student_report_sections(story, styles, user_row, latest_prediction, predictions)


def build_user_report_story(story, styles, user_row, predictions, include_page_break=False):
    if not predictions:
        if include_page_break:
            story.append(PageBreak())
        report_styles = get_report_styles()
        story.append(Paragraph(f"Student: {user_row['name']} ({user_row['email']})", report_styles['section']))
        story.append(Paragraph('No prediction history is available for this student yet.', report_styles['body']))
        return

    build_professional_student_report(story, user_row, predictions, include_page_break=include_page_break)


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
        db.execute(
        '''CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            attendance REAL NOT NULL,
            avg_marks REAL NOT NULL,
            study_hours REAL NOT NULL,
            backlogs INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )'''
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
            # Preserve form values for repopulation (round for display)
            form_data = {
                'attendance': str(round(float(request.form.get('attendance', 0)))),
                'avg_marks': str(round(float(request.form.get('avg_marks', 0)))),
                'study_hours': str(round(float(request.form.get('study_hours', 0)))),
                'backlogs': str(int(float(request.form.get('backlogs', 0))))
            }
            return render_template('predict.html', form_data=form_data)

        student = classify_student(attendance, avg_marks, study_hours, backlogs)
        results = [student]
        total, high, medium, low = compute_summary(results)

        # Save prediction to database
        db = get_db()
        db.execute(
            'INSERT INTO predictions (user_id, attendance, avg_marks, study_hours, backlogs, risk_level) VALUES (?, ?, ?, ?, ?, ?)',
            (current_user.id, attendance, avg_marks, study_hours, backlogs, student['risk'])
        )
        db.commit()

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

    return render_template('predict.html', form_data=None)


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



    


@app.route('/admin/users')
@admin_required
def admin_users():
    # Get all users with their prediction counts
    users = query_db('''
        SELECT u.id, u.name, u.email, u.role,
               COUNT(p.id) as prediction_count,
               MAX(p.prediction_date) as last_prediction
        FROM users u
        LEFT JOIN predictions p ON u.id = p.user_id
        GROUP BY u.id
        ORDER BY u.name
    ''')

    return render_template('admin_users.html', users=users)


@app.route('/admin/user_history/<int:user_id>')
@admin_required
def admin_user_history(user_id):
    # Get specific user's prediction history
    user = query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin_users'))

    predictions = query_db(
        'SELECT * FROM predictions WHERE user_id = ? ORDER BY prediction_date DESC',
        [user_id]
    )

    # Convert to list of dictionaries for template
    history_data = []
    for pred in predictions:
        history_data.append({
            'id': pred['id'],
            'attendance': pred['attendance'],
            'avg_marks': pred['avg_marks'],
            'study_hours': pred['study_hours'],
            'backlogs': pred['backlogs'],
            'risk_level': pred['risk_level'],
            'prediction_date': pred['prediction_date']
        })

    return render_template('admin_user_history.html',
                         user=user,
                         predictions=history_data)


@app.route('/dashboard')
@admin_required
def dashboard():
    # Get all predictions from database for admin overview
    all_predictions = query_db('SELECT * FROM predictions ORDER BY prediction_date DESC')

    # Calculate overall statistics
    total_predictions = len(all_predictions)
    high_risk = len([p for p in all_predictions if p['risk_level'] == 'High'])
    medium_risk = len([p for p in all_predictions if p['risk_level'] == 'Medium'])
    low_risk = len([p for p in all_predictions if p['risk_level'] == 'Low'])

    # Get total users count
    total_users = query_db('SELECT COUNT(*) as count FROM users', one=True)['count']

    return render_template(
        'dashboard.html',
        user=current_user,
        total=total_predictions,
        high=high_risk,
        medium=medium_risk,
        low=low_risk,
        total_users=total_users,
        recent_predictions=all_predictions[:10]  # Show last 10 predictions
    )


@app.route('/counselling')
@admin_required
def counselling():
    # Get all predictions from database for admin counseling overview
    all_predictions = query_db('SELECT * FROM predictions ORDER BY prediction_date DESC')

    # Group by risk level
    high_students = []
    medium_students = []
    low_students = []

    for pred in all_predictions:
        # Get user info for each prediction
        user = query_db('SELECT name, email FROM users WHERE id = ?', [pred['user_id']], one=True)

        # Generate suggestion based on risk level
        suggestion = suggestion_for_risk(pred['risk_level'])

        student_data = {
            'id': pred['id'],
            'user_name': user['name'] if user else 'Unknown',
            'user_email': user['email'] if user else 'Unknown',
            'attendance': pred['attendance'],
            'avg_marks': pred['avg_marks'],
            'study_hours': pred['study_hours'],
            'backlogs': pred['backlogs'],
            'risk': pred['risk_level'],
            'suggestion': suggestion,
            'prediction_date': pred['prediction_date']
        }

        if pred['risk_level'] == 'High':
            high_students.append(student_data)
        elif pred['risk_level'] == 'Medium':
            medium_students.append(student_data)
        elif pred['risk_level'] == 'Low':
            low_students.append(student_data)

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
    # Get date range from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Default: last 30 days
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    if current_user.is_admin:
        # Admin sees analytics for ALL users with date filter
        all_predictions = query_db('''
            SELECT * FROM predictions 
            WHERE DATE(prediction_date) BETWEEN ? AND ?
            ORDER BY prediction_date DESC
        ''', [start_date, end_date])
        
        analytics_data = []
        for pred in all_predictions:
            analytics_data.append({
                'attendance': pred['attendance'],
                'backlogs': pred['backlogs'],
                'study_hours': pred['study_hours'],
                'risk': pred['risk_level']
            })
        metrics = compute_analytics(analytics_data)
    else:
        # Regular users see analytics for their own predictions with date filter
        user_predictions = query_db('''
            SELECT * FROM predictions 
            WHERE user_id = ? AND DATE(prediction_date) BETWEEN ? AND ?
            ORDER BY prediction_date DESC
        ''', [current_user.id, start_date, end_date])
        
        analytics_data = []
        for pred in user_predictions:
            analytics_data.append({
                'attendance': pred['attendance'],
                'backlogs': pred['backlogs'],
                'study_hours': pred['study_hours'],
                'risk': pred['risk_level']
            })
        metrics = compute_analytics(analytics_data)

    return render_template('analytics.html', start_date=start_date, end_date=end_date, **metrics)


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


@app.route('/download_pdf_report')
@login_required
def download_pdf_report():
    """Generate and download a professional student PDF report."""
    user_predictions = query_db(
        'SELECT * FROM predictions WHERE user_id = ? ORDER BY prediction_date DESC',
        [current_user.id]
    )

    if not user_predictions:
        flash('No prediction data available. Please make a prediction first.', 'error')
        return redirect(url_for('predict'))

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch
    )
    story = []

    user_row = {
        'name': current_user.name,
        'email': current_user.email,
        'role': current_user.role
    }
    build_professional_student_report(story, user_row, user_predictions)
    doc.build(story)
    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'report_{current_user.name}_{datetime.now().strftime("%Y%m%d")}.pdf'
    )


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user and their predictions"""
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin_users'))
    
    db = get_db()
    # Delete predictions first (foreign key)
    db.execute('DELETE FROM predictions WHERE user_id = ?', [user_id])
    # Delete user
    db.execute('DELETE FROM users WHERE id = ?', [user_id])
    db.commit()
    
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/bulk_email', methods=['GET', 'POST'])
@admin_required
def bulk_email():
    """Send bulk email notifications to students"""
    if request.method == 'POST':
        recipient_type = request.form.get('recipient_type')
        subject = (request.form.get('subject') or '').strip()
        message = (request.form.get('message') or '').strip()

        if not subject or not message:
            flash('Subject and message are required.', 'error')
            return redirect(url_for('bulk_email'))

        if recipient_type == 'all':
            recipients = query_db('SELECT email, name FROM users WHERE role = "user"')
        elif recipient_type == 'high_risk':
            recipients = query_db('''
                SELECT DISTINCT u.email, u.name 
                FROM users u 
                JOIN predictions p ON u.id = p.user_id 
                WHERE p.risk_level = "High"
            ''')
        elif recipient_type == 'medium_risk':
            recipients = query_db('''
                SELECT DISTINCT u.email, u.name 
                FROM users u 
                JOIN predictions p ON u.id = p.user_id 
                WHERE p.risk_level = "Medium"
            ''')
        elif recipient_type == 'low_risk':
            recipients = query_db('''
                SELECT DISTINCT u.email, u.name 
                FROM users u 
                JOIN predictions p ON u.id = p.user_id 
                WHERE p.risk_level = "Low"
            ''')
        else:
            flash('Invalid recipient type.', 'error')
            return redirect(url_for('bulk_email'))

        if not recipients:
            flash('No student recipients matched the selected filter.', 'error')
            return redirect(url_for('bulk_email'))

        try:
            success, feedback = send_bulk_notifications(recipients, subject, message)
        except Exception as exc:
            flash(f'Bulk email delivery failed: {exc}', 'error')
            return redirect(url_for('bulk_email'))

        flash(feedback, 'success' if success else 'info')
        return redirect(url_for('bulk_email'))
    
    # GET request - display form with stats
    total_users = len(query_db('SELECT id FROM users WHERE role = "user"'))
    high_risk_users = query_db('''
        SELECT DISTINCT u.id FROM users u 
        JOIN predictions p ON u.id = p.user_id 
        WHERE p.risk_level = "High"
    ''')
    high_risk_count = len(high_risk_users) if high_risk_users else 0
    
    medium_risk_users = query_db('''
        SELECT DISTINCT u.id FROM users u 
        JOIN predictions p ON u.id = p.user_id 
        WHERE p.risk_level = "Medium"
    ''')
    medium_risk_count = len(medium_risk_users) if medium_risk_users else 0
    
    low_risk_users = query_db('''
        SELECT DISTINCT u.id FROM users u 
        JOIN predictions p ON u.id = p.user_id 
        WHERE p.risk_level = "Low"
    ''')
    low_risk_count = len(low_risk_users) if low_risk_users else 0
    
    return render_template('admin_bulk_email.html',
                         total_users=total_users,
                         high_risk_count=high_risk_count,
                         medium_risk_count=medium_risk_count,
                         low_risk_count=low_risk_count)


@app.route('/admin/download_pdf_reports')
@admin_required
def admin_download_pdf_reports():
    """Download PDF reports for all users"""
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch
    )
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#38bdf8'),
        spaceAfter=20,
        alignment=TA_CENTER
    )

    subtitle_style = ParagraphStyle(
        'InstitutionSubtitle',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=colors.HexColor('#334155'),
        alignment=TA_CENTER,
        spaceAfter=16
    )

    story.append(Paragraph('Institution Report - All Students', title_style))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        subtitle_style
    ))
    story.append(Spacer(1, 0.3*inch))

    users = query_db('SELECT id, name, email, role FROM users ORDER BY name')
    all_predictions = query_db('SELECT * FROM predictions ORDER BY user_id, prediction_date DESC')
    predictions_by_user = {}
    for prediction in all_predictions:
        predictions_by_user.setdefault(prediction['user_id'], []).append(prediction)

    summary_table = Table([
        ['Total Users', str(len(users))],
        ['Students With Predictions', str(sum(1 for user in users if predictions_by_user.get(user['id'])))],
        ['Total Predictions', str(len(all_predictions))],
        ['High Risk Records', str(sum(1 for prediction in all_predictions if prediction['risk_level'] == 'High'))],
        ['Medium Risk Records', str(sum(1 for prediction in all_predictions if prediction['risk_level'] == 'Medium'))],
        ['Low Risk Records', str(sum(1 for prediction in all_predictions if prediction['risk_level'] == 'Low'))],
    ], colWidths=[2.3 * inch, 1.6 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e2e8f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.25 * inch))

    for index, user in enumerate(users):
        build_user_report_story(
            story,
            styles,
            user,
            predictions_by_user.get(user['id'], []),
            include_page_break=index > 0
        )

    doc.build(story)
    pdf_buffer.seek(0)
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'institution_report_{datetime.now().strftime("%Y%m%d")}.pdf'
    )


if __name__ == '__main__':
    app.run(debug=True)
