
import markdown
import pdfkit
from flask import Flask, render_template, request, redirect, session, url_for, flash, get_flashed_messages, make_response
import google.generativeai as genai
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a-strong-secret-key-for-development-only')

# Handle PostgreSQL URL format for Render with psycopg3 (Python 3.13 compatible)
database_url = os.environ.get('DATABASE_URL', 'sqlite:///users.db')

logger.info(f"Original DATABASE_URL: {database_url[:50]}...")

# Configure for psycopg3 (modern PostgreSQL adapter)
if database_url.startswith('postgres://'):
    # Use psycopg3 driver for Python 3.13 compatibility
    database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    logger.info("Configured PostgreSQL with psycopg3 driver")
elif database_url.startswith('postgresql://') and '+psycopg' not in database_url:
    # Ensure we use psycopg3 driver
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    logger.info("Configured PostgreSQL with psycopg3 driver")
else:
    logger.info("Using SQLite database for local development")

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

# Initialize database tables with better error handling
def init_db():
    try:
        with app.app_context():
            # Test database connection first
            logger.info(f"Testing connection to: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
            connection = db.engine.connect()
            connection.close()
            logger.info("Database connection test successful!")
            
            # Create tables
            db.create_all()
            logger.info("Database tables created successfully!")
            
            # Test a simple query
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT 1")).fetchone()
            logger.info("Database query test successful!")
            return True
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        logger.error(f"Database URL being used: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        return False

# Initialize database with retry logic
db_initialized = False
try:
    db_initialized = init_db()
except Exception as e:
    print(f"Initial database setup failed: {e}")

# Function to ensure database is initialized on first request
def ensure_db_initialized():
    global db_initialized
    if not db_initialized:
        db_initialized = init_db()
    return db_initialized

@app.route('/')
def home():
    return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """Health check endpoint for debugging"""
    health_info = {}
    
    try:
        # Test database connection
        connection = db.engine.connect()
        connection.close()
        health_info['database'] = "Connected"
        health_info['db_url'] = app.config['SQLALCHEMY_DATABASE_URI'][:50] + "..."
    except Exception as e:
        health_info['database'] = f"Failed: {str(e)}"
        health_info['db_url'] = app.config['SQLALCHEMY_DATABASE_URI'][:50] + "..."
    
    # Test API key
    health_info['api_key'] = "Available" if API_KEY else "Missing"
    health_info['db_initialized'] = db_initialized
    
    # Environment info
    health_info['env_vars'] = {
        'SECRET_KEY': 'Set' if os.environ.get('SECRET_KEY') else 'Missing',
        'DATABASE_URL': 'Set' if os.environ.get('DATABASE_URL') else 'Missing',
        'API_KEY': 'Set' if os.environ.get('API_KEY') else 'Missing'
    }
    
    return health_info

@app.route('/test-db')
def test_database():
    """Test database operations"""
    try:
        # Ensure database is initialized
        if not ensure_db_initialized():
            return {"error": "Database initialization failed"}, 500
        
        # Test database operations
        with app.app_context():
            # Test connection
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT 1 as test")).fetchone()
                
            # Test table creation
            db.create_all()
            
            # Test user table exists
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            return {
                "status": "success",
                "test_query": result[0] if result else None,
                "tables": tables,
                "user_table_exists": "user" in tables
            }
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return {"error": str(e)}, 500

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            
            # Ensure database is initialized
            if not ensure_db_initialized():
                flash('Database connection error. Please try again later.', 'error')
                return render_template('login.html')
            
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                session['user'] = user.email
                return redirect(url_for('chat'))
            else:
                flash('Invalid email or password. Please try again.', 'error')
                return render_template('login.html')
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            
            # Ensure database is initialized
            if not ensure_db_initialized():
                flash('Database connection error. Please try again later.', 'error')
                return render_template('register.html')
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email already registered. Please use a different email.', 'error')
                return render_template('register.html')
            
            # Create new user
            new_user = User(email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            session['user'] = new_user.email
            flash('Registration successful! Welcome to Vision U!', 'success')
            return redirect(url_for('chat'))
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            db.session.rollback()  # Rollback in case of error
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('register.html')
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
