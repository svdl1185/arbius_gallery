from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import ArbiusImage, ScanStatus


def index(request):
    """Gallery index view with automatic pagination"""
    # Get all images ordered by accessibility first, then by timestamp
    # Filter out invalid entries (those with prompts starting with <|begin_of_text|>)
    images = ArbiusImage.objects.exclude(
        prompt__startswith="<|begin_of_text|>"
    ).order_by('-is_accessible', '-timestamp')
    
    # Calculate stats for display
    total_images = images.count()
    
    # Count unique wallets that have generated images (using solution_provider since it's more accurate)
    unique_wallets = images.values('solution_provider').distinct().count()
    
    # Count new images in the last 24 hours
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    new_images_24h = images.filter(timestamp__gte=twenty_four_hours_ago).count()
    
    # Pagination
    paginator = Paginator(images, 12)  # Show 12 images per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'images': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'total_images': total_images,
        'unique_wallets': unique_wallets,
        'new_images_24h': new_images_24h,
    }
    
    return render(request, 'gallery/index.html', context)


def image_detail(request, image_id):
    """Individual image detail view"""
    image = get_object_or_404(ArbiusImage, id=image_id)
    
    # Get related images for suggestions, filtering out invalid entries
    related_images = ArbiusImage.objects.filter(
        is_accessible=True
    ).exclude(
        prompt__startswith="<|begin_of_text|>"
    ).exclude(id=image.id).order_by('-timestamp')[:6]
    
    context = {
        'image': image,
        'related_images': related_images,
    }
    
    return render(request, 'gallery/image_detail.html', context)


def info(request):
    """Information page about the Arbius gallery and process"""
    # Filter out invalid entries for consistent stats
    valid_images = ArbiusImage.objects.exclude(prompt__startswith="<|begin_of_text|>")
    
    # Calculate comprehensive stats
    total_images = valid_images.count()
    accessible_images = valid_images.filter(is_accessible=True).count()
    
    # Calculate new statistics
    unique_models = valid_images.exclude(model_id__isnull=True).exclude(model_id__exact='').values('model_id').distinct().count()
    unique_users = valid_images.values('owner_address').distinct().count()
    unique_miners = valid_images.values('solution_provider').distinct().count()
    
    # Most popular model overall
    from django.db.models import Count
    most_popular_model = valid_images.exclude(model_id__isnull=True).exclude(model_id__exact='').values('model_id').annotate(count=Count('model_id')).order_by('-count').first()
    most_popular_model_id = most_popular_model['model_id'] if most_popular_model else None
    most_popular_model_short = f"{most_popular_model_id[:8]}...{most_popular_model_id[-8:]}" if most_popular_model_id and len(most_popular_model_id) > 16 else (most_popular_model_id or "N/A")
    
    # Most popular model this week
    one_week_ago = timezone.now() - timedelta(weeks=1)
    most_popular_model_week = valid_images.filter(timestamp__gte=one_week_ago).exclude(model_id__isnull=True).exclude(model_id__exact='').values('model_id').annotate(count=Count('model_id')).order_by('-count').first()
    most_popular_model_week_id = most_popular_model_week['model_id'] if most_popular_model_week else None
    most_popular_model_week_short = f"{most_popular_model_week_id[:8]}...{most_popular_model_week_id[-8:]}" if most_popular_model_week_id and len(most_popular_model_week_id) > 16 else (most_popular_model_week_id or "N/A")
    
    # Images generated this week
    images_this_week = valid_images.filter(timestamp__gte=one_week_ago).count()
    
    # Get scan status info
    scan_status = ScanStatus.objects.first()
    last_scan_time = scan_status.last_scan_time if scan_status else None
    last_scanned_block = scan_status.last_scanned_block if scan_status else None
    
    # Get recent images for preview, filtering out invalid entries
    recent_images = valid_images.order_by('-timestamp')[:12]
    
    context = {
        'total_images': total_images,
        'accessible_images': accessible_images,
        'unique_models': unique_models,
        'unique_users': unique_users,
        'unique_miners': unique_miners,
        'most_popular_model_short': most_popular_model_short,
        'most_popular_model_week_short': most_popular_model_week_short,
        'images_this_week': images_this_week,
        'last_scan_time': last_scan_time,
        'last_scanned_block': last_scanned_block,
        'recent_images': recent_images,
    }
    
    return render(request, 'gallery/info.html', context)
