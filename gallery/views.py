from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import ArbiusImage, ScanStatus


def index(request):
    """Gallery index view with automatic pagination"""
    # Get all images ordered by accessibility first, then by timestamp
    images = ArbiusImage.objects.all().order_by('-is_accessible', '-timestamp')
    
    # Calculate stats for display
    total_images = ArbiusImage.objects.count()
    
    # Count unique wallets that have generated images (using miner_address since it's populated)
    unique_wallets = ArbiusImage.objects.values('miner_address').distinct().count()
    
    # Count new images in the last 24 hours
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    new_images_24h = ArbiusImage.objects.filter(timestamp__gte=twenty_four_hours_ago).count()
    
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
    
    # Get related images for suggestions
    related_images = ArbiusImage.objects.filter(
        is_accessible=True
    ).exclude(id=image.id).order_by('-timestamp')[:6]
    
    context = {
        'image': image,
        'related_images': related_images,
    }
    
    return render(request, 'gallery/image_detail.html', context)


def stats(request):
    """Statistics and information page"""
    # Calculate comprehensive stats
    total_images = ArbiusImage.objects.count()
    accessible_images = ArbiusImage.objects.filter(is_accessible=True).count()
    pending_images = total_images - accessible_images
    
    # Calculate accessibility percentage
    accessibility_percentage = round(
        (accessible_images / total_images * 100) if total_images > 0 else 0, 1
    )
    
    # Get scan status info
    scan_status = ScanStatus.objects.first()
    last_scan_time = scan_status.last_scan_time if scan_status else None
    last_scanned_block = scan_status.last_scanned_block if scan_status else None
    
    # Get recent images for preview
    recent_images = ArbiusImage.objects.order_by('-timestamp')[:12]
    
    context = {
        'total_images': total_images,
        'accessible_images': accessible_images,
        'pending_images': pending_images,
        'accessibility_percentage': accessibility_percentage,
        'last_scan_time': last_scan_time,
        'last_scanned_block': last_scanned_block,
        'recent_images': recent_images,
    }
    
    return render(request, 'gallery/stats.html', context)
