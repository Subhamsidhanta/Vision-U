# 🚀 Render Deployment Setup Guide

## Database Connection Issue Fix

If you're getting the error "DATABASE_URL environment variable is required in production", follow these steps:

### Step 1: Manual Database Connection

1. **Go to your Render Dashboard**: https://dashboard.render.com
2. **Select your web service**: `vision-u`
3. **Go to Environment tab**
4. **Click "Add Environment Variable"**
5. **Add the database connection**:
   - If you see a database connection option, connect `vision-u-db`
   - This will automatically add `DATABASE_URL`

### Step 2: Alternative - Create Database Manually

If the database doesn't exist:

1. **Create a new PostgreSQL database**:
   - Name: `vision-u-db`
   - Plan: Free
   - Database Name: `vision_u_prod`

2. **Connect to Web Service**:
   - Go to your web service settings
   - Environment tab
   - Add database connection
   - Select the created PostgreSQL database

### Step 3: Verify Environment Variables

After connecting, you should see:
- `DATABASE_URL` - PostgreSQL connection string
- `FLASK_ENV` - Should be "production"
- `PYTHON_VERSION` - Should be "3.12.0"

### Step 4: Deploy

After connecting the database:
1. **Manual Deploy**: Click "Manual Deploy" in Render dashboard
2. **Or Push Changes**: Any new commit will trigger auto-deploy

## Expected Environment Variables

Your Render environment should have:
```
DATABASE_URL=postgresql://user:password@hostname:port/database_name
FLASK_ENV=production
PYTHON_VERSION=3.12.0
```

## Troubleshooting

If deployment still fails:

1. **Check Logs**: View deployment logs in Render dashboard
2. **Verify Database**: Ensure PostgreSQL database is running
3. **Test Connection**: Database should show "Connected" status
4. **Environment Variables**: Confirm DATABASE_URL is set

## Manual Environment Variable Setup

If auto-connection doesn't work, manually add:

1. Go to Environment tab in your web service
2. Add environment variable:
   - **Key**: `DATABASE_URL`
   - **Value**: Your PostgreSQL connection string from the database info page

## Contact Support

If issues persist:
- Check Render documentation: https://render.com/docs
- Contact Render support through dashboard
- Verify your PostgreSQL database is properly created and accessible