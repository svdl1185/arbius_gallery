"""
Cryptographic utilities for secure wallet authentication
"""
import hashlib
import time
from eth_account.messages import encode_defunct
from eth_account import Account
from django.core.cache import cache
from django.conf import settings


def generate_auth_nonce(wallet_address):
    """Generate a secure nonce for wallet authentication"""
    timestamp = int(time.time())
    nonce = hashlib.sha256(f"{wallet_address.lower()}{timestamp}{settings.SECRET_KEY}".encode()).hexdigest()[:16]
    
    # Store nonce in cache with 10-minute expiration
    cache_key = f"auth_nonce_{wallet_address.lower()}"
    cache.set(cache_key, {
        'nonce': nonce,
        'timestamp': timestamp
    }, timeout=600)  # 10 minutes
    
    return nonce, timestamp


def verify_wallet_signature(wallet_address, signature, message, max_age_seconds=600):
    """
    Verify that a signature was created by the owner of the wallet address.
    
    Args:
        wallet_address: The Ethereum wallet address
        signature: The signature to verify
        message: The original message that was signed
        max_age_seconds: Maximum age of the signature in seconds (default 10 minutes)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Normalize wallet address
        wallet_address = wallet_address.lower()
        
        # Parse message to extract nonce and timestamp
        lines = message.split('\n')
        nonce_line = next((line for line in lines if line.startswith('Nonce:')), None)
        timestamp_line = next((line for line in lines if line.startswith('Timestamp:')), None)
        
        if not nonce_line or not timestamp_line:
            return False, "Invalid message format - missing nonce or timestamp"
        
        try:
            nonce = nonce_line.split('Nonce: ')[1].strip()
            timestamp = int(timestamp_line.split('Timestamp: ')[1].strip())
        except (IndexError, ValueError):
            return False, "Invalid message format - malformed nonce or timestamp"
        
        # Check if signature is too old
        current_time = int(time.time())
        if current_time - timestamp > max_age_seconds:
            return False, "Signature expired - please reconnect your wallet"
        
        # Verify nonce against stored value
        cache_key = f"auth_nonce_{wallet_address}"
        stored_data = cache.get(cache_key)
        
        if not stored_data:
            return False, "Invalid nonce - please refresh and try again"
        
        if stored_data['nonce'] != nonce or stored_data['timestamp'] != timestamp:
            return False, "Invalid nonce - authentication failed"
        
        # Encode message for signature verification
        message_encoded = encode_defunct(text=message)
        
        # Verify signature
        recovered_address = Account.recover_message(message_encoded, signature=signature)
        
        if recovered_address.lower() != wallet_address:
            return False, "Signature verification failed - invalid signature"
        
        # Clear the nonce to prevent replay attacks
        cache.delete(cache_key)
        
        return True, "Signature verified successfully"
        
    except Exception as e:
        return False, f"Signature verification error: {str(e)}"


def create_auth_message(wallet_address, nonce, timestamp):
    """Create a standardized authentication message"""
    return f"""Welcome to Arbius Gallery!

Connect your wallet to interact with images and manage your profile.

This signature proves you own this wallet and authorizes access to your account.

Wallet: {wallet_address}
Nonce: {nonce}  
Timestamp: {timestamp}

This signature is valid for 10 minutes only.""" 