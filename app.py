"""
Vision U - AI-Powered Career Counseling Platform
Enhanced version with security, performance, and reliability improvements
"""
import os
import logging
import html
import time
from datetime import datetime
from typing import Optional, Dict, Any

import markdown
import pdfkit
import google.generativeai as genai
from flask import Flask, render_template, request, redirect, session, url_for, flash, make_response, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import RequestEntityTooLarge, BadRequest
from werkzeug.middleware.proxy_fix import ProxyFix

# Local imports
from config import get_config
from models import db, User, Assessment, AIUsage
from forms import LoginForm, RegisterForm, AssessmentForm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name: Optional[str] = None) -> Flask:
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    config_class = get_config()
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # Trust proxy headers (for Render deployment)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Initialize extensions
    db.init_app(app)
    csrf = CSRFProtect(app)
    
    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL'),
        default_limits=[app.config.get('RATELIMIT_DEFAULT')]
    )
    
    # Configure AI
    api_key = app.config.get('API_KEY')
    if not api_key:
        logger.warning("API_KEY not found in environment variables")
    else:
        genai.configure(api_key=api_key)
    
    # Security headers
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self';"
        )
        return response
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f"Internal server error: {error}")
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(413)
    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(error):
        return jsonify({'error': 'File too large'}), 413
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
    
    # Database initialization
    def init_db():
        """Initialize database with proper error handling"""
        try:
            with app.app_context():
                # Test database connection
                db.engine.connect().close()
                logger.info("Database connection test successful")
                
                # Create tables
                db.create_all()
                logger.info("Database tables created successfully")
                return True
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            return False
    
    # Routes
    @app.route('/')
    def home():
        """Home page redirect"""
        return redirect(url_for('index'))
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        health_info = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'unknown',
            'ai_api': 'configured' if app.config.get('API_KEY') else 'missing'
        }
        
        try:
            db.engine.connect().close()
            health_info['database'] = 'connected'
        except Exception as e:
            health_info['database'] = f'error: {str(e)}'
            health_info['status'] = 'unhealthy'
        
        status_code = 200 if health_info['status'] == 'healthy' else 503
        return jsonify(health_info), status_code
    
    @app.route('/index')
    def index():
        """Landing page"""
        return render_template('index.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    @limiter.limit("10 per minute")
    def login():
        """Enhanced login with rate limiting and validation"""
        form = LoginForm()
        
        if form.validate_on_submit():
            try:
                if form.validate_login():
                    user = form.user
                    session['user_id'] = user.id
                    session['user'] = user.email
                    user.update_last_login()
                    
                    flash('Login successful!', 'success')
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('chat'))
                else:
                    flash('Invalid email or password.', 'error')
            except Exception as e:
                logger.error(f"Login error for {form.email.data}: {e}")
                flash('An error occurred during login. Please try again.', 'error')
        
        return render_template('login.html', form=form)
    
    @app.route('/register', methods=['GET', 'POST'])
    @limiter.limit("5 per minute")
    def register():
        """Enhanced registration with validation"""
        form = RegisterForm()
        
        if form.validate_on_submit():
            try:
                user = User(email=form.email.data)
                user.set_password(form.password.data)
                
                db.session.add(user)
                db.session.commit()
                
                session['user_id'] = user.id
                session['user'] = user.email
                user.update_last_login()
                
                flash('Registration successful! Welcome to Vision U!', 'success')
                return redirect(url_for('chat'))
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Registration error: {e}")
                flash('An error occurred during registration. Please try again.', 'error')
        
        return render_template('register.html', form=form)
    
    @app.route('/chat')
    def chat():
        """Chat interface - requires authentication"""
        if 'user' not in session:
            return redirect(url_for('login'))
        return render_template('chat.html')
    
    @app.route('/ask', methods=['POST'])
    @limiter.limit("20 per hour")
    def ask():
        """Enhanced AI processing with rate limiting and validation"""
        if 'user' not in session:
            return redirect(url_for('login'))
        
        start_time = time.time()
        user_id = session.get('user_id')
        ip_address = get_remote_address()
        
        try:
            data = request.get_json()
            if not data:
                raise BadRequest("No JSON data provided")
            
            user_info = data.get('user_info', {})
            prompt = data.get('prompt', '')
            
            # Validate and sanitize input
            form = AssessmentForm(data=user_info)
            form.prompt.data = prompt
            
            if not form.validate():
                logger.warning(f"Invalid form data from user {user_id}: {form.errors}")
                flash('Please check your input and try again.', 'error')
                return redirect(url_for('chat'))
            
            # Clean the data
            form.clean_data()
            
            # Check if API key is available
            if not app.config.get('API_KEY'):
                flash('AI service is currently unavailable. Please try again later.', 'error')
                return redirect(url_for('chat'))
            
            # Generate AI response
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            ai_prompt = f"""
You are an expert student career counselor.
Your task: Give a **personalized career guide** for the student **in short, clean, and point-wise format**.
Keep each section **short, bullet-based, and easy for students to read**.
Always respond in **Markdown format** only.

**User Info**:
- Name: {form.name.data}
- Age: {form.age.data}
- Education: {form.education.data}
- Interests: {form.interest.data}
- Hobbies: {form.hobby.data}

**Goal:** "{form.prompt.data}"

**Output Format**:
# Personalized Career Guide for {form.name.data}

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
"""
            
            response = model.generate_content(ai_prompt)
            response_time = time.time() - start_time
            
            # Save assessment to database
            assessment = Assessment(
                user_id=user_id,
                name=form.name.data,
                age=form.age.data,
                education=form.education.data,
                interest=form.interest.data,
                hobby=form.hobby.data,
                career_goal=form.prompt.data,
                ai_response=response.text,
                response_format='markdown'
            )
            
            db.session.add(assessment)
            
            # Log AI usage
            ai_usage = AIUsage(
                user_id=user_id,
                ip_address=ip_address,
                endpoint='/ask',
                response_time=response_time,
                success=True
            )
            db.session.add(ai_usage)
            db.session.commit()
            
            # Convert to HTML and redirect to results
            html_content = markdown.markdown(response.text.strip())
            return redirect(url_for('result', content=html_content))
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"AI processing error for user {user_id}: {e}")
            
            # Log failed usage
            ai_usage = AIUsage(
                user_id=user_id,
                ip_address=ip_address,
                endpoint='/ask',
                response_time=response_time,
                success=False,
                error_message=str(e)
            )
            db.session.add(ai_usage)
            db.session.commit()
            
            flash('An error occurred while processing your request. Please try again.', 'error')
            return redirect(url_for('chat'))
    
    @app.route('/result')
    def result():
        """Display assessment results"""
        if 'user' not in session:
            return redirect(url_for('login'))
        
        content = request.args.get('content')
        if not content:
            flash('No assessment results found.', 'error')
            return redirect(url_for('chat'))
        
        return render_template('result.html', content=content)
    
    @app.route('/dashboard')
    def dashboard():
        """User dashboard with assessment history"""
        if 'user' not in session:
            return redirect(url_for('login'))
        
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        # Get recent assessments
        recent_assessments = Assessment.query.filter_by(user_id=user_id)\
            .order_by(Assessment.created_at.desc())\
            .limit(5)\
            .all()
        
        return render_template('dashboard.html', 
                             user=user, 
                             assessments=recent_assessments)
    
    @app.route('/logout')
    def logout():
        """Logout user"""
        session.clear()
        flash('You have been logged out successfully.', 'info')
        return redirect(url_for('login'))
    
    @app.route('/download_pdf', methods=['POST'])
    @limiter.limit("10 per hour")
    def download_pdf():
        """Enhanced PDF download with better error handling"""
        if 'user' not in session:
            return redirect(url_for('login'))
        
        try:
            html_content = request.form.get('html_content')
            if not html_content:
                flash('No content to download.', 'error')
                return redirect(url_for('chat'))
            
            # Create full HTML with styling
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
                    h1, h2, h3 {{ color: #333; }}
                    ul {{ margin-left: 20px; }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Vision U - Career Guide</h1>
                    <p>Generated on {datetime.now().strftime('%B %d, %Y')}</p>
                </div>
                {html_content}
                <div class="footer">
                    <p>Generated by Vision U - AI-Powered Career Counseling</p>
                </div>
            </body>
            </html>
            """
            
            # PDF generation options
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'enable-local-file-access': None
            }
            
            pdf = pdfkit.from_string(full_html, False, options=options)
            
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = 'attachment; filename=vision_u_career_guide.pdf'
            
            return response
            
        except FileNotFoundError:
            logger.error("wkhtmltopdf not found")
            flash('PDF generation service is currently unavailable.', 'error')
            return redirect(request.referrer or url_for('chat'))
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            flash('An error occurred while generating the PDF.', 'error')
            return redirect(request.referrer or url_for('chat'))
    
    # Initialize database at app startup (Flask 3: before_first_request removed)
    with app.app_context():
        if not init_db():
            logger.error("Failed to initialize database")
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
