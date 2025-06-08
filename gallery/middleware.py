import json
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .models import UserProfile


class Web3AuthMiddleware(MiddlewareMixin):
    """Middleware to handle Web3 wallet authentication"""
    
    def process_request(self, request):
        """Add wallet information to request object"""
        # Get wallet address from session or header
        wallet_address = request.session.get('wallet_address') or request.META.get('HTTP_X_WALLET_ADDRESS')
        
        if wallet_address:
            # Normalize address to lowercase for consistency
            wallet_address = wallet_address.lower()
            request.wallet_address = wallet_address
            
            # Try to get or create user profile
            try:
                profile, created = UserProfile.objects.get_or_create(
                    wallet_address=wallet_address,
                    defaults={'display_name': f"User {wallet_address[:8]}..."}
                )
                request.user_profile = profile
                request.is_authenticated = True
            except Exception:
                request.user_profile = None
                request.is_authenticated = False
        else:
            request.wallet_address = None
            request.user_profile = None
            request.is_authenticated = False
        
        return None


def require_wallet_auth(view_func):
    """Decorator to require wallet authentication for views"""
    def wrapper(request, *args, **kwargs):
        if not getattr(request, 'is_authenticated', False):
            return JsonResponse({'error': 'Wallet authentication required'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper 