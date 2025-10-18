"""
Database models for Vision U application
"""
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from typing import Optional
import secrets

db = SQLAlchemy()

class User(db.Model):
    """User model with enhanced features"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Password reset functionality
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expires = db.Column(db.DateTime)
    
    # Relationships
    assessments = db.relationship('Assessment', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password: str) -> None:
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self) -> str:
        """Generate password reset token"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
        db.session.commit()
        return self.reset_token
    
    def verify_reset_token(self, token: str) -> bool:
        """Verify reset token is valid and not expired"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        
        if datetime.utcnow() > self.reset_token_expires:
            self.clear_reset_token()
            return False
        
        return self.reset_token == token
    
    def clear_reset_token(self) -> None:
        """Clear reset token after use or expiration"""
        self.reset_token = None
        self.reset_token_expires = None
        db.session.commit()
    
    def update_last_login(self) -> None:
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def find_by_reset_token(token: str) -> Optional['User']:
        """Find user by reset token"""
        return User.query.filter_by(reset_token=token).first()
    
    def to_dict(self) -> dict:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }
    
    def __repr__(self) -> str:
        return f'<User {self.email}>'

class Assessment(db.Model):
    """Assessment model to store user career assessments"""
    __tablename__ = 'assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Assessment data
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    education = db.Column(db.String(200), nullable=False)
    interest = db.Column(db.Text, nullable=False)
    hobby = db.Column(db.Text, nullable=False)
    career_goal = db.Column(db.Text, nullable=False)
    
    # AI Response
    ai_response = db.Column(db.Text)
    response_format = db.Column(db.String(20), default='markdown')
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert assessment to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'age': self.age,
            'education': self.education,
            'interest': self.interest,
            'hobby': self.hobby,
            'career_goal': self.career_goal,
            'ai_response': self.ai_response,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self) -> str:
        return f'<Assessment {self.id} for User {self.user_id}>'

class AIUsage(db.Model):
    """Track AI API usage for monitoring and rate limiting"""
    __tablename__ = 'ai_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    endpoint = db.Column(db.String(100))
    tokens_used = db.Column(db.Integer, default=0)
    response_time = db.Column(db.Float)  # in seconds
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self) -> str:
        return f'<AIUsage {self.id} - User {self.user_id}>'