#!/bin/bash

# GitHub Setup Script for Arbius Gallery
echo "🐙 Setting up GitHub repository for Arbius Gallery..."

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI not found. Installing with brew..."
    if command -v brew &> /dev/null; then
        brew install gh
    else
        echo "❌ Please install GitHub CLI first: https://cli.github.com/"
        exit 1
    fi
fi

# Get GitHub username
read -p "Enter your GitHub username: " GITHUB_USERNAME

# Create GitHub repository
echo "📂 Creating GitHub repository..."
gh repo create $GITHUB_USERNAME/arbius_gallery --public --description "Beautiful gallery for AI-generated images from the Arbius network on Arbitrum" --source=. --remote=origin --push

# Set up GitHub secrets for Actions
echo "🔐 Setting up GitHub secrets..."
echo "   You'll need to add these secrets to your GitHub repository:"
echo "   Go to: https://github.com/$GITHUB_USERNAME/arbius_gallery/settings/secrets/actions"
echo ""
echo "   Add these secrets:"
echo "   - HEROKU_API_KEY: Your Heroku API key (get from: heroku auth:token)"
echo "   - HEROKU_APP_NAME: arbius"
echo ""

# Get Heroku API token
echo "🔑 Getting your Heroku API token..."
heroku auth:token

echo ""
echo "✅ GitHub repository created!"
echo "🌐 Repository URL: https://github.com/$GITHUB_USERNAME/arbius_gallery"
echo ""
echo "📋 Next steps:"
echo "   1. Copy the Heroku API token shown above"
echo "   2. Go to: https://github.com/$GITHUB_USERNAME/arbius_gallery/settings/secrets/actions"
echo "   3. Add secret: HEROKU_API_KEY = [your token]"
echo "   4. Add secret: HEROKU_APP_NAME = arbius"
echo "   5. GitHub Actions will then scan for new images every minute!"
echo ""
echo "🎉 All set! Your code is now on GitHub with automated scanning!" 