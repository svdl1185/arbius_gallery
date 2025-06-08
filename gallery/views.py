from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db.models.functions import Length, TruncDate
from django.utils import timezone
from datetime import timedelta
from .models import ArbiusImage, ScanStatus
import json


def get_base_queryset():
    """Get the base queryset with all filtering applied"""
    return ArbiusImage.objects.annotate(
        prompt_length=Length('prompt')
    ).exclude(
        prompt__startswith="<|begin_of_text|>"
    ).exclude(
        prompt__startswith="<|end_of_text|>"
    ).exclude(
        prompt__startswith='{"System prompt"'
    ).exclude(
        prompt__startswith='{"MessageHistory"'
    ).exclude(
        prompt_length__gt=5000  # Exclude extremely long prompts (likely text outputs)
    ).exclude(
        prompt__icontains='hitler'  # Filter out Hitler-related content
    ).filter(
        is_accessible=True  # Only show accessible images
    )


def get_image_models_queryset():
    """Get queryset that only includes valid image generation models"""
    return get_base_queryset().exclude(
        model_id__isnull=True
    ).exclude(
        model_id=''
    ).exclude(
        model_id__startswith='0x000000'  # Filter out null/empty model IDs
    ).exclude(
        model_id='0x89c39001e3b23d2092bd998b62f07b523d23deb55e1627048b4ed47a4a38d5cc'  # Filter out text model (2564 images)
    ).exclude(
        model_id='0x6cb3eed9fe3f32da1910825b98bd49d537912c99410e7a35f30add137fd3b64c'  # Filter out text model (36 images)
    )


def index(request):
    """Gallery index view with automatic pagination and model filtering"""
    # Get base queryset
    images = get_base_queryset()
    
    # Apply model filter if provided
    model_filter = request.GET.get('model', '')
    if model_filter:
        images = images.filter(model_id=model_filter)
    
    # Apply task submitter filter if provided
    task_submitter_filter = request.GET.get('task_submitter', '')
    if task_submitter_filter:
        images = images.filter(task_submitter=task_submitter_filter)
    
    # Order by timestamp
    images = images.order_by('-timestamp')
    
    # Get available models for filter dropdown
    available_models = get_image_models_queryset().values('model_id').annotate(
        count=Count('id')
    ).order_by('-count')[:20]  # Top 20 models by usage
    
    # Calculate stats for display
    total_images = images.count()
    
    # Count new images in the last 24 hours
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    new_images_24h = images.filter(timestamp__gte=twenty_four_hours_ago).count()
    
    # Count new images in the last week
    one_week_ago = timezone.now() - timedelta(weeks=1)
    images_this_week = images.filter(timestamp__gte=one_week_ago).count()
    
    # Pagination
    paginator = Paginator(images, 24)  # Show 24 images per page (6 rows × 4 columns)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'images': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'total_images': total_images,
        'new_images_24h': new_images_24h,
        'images_this_week': images_this_week,
        'available_models': available_models,
        'selected_model': model_filter,
        'selected_task_submitter': task_submitter_filter,
    }
    
    return render(request, 'gallery/index.html', context)


def search(request):
    """Search view for finding images by prompt keywords with model filtering"""
    query = request.GET.get('q', '').strip()
    model_filter = request.GET.get('model', '')
    task_submitter_filter = request.GET.get('task_submitter', '')
    
    # Get base queryset
    images = get_base_queryset()
    
    if query:
        # Split the query into individual words and create Q objects for each
        query_words = query.split()
        q_objects = Q()
        
        # Create an AND condition for each word
        for word in query_words:
            q_objects &= Q(prompt__icontains=word)
        
        # Apply search filter
        images = images.filter(q_objects)
    
    # Apply model filter if provided
    if model_filter:
        images = images.filter(model_id=model_filter)
    
    # Apply task submitter filter if provided
    if task_submitter_filter:
        images = images.filter(task_submitter=task_submitter_filter)
    
    # Order by timestamp
    images = images.order_by('-timestamp')
    
    # Get available models for filter dropdown
    available_models = get_image_models_queryset().values('model_id').annotate(
        count=Count('id')
    ).order_by('-count')[:20]  # Top 20 models by usage
    
    # Calculate stats for display (use same filtering)
    total_images = get_base_queryset().count()
    
    # Count new images in the last 24 hours
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    new_images_24h = get_base_queryset().filter(
        timestamp__gte=twenty_four_hours_ago
    ).count()
    
    # Count new images in the last week
    one_week_ago = timezone.now() - timedelta(weeks=1)
    images_this_week = get_base_queryset().filter(
        timestamp__gte=one_week_ago
    ).count()
    
    # Pagination
    paginator = Paginator(images, 24)  # Show 24 images per page (6 rows × 4 columns)
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
        'available_models': available_models,
        'selected_model': model_filter,
        'selected_task_submitter': task_submitter_filter,
    }
    
    return render(request, 'gallery/index.html', context)


