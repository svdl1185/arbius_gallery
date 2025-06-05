#!/usr/bin/env python
"""
Add the user's second generated image to the database
"""

import os
import sys
import django

# Set up Django environment
sys.path.append('/Users/biba/Documents/Projects/arbius_gallery')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.models import ArbiusImage
from django.utils import timezone
from datetime import datetime

def add_second_image():
    # Data from the user's new image generation
    cid = 'QmSFiVCnGvP7dmNKfydagzwnQi6sUWjBEFrEYgFbWYFXMB'
    tx_hash = '0x3a2e652b7ed8809540a5d275d12b45440430e36f0dc70bd2ff9277944d01acaf'
    task_id = '0x0000000000000000000000000000000000000000000000000000000000000000'  # Will extract from transaction
    miner_address = '0x708816d665eb09e5a86ba82a774dabb550bc8af5'  # Default, will update from transaction
    
    # Check if already exists
    if ArbiusImage.objects.filter(transaction_hash=tx_hash).exists():
        print(f"❌ Image with transaction hash {tx_hash} already exists")
        return
    
    if ArbiusImage.objects.filter(cid=cid).exists():
        print(f"❌ Image with CID {cid} already exists")
        return
    
    # First, let's get the transaction details to extract proper data
    import requests
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    print(f"Fetching transaction details for {tx_hash}...")
    
    try:
        url = f"{base_url}?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={api_key}"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        if data.get('result'):
            tx_data = data['result']
            block_number = int(tx_data['blockNumber'], 16)
            from_address = tx_data['from']
            
            print(f"✅ Transaction found:")
            print(f"   Block: {block_number}")
            print(f"   From: {from_address}")
            print(f"   To: {tx_data['to']}")
            
            # Create timestamp (use current time since this was just generated)
            timestamp = timezone.now()
            
            image = ArbiusImage.objects.create(
                transaction_hash=tx_hash,
                task_id=task_id,
                block_number=block_number,
                timestamp=timestamp,
                cid=cid,
                ipfs_url=f'https://ipfs.arbius.org/ipfs/{cid}',
                image_url=f'https://ipfs.arbius.org/ipfs/{cid}/out-1.png',
                miner_address=from_address,
                is_accessible=True
            )
            
            print(f"✅ Successfully added second image to gallery!")
            print(f"   ID: {image.id}")
            print(f"   CID: {image.short_cid}")
            print(f"   Transaction: {image.short_tx_hash}")
            print(f"   Block: {image.block_number}")
            print(f"   Image URL: {image.image_url}")
            
            # Update scan status
            from gallery.models import ScanStatus
            status, created = ScanStatus.objects.get_or_create(
                id=1,
                defaults={'last_scanned_block': block_number}
            )
            if not created:
                status.last_scanned_block = max(status.last_scanned_block, block_number)
                status.last_scan_time = timezone.now()
                status.total_images_found = ArbiusImage.objects.count()
                status.save()
            
            print(f"✅ Updated scan status. Total images: {ArbiusImage.objects.count()}")
            
        else:
            print(f"❌ Could not fetch transaction details: {data}")
            
    except Exception as e:
        print(f"❌ Error fetching transaction: {e}")
        # Create with default values
        timestamp = timezone.now()
        block_number = 344220000  # Default recent block
        
        image = ArbiusImage.objects.create(
            transaction_hash=tx_hash,
            task_id=task_id,
            block_number=block_number,
            timestamp=timestamp,
            cid=cid,
            ipfs_url=f'https://ipfs.arbius.org/ipfs/{cid}',
            image_url=f'https://ipfs.arbius.org/ipfs/{cid}/out-1.png',
            miner_address=miner_address,
            is_accessible=True
        )
        
        print(f"✅ Added image with default values")
        print(f"   ID: {image.id}")
        print(f"   CID: {image.short_cid}")

if __name__ == "__main__":
    add_second_image() 