from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Q, Count, Case, When, IntegerField, Exists, OuterRef
from django.db.models.functions import Length
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import ArbiusImage, UserProfile, ImageUpvote, ImageComment
from .middleware import require_wallet_auth


def get_display_name_for_wallet(wallet_address):
    """Get appropriate display name for a wallet address"""
    if wallet_address.lower() == '0x708816d665eb09e5a86ba82a774dabb550bc8af5':
        return "Arbius Telegram Bot"
    else:
        return f"User {wallet_address[:8]}..."


def get_base_queryset():
    """Get the base queryset for images with optimizations and filtering"""
    
    # Only allow the main image model - be very restrictive
    ALLOWED_MODELS = [
        '0xa473c70e9d7c872ac948d20546bc79db55fa64ca325a4b229aaffddb7f86aae0',  # Main image model only
    ]
    
    queryset = ArbiusImage.objects.select_related().prefetch_related('upvotes', 'comments').filter(
        is_accessible=True,  # Only show accessible images
        model_id__in=ALLOWED_MODELS  # Only allow whitelisted models
    )
    
    # Additional content filtering for extra safety
    queryset = queryset.exclude(
        # Filter out images with problematic prompts
        Q(prompt__icontains='hitler') |
        Q(prompt__icontains='nazi') |
        Q(prompt__icontains='violence') |
        Q(prompt__icontains='explicit') |
        Q(prompt__icontains='nsfw') |
        # Add more filter terms as needed
        Q(prompt__iregex=r'\b(porn|sex|nude|naked)\b')  # Case insensitive regex
    )
    
    return queryset


def annotate_upvote_status(queryset, wallet_address):
    """Annotate queryset with upvote status for the given wallet address"""
    if not wallet_address:
        # If no wallet address, just add a False annotation
        return queryset.annotate(user_has_upvoted=Case(When(id__isnull=True, then=False), default=False, output_field=IntegerField()))
    
    # Annotate with whether the current user has upvoted each image
    return queryset.annotate(
        user_has_upvoted=Exists(
            ImageUpvote.objects.filter(
                image=OuterRef('pk'),
                wallet_address__iexact=wallet_address
            )
        )
    )


def get_available_models_with_categories():
    """Get available models organized by categories with restrictive filtering"""
    
    # Only allow the main image model
    ALLOWED_MODELS = [
        '0xa473c70e9d7c872ac948d20546bc79db55fa64ca325a4b229aaffddb7f86aae0',  # Main image model only
    ]
    
    # Get model stats only for allowed models
    all_models = ArbiusImage.objects.values('model_id').annotate(
        count=Count('id')
    ).filter(
        model_id__in=ALLOWED_MODELS,
        is_accessible=True
    ).order_by('-count')
    
    # Format the allowed models
    filtered_models = []
    for model in all_models:
        model_info = {
            'model_id': model['model_id'],
            'count': model['count'],
            'short_name': f"{model['model_id'][:8]}...{model['model_id'][-8:]}" if len(model['model_id']) > 16 else model['model_id']
        }
        filtered_models.append(model_info)
    
    # Simple categorization - all allowed models go to "Available"
    categorized = {'Available': filtered_models, 'Other': []}
    
    return filtered_models, categorized


def index(request):
    """Main gallery view with Web3 integration"""
    # Get filter parameters
    search_query = request.GET.get('q', '').strip()
    selected_task_submitter = request.GET.get('task_submitter', '').strip()
    selected_model = request.GET.get('model', '').strip()
    sort_by = request.GET.get('sort', 'upvotes')  # Default to most upvoted
    
    # Get current user's wallet address
    current_wallet_address = getattr(request, 'wallet_address', None)
    
    # Base queryset - now includes comprehensive filtering
    images = get_base_queryset()
    
    # Apply filters (existing logic)
    if search_query:
        images = images.filter(
            Q(prompt__icontains=search_query) |
            Q(cid__icontains=search_query) |
            Q(transaction_hash__icontains=search_query) |
            Q(task_id__icontains=search_query)
        )
    
    if selected_task_submitter:
        images = images.filter(task_submitter__iexact=selected_task_submitter)
    
    if selected_model:
        images = images.filter(model_id=selected_model)
    
    # Apply sorting
    if sort_by == 'upvotes':
        images = images.annotate(upvote_count_db=Count('upvotes')).order_by('-upvote_count_db', '-timestamp')
    elif sort_by == 'comments':
        images = images.annotate(comment_count_db=Count('comments')).order_by('-comment_count_db', '-timestamp')
    elif sort_by == 'newest':
        images = images.order_by('-timestamp')
    elif sort_by == 'oldest':
        images = images.order_by('timestamp')
    else:
        # Default fallback to most upvoted
        images = images.annotate(upvote_count_db=Count('upvotes')).order_by('-upvote_count_db', '-timestamp')
    
    # Annotate with upvote status for current user
    images = annotate_upvote_status(images, current_wallet_address)
    
    # Get available models with improved categorization
    available_models, model_categories = get_available_models_with_categories()
    
    # Pagination
    paginator = Paginator(images, 24)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_task_submitter': selected_task_submitter,
        'selected_model': selected_model,
        'sort_by': sort_by,
        'available_models': available_models,
        'model_categories': model_categories,
        'total_images': ArbiusImage.objects.filter(is_accessible=True).count(),  # Use filtered count
        'wallet_address': current_wallet_address,
        'user_profile': getattr(request, 'user_profile', None),
    }
    return render(request, 'gallery/index.html', context)


