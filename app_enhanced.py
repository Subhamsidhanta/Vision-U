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
import io
import base64

import markdown
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from bs4 import BeautifulSoup
    import html2text
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

import google.generativeai as genai
from flask import Flask, render_template, request, redirect, session, url_for, flash, make_response, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import RequestEntityTooLarge, BadRequest
from werkzeug.middleware.proxy_fix import ProxyFix
try:
    from whitenoise import WhiteNoise
    WHITENOISE_AVAILABLE = True
except Exception:
    WHITENOISE_AVAILABLE = False

# Local imports
from config import get_config
from models import db, User, Assessment, AIUsage
from forms import LoginForm, RegisterForm, AssessmentForm, ForgotPasswordForm, ResetPasswordForm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d]: %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name: Optional[str] = None) -> Flask:
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    # Get config class based on environment
    from config import config
    config_class = config.get(config_name, config['default'])

    # Ensure a usable DB URI is available before applying production config
    if config_name == 'production':
        database_url = os.environ.get('DATABASE_URL')
        if database_url and database_url.startswith('postgres://'):
            # Fix postgres:// to postgresql:// for SQLAlchemy
            os.environ['DATABASE_URL'] = database_url.replace('postgres://', 'postgresql://', 1)
        elif not database_url:
            # Local dev fallback when running production entrypoint without DATABASE_URL
            sqlite_path = os.path.join(os.path.dirname(__file__), 'instance', 'users.db')
            os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
            os.environ['DATABASE_URL'] = f"sqlite:///{sqlite_path}"
            logger.warning("DATABASE_URL not set; falling back to local SQLite at %s", sqlite_path)
    
    # Load configuration
    app.config.from_object(config_class)

    # Normalize SQLite relative paths to absolute to avoid CWD issues
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL')
    if db_uri and db_uri.startswith('sqlite:///') and '://' in db_uri:
        # Extract path part for sqlite relative URIs
        path = db_uri.replace('sqlite:///', '', 1)
        if not os.path.isabs(path):
            abs_path = os.path.join(app.root_path, path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{abs_path}"
            logger.info("Normalized SQLite path to absolute: %s", abs_path)

    # Now run environment-specific init
    config_class.init_app(app)

    # Enforce SECRET_KEY from environment in production
    env_secret = os.environ.get('SECRET_KEY')
    if env_secret:
        app.config['SECRET_KEY'] = env_secret

    if os.getenv('FLASK_ENV') == 'production':
        # Fail fast if secret key missing in production
        if not app.config.get('SECRET_KEY'):
            raise RuntimeError('SECRET_KEY environment variable is required in production')

    # Security: secure cookies
    app.config.setdefault('SESSION_COOKIE_SECURE', os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True')
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', os.getenv('SESSION_COOKIE_SAMESITE', 'Lax'))
    
    # Trust proxy headers (for Render deployment)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # WhiteNoise static serving (optional, improves static handling on some hosts)
    if WHITENOISE_AVAILABLE:
        app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(app.root_path, 'static'), prefix='')
    
    # Initialize extensions
    db.init_app(app)
    csrf = CSRFProtect(app)
    
    # Add custom Jinja2 filters
    @app.template_filter('markdown')
    def markdown_filter(text):
        """Convert markdown text to HTML"""
        if not text:
            return ""
        try:
            return markdown.markdown(text, extensions=['extra', 'codehilite', 'toc', 'tables'])
        except ImportError:
            # Fallback to basic markdown if extensions aren't available
            return markdown.markdown(text)
    
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
        """Initialize database with proper error handling and migration support"""
        try:
            with app.app_context():
                # Test database connection
                db.engine.connect().close()
                logger.info("Database connection test successful")
                
                # Create tables (this will handle new columns automatically)
                db.create_all()
                logger.info("Database tables created successfully")
                
                # Handle potential schema updates for existing users
                try:
                    # Check if reset_token columns exist, if not create them
                    with db.engine.begin() as conn:
                        # Try to access reset_token column
                        result = conn.execute(db.text("SELECT reset_token FROM users LIMIT 1"))
                        logger.info("Reset token columns already exist")
                except Exception as column_error:
                    # Columns don't exist, add them
                    try:
                        with db.engine.begin() as conn:
                            conn.execute(db.text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(100)"))
                            conn.execute(db.text("ALTER TABLE users ADD COLUMN reset_token_expires DATETIME"))
                        logger.info("Added reset token columns to existing users table")
                    except Exception as alter_error:
                        logger.warning(f"Could not add reset token columns: {alter_error}")
                
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
    
    @app.route('/ready')
    def readiness_probe():
        """Readiness probe for deployment health checks (lightweight)"""
        try:
            # Fast SQL check (works with SQLAlchemy 1.x and 2.x)
            with db.engine.connect() as conn:
                conn.execute(db.text('SELECT 1'))
            return jsonify({'ready': True}), 200
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return jsonify({'ready': False, 'error': str(e)}), 503
    
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
    
    @app.route('/forgot-password', methods=['GET', 'POST'])
    @limiter.limit("3 per minute")
    def forgot_password():
        """Forgot password - generate reset token"""
        form = ForgotPasswordForm()
        
        if form.validate_on_submit():
            try:
                user = User.query.filter_by(email=form.email.data).first()
                if user:
                    token = user.generate_reset_token()
                    
                    # In a real application, you would send an email here
                    # For now, we'll just provide a reset link
                    reset_url = url_for('reset_password', token=token, _external=True)
                    
                    flash(f'Password reset instructions have been sent to your email. '
                          f'Reset link: {reset_url}', 'info')
                else:
                    # Don't reveal that email doesn't exist for security
                    flash('If your email is registered, you will receive reset instructions.', 'info')
                
                return redirect(url_for('login'))
                
            except Exception as e:
                logger.error(f"Forgot password error: {e}")
                flash('An error occurred. Please try again.', 'error')
        
        return render_template('forgot_password.html', form=form)
    
    @app.route('/reset-password/<token>', methods=['GET', 'POST'])
    @limiter.limit("3 per minute")
    def reset_password(token):
        """Reset password with token"""
        user = User.find_by_reset_token(token)
        
        if not user or not user.verify_reset_token(token):
            flash('Invalid or expired reset token.', 'error')
            return redirect(url_for('forgot_password'))
        
        form = ResetPasswordForm()
        
        if form.validate_on_submit():
            try:
                user.set_password(form.password.data)
                user.clear_reset_token()
                
                flash('Your password has been updated! You can now log in.', 'success')
                return redirect(url_for('login'))
                
            except Exception as e:
                logger.error(f"Reset password error: {e}")
                flash('An error occurred. Please try again.', 'error')
        
        return render_template('reset_password.html', form=form)
    
    # Note: single logout route (avoid duplicate endpoint definition)
    
    @app.route('/chat')
    def chat():
        """Chat interface - requires authentication"""
        if 'user' not in session:
            return redirect(url_for('login'))
        
        form = AssessmentForm()
        return render_template('chat.html', form=form)
    
    @app.route('/ask', methods=['POST'])
    @limiter.limit("20 per hour")
    def ask():
        """Enhanced AI processing with rate limiting and validation"""
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        start_time = time.time()
        user_id = session.get('user_id')
        ip_address = get_remote_address()
        
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            user_info = data.get('user_info', {})
            prompt = data.get('prompt', '')
            
            # Validate required fields
            required_fields = ['name', 'age', 'education', 'interest', 'hobby']
            for field in required_fields:
                if not user_info.get(field):
                    return jsonify({'error': f'{field.title()} is required'}), 400
            
            if not prompt:
                return jsonify({'error': 'Career goal is required'}), 400
            
            # Check if API key is available
            if not app.config.get('API_KEY'):
                return jsonify({'error': 'AI service is currently unavailable'}), 503
            
            # Generate AI response
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            ai_prompt = f"""
You are an expert student career counselor.
Your task: Give a **personalized career guide** for the student **in short, clean, and point-wise format**.
Keep each section **short, bullet-based, and easy for students to read**.
Always respond in **Markdown format** only.

**User Info**:
- Name: {user_info['name']}
- Age: {user_info['age']}
- Education: {user_info['education']}
- Interests: {user_info['interest']}
- Hobbies: {user_info['hobby']}

**Goal:** "{prompt}"

**Output Format**:
# Personalized Career Guide for {user_info['name']}

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
            
            if not response.text:
                return jsonify({'error': 'AI service returned empty response'}), 503
            
            # Save assessment to database
            assessment = Assessment(
                user_id=user_id,
                name=user_info['name'],
                age=int(user_info['age']),
                education=user_info['education'],
                interest=user_info['interest'],
                hobby=user_info['hobby'],
                career_goal=prompt,
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
            
            # Return success response
            return jsonify({
                'success': True,
                'assessment_id': assessment.id,
                'redirect_url': url_for('view_assessment', assessment_id=assessment.id)
            })
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"AI processing error for user {user_id}: {e}")
            
            # Log failed usage
            try:
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
            except:
                pass  # Don't fail if logging fails
            
            return jsonify({'error': 'Sorry, there was an error processing your request. Please try again.'}), 500
    
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
    
    @app.route('/assessment/<int:assessment_id>')
    def view_assessment(assessment_id):
        """View a specific assessment"""
        if 'user' not in session:
            return redirect(url_for('login'))
        
        user_id = session.get('user_id')
        assessment = Assessment.query.filter_by(id=assessment_id, user_id=user_id).first()
        
        if not assessment:
            flash('Assessment not found.', 'error')
            return redirect(url_for('dashboard'))
        
        # Convert markdown to HTML with safe extensions
        try:
            html_content = markdown.markdown(
                assessment.ai_response.strip(), 
                extensions=['extra', 'codehilite', 'toc', 'tables']
            )
        except ImportError:
            # Fallback to basic markdown if extensions aren't available
            html_content = markdown.markdown(assessment.ai_response.strip())
        
        return render_template('result.html', content=html_content)
    
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
        """Enhanced PDF download with multiple fallback methods"""
        if 'user' not in session:
            return redirect(url_for('login'))
        
        try:
            html_content = request.form.get('html_content')
            if not html_content:
                flash('No content to download.', 'error')
                return redirect(url_for('chat'))
            
            # Try different PDF generation methods
            pdf_data = None
            
            # Method 1: Try wkhtmltopdf if available
            if PDFKIT_AVAILABLE:
                try:
                    pdf_data = generate_pdf_with_pdfkit(html_content)
                    logger.info("PDF generated using pdfkit/wkhtmltopdf")
                except Exception as e:
                    logger.warning(f"pdfkit failed: {e}")
            
            # Method 2: Try ReportLab if pdfkit failed
            if not pdf_data and REPORTLAB_AVAILABLE:
                try:
                    pdf_data = generate_pdf_with_reportlab(html_content)
                    logger.info("PDF generated using ReportLab")
                except Exception as e:
                    logger.warning(f"ReportLab failed: {e}")
            
            # Method 3: Fallback to text download
            if not pdf_data:
                return generate_text_download(html_content)
            
            # Create response
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = 'attachment; filename=vision_u_career_guide.pdf'
            
            return response
            
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            flash('An error occurred while generating the PDF. Trying alternative download...', 'error')
            return generate_text_download(html_content)
    
    def generate_pdf_with_pdfkit(html_content):
        """Generate PDF using pdfkit/wkhtmltopdf with beautiful styling"""
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
                
                body {{ 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                    line-height: 1.7; 
                    margin: 0; 
                    padding: 20px; 
                    color: #1f2937; 
                    background: #ffffff;
                }}
                
                .container {{ max-width: 100%; margin: 0 auto; }}
                
                .header {{ 
                    text-align: center; 
                    margin-bottom: 40px; 
                    padding: 25px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                
                .header h1 {{ 
                    font-size: 2.2em; 
                    font-weight: 700; 
                    margin: 0 0 10px 0; 
                    text-shadow: 0 2px 4px rgba(0,0,0,0.3);
                }}
                
                .header .subtitle {{ 
                    font-size: 1.1em; 
                    font-weight: 300; 
                    opacity: 0.9;
                    margin-bottom: 15px;
                }}
                
                .header .date {{ 
                    font-size: 0.9em; 
                    opacity: 0.8;
                }}
                
                h1 {{ 
                    color: #1e40af; 
                    font-size: 1.8em; 
                    font-weight: 600; 
                    margin: 30px 0 15px 0; 
                    padding-bottom: 8px;
                    border-bottom: 3px solid #3b82f6;
                    position: relative;
                }}
                
                h2 {{ 
                    color: #1e293b; 
                    font-size: 1.4em; 
                    font-weight: 500; 
                    margin: 25px 0 12px 0; 
                    padding: 12px 16px; 
                    background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%); 
                    border-left: 4px solid #3b82f6;
                    border-radius: 0 8px 8px 0;
                }}
                
                h3 {{ 
                    color: #059669; 
                    font-size: 1.2em; 
                    font-weight: 500; 
                    margin: 20px 0 10px 0;
                }}
                
                p {{ 
                    margin: 0 0 12px 0; 
                    text-align: justify;
                    line-height: 1.6;
                }}
                
                ul, ol {{ 
                    margin: 15px 0; 
                    padding-left: 25px; 
                }}
                
                li {{ 
                    margin-bottom: 8px; 
                    line-height: 1.5;
                }}
                
                strong, b {{ 
                    color: #1f2937; 
                    font-weight: 600; 
                }}
                
                em, i {{ 
                    font-style: italic; 
                    color: #4b5563; 
                }}
                
                .highlight {{ 
                    background: linear-gradient(120deg, #fef3c7 0%, #fde68a 100%); 
                    padding: 12px 16px; 
                    border-radius: 8px; 
                    border-left: 4px solid #f59e0b;
                    margin: 15px 0;
                    box-shadow: 0 2px 8px rgba(245, 158, 11, 0.1);
                }}
                
                .footer {{ 
                    text-align: center; 
                    margin-top: 50px; 
                    padding: 25px; 
                    background: #f8fafc; 
                    border-radius: 12px;
                    border-top: 3px solid #3b82f6;
                }}
                
                .footer p {{ 
                    margin: 5px 0; 
                    color: #64748b; 
                }}
                
                .footer .brand {{ 
                    font-weight: 600; 
                    color: #1e40af; 
                    font-size: 1.1em;
                }}
                
                .section-divider {{ 
                    height: 2px; 
                    background: linear-gradient(90deg, transparent 0%, #3b82f6 50%, transparent 100%); 
                    margin: 25px 0; 
                    border: none;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 Vision U</h1>
                    <div class="subtitle">AI-Powered Career Guidance Report</div>
                    <div class="date">📅 Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
                </div>
                
                <hr class="section-divider">
                
                {html_content}
                
                <div class="footer">
                    <p class="brand">🚀 Vision U - AI-Powered Career Counseling Platform</p>
                    <p>Empowering your career journey with intelligent guidance</p>
                    <p>📧 support@vision-u.com | 🌐 www.vision-u.com</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'enable-local-file-access': None,
            'no-outline': None
        }
        
        return pdfkit.from_string(full_html, False, options=options)
    
    def format_paragraph_text(element, text):
        """Helper function to format paragraph text with inline styling"""
        formatted_text = text
        
        # Handle bold elements
        for strong in element.find_all(['strong', 'b']):
            bold_text = strong.get_text()
            formatted_text = formatted_text.replace(bold_text, f'<b>{bold_text}</b>')
        
        # Handle italic elements  
        for em in element.find_all(['em', 'i']):
            italic_text = em.get_text()
            formatted_text = formatted_text.replace(italic_text, f'<i>{italic_text}</i>')
        
        return formatted_text

    def generate_pdf_with_reportlab(html_content):
        """Generate PDF using ReportLab with proper HTML parsing"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        # Get styles and create custom ones
        styles = getSampleStyleSheet()
        
        # Beautiful custom styles for different elements
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1e40af'),
            alignment=1,  # Center
            spaceAfter=30,
            spaceBefore=20,
            borderWidth=2,
            borderColor=colors.HexColor('#3b82f6'),
            borderPadding=12,
            backColor=colors.HexColor('#eff6ff')
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            fontName='Helvetica',
            textColor=colors.HexColor('#64748b'),
            alignment=1,  # Center
            spaceAfter=25,
            spaceBefore=5
        )
        
        h1_style = ParagraphStyle(
            'CustomH1',
            parent=styles['Heading1'],
            fontSize=18,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=16,
            spaceBefore=20,
            borderWidth=0,
            borderColor=colors.HexColor('#3b82f6'),
            borderPadding=0,
            borderRadius=0,
            leftIndent=0,
            rightIndent=0,
            leading=22
        )
        
        h2_style = ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontSize=15,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=12,
            spaceBefore=18,
            leftIndent=12,
            borderWidth=1,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=8,
            backColor=colors.HexColor('#f8fafc'),
            leading=18
        )
        
        h3_style = ParagraphStyle(
            'CustomH3',
            parent=styles['Heading3'],
            fontSize=13,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#059669'),
            spaceAfter=10,
            spaceBefore=14,
            leftIndent=6,
            leading=16
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            fontName='Helvetica',
            spaceAfter=10,
            spaceBefore=2,
            textColor=colors.HexColor('#374151'),
            leading=16,
            alignment=0,  # Left align
            leftIndent=0,
            rightIndent=0
        )
        
        bullet_style = ParagraphStyle(
            'CustomBullet',
            parent=styles['Normal'],
            fontSize=11,
            fontName='Helvetica',
            spaceAfter=6,
            spaceBefore=2,
            leftIndent=24,
            bulletIndent=12,
            textColor=colors.HexColor('#374151'),
            leading=15,
            bulletFontName='Symbol',
            bulletColor=colors.HexColor('#3b82f6')
        )
        
        highlight_style = ParagraphStyle(
            'CustomHighlight',
            parent=styles['Normal'],
            fontSize=11,
            fontName='Helvetica',
            spaceAfter=12,
            spaceBefore=8,
            textColor=colors.HexColor('#1f2937'),
            leading=16,
            leftIndent=16,
            rightIndent=16,
            borderWidth=1,
            borderColor=colors.HexColor('#fbbf24'),
            borderPadding=10,
            backColor=colors.HexColor('#fffbeb')
        )
        
        story = []
        
        # Add beautiful header with branding
        story.append(Paragraph("🎯 Vision U", title_style))
        story.append(Paragraph("AI-Powered Career Guidance Report", subtitle_style))
        story.append(Spacer(1, 15))
        
        # Add generation info in a nice format
        date_info = f"📅 Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        story.append(Paragraph(date_info, subtitle_style))
        story.append(Spacer(1, 25))
        
        # Add a separator line effect
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 20))
        
        try:
            # Parse HTML content using BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Process each element with enhanced formatting
            processed_elements = set()  # Track processed elements to avoid duplicates
            
            for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'strong', 'em']):
                if id(element) in processed_elements:
                    continue
                    
                if element.name == 'h1':
                    text = element.get_text().strip()
                    if text:
                        # Add section divider before h1
                        story.append(Spacer(1, 15))
                        story.append(HRFlowable(width="60%", thickness=2, color=colors.HexColor('#3b82f6')))
                        story.append(Spacer(1, 10))
                        story.append(Paragraph(f"📊 {text}", h1_style))
                        story.append(Spacer(1, 12))
                        processed_elements.add(id(element))
                        
                elif element.name == 'h2':
                    text = element.get_text().strip()
                    if text:
                        story.append(Spacer(1, 8))
                        story.append(Paragraph(f"🔹 {text}", h2_style))
                        story.append(Spacer(1, 8))
                        processed_elements.add(id(element))
                        
                elif element.name == 'h3':
                    text = element.get_text().strip()
                    if text:
                        story.append(Paragraph(f"▶ {text}", h3_style))
                        story.append(Spacer(1, 6))
                        processed_elements.add(id(element))
                        
                elif element.name == 'p':
                    text = element.get_text().strip()
                    if text and not element.find_parent(['ul', 'ol']):  # Avoid duplicate processing
                        # Enhanced formatting preservation
                        formatted_text = format_paragraph_text(element, text)
                        
                        # Check if it's a highlight/important paragraph
                        if any(word in text.lower() for word in ['important', 'note:', 'remember', 'key']):
                            story.append(Paragraph(f"💡 {formatted_text}", highlight_style))
                        else:
                            story.append(Paragraph(formatted_text, normal_style))
                        story.append(Spacer(1, 4))
                        processed_elements.add(id(element))
                        
                elif element.name in ['ul', 'ol']:
                    if id(element) not in processed_elements:
                        story.append(Spacer(1, 6))
                        list_items = element.find_all('li', recursive=False)  # Only direct children
                        for i, li in enumerate(list_items):
                            text = li.get_text().strip()
                            if text:
                                # Different bullets for nested lists
                                if element.name == 'ol':
                                    bullet = f"{i+1}."
                                else:
                                    bullet = "●"
                                story.append(Paragraph(f"{bullet} {text}", bullet_style))
                        story.append(Spacer(1, 10))
                        processed_elements.add(id(element))
                    
        except Exception as e:
            logger.warning(f"HTML parsing failed, using simple text conversion: {e}")
            
            # Fallback to simple text conversion
            import re
            text_content = re.sub('<[^<]+?>', '', html_content)
            text_content = text_content.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
            
            paragraphs = text_content.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if para:
                    # Simple formatting detection
                    if para.startswith('# '):
                        story.append(Paragraph(para[2:], h1_style))
                    elif para.startswith('## '):
                        story.append(Paragraph(para[3:], h2_style))
                    elif para.startswith('### '):
                        story.append(Paragraph(para[4:], h3_style))
                    elif para.startswith('- ') or para.startswith('* '):
                        lines = para.split('\n')
                        for line in lines:
                            if line.strip().startswith(('- ', '* ')):
                                story.append(Paragraph(f"• {line.strip()[2:]}", bullet_style))
                    else:
                        story.append(Paragraph(para, normal_style))
                    story.append(Spacer(1, 8))
        
        # Add beautiful footer
        story.append(Spacer(1, 30))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 15))
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#64748b'),
            alignment=1,
            leading=12
        )
        
        story.append(Paragraph("🚀 <b>Vision U</b> - AI-Powered Career Counseling Platform", footer_style))
        story.append(Spacer(1, 5))
        story.append(Paragraph("Empowering your career journey with intelligent guidance", footer_style))
        story.append(Spacer(1, 5))
        story.append(Paragraph("📧 support@vision-u.com | 🌐 www.vision-u.com", footer_style))
        
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data
    
    def generate_text_download(html_content):
        """Fallback: Generate plain text download"""
        import re
        
        # Convert HTML to plain text
        text_content = re.sub('<[^<]+?>', '', html_content)
        text_content = text_content.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
        
        # Add header
        full_text = f"""
VISION U - CAREER GUIDE
Generated on {datetime.now().strftime('%B %d, %Y')}
{"="*50}

{text_content}

{"="*50}
Generated by Vision U - AI-Powered Career Counseling Platform
Visit us for more personalized career guidance!
"""
        
        response = make_response(full_text)
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=vision_u_career_guide.txt'
        
        flash('PDF generation unavailable. Downloaded as text file instead.', 'info')
        return response
    
    # Initialize database
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