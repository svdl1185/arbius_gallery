from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Q, Avg, Min, Max, Case, When, IntegerField, Exists, OuterRef
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from datetime import datetime, timedelta
# from django_ratelimit.decorators import ratelimit  # Removed
import json
import logging

from .models import ArbiusImage, UserProfile, ImageUpvote, ImageComment, MinerAddress
from .middleware import require_wallet_auth, get_display_name_for_wallet
from .crypto_utils import generate_auth_nonce, verify_wallet_signature, create_auth_message


def get_display_name_for_wallet(wallet_address):
    """Get appropriate display name for a wallet address"""
    if wallet_address.lower() == '0x708816d665eb09e5a86ba82a774dabb550bc8af5':
        return "Arbius Telegram Bot"
    else:
        return f"User {wallet_address[:8]}..."


def get_base_queryset(exclude_automine=False):
    """Get the base queryset for images with optimizations and filtering"""
    
    # Only allow the main image model - be very restrictive
    ALLOWED_MODELS = [
        '0xa473c70e9d7c872ac948d20546bc79db55fa64ca325a4b229aaffddb7f86aae0',  # Main image model only
    ]
    
    queryset = ArbiusImage.objects.select_related().prefetch_related('upvotes', 'comments').filter(
        is_accessible=True,  # Only show accessible images
        model_id__in=ALLOWED_MODELS  # Only allow whitelisted models
    )
    
    # Filter out automine images if requested
    if exclude_automine:
        # Get ALL identified miner addresses (both active and inactive)
        # Once a wallet is identified as a miner, it should always be filtered
        miner_wallets = list(MinerAddress.objects.all().values_list('wallet_address', flat=True))
        
        # Fallback to hardcoded list if no miners found in database yet
        if not miner_wallets:
            miner_wallets = [
                '0x5e33e2cead338b1224ddd34636dac7563f97c300',
                '0xdc790a53e50207861591622d349e989fef6f84bc',
                '0x4d826895b255a4f38d7ba87688604c358f4132b6',
                '0xd04c1b09576aa4310e4768d8e9cd12fac3216f95',
            ]
        
        queryset = queryset.exclude(task_submitter__in=miner_wallets)
    
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
    exclude_automine = request.GET.get('exclude_automine', 'true').lower() in ['true', '1', 'on']  # Default to True
    
    # Get current user's wallet address
    current_wallet_address = getattr(request, 'wallet_address', None)
    
    # Base queryset - now includes comprehensive filtering
    images = get_base_queryset(exclude_automine=exclude_automine)
    
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
        'exclude_automine': exclude_automine,
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
    exclude_automine = request.GET.get('exclude_automine', 'true').lower() in ['true', '1', 'on']  # Default to True
    
    # Get current user's wallet address
    current_wallet_address = getattr(request, 'wallet_address', None)
    
    # Base queryset - now includes comprehensive filtering
    images = get_base_queryset(exclude_automine=exclude_automine)
    
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
        'exclude_automine': exclude_automine,
        'available_models': available_models,
        'model_categories': model_categories,
        'wallet_address': current_wallet_address,
        'user_profile': getattr(request, 'user_profile', None),
    }
    return render(request, 'gallery/search.html', context)


def image_detail(request, image_id):
    """Individual image detail view with social features"""
    image = get_object_or_404(ArbiusImage, id=image_id)
    
    # Get automine filter preference
    exclude_automine = request.GET.get('exclude_automine', 'true').lower() in ['true', '1', 'on']  # Default to True
    
    # Get related images
    same_user_images = None
    if image.task_submitter:
        same_user_images = get_base_queryset(exclude_automine=exclude_automine).filter(
            task_submitter__iexact=image.task_submitter
        ).exclude(id=image.id).order_by('-timestamp')[:6]
    
    same_model_images = None
    if image.model_id:
        same_model_images = get_base_queryset(exclude_automine=exclude_automine).filter(
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
        'exclude_automine': exclude_automine,
        'wallet_address': getattr(request, 'wallet_address', None),
        'user_profile': getattr(request, 'user_profile', None),
    }
    
    return render(request, 'gallery/image_detail.html', context)


