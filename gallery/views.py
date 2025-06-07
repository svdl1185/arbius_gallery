from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Length, Count
from django.utils import timezone
from datetime import timedelta
from .models import ArbiusImage, ScanStatus


def index(request):
    """Gallery index view with automatic pagination"""
    # Get all images ordered by accessibility first, then by timestamp
    # Filter out invalid entries (text model outputs and non-images)
    images = ArbiusImage.objects.annotate(
        prompt_length=Length('prompt')
    ).exclude(
        prompt__startswith="<|begin_of_text|>"
    ).exclude(
        prompt__startswith="<|end_of_text|>"
    ).exclude(
        prompt_length__gt=5000  # Exclude extremely long prompts (likely text outputs)
    ).filter(
        is_accessible=True  # Only show accessible images
    ).order_by('-timestamp')
    
    # Calculate stats for display
    total_images = images.count()
    
    # Count new images in the last 24 hours
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    new_images_24h = images.filter(timestamp__gte=twenty_four_hours_ago).count()
    
    # Count new images in the last week
    one_week_ago = timezone.now() - timedelta(weeks=1)
    images_this_week = images.filter(timestamp__gte=one_week_ago).count()
    
    # Pagination
    paginator = Paginator(images, 25)  # Show 25 images per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'images': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'total_images': total_images,
        'new_images_24h': new_images_24h,
        'images_this_week': images_this_week,
    }
    
    return render(request, 'gallery/index.html', context)


def search(request):
    """Search view for finding images by prompt keywords"""
    query = request.GET.get('q', '').strip()
    
    if query:
        # Search only in the prompt field with improved filtering for text outputs
        images = ArbiusImage.objects.annotate(
            prompt_length=Length('prompt')
        ).exclude(
            prompt__startswith="<|begin_of_text|>"
        ).exclude(
            prompt__startswith="<|end_of_text|>"
        ).exclude(
            prompt_length__gt=5000  # Exclude extremely long prompts (likely text outputs)
        ).filter(
            is_accessible=True,  # Only show accessible images
            prompt__icontains=query
        ).order_by('-timestamp')
    else:
        # If no query, redirect to regular index
        images = ArbiusImage.objects.annotate(
            prompt_length=Length('prompt')
        ).exclude(
            prompt__startswith="<|begin_of_text|>"
        ).exclude(
            prompt__startswith="<|end_of_text|>"
        ).exclude(
            prompt_length__gt=5000
        ).filter(
            is_accessible=True
        ).order_by('-timestamp')
    
    # Calculate stats for display (use same filtering)
    total_images = ArbiusImage.objects.annotate(
        prompt_length=Length('prompt')
    ).exclude(
        prompt__startswith="<|begin_of_text|>"
    ).exclude(
        prompt__startswith="<|end_of_text|>"
    ).exclude(
        prompt_length__gt=5000
    ).filter(is_accessible=True).count()
    
    # Count new images in the last 24 hours
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    new_images_24h = ArbiusImage.objects.annotate(
        prompt_length=Length('prompt')
    ).exclude(
        prompt__startswith="<|begin_of_text|>"
    ).exclude(
        prompt__startswith="<|end_of_text|>"
    ).exclude(
        prompt_length__gt=5000
    ).filter(
        is_accessible=True,
        timestamp__gte=twenty_four_hours_ago
    ).count()
    
    # Count new images in the last week
    one_week_ago = timezone.now() - timedelta(weeks=1)
    images_this_week = ArbiusImage.objects.annotate(
        prompt_length=Length('prompt')
    ).exclude(
        prompt__startswith="<|begin_of_text|>"
    ).exclude(
        prompt__startswith="<|end_of_text|>"
    ).exclude(
        prompt_length__gt=5000
    ).filter(
        is_accessible=True,
        timestamp__gte=one_week_ago
    ).count()
    
    # Pagination
    paginator = Paginator(images, 25)  # Show 25 images per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'images': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'total_images': total_images,
        'new_images_24h': new_images_24h,
        'images_this_week': images_this_week,
        'query': query,
    }
    
    return render(request, 'gallery/index.html', context)


def image_detail(request, image_id):
    """Individual image detail view"""
    image = get_object_or_404(ArbiusImage, id=image_id)
    
    # Get related images for suggestions, filtering out text outputs
    related_images = ArbiusImage.objects.annotate(
        prompt_length=Length('prompt')
    ).exclude(
        prompt__startswith="<|begin_of_text|>"
    ).exclude(
        prompt__startswith="<|end_of_text|>"
    ).exclude(
        prompt_length__gt=5000
    ).filter(
        is_accessible=True
    ).exclude(id=image.id).order_by('-timestamp')[:6]
    
    context = {
        'image': image,
        'related_images': related_images,
    }
    
    return render(request, 'gallery/image_detail.html', context)


def info(request):
    """Information page about the Arbius gallery and process"""
    # Filter out text outputs for consistent stats
    valid_images = ArbiusImage.objects.annotate(
        prompt_length=Length('prompt')
    ).exclude(
        prompt__startswith="<|begin_of_text|>"
    ).exclude(
        prompt__startswith="<|end_of_text|>"
    ).exclude(
        prompt_length__gt=5000
    ).filter(is_accessible=True)
    
    # Calculate comprehensive stats
    total_images = valid_images.count()
    images_with_prompts = valid_images.filter(prompt__isnull=False).exclude(prompt='').count()
    
    # Calculate new statistics
    unique_models = valid_images.filter(model_id__isnull=False).exclude(model_id='').values('model_id').distinct().count()
    
    # Calculate daily average (images per day)
    if total_images > 0:
        oldest_image = valid_images.order_by('timestamp').first()
        newest_image = valid_images.order_by('-timestamp').first()
        if oldest_image and newest_image:
            days_span = (newest_image.timestamp - oldest_image.timestamp).days + 1
            daily_average = round(total_images / days_span, 1) if days_span > 0 else total_images
        else:
            daily_average = 0
    else:
        daily_average = 0
    
    # Most popular model overall
    most_popular_model = valid_images.filter(model_id__isnull=False).exclude(model_id='').values('model_id').annotate(count=Count('model_id')).order_by('-count').first()
    most_popular_model_id = most_popular_model['model_id'] if most_popular_model else None
    most_popular_model_short = f"{most_popular_model_id[:8]}...{most_popular_model_id[-8:]}" if most_popular_model_id and len(most_popular_model_id) > 16 else (most_popular_model_id or "N/A")
    
    # Most popular model this week
    one_week_ago = timezone.now() - timedelta(weeks=1)
    most_popular_model_week = valid_images.filter(timestamp__gte=one_week_ago, model_id__isnull=False).exclude(model_id='').values('model_id').annotate(count=Count('model_id')).order_by('-count').first()
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
        'images_with_prompts': images_with_prompts,
        'unique_models': unique_models,
        'daily_average': daily_average,
        'most_popular_model_short': most_popular_model_short,
        'most_popular_model_week_short': most_popular_model_week_short,
        'images_this_week': images_this_week,
        'last_scan_time': last_scan_time,
        'last_scanned_block': last_scanned_block,
        'recent_images': recent_images,
    }
    
    return render(request, 'gallery/info.html', context)
