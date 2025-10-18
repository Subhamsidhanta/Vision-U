# Vision U - Production Deployment Guide

## 🚀 Render Deployment (Production)

### Required Environment Variables

Set these in your Render dashboard for production deployment:

```bash
# Core Flask Configuration (REQUIRED)
SECRET_KEY=your-strong-production-secret-key-32-chars-minimum
FLASK_ENV=production

# AI Service (REQUIRED) 
API_KEY=your-google-gemini-api-key-from-ai-studio

# Database (AUTO-MANAGED by Render)
DATABASE_URL=postgresql://user:pass@hostname:port/db_name

# Optional Security Settings
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=Lax

# Rate Limiting (Optional - defaults to memory)
RATELIMIT_STORAGE_URL=redis://your-redis-url:6379
```

### 🗄️ Database Support

**Render Supported Databases:**
- ✅ **PostgreSQL** (REQUIRED for production - Free tier: 1GB storage)
- ✅ **Redis** (Optional for rate limiting)

**Your App Configuration:**
- ✅ **PostgreSQL ONLY** in production (no SQLite fallback)
- ✅ Auto-converts `postgres://` to `postgresql://` format  
- ✅ Connection pooling (10 connections, auto-reconnect)
- ✅ Uses `psycopg2-binary` driver (fast, reliable)
- ✅ Fails fast if DATABASE_URL missing in production
- ✅ SQLite only for local development

### 🚀 Quick Deploy to Render

**Step 1: Create Services**
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Use these settings:
   - **Name:** vision-u (or your preferred name)
   - **Branch:** main
   - **Runtime:** Python 3
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn wsgi:app --workers 3 --threads 2 --timeout 120`

**Step 2: Add Database (REQUIRED)**
1. Click "New" → "PostgreSQL" 
2. Choose **Free** plan (1GB storage, 1M rows)
3. Name it `vision-u-db`
4. **IMPORTANT:** `DATABASE_URL` will be auto-set in your web service
5. **Note:** App will fail to start without PostgreSQL in production

**Step 3: Set Environment Variables**
In your web service settings, add:
```
SECRET_KEY=your-32-char-secret-key-here
API_KEY=your-google-gemini-api-key  
FLASK_ENV=production
```

**Step 4: Deploy**
- Click "Create Web Service"
- Render will automatically build and deploy
- First deploy takes ~5-10 minutes

### Health Checks & Monitoring

Your app exposes these endpoints:
- `/health` - Full health check (DB + AI service status)
- `/ready` - Fast readiness probe (DB connectivity)

### Production Features

✅ **Security**: HTTPS cookies, CSRF protection, security headers, rate limiting  
✅ **Performance**: WhiteNoise static serving, Gunicorn multi-worker  
✅ **Monitoring**: Structured logging, error tracking, health endpoints

---

## 🚀 Quick Deployment Steps (Legacy)

### 1. Prerequisites
- GitHub account
- Render account (https://render.com)
- Your API keys ready

### 2. Prepare Repository
1. **Push to GitHub** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit for Vision U deployment"
   git branch -M main
   git remote add origin https://github.com/yourusername/vision-u.git
   git push -u origin main
   ```

### 3. Deploy on Render

#### Option A: Update Existing Blueprint (Recommended for your case)
1. **Update Existing Blueprint**:
   - Go to https://render.com/dashboard
   - Find your existing blueprint: `Vision-U_as4`
   - Click "Sync" to pull latest changes from GitHub
   - Or delete the old blueprint and create new one

2. **Use Your Existing Database**:
   - You already have `Vision-u-db` database
   - Get the connection string from your database dashboard
   - Update environment variables with your existing database URL

#### Option B: Create New Blueprint
1. **Create New Blueprint**:
   - Go to https://render.com/dashboard
   - Click "New +" → "Blueprint" 
   - Connect your GitHub repository: `Subhamsidhanta/Vision-U`
   - This will create `vision-u-app-v2` (different name to avoid conflict)

#### Option B: Manual Service Creation
1. **Create Web Service**:
   - Go to https://render.com/dashboard
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Service Configuration**:
   ```
   Name: vision-u-app
   Environment: Python 3
   Build Command: ./build.sh
   Start Command: gunicorn app:app
   ```

3. **Environment Variables**:
   Add the same variables as Option A

### 4. Database Setup
1. **Create PostgreSQL Database**:
   - In Render dashboard: "New +" → "PostgreSQL"
   - Choose free tier
   - Note the connection details

2. **Update DATABASE_URL**:
   - Copy the External Database URL from Render
   - Add it to your web service environment variables

### 5. Post-Deployment
1. **Check Logs**: Monitor deployment in Render dashboard
2. **Test Application**: Visit your app URL
3. **Verify Database**: Test user registration/login

## 🔧 Configuration Details

### Files Ready for Deployment
- ✅ `render.yaml` - Render service configuration
- ✅ `requirements.txt` - Python dependencies
- ✅ `build.sh` - Build script with wkhtmltopdf
- ✅ `runtime.txt` - Python version specification
- ✅ `Procfile` - Process file for alternative deployment
- ✅ `app.py` - Updated with production settings
- ✅ `.gitignore` - Comprehensive ignore patterns

### Environment Variables Required
```
SECRET_KEY=your-secret-key-here
API_KEY=your-gemini-api-key-here  
DATABASE_URL=postgresql://user:pass@host:port/db
```

### Important Notes
1. **API Key**: Get your Gemini API key from Google AI Studio
2. **Secret Key**: Generate a strong secret key for sessions
3. **Database**: Render provides free PostgreSQL (limited)
4. **PDF Generation**: wkhtmltopdf is installed via build.sh
5. **Static Files**: Served automatically by Flask

## 🛠 Troubleshooting

### Common Issues
1. **Build Fails**: Check build.sh permissions
   ```bash
   chmod +x build.sh
   ```

2. **Database Connection**: Verify DATABASE_URL format
3. **API Key Issues**: Ensure Gemini API is enabled
4. **PDF Generation**: Check wkhtmltopdf installation logs

### Logs Access
- View logs in Render dashboard
- Check for missing dependencies
- Monitor API call limits

## 📱 Features Deployed
- ✅ User Authentication (Register/Login)
- ✅ AI Career Counseling with Gemini
- ✅ PDF Report Generation
- ✅ Responsive Design
- ✅ PostgreSQL Database
- ✅ Session Management

## 🔗 Next Steps After Deployment
1. Test all features thoroughly
2. Set up custom domain (if needed)
3. Configure monitoring/alerts
4. Plan for scaling if usage grows
5. Set up backup procedures for database

## 📞 Support
If you encounter issues:
1. Check Render documentation
2. Review application logs
3. Verify environment variables
4. Test API endpoints individually

Your Vision U application is now ready for production deployment on Render! 🎉