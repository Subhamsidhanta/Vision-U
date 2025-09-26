# Vision U - Environment Setup

## Local Development Setup

### 1. Create Virtual Environment
```bash
python -m venv venv
```

### 2. Activate Virtual Environment
**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Create a `.env` file with:
```
SECRET_KEY=your-development-secret-key
API_KEY=your-gemini-api-key
DATABASE_URL=sqlite:///instance/users.db
```

### 5. Run Application
```bash
python app.py
```

Application will be available at: http://localhost:5000

## Production Environment Variables (Render)
```
SECRET_KEY=strong-production-secret-key
API_KEY=your-gemini-api-key
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

## API Key Setup
1. Go to https://aistudio.google.com/
2. Create/select a project  
3. Generate API key for Gemini
4. Add to environment variables

## Database Setup
- **Development**: SQLite (automatic)
- **Production**: PostgreSQL (Render managed)