#!/usr/bin/env python
"""
Script to check production database statistics for the top users leaderboard.
Run this on Heroku with: heroku run python check_production_stats.py --app arbius
"""

import os
import sys
import django

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.models import ArbiusImage, ImageUpvote, UserProfile
from django.db.models import Count, Q

def get_base_queryset():
    """Get the base queryset for images with filtering"""
    ALLOWED_MODELS = [
        '0xa473c70e9d7c872ac948d20546bc79db55fa64ca325a4b229aaffddb7f86aae0',
    ]
    
    return ArbiusImage.objects.select_related().prefetch_related('upvotes', 'comments').filter(
        is_accessible=True,
        model_id__in=ALLOWED_MODELS
    ).exclude(
        Q(prompt__icontains='hitler') |
        Q(prompt__icontains='nazi') |
        Q(prompt__icontains='violence') |
        Q(prompt__icontains='explicit') |
        Q(prompt__icontains='nsfw') |
        Q(prompt__iregex=r'\b(porn|sex|nude|naked)\b')
    )

def main():
    print("=== ARBIUS GALLERY PRODUCTION STATISTICS ===")
    print()
    
    # Basic stats
    total_images = get_base_queryset().count()
    total_users = get_base_queryset().filter(
        task_submitter__isnull=False
    ).values('task_submitter').distinct().count()
    total_upvotes = ImageUpvote.objects.count()
    total_profiles = UserProfile.objects.count()
    
    print(f"📊 Overview:")
    print(f"   Total filtered images: {total_images:,}")
    print(f"   Total unique creators: {total_users:,}")
    print(f"   Total upvotes given: {total_upvotes:,}")
    print(f"   User profiles created: {total_profiles:,}")
    print()
    
    # Top creators by images
    print("🏆 Top 10 Creators by Images:")
    top_by_images = get_base_queryset().filter(
        task_submitter__isnull=False
    ).values('task_submitter').annotate(
        image_count=Count('id')
    ).order_by('-image_count')[:10]
    
    for i, creator in enumerate(top_by_images, 1):
        wallet = creator['task_submitter']
        count = creator['image_count']
        # Get upvotes for this user
        upvotes = ImageUpvote.objects.filter(
            image__task_submitter__iexact=wallet
        ).count()
        print(f"   {i:2d}. {wallet[:10]}... - {count:3d} images, {upvotes:3d} upvotes")
    print()
    
    # Top creators by upvotes
    print("❤️  Top 10 Creators by Upvotes:")
    top_by_upvotes = get_base_queryset().filter(
        task_submitter__isnull=False
    ).values('task_submitter').annotate(
        image_count=Count('id'),
        total_upvotes=Count('upvotes', distinct=True)
    ).order_by('-total_upvotes', '-image_count')[:10]
    
    for i, creator in enumerate(top_by_upvotes, 1):
        wallet = creator['task_submitter']
        images = creator['image_count']
        upvotes = creator['total_upvotes']
        print(f"   {i:2d}. {wallet[:10]}... - {upvotes:3d} upvotes, {images:3d} images")
    print()
    
    # Distribution analysis
    print("📈 Creator Distribution:")
    creator_counts = get_base_queryset().filter(
        task_submitter__isnull=False
    ).values('task_submitter').annotate(
        image_count=Count('id')
    ).values_list('image_count', flat=True)
    
    creators_1_image = sum(1 for x in creator_counts if x == 1)
    creators_2_5 = sum(1 for x in creator_counts if 2 <= x <= 5)
    creators_6_10 = sum(1 for x in creator_counts if 6 <= x <= 10)
    creators_11_plus = sum(1 for x in creator_counts if x > 10)
    
    print(f"   📷 1 image: {creators_1_image} creators")
    print(f"   📷 2-5 images: {creators_2_5} creators")
    print(f"   📷 6-10 images: {creators_6_10} creators")
    print(f"   📷 11+ images: {creators_11_plus} creators")
    print()
    
    # Check if we have enough for top 50
    if total_users >= 50:
        print("✅ Sufficient users for Top 50 leaderboard")
    else:
        print(f"⚠️  Only {total_users} creators available (less than 50)")
    
    print()
    print("Run this command on Heroku:")
    print("heroku run python check_production_stats.py --app arbius")

if __name__ == "__main__":
    main() 