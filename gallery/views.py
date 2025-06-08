from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Q, Count, Case, When, IntegerField
from django.db.models.functions import Length
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import ArbiusImage, UserProfile, ImageUpvote, ImageComment
from .middleware import require_wallet_auth


def get_base_queryset():
    """Get the base queryset for images with optimizations and filtering"""
    
    # Define known valid image generation models 
    VALID_IMAGE_MODELS = [
        '0xa473c70e9d7c872ac948d20546bc79db55fa64ca325a4b229aaffddb7f86aae0',  # Main stable diffusion model
        '0x89c39001e3b23d2095a1d59cb8c02c3eeb74d83a',  # Another valid model
        '0x6cb3eed9fe3f32da1',  # Valid model
        # Add more known valid models here as they are identified
    ]
    
    queryset = ArbiusImage.objects.select_related().prefetch_related('upvotes', 'comments').filter(
        is_accessible=True  # Only show accessible images
    )
    
    # For now, only show images from known valid models (safest approach)
    # This prevents showing any test/text content
    queryset = queryset.filter(model_id__in=VALID_IMAGE_MODELS)
    
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


def get_available_models_with_categories():
    """Get available models organized by categories with comprehensive filtering"""
    
    # Define known valid image generation models (whitelist approach)
    VALID_IMAGE_MODELS = [
        '0xa473c70e9d7c872ac948d20546bc79db55fa64ca325a4b229aaffddb7f86aae0',  # Main stable diffusion model
        '0x89c39001e3b23d2095a1d59cb8c02c3eeb74d83a',  # Another valid model
        '0x6cb3eed9fe3f32da1',  # Valid model
        # Add more known valid models here as they are identified
    ]
    
    # Get all model stats
    all_models = ArbiusImage.objects.values('model_id').annotate(
        count=Count('id')
    ).filter(
        model_id__isnull=False
    ).exclude(
        model_id=''
    ).order_by('-count')
    
    # Apply aggressive filtering to remove test/text models
    filtered_models = []
    for model in all_models:
        model_id = model['model_id']
        
        # Skip if model_id is too short (invalid)
        if len(model_id) < 10:
            continue
            
        # Skip all-zero or mostly-zero models (test models)
        if model_id.replace('0x', '').replace('0', '').replace('.', '') == '':
            continue
            
        # Skip models that are all zeros with trailing characters
        hex_part = model_id.replace('0x', '')
        if len(hex_part.replace('0', '')) <= 3:  # Mostly zeros
            continue
            
        # For now, use whitelist approach - only include known good models
        # This is safer than trying to detect all bad patterns
        if model_id in VALID_IMAGE_MODELS:
            filtered_models.append(model)
        # Also include models with very high usage counts (likely valid)
        elif model['count'] >= 1000:  # High usage suggests it's a real model
            # But still exclude obvious test patterns
            hex_part = model_id.replace('0x', '').lower()
            if not (hex_part.startswith('000000') or hex_part.endswith('000000')):
                filtered_models.append(model)
    
    # Define custom model categories for better UX
    MODEL_CATEGORIES = {
        'Popular Models': [
            '0xa473c70e9d7c872ac948d20546bc79db55fa64ca325a4b229aaffddb7f86aae0',
        ],
        'Alternative Models': [
            '0x89c39001e3b23d209092e3c6b8c02c3eeb74d83a',
            '0x6cb3eed9fe3f32da1',
        ]
    }
    
    # Separate models into categories
    categorized = {'Popular': [], 'Alternative': [], 'Other': []}
    popular_model_ids = MODEL_CATEGORIES.get('Popular Models', [])
    alternative_model_ids = MODEL_CATEGORIES.get('Alternative Models', [])
    
    for model in filtered_models:
        model_info = {
            'model_id': model['model_id'],
            'count': model['count'],
            'short_name': f"{model['model_id'][:8]}...{model['model_id'][-8:]}" if len(model['model_id']) > 16 else model['model_id']
        }
        
        if model['model_id'] in popular_model_ids:
            categorized['Popular'].append(model_info)
        elif model['model_id'] in alternative_model_ids:
            categorized['Alternative'].append(model_info)
        else:
            categorized['Other'].append(model_info)
    
    # Sort each category by count
    for category in categorized:
        categorized[category] = sorted(categorized[category], key=lambda x: x['count'], reverse=True)
    
    # Flatten for backward compatibility, prioritizing popular models
    flattened = categorized['Popular'] + categorized['Alternative'] + categorized['Other']
    
    return flattened, categorized


def index(request):
    """Main gallery view with Web3 integration"""
    # Get filter parameters
    search_query = request.GET.get('q', '').strip()
    selected_task_submitter = request.GET.get('task_submitter', '').strip()
    selected_model = request.GET.get('model', '').strip()
    sort_by = request.GET.get('sort', 'upvotes')  # Default to most upvoted
    
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
        'wallet_address': getattr(request, 'wallet_address', None),
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
        'wallet_address': getattr(request, 'wallet_address', None),
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
    total_images = ArbiusImage.objects.count()
    total_accessible = ArbiusImage.objects.filter(is_accessible=True).count()
    
    # Recent activity
    last_24h = timezone.now() - timedelta(hours=24)
    recent_images = ArbiusImage.objects.filter(discovered_at__gte=last_24h).count()
    
    # Top creators
    top_creators = ArbiusImage.objects.filter(
        task_submitter__isnull=False
    ).values('task_submitter').annotate(
        image_count=Count('id')
    ).order_by('-image_count')[:10]
    
    # Model statistics
    model_stats = ArbiusImage.objects.filter(
        model_id__isnull=False
    ).exclude(model_id='').values('model_id').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Social statistics
    total_upvotes = ImageUpvote.objects.count()
    total_comments = ImageComment.objects.count()
    total_profiles = UserProfile.objects.count()
    
    context = {
        'total_images': total_images,
        'total_accessible': total_accessible,
        'recent_images': recent_images,
        'top_creators': top_creators,
        'model_stats': model_stats,
        'total_upvotes': total_upvotes,
        'total_comments': total_comments,
        'total_profiles': total_profiles,
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
            defaults={'display_name': f"User {wallet_address[:8]}..."}
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


@require_wallet_auth
def user_profile(request, wallet_address):
    """Display user profile page"""
    profile = get_object_or_404(UserProfile, wallet_address__iexact=wallet_address)
    
    # Get user's images - simplified for now
    user_images = get_base_queryset().filter(
        task_submitter__iexact=wallet_address
    ).order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(user_images, 24)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Check if viewing own profile
    is_own_profile = (hasattr(request, 'wallet_address') and 
                     request.wallet_address and 
                     request.wallet_address.lower() == wallet_address.lower())
    
    context = {
        'profile': profile,
        'page_obj': page_obj,
        'is_own_profile': is_own_profile,
        'wallet_address': getattr(request, 'wallet_address', None),
        'user_profile': getattr(request, 'user_profile', None),
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