def search(request):
    """Search view with Web3 integration"""
    # Get search parameters
    search_query = request.GET.get('q', '').strip()
    selected_task_submitter = request.GET.get('task_submitter', '').strip()
    selected_model = request.GET.get('model', '').strip()
    sort_by = request.GET.get('sort', 'upvotes')  # Default to most upvoted
    
    # Get current user's wallet address
    current_wallet_address = getattr(request, 'wallet_address', None)
    
    # Base queryset - now includes comprehensive filtering
    images = get_base_queryset()
    
    # Apply search filters
    if search_query:
        images = images.filter(
            Q(prompt__icontains=search_query) |
            Q(cid__icontains=search_query) |
            Q(transaction_hash__icontains=search_query) |
            Q(task_id__icontains=search_query)
        )
    
    if selected_task_submitter:
        images = images.filter(task_submitter__iexact=selected_task_submitter)
    
    if selected_model:
        images = images.filter(model_id=selected_model)
    
    # Apply sorting
    if sort_by == 'upvotes':
        images = images.annotate(upvote_count_db=Count('upvotes')).order_by('-upvote_count_db', '-timestamp')
    elif sort_by == 'comments':
        images = images.annotate(comment_count_db=Count('comments')).order_by('-comment_count_db', '-timestamp')
    elif sort_by == 'newest':
        images = images.order_by('-timestamp')
    elif sort_by == 'oldest':
        images = images.order_by('timestamp')
    else:
        # Default fallback to most upvoted
        images = images.annotate(upvote_count_db=Count('upvotes')).order_by('-upvote_count_db', '-timestamp')
    
    # Annotate with upvote status for current user
    images = annotate_upvote_status(images, current_wallet_address)
    
    # Get available models with improved categorization
    available_models, model_categories = get_available_models_with_categories()
    
    # Pagination
    paginator = Paginator(images, 24)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_task_submitter': selected_task_submitter,
        'selected_model': selected_model,
        'sort_by': sort_by,
        'available_models': available_models,
        'model_categories': model_categories,
        'wallet_address': current_wallet_address,
        'user_profile': getattr(request, 'user_profile', None),
    }
    return render(request, 'gallery/search.html', context)


def image_detail(request, image_id):
    """Individual image detail view with social features"""
    image = get_object_or_404(ArbiusImage, id=image_id)
    
    # Get related images
    same_user_images = None
    if image.task_submitter:
        same_user_images = get_base_queryset().filter(
            task_submitter__iexact=image.task_submitter
        ).exclude(id=image.id).order_by('-timestamp')[:6]
    
    same_model_images = None
    if image.model_id:
        same_model_images = get_base_queryset().filter(
            model_id=image.model_id
        ).exclude(id=image.id).order_by('-timestamp')[:6]
    
    # Get comments
    comments = image.comments.all()[:20]  # Latest 20 comments
    
    # Check if current user has upvoted
    has_upvoted = False
    if hasattr(request, 'wallet_address') and request.wallet_address:
        has_upvoted = image.has_upvoted(request.wallet_address)
    
    context = {
        'image': image,
        'same_user_images': same_user_images,
        'same_model_images': same_model_images,
        'comments': comments,
        'has_upvoted': has_upvoted,
        'wallet_address': getattr(request, 'wallet_address', None),
        'user_profile': getattr(request, 'user_profile', None),
    }
    
    return render(request, 'gallery/image_detail.html', context)


