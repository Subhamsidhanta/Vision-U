"""
Forms for Vision U application with proper validation
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError, EqualTo
from werkzeug.security import check_password_hash
from models import User

class LoginForm(FlaskForm):
    """Login form with validation"""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address'),
        Length(max=120, message='Email must be less than 120 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    submit = SubmitField('Log In')
    
    def validate_login(self):
        """Validate login credentials"""
        if not self.validate():
            return False
        
        user = User.query.filter_by(email=self.email.data).first()
        if not user or not user.check_password(self.password.data):
            self.email.errors.append('Invalid email or password')
            return False
        
        self.user = user
        return True

class RegisterForm(FlaskForm):
    """Registration form with validation"""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address'),
        Length(max=120, message='Email must be less than 120 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, max=128, message='Password must be 8-128 characters'),
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')
    
    def validate_email(self, field):
        """Check if email already exists"""
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered. Please use a different email.')

class ForgotPasswordForm(FlaskForm):
    """Forgot password form"""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address'),
        Length(max=120, message='Email must be less than 120 characters')
    ])
    submit = SubmitField('Reset Password')
    
    def validate_email(self, field):
        """Check if email exists"""
        if not User.query.filter_by(email=field.data).first():
            raise ValidationError('Email not found. Please check your email address.')

class ResetPasswordForm(FlaskForm):
    """Reset password form"""
    password = PasswordField('New Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, max=128, message='Password must be 8-128 characters'),
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Update Password')

class AssessmentForm(FlaskForm):
    """Assessment form with comprehensive validation"""
    name = StringField('Name', validators=[
        DataRequired(message='Name is required'),
        Length(min=2, max=100, message='Name must be 2-100 characters')
    ])
    age = IntegerField('Age', validators=[
        DataRequired(message='Age is required'),
        NumberRange(min=13, max=100, message='Age must be between 13 and 100')
    ])
    education = StringField('Education', validators=[
        DataRequired(message='Education level is required'),
        Length(min=2, max=200, message='Education must be 2-200 characters')
    ])
    interest = StringField('Interest', validators=[
        DataRequired(message='Interest is required'),
        Length(min=2, max=500, message='Interest must be 2-500 characters')
    ])
    hobby = StringField('Hobby', validators=[
        DataRequired(message='Hobby is required'),
        Length(min=2, max=500, message='Hobby must be 2-500 characters')
    ])
    prompt = TextAreaField('Your Goal', validators=[
        DataRequired(message='Career goal is required'),
        Length(min=10, max=1000, message='Goal must be 10-1000 characters')
    ])
    
    def clean_data(self):
        """Clean and sanitize form data"""
        # Basic XSS prevention
        import html
        self.name.data = html.escape(self.name.data.strip())
        self.education.data = html.escape(self.education.data.strip())
        self.interest.data = html.escape(self.interest.data.strip())
        self.hobby.data = html.escape(self.hobby.data.strip())
        self.prompt.data = html.escape(self.prompt.data.strip())