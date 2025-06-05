#!/bin/bash

# Arbius Gallery - Heroku Deployment Script
echo "🚀 Deploying Arbius Gallery to Heroku..."

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI is not installed. Please install it first:"
    echo "   https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Get app name from user
read -p "Enter your Heroku app name: " APP_NAME

if [ -z "$APP_NAME" ]; then
    echo "❌ App name is required"
    exit 1
fi

echo "📱 Creating Heroku app: $APP_NAME"
heroku create $APP_NAME

echo "🗄️ Adding PostgreSQL database..."
heroku addons:create heroku-postgresql:mini --app $APP_NAME

echo "🔐 Setting environment variables..."
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
heroku config:set SECRET_KEY="$SECRET_KEY" --app $APP_NAME
heroku config:set DEBUG=False --app $APP_NAME
heroku config:set ALLOWED_HOSTS="$APP_NAME.herokuapp.com" --app $APP_NAME

echo "📦 Deploying to Heroku..."
git push heroku main

echo "🔄 Running migrations..."
heroku run python manage.py migrate --app $APP_NAME

echo "📊 Initial scan for images..."
heroku run python manage.py scan_arbius --blocks 1000 --app $APP_NAME

echo "⏰ Setting up automatic scanning..."
heroku addons:create scheduler:standard --app $APP_NAME

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your gallery is live at: https://$APP_NAME.herokuapp.com"
echo ""
echo "⚠️  IMPORTANT: Set up automatic scanning:"
echo "   1. Run: heroku addons:open scheduler --app $APP_NAME"
echo "   2. Add this job to run every minute:"
echo "      python manage.py scan_arbius --blocks 100 --quiet"
echo ""
echo "🎉 Enjoy your beautiful Arbius Gallery!" 