def info(request):
    """Info page with enhanced statistics"""
    from django.db.models import Q
    import json
    
    total_images = ArbiusImage.objects.count()
    total_accessible = ArbiusImage.objects.filter(is_accessible=True).count()
    
    # Time periods
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_week = now - timedelta(days=7)
    
    # Recent activity
    recent_images = ArbiusImage.objects.filter(discovered_at__gte=last_24h).count()
    images_this_week = ArbiusImage.objects.filter(discovered_at__gte=last_week).count()
    
    # User statistics
    unique_users = ArbiusImage.objects.filter(
        task_submitter__isnull=False
    ).values('task_submitter').distinct().count()
    
    new_users_this_week = ArbiusImage.objects.filter(
        discovered_at__gte=last_week,
        task_submitter__isnull=False
    ).values('task_submitter').distinct().count()
    
    # Model statistics
    unique_models = ArbiusImage.objects.filter(
        model_id__isnull=False
    ).exclude(model_id='').values('model_id').distinct().count()
    
    # Most used models
    most_used_model = ArbiusImage.objects.filter(
        model_id__isnull=False
    ).exclude(model_id='').values('model_id').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    most_used_model_week = ArbiusImage.objects.filter(
        model_id__isnull=False,
        discovered_at__gte=last_week
    ).exclude(model_id='').values('model_id').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    # Top creators
    top_creators = ArbiusImage.objects.filter(
        task_submitter__isnull=False
    ).values('task_submitter').annotate(
        image_count=Count('id')
    ).order_by('-image_count')[:10]
    
    # Model statistics for old context (keeping for compatibility)
    model_stats = ArbiusImage.objects.filter(
        model_id__isnull=False
    ).exclude(model_id='').values('model_id').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Chart data - Daily images (last 25 days)
    daily_chart_data = []
    for i in range(24, -1, -1):
        date = now - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        count = ArbiusImage.objects.filter(
            discovered_at__gte=date_start,
            discovered_at__lt=date_end
        ).count()
        
        daily_chart_data.append({
            'date': date.strftime('%m/%d'),
            'count': count
        })
    
    # Chart data - Cumulative images (last 25 days)
    cumulative_chart_data = []
    total_so_far = ArbiusImage.objects.filter(
        discovered_at__lt=now - timedelta(days=24)
    ).count()
    
    for i in range(24, -1, -1):
        date = now - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        daily_count = ArbiusImage.objects.filter(
            discovered_at__gte=date_start,
            discovered_at__lt=date_end
        ).count()
        
        total_so_far += daily_count
        
        cumulative_chart_data.append({
            'date': date.strftime('%m/%d'),
            'total': total_so_far
        })
    
    # Social statistics
    total_upvotes = ImageUpvote.objects.count()
    total_comments = ImageComment.objects.count()
    total_profiles = UserProfile.objects.count()
    
    # Last scan time (use the latest image discovery time)
    latest_image = ArbiusImage.objects.order_by('-discovered_at').first()
    last_scan_time = latest_image.discovered_at if latest_image else None
    
    context = {
        'total_images': total_images,
        'total_accessible': total_accessible,
        'recent_images': recent_images,
        'images_this_week': images_this_week,
        'new_images_24h': recent_images,
        'unique_users': unique_users,
        'new_users_this_week': new_users_this_week,
        'unique_models': unique_models,
        'most_used_model': most_used_model,
        'most_used_model_week': most_used_model_week,
        'top_creators': top_creators,
        'model_stats': model_stats,
        'total_upvotes': total_upvotes,
        'total_comments': total_comments,
        'total_profiles': total_profiles,
        'cumulative_chart_data': json.dumps(cumulative_chart_data),
        'daily_chart_data': json.dumps(daily_chart_data),
        'last_scan_time': last_scan_time,
        'wallet_address': getattr(request, 'wallet_address', None),
        'user_profile': getattr(request, 'user_profile', None),
    }
    return render(request, 'gallery/info.html', context)


# === Web3 Authentication Views ===

