#!/bin/bash

# Cleanup script for Arbius Gallery
echo "🧹 Cleaning up repository..."

# Remove Python cache files
echo "Removing __pycache__ directories..."
find . -name "__pycache__" -type d ! -path "./arbius_env/*" -exec rm -rf {} + 2>/dev/null

# Remove .pyc files
echo "Removing .pyc files..."
find . -name "*.pyc" -type f ! -path "./arbius_env/*" -delete 2>/dev/null

# Remove .DS_Store files (macOS)
echo "Removing .DS_Store files..."
find . -name ".DS_Store" -type f -delete 2>/dev/null

# Remove log files
echo "Removing log files..."
find . -name "*.log" -type f ! -path "./arbius_env/*" -delete 2>/dev/null

# Remove temporary files
echo "Removing temporary files..."
find . -name "*~" -type f -delete 2>/dev/null
find . -name "*.swp" -type f -delete 2>/dev/null
find . -name "*.swo" -type f -delete 2>/dev/null

echo "✅ Repository cleanup complete!"
echo "📊 Current status:"
git status --short 