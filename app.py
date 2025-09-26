
import markdown
import pdfkit
from flask import Flask, render_template, request, redirect, session, url_for, flash, get_flashed_messages, make_response
import google.generativeai as genai
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a-strong-secret-key-for-development-only')

# Handle PostgreSQL URL format for Render
database_url = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
if database_url.startswith('postgres://'):
    # Use pg8000 driver instead of psycopg2 for better Python 3.13 compatibility
    database_url = database_url.replace('postgres://', 'postgresql+pg8000://', 1)
elif database_url.startswith('postgresql://') and 'pg8000' not in database_url:
    # Ensure we use pg8000 driver
    database_url = database_url.replace('postgresql://', 'postgresql+pg8000://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

API_KEY = os.getenv("API_KEY") # It is recommended to use environment variables for API keys
genai.configure(api_key=API_KEY)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Initialize database tables
try:
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")
except Exception as e:
    print(f"Database initialization error: {e}")
    # Continue running the app even if database setup fails initially

@app.route('/')
def home():
    return redirect(url_for('index'))

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user'] = user.email
            return redirect(url_for('chat'))
        else:
            flash('Login failed. Try again.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            return 'Email already registered.'
        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        session['user'] = new_user.email
        return redirect(url_for('chat'))
    return render_template('register.html')

@app.route('/chat')
def chat():
    if 'user' in session:
        return render_template('chat.html')
    return redirect(url_for('login'))

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    user_info = data['user_info']
    prompt = data['prompt']

    model = genai.GenerativeModel('gemini-2.5-flash')

    # Send a stricter, shorter prompt to Gemini
    response = model.generate_content(f"""
You are an expert student career counselor.
Your task: Give a **personalized career guide** for the student **in short, clean, and point-wise format**.
Keep each section **short, bullet-based, and easy for students to read**.
Always respond in **Markdown format** only.

**User Info**:
- Name: {user_info.get('name', 'N/A')}
- Education: {user_info.get('education', 'N/A')}
- Interests: {user_info.get('interest', 'N/A')}
- Hobbies: {user_info.get('hobby', 'N/A')}

**Goal:** "{prompt}"

**Output Format**:
# Personalized Career Guide for {user_info.get('name', 'Student')}

## 1. Career Path Name
- **Why Fit:** 1 short line
- **Description:** 1–2 lines max
- **Skills to Learn:** • HTML • Python • SQL
- **Action Steps:** 
    - Take X course
    - Build Y project
    - Earn Z certificate
- **Industry Demand:** 1 short line

## 2. Career Path Name
(same format)

## 3. Career Path Name
(same format)

**Rules:**
- Use bullet points ✅
- Avoid long paragraphs ❌
- Make it simple, clean & beginner-friendly ✅
""")

    # Post-process response to remove unwanted spaces & keep it clean
    formatted_text = response.text.strip()
    html_content = markdown.markdown(formatted_text)
    return redirect(url_for('result', content=html_content))


@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('dashboard.html', user=session['user'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/result')
def result():
    content = request.args.get('content')
    return render_template('result.html', content=content)

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    try:
        config = pdfkit.configuration()
        html_content = request.form['html_content']
        
        # Add the CSS styles to the HTML content
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="{url_for('static', filename='result.css', _external=True)}">
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        pdf = pdfkit.from_string(full_html, False, configuration=config, options={"enable-local-file-access": ""})
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=career_guide.pdf'
        
        return response
    except FileNotFoundError:
        flash('wkhtmltopdf not found. Please install it and make sure it is in your PATH.', 'error')
        return render_template('result.html', content=request.form['html_content'])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