def info(request):
    """Info page with enhanced statistics"""
    from django.db.models import Q
    import json
    
    # Get automine filter preference
    exclude_automine = request.GET.get('exclude_automine', 'true').lower() in ['true', '1', 'on']  # Default to True
    
    # Use the same filtering as the main gallery
    base_queryset = get_base_queryset(exclude_automine=exclude_automine)
    
    total_images = base_queryset.count()
    total_accessible = base_queryset.filter(is_accessible=True).count()
    
    # Time periods
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_week = now - timedelta(days=7)
    
    # Recent activity - use timestamp (blockchain time) instead of discovered_at
    recent_images = base_queryset.filter(timestamp__gte=last_24h).count()
    images_this_week = base_queryset.filter(timestamp__gte=last_week).count()
    
    # User statistics
    unique_users = base_queryset.filter(
        task_submitter__isnull=False
    ).values('task_submitter').distinct().count()
    
    new_users_this_week = base_queryset.filter(
        timestamp__gte=last_week,
        task_submitter__isnull=False
    ).values('task_submitter').distinct().count()
    
    # Model statistics - use filtered queryset
    unique_models = base_queryset.filter(
        model_id__isnull=False
    ).exclude(model_id='').values('model_id').distinct().count()
    
    # Most used models - use filtered queryset
    most_used_model = base_queryset.filter(
        model_id__isnull=False
    ).exclude(model_id='').values('model_id').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    most_used_model_week = base_queryset.filter(
        model_id__isnull=False,
        timestamp__gte=last_week
    ).exclude(model_id='').values('model_id').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    # Top creators - use filtered queryset
    top_creators = base_queryset.filter(
        task_submitter__isnull=False
    ).values('task_submitter').annotate(
        image_count=Count('id')
    ).order_by('-image_count')[:10]
    
    # Model statistics for old context (keeping for compatibility)
    model_stats = base_queryset.filter(
        model_id__isnull=False
    ).exclude(model_id='').values('model_id').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Chart data - Daily images (last 25 days) - use timestamp
    daily_chart_data = []
    for i in range(24, -1, -1):
        date = now - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        count = base_queryset.filter(
            timestamp__gte=date_start,
            timestamp__lt=date_end
        ).count()
        
        daily_chart_data.append({
            'date': date.strftime('%m/%d'),
            'count': count
        })
    
    # Chart data - Cumulative images (last 25 days) - use timestamp
    cumulative_chart_data = []
    total_so_far = 0  # Start at 0 for the period
    
    for i in range(24, -1, -1):
        date = now - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        daily_count = base_queryset.filter(
            timestamp__gte=date_start,
            timestamp__lt=date_end
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
        'exclude_automine': exclude_automine,
        'wallet_address': getattr(request, 'wallet_address', None),
        'user_profile': getattr(request, 'user_profile', None),
    }
    return render(request, 'gallery/info.html', context)


# === Web3 Authentication Views ===