@csrf_exempt
@require_POST
def connect_wallet(request):
    """Handle wallet connection"""
    try:
        data = json.loads(request.body)
        wallet_address = data.get('wallet_address', '').lower()
        signature = data.get('signature', '')
        message = data.get('message', '')
        
        if not wallet_address or not signature:
            return JsonResponse({'error': 'Missing wallet address or signature'}, status=400)
        
        # TODO: Verify signature against message (implement signature verification)
        # For now, we'll trust the frontend verification
        
        # Store wallet address in session
        request.session['wallet_address'] = wallet_address
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(
            wallet_address=wallet_address,
            defaults={'display_name': get_display_name_for_wallet(wallet_address)}
        )
        
        if created:
            profile.update_stats()
        
        return JsonResponse({
            'success': True,
            'wallet_address': wallet_address,
            'profile': {
                'display_name': profile.display_name,
                'total_images_created': profile.total_images_created,
                'total_upvotes_received': profile.total_upvotes_received,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
def disconnect_wallet(request):
    """Handle wallet disconnection"""
    request.session.pop('wallet_address', None)
    return JsonResponse({'success': True})


# === Social Feature Views ===

@csrf_exempt
@require_POST
@require_wallet_auth
def toggle_upvote(request, image_id):
    """Toggle upvote on an image"""
    try:
        image = get_object_or_404(ArbiusImage, id=image_id)
        wallet_address = request.wallet_address
        
        upvote, created = ImageUpvote.objects.get_or_create(
            image=image,
            wallet_address=wallet_address
        )
        
        if not created:
            # Remove upvote if it already exists
            upvote.delete()
            upvoted = False
        else:
            upvoted = True
        
        # Update creator's stats if they have a profile
        if image.task_submitter:
            try:
                creator_profile = UserProfile.objects.get(wallet_address=image.task_submitter)
                creator_profile.update_stats()
            except UserProfile.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'upvoted': upvoted,
            'upvote_count': image.upvote_count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
@require_wallet_auth
def add_comment(request, image_id):
    """Add a comment to an image"""
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content or len(content) > 1000:
            return JsonResponse({'error': 'Comment must be between 1 and 1000 characters'}, status=400)
        
        image = get_object_or_404(ArbiusImage, id=image_id)
        
        comment = ImageComment.objects.create(
            image=image,
            wallet_address=request.wallet_address,
            content=content
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'wallet_address': comment.wallet_address,
                'created_at': comment.created_at.isoformat(),
            },
            'comment_count': image.comment_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def user_profile(request, wallet_address):
    """Display user profile page"""
    
    # Try to get existing profile, or create one if the wallet has images
    try:
        profile = UserProfile.objects.get(wallet_address__iexact=wallet_address)
    except UserProfile.DoesNotExist:
        # Check if this wallet has created any images
        has_images = get_base_queryset().filter(task_submitter__iexact=wallet_address).exists()
        
        if has_images:
            # Auto-create a basic profile for wallets that have created images
            profile = UserProfile.objects.create(
                wallet_address=wallet_address.lower(),
                display_name=get_display_name_for_wallet(wallet_address)
            )
            # Update stats for the new profile
            profile.update_stats()
        else:
            # No images and no profile - this wallet doesn't exist in our system
            raise Http404("This wallet address has not created any images in the gallery.")
    
    # Get sort parameter
    sort_by = request.GET.get('sort', 'upvotes')  # Default to most upvoted
    
    # Get current user's wallet address
    current_wallet_address = getattr(request, 'wallet_address', None)
    
    # Get user's images with sorting
    user_images = get_base_queryset().filter(
        task_submitter__iexact=wallet_address
    )
    
    # Apply sorting
    if sort_by == 'upvotes':
        user_images = user_images.annotate(upvote_count_db=Count('upvotes')).order_by('-upvote_count_db', '-timestamp')
    elif sort_by == 'comments':
        user_images = user_images.annotate(comment_count_db=Count('comments')).order_by('-comment_count_db', '-timestamp')
    elif sort_by == 'newest':
        user_images = user_images.order_by('-timestamp')
    elif sort_by == 'oldest':
        user_images = user_images.order_by('timestamp')
    else:
        # Default fallback to most upvoted
        user_images = user_images.annotate(upvote_count_db=Count('upvotes')).order_by('-upvote_count_db', '-timestamp')
    
    # Annotate with upvote status for current user
    user_images = annotate_upvote_status(user_images, current_wallet_address)
    
    # Pagination
    paginator = Paginator(user_images, 24)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Check if viewing own profile (only if user is authenticated)
    is_own_profile = (current_wallet_address and 
                     current_wallet_address.lower() == wallet_address.lower())
    
    # Get current user's profile (may be None for visitors)
    current_user_profile = getattr(request, 'user_profile', None)
    
    context = {
        'profile': profile,
        'page_obj': page_obj,
        'sort_by': sort_by,
        'is_own_profile': is_own_profile,
        'wallet_address': current_wallet_address,  # Current user's wallet (may be None)
        'user_profile': current_user_profile,  # Current user's profile (may be None)
    }
    return render(request, 'gallery/user_profile.html', context)


@csrf_exempt
@require_POST
@require_wallet_auth
def update_profile(request):
    """Update user profile"""
    try:
        data = json.loads(request.body)
        profile = request.user_profile
        
        # Update allowed fields
        if 'display_name' in data:
            display_name = data['display_name'].strip()
            if len(display_name) <= 50:
                profile.display_name = display_name
        
        if 'bio' in data:
            bio = data['bio'].strip()
            if len(bio) <= 500:
                profile.bio = bio
        
        if 'website' in data:
            profile.website = data['website'].strip()
        
        if 'twitter_handle' in data:
            twitter = data['twitter_handle'].strip()
            if twitter.startswith('@'):
                twitter = twitter[1:]
            if len(twitter) <= 50:
                profile.twitter_handle = twitter
        
        profile.save()
        
        return JsonResponse({
            'success': True,
            'profile': {
                'display_name': profile.display_name,
                'bio': profile.bio,
                'website': profile.website,
                'twitter_handle': profile.twitter_handle,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
