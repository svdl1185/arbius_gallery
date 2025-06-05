#!/bin/bash

# Heroku Deployment Script for Arbius Gallery
set -e

echo "🚀 Deploying Arbius Gallery to Heroku..."

# Get app name from user
read -p "Enter your Heroku app name: " APP_NAME

# Create Heroku app
echo "📱 Creating Heroku app: $APP_NAME"
heroku create $APP_NAME

# Add PostgreSQL database (using essential-0 instead of mini)
echo "🗄️ Adding PostgreSQL database..."
heroku addons:create heroku-postgresql:essential-0 --app $APP_NAME

# Set environment variables
echo "🔐 Setting environment variables..."
heroku config:set SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())') --app $APP_NAME
heroku config:set DEBUG=False --app $APP_NAME
heroku config:set ALLOWED_HOSTS=$APP_NAME.herokuapp.com --app $APP_NAME

# Add Heroku git remote (if not already added)
heroku git:remote -a $APP_NAME

# Deploy to Heroku
echo "📦 Deploying to Heroku..."
git push heroku main

# Run migrations
echo "🔄 Running migrations..."
heroku run python3 manage.py migrate --app $APP_NAME

# Collect static files
echo "📁 Collecting static files..."
heroku run python3 manage.py collectstatic --noinput --app $APP_NAME

# Initial scan for images
echo "📊 Initial scan for images..."
heroku run python3 manage.py scan_arbius --blocks 1000 --app $APP_NAME

# Set up Heroku Scheduler for automatic scanning
echo "⏰ Setting up automatic scanning..."
heroku addons:create scheduler:standard --app $APP_NAME

echo "✅ Deployment complete!"
echo "🌐 Your gallery is live at: https://$APP_NAME.herokuapp.com"
echo ""
echo "⚠️  IMPORTANT: Set up automatic scanning:"
echo "   1. Run: heroku addons:open scheduler --app $APP_NAME"
echo "   2. Add this job to run every 10 minutes:"
echo "      python3 manage.py scan_arbius --blocks 100 --quiet"
echo ""
echo "   Note: Heroku Scheduler only supports 10-minute intervals minimum."
echo "   For 1-minute intervals, consider using GitHub Actions or another service."
echo ""
echo "🎉 Enjoy your beautiful Arbius Gallery!" 