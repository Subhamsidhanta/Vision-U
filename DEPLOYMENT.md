# Vision U - Render Deployment Guide

## 🚀 Quick Deployment Steps

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

#### Option A: Using render.yaml (Recommended)
1. **Connect GitHub Repository**:
   - Go to https://render.com/dashboard
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Select the repository containing Vision U

2. **Configure Environment Variables**:
   - Go to your service settings
   - Add these environment variables:
     ```
     SECRET_KEY=your-secret-key-here
     API_KEY=your-gemini-api-key
     DATABASE_URL=postgresql://username:password@host:port/dbname
     ```

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