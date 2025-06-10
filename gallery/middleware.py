import json
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .models import UserProfile


def get_display_name_for_wallet(wallet_address):
    """Get appropriate display name for a wallet address"""
    if wallet_address.lower() == '0x708816d665eb09e5a86ba82a774dabb550bc8af5':
        return "Arbius Telegram Bot"
    else:
        return f"User {wallet_address[:8]}..."


class Web3AuthMiddleware(MiddlewareMixin):
    """Middleware to handle Web3 wallet authentication"""
    
    def process_request(self, request):
        """Add wallet information to request object"""
        # Only get wallet address from secure session, not from headers
        wallet_address = request.session.get('wallet_address')
        
        if wallet_address:
            # Normalize address to lowercase for consistency
            wallet_address = wallet_address.lower()
            request.wallet_address = wallet_address
            
            # Try to get user profile
            try:
                profile = UserProfile.objects.get(wallet_address=wallet_address)
                request.user_profile = profile
                request.is_authenticated = True
            except UserProfile.DoesNotExist:
                # Create profile if wallet has authenticated but profile doesn't exist
                profile = UserProfile.objects.create(
                    wallet_address=wallet_address,
                    display_name=get_display_name_for_wallet(wallet_address)
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