def image_detail(request, image_id):
    """Individual image detail view with related images by same user and same model"""
    image = get_object_or_404(ArbiusImage, id=image_id)
    
    # Get images by the same user (task submitter)
    same_user_images = None
    if image.task_submitter:
        same_user_images = get_base_queryset().filter(
            task_submitter=image.task_submitter
        ).exclude(id=image.id).order_by('-timestamp')[:6]
    
    # Get images from the same model
    same_model_images = None
    if image.model_id:
        same_model_images = get_base_queryset().filter(
            model_id=image.model_id
        ).exclude(id=image.id).order_by('-timestamp')[:6]
    
    context = {
        'image': image,
        'same_user_images': same_user_images,
        'same_model_images': same_model_images,
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
        prompt__startswith='{"System prompt"'
    ).exclude(
        prompt__startswith='{"MessageHistory"'
    ).exclude(
        prompt_length__gt=5000
    ).exclude(
        prompt__icontains='hitler'  # Filter out Hitler-related content
    ).filter(is_accessible=True)
    
    # Calculate comprehensive stats
    total_images = valid_images.count()
    images_with_prompts = valid_images.filter(prompt__isnull=False).exclude(prompt='').count()
    
    # Images generated in the last 24 hours (replacing daily average)
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    new_images_24h = valid_images.filter(timestamp__gte=twenty_four_hours_ago).count()
    
    # Images generated this week
    one_week_ago = timezone.now() - timedelta(weeks=1)
    images_this_week = valid_images.filter(timestamp__gte=one_week_ago).count()
    
    # Number of unique users (task submitters)
    unique_users = valid_images.exclude(
        task_submitter__isnull=True
    ).exclude(
        task_submitter=''
    ).values('task_submitter').distinct().count()
    
    # Number of different models
    unique_models = get_image_models_queryset().values('model_id').distinct().count()
    
    # New users this week
    new_users_this_week = valid_images.filter(
        timestamp__gte=one_week_ago
    ).exclude(
        task_submitter__isnull=True
    ).exclude(
        task_submitter=''
    ).values('task_submitter').distinct().count()
    
    # Most used model overall
    most_used_model = get_image_models_queryset().values('model_id').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    # Most used model this week
    most_used_model_week = get_image_models_queryset().filter(
        timestamp__gte=one_week_ago
    ).values('model_id').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    # Get data for cumulative chart (using date formatting instead of DATE_TRUNC for SQLite)
    cumulative_data = []
    if total_images > 0:
        # Group by month using Python date formatting since SQLite doesn't support DATE_TRUNC
        all_images = valid_images.order_by('timestamp')
        monthly_counts = {}
        
        for image in all_images:
            month_key = image.timestamp.strftime('%Y-%m')
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
        
        cumulative_total = 0
        for month in sorted(monthly_counts.keys()):
            cumulative_total += monthly_counts[month]
            cumulative_data.append({
                'date': month,
                'total': cumulative_total
            })
    
    # Get data for daily chart (last 25 days) - using Python grouping instead of database functions
    twenty_five_days_ago = timezone.now() - timedelta(days=25)
    recent_images = valid_images.filter(
        timestamp__gte=twenty_five_days_ago
    ).order_by('timestamp')
    
    # Group by date using Python
    daily_counts = {}
    for image in recent_images:
        date_key = image.timestamp.date()
        daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
    
    # Convert to format suitable for Chart.js
    daily_chart_data = []
    for i in range(25):
        date = (timezone.now() - timedelta(days=24-i)).date()
        count = daily_counts.get(date, 0)
        daily_chart_data.append({
            'date': date.strftime('%m/%d'),
            'count': count
        })
    
    # Get scan status info
    scan_status = ScanStatus.objects.first()
    last_scan_time = scan_status.last_scan_time if scan_status else None
    last_scanned_block = scan_status.last_scanned_block if scan_status else None
    
    # Get recent images for preview, filtering out invalid entries
    recent_images = valid_images.order_by('-timestamp')[:12]
    
    context = {
        'total_images': total_images,
        'images_with_prompts': images_with_prompts,
        'new_images_24h': new_images_24h,  # Replaced daily_average
        'images_this_week': images_this_week,
        'unique_users': unique_users,
        'unique_models': unique_models,
        'new_users_this_week': new_users_this_week,
        'most_used_model': most_used_model,
        'most_used_model_week': most_used_model_week,
        'last_scan_time': last_scan_time,
        'last_scanned_block': last_scanned_block,
        'recent_images': recent_images,
        'cumulative_chart_data': json.dumps(cumulative_data),
        'daily_chart_data': json.dumps(daily_chart_data),
    }
    
    return render(request, 'gallery/info.html', context)