@csrf_exempt
@require_POST
def get_auth_nonce(request):
    """Generate a secure nonce for wallet authentication"""
    try:
        data = json.loads(request.body)
        wallet_address = data.get('wallet_address', '').strip()
        
        if not wallet_address:
            return JsonResponse({'error': 'Wallet address is required'}, status=400)
        
        # Basic validation of wallet address format
        if not wallet_address.startswith('0x') or len(wallet_address) != 42:
            return JsonResponse({'error': 'Invalid wallet address format'}, status=400)
        
        # Generate nonce and timestamp
        nonce, timestamp = generate_auth_nonce(wallet_address)
        
        # Create message to be signed
        message = create_auth_message(wallet_address, nonce, timestamp)
        
        return JsonResponse({
            'success': True,
            'message': message,
            'nonce': nonce,
            'timestamp': timestamp
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.error(f"Error generating auth nonce: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_POST
def connect_wallet(request):
    """Handle secure wallet connection with signature verification"""
    try:
        data = json.loads(request.body)
        wallet_address = data.get('wallet_address', '').lower().strip()
        signature = data.get('signature', '').strip()
        message = data.get('message', '').strip()
        
        if not wallet_address or not signature or not message:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Verify the signature
        is_valid, error_message = verify_wallet_signature(wallet_address, signature, message)
        
        if not is_valid:
            return JsonResponse({'error': error_message}, status=400)
        
        # Regenerate session to prevent session fixation attacks
        request.session.cycle_key()
        
        # Store wallet address in session
        request.session['wallet_address'] = wallet_address
        request.session.modified = True
        
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
                'wallet_address': profile.wallet_address,
                'total_images_created': profile.total_images_created,
                'total_upvotes_received': profile.total_upvotes_received
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.error(f"Error connecting wallet: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_POST
def disconnect_wallet(request):
    """Handle wallet disconnection with session cleanup"""
    try:
        # Clear wallet address from session
        request.session.pop('wallet_address', None)
        
        # Regenerate session ID for security
        request.session.cycle_key()
        request.session.modified = True
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        logging.error(f"Error disconnecting wallet: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


# === Social Feature Views ===

@csrf_exempt
@require_POST
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
        logging.error(f"Error toggling upvote: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_POST
def add_comment(request, image_id):
    """Add a comment to an image"""
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content or len(content) > 1000:
            return JsonResponse({'error': 'Comment must be between 1 and 1000 characters'}, status=400)
        
        # Basic content validation to prevent spam/abuse
        if len(content) < 2:
            return JsonResponse({'error': 'Comment too short'}, status=400)
            
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
        logging.error(f"Error adding comment: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def user_profile(request, wallet_address):
    """Display user profile page"""
    
    # Get automine filter preference
    exclude_automine = request.GET.get('exclude_automine', 'true').lower() in ['true', '1', 'on']  # Default to True
    
    # Try to get existing profile, or create one if the wallet has images
    try:
        profile = UserProfile.objects.get(wallet_address__iexact=wallet_address)
    except UserProfile.DoesNotExist:
        # Check if this wallet has created any images
        has_images = get_base_queryset(exclude_automine=exclude_automine).filter(task_submitter__iexact=wallet_address).exists()
        
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
    user_images = get_base_queryset(exclude_automine=exclude_automine).filter(
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
        'exclude_automine': exclude_automine,
        'is_own_profile': is_own_profile,
        'wallet_address': current_wallet_address,  # Current user's wallet (may be None)
        'user_profile': current_user_profile,  # Current user's profile (may be None)
    }
    return render(request, 'gallery/user_profile.html', context)


@csrf_exempt
@require_POST
def update_profile(request):
    """Update user profile information"""
    try:
        data = json.loads(request.body)
        display_name = data.get('display_name', '').strip()
        
        if not display_name:
            return JsonResponse({'error': 'Display name is required'}, status=400)
        
        if len(display_name) > 50:
            return JsonResponse({'error': 'Display name too long (max 50 characters)'}, status=400)
        
        # Basic validation - no special characters that could cause issues
        if not display_name.replace(' ', '').replace('-', '').replace('_', '').isalnum():
            return JsonResponse({'error': 'Display name can only contain letters, numbers, spaces, hyphens and underscores'}, status=400)
        
        # Check if user profile exists - it should be set by middleware
        profile = getattr(request, 'user_profile', None)
        if not profile:
            # This shouldn't happen if middleware is working correctly
            logging.error(f"User profile not found for authenticated wallet: {getattr(request, 'wallet_address', 'Unknown')}")
            
            # Try to get or create profile manually
            wallet_address = getattr(request, 'wallet_address', None)
            if not wallet_address:
                return JsonResponse({'error': 'Wallet address not found in session'}, status=400)
            
            try:
                profile = UserProfile.objects.get(wallet_address=wallet_address)
            except UserProfile.DoesNotExist:
                # Create profile if it doesn't exist
                profile = UserProfile.objects.create(
                    wallet_address=wallet_address,
                    display_name=get_display_name_for_wallet(wallet_address)
                )
                logging.info(f"Created new profile for wallet: {wallet_address}")
        
        # Update the profile
        profile.display_name = display_name
        profile.save()
        
        logging.info(f"Profile updated for wallet {profile.wallet_address}: {profile.display_name}")
        
        return JsonResponse({
            'success': True,
            'profile': {
                'display_name': profile.display_name,
                'wallet_address': profile.wallet_address,
                'total_images_created': profile.total_images_created,
                'total_upvotes_received': profile.total_upvotes_received
            }
        })
        
    except json.JSONDecodeError:
        logging.error("Invalid JSON in profile update request")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.error(f"Error updating profile: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def top_users(request):
    """Display top 50 users by image creation count or upvotes"""
    
    # Get sort parameter - 'images' (default) or 'upvotes'
    sort_by = request.GET.get('sort', 'images')
    
    if sort_by == 'upvotes':
        # Sort by total upvotes received - use a simpler approach
        # Get all users who have created images, then sort by upvotes
        # Filter out automine wallets from leaderboards
        top_creators_raw = get_base_queryset(exclude_automine=True).filter(
            task_submitter__isnull=False
        ).values('task_submitter').annotate(
            image_count=Count('id'),
            total_upvotes=Count('upvotes', distinct=True)
        ).order_by('-total_upvotes', '-image_count')[:50]
        
        # Convert to consistent format
        top_creators = []
        for creator in top_creators_raw:
            top_creators.append({
                'task_submitter': creator['task_submitter'],
                'image_count': creator['image_count'],
                'total_upvotes': creator['total_upvotes']
            })
        
    else:
        # Default: Sort by image count (existing logic)
        # Filter out automine wallets from leaderboards
        top_creators_raw = get_base_queryset(exclude_automine=True).filter(
            task_submitter__isnull=False
        ).values('task_submitter').annotate(
            image_count=Count('id')
        ).order_by('-image_count')[:50]
        
        # Convert to consistent format and add upvote counts
        top_creators = []
        for creator in top_creators_raw:
            # Get upvotes for this user (from non-automine images only)
            total_upvotes = ImageUpvote.objects.filter(
                image__task_submitter__iexact=creator['task_submitter'],
                image__in=get_base_queryset(exclude_automine=True)
            ).count()
            
            top_creators.append({
                'task_submitter': creator['task_submitter'],
                'image_count': creator['image_count'],
                'total_upvotes': total_upvotes
            })
    
    # Enrich the data with user profiles and additional stats
    enriched_creators = []
    for i, creator in enumerate(top_creators, 1):
        wallet_address = creator['task_submitter']
        image_count = creator['image_count']
        total_upvotes = creator['total_upvotes']
        
        # Try to get user profile for display name
        try:
            profile = UserProfile.objects.get(wallet_address__iexact=wallet_address)
            display_name = profile.display_name
        except UserProfile.DoesNotExist:
            display_name = get_display_name_for_wallet(wallet_address)
        
        enriched_creators.append({
            'rank': i,
            'wallet_address': wallet_address,
            'display_name': display_name,
            'image_count': image_count,
            'total_upvotes': total_upvotes,
            'short_address': f"{wallet_address[:6]}...{wallet_address[-4:]}",
        })
    
    context = {
        'top_creators': enriched_creators,
        'sort_by': sort_by,
        'wallet_address': getattr(request, 'wallet_address', None),
        'user_profile': getattr(request, 'user_profile', None),
    }
    
    return render(request, 'gallery/top_users.html', context)


def mining_dashboard(request):
    """Hidden mining analytics dashboard - only accessible via direct URL"""
    from django.db.models import Sum, Count, Avg, F, Q
    from django.db.models.functions import TruncDate, TruncHour
    
    # Get current user's wallet address
    current_wallet_address = getattr(request, 'wallet_address', None)
    
    # Get all miners with their statistics
    miners_stats = ArbiusImage.objects.values('solution_provider').annotate(
        total_tasks_completed=Count('id'),
        first_task=Min('timestamp'),
        last_task=Max('timestamp'),
        unique_submitters_served=Count('task_submitter', distinct=True)
    ).filter(
        solution_provider__isnull=False
    ).exclude(
        solution_provider='0x0000000000000000000000000000000000000000'
    ).order_by('-total_tasks_completed')
    
    # Calculate total rewards (based on task completion, assuming 1 AIUS per task)
    for miner in miners_stats:
        miner['estimated_rewards'] = miner['total_tasks_completed'] * 1.0  # 1 AIUS per task
        miner['display_name'] = get_display_name_for_wallet(miner['solution_provider'])
        miner['short_address'] = f"{miner['solution_provider'][:8]}...{miner['solution_provider'][-8:]}"
        
        # Calculate active days
        if miner['first_task'] and miner['last_task']:
            active_days = (miner['last_task'] - miner['first_task']).days + 1
            miner['active_days'] = active_days
            miner['avg_tasks_per_day'] = round(miner['total_tasks_completed'] / max(active_days, 1), 2)
        else:
            miner['active_days'] = 0
            miner['avg_tasks_per_day'] = 0
    
    # Get total network statistics
    total_tasks = ArbiusImage.objects.count()
    total_unique_miners = ArbiusImage.objects.filter(
        solution_provider__isnull=False
    ).exclude(
        solution_provider='0x0000000000000000000000000000000000000000'
    ).values('solution_provider').distinct().count()
    
    total_estimated_rewards = total_tasks * 1.0  # 1 AIUS per task
    
    # Get mining activity over time (daily)
    mining_activity_daily = ArbiusImage.objects.filter(
        solution_provider__isnull=False
    ).exclude(
        solution_provider='0x0000000000000000000000000000000000000000'
    ).annotate(
        date=TruncDate('timestamp')
    ).values('date').annotate(
        tasks_completed=Count('id'),
        unique_miners=Count('solution_provider', distinct=True)
    ).order_by('date')
    
    # Get hourly mining activity for the last 48 hours
    last_48_hours = timezone.now() - timedelta(hours=48)
    mining_activity_hourly = ArbiusImage.objects.filter(
        solution_provider__isnull=False,
        timestamp__gte=last_48_hours
    ).exclude(
        solution_provider='0x0000000000000000000000000000000000000000'
    ).annotate(
        hour=TruncHour('timestamp')
    ).values('hour').annotate(
        tasks_completed=Count('id'),
        unique_miners=Count('solution_provider', distinct=True)
    ).order_by('hour')
    
    # Get top miners by different metrics
    top_miners_by_volume = list(miners_stats[:10])
    top_miners_by_consistency = sorted(
        [m for m in miners_stats if m['active_days'] > 0],
        key=lambda x: x['avg_tasks_per_day'],
        reverse=True
    )[:10]
    
    # Get recent mining activity
    recent_mining_activity = ArbiusImage.objects.filter(
        solution_provider__isnull=False
    ).exclude(
        solution_provider='0x0000000000000000000000000000000000000000'
    ).select_related().order_by('-timestamp')[:20]
    
    # Add display names for recent activity
    for activity in recent_mining_activity:
        activity.miner_display_name = get_display_name_for_wallet(activity.solution_provider)
        activity.submitter_display_name = get_display_name_for_wallet(activity.task_submitter)
    
    # Get mining distribution by model
    mining_by_model = ArbiusImage.objects.values('model_id').annotate(
        total_tasks=Count('id'),
        unique_miners=Count('solution_provider', distinct=True)
    ).filter(
        solution_provider__isnull=False
    ).exclude(
        solution_provider='0x0000000000000000000000000000000000000000'
    ).order_by('-total_tasks')
    
    # Calculate average tasks per miner for each model
    for model in mining_by_model:
        if model['unique_miners'] > 0:
            model['avg_tasks_per_miner'] = round(model['total_tasks'] / model['unique_miners'], 1)
        else:
            model['avg_tasks_per_miner'] = 0
    
    # Calculate mining efficiency metrics
    avg_tasks_per_miner = round(total_tasks / max(total_unique_miners, 1), 2)
    
    # Get weekly mining statistics
    one_week_ago = timezone.now() - timedelta(days=7)
    weekly_stats = ArbiusImage.objects.filter(
        solution_provider__isnull=False,
        timestamp__gte=one_week_ago
    ).exclude(
        solution_provider='0x0000000000000000000000000000000000000000'
    ).aggregate(
        tasks_this_week=Count('id'),
        unique_miners_this_week=Count('solution_provider', distinct=True),
        unique_submitters_this_week=Count('task_submitter', distinct=True)
    )
    
    # Get monthly mining statistics
    one_month_ago = timezone.now() - timedelta(days=30)
    monthly_stats = ArbiusImage.objects.filter(
        solution_provider__isnull=False,
        timestamp__gte=one_month_ago
    ).exclude(
        solution_provider='0x0000000000000000000000000000000000000000'
    ).aggregate(
        tasks_this_month=Count('id'),
        unique_miners_this_month=Count('solution_provider', distinct=True),
        unique_submitters_this_month=Count('task_submitter', distinct=True)
    )
    
    # Prepare chart data
    daily_chart_data = {
        'labels': [activity['date'].strftime('%Y-%m-%d') for activity in mining_activity_daily],
        'tasks': [activity['tasks_completed'] for activity in mining_activity_daily],
        'miners': [activity['unique_miners'] for activity in mining_activity_daily]
    }
    
    hourly_chart_data = {
        'labels': [activity['hour'].strftime('%m-%d %H:00') for activity in mining_activity_hourly],
        'tasks': [activity['tasks_completed'] for activity in mining_activity_hourly],
        'miners': [activity['unique_miners'] for activity in mining_activity_hourly]
    }
    
    context = {
        'miners_stats': miners_stats,
        'total_tasks': total_tasks,
        'total_unique_miners': total_unique_miners,
        'total_estimated_rewards': total_estimated_rewards,
        'top_miners_by_volume': top_miners_by_volume,
        'top_miners_by_consistency': top_miners_by_consistency,
        'recent_mining_activity': recent_mining_activity,
        'mining_by_model': mining_by_model,
        'avg_tasks_per_miner': avg_tasks_per_miner,
        'weekly_stats': weekly_stats,
        'monthly_stats': monthly_stats,
        'daily_chart_data': daily_chart_data,
        'hourly_chart_data': hourly_chart_data,
        'wallet_address': current_wallet_address,
        'user_profile': getattr(request, 'user_profile', None),
    }
    
    return render(request, 'gallery/mining_dashboard.html', context)
