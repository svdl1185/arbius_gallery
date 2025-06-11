#!/bin/bash

echo "🚀 Starting comprehensive catch-up scan for missed images"
echo "📅 Scanning ~5 days of missed blocks (June 6-11, 2025)"

# Run multiple scans to catch all missed images
# Each scan covers a different range to ensure complete coverage

echo "📊 Running scan 1/4 - 600k blocks..."
heroku run --app arbius "python manage.py scan_arbius --blocks 600000 --quiet"

echo "📊 Running scan 2/4 - another 500k blocks..."  
heroku run --app arbius "python manage.py scan_arbius --blocks 500000 --quiet"

echo "📊 Running scan 3/4 - another 400k blocks..."
heroku run --app arbius "python manage.py scan_arbius --blocks 400000 --quiet"

echo "📊 Running scan 4/4 - final 300k blocks..."
heroku run --app arbius "python manage.py scan_arbius --blocks 300000 --quiet"

echo "✅ Catch-up scanning complete!"

# Check final status
echo "📈 Final database status:"
heroku run --app arbius "python manage.py shell -c \"from gallery.models import ArbiusImage; print(f'Total images: {ArbiusImage.objects.count()}'); latest = ArbiusImage.objects.order_by('-discovered_at').first(); earliest = ArbiusImage.objects.order_by('discovered_at').first(); print(f'Date range: {earliest.discovered_at.date()} to {latest.discovered_at.date()}' if latest and earliest else 'No images')\""

# Check for the specific missing image
echo "🔍 Checking for specific missing image..."
heroku run --app arbius "python manage.py shell -c \"from gallery.models import ArbiusImage; img = ArbiusImage.objects.filter(cid='QmeaYYSgpQuZPLgnC44NTQ2xNFD5iw7sRESxG8XPk8WFL6').first(); print(f'QmeaYYSgpQuZPLgnC44NTQ2xNFD5iw7sRESxG8XPk8WFL6 found: {img is not None}')\"" 

echo "🎉 Catch-up process completed!" 