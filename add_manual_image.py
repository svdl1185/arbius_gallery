#!/usr/bin/env python
"""
Manually add the user's generated image to the database
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

def add_manual_image():
    # Data from the user's recent image generation
    cid = 'QmVxV7PdqK3V1VEA3nDiwcSK55N8Tq34fQxVFfSeLgc8hw'
    tx_hash = '0xad80415aeccc8b31f224531a78e51453fbdc1e71e790501071c400b27dbc0899'
    block_number = 344216552
    task_id = '0x0000000000000000000000000000000000000000000000000000000000000000'  # From the task transaction
    miner_address = '0x708816d665eb09e5a86ba82a774dabb550bc8af5'  # Task submitter
    
    # Check if already exists
    if ArbiusImage.objects.filter(transaction_hash=tx_hash).exists():
        print(f"❌ Image with transaction hash {tx_hash} already exists")
        return
    
    if ArbiusImage.objects.filter(cid=cid).exists():
        print(f"❌ Image with CID {cid} already exists")
        return
    
    # Create timestamp (use current time since we know it was just generated)
    timestamp = timezone.now()
    
    try:
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
        
        print(f"✅ Successfully added image to gallery!")
        print(f"   ID: {image.id}")
        print(f"   CID: {image.short_cid}")
        print(f"   Transaction: {image.short_tx_hash}")
        print(f"   Block: {image.block_number}")
        print(f"   Image URL: {image.image_url}")
        print(f"   IPFS URL: {image.ipfs_url}")
        
        # Update scan status too
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
        
        print(f"✅ Updated scan status to block {status.last_scanned_block}")
        
    except Exception as e:
        print(f"❌ Error adding image: {e}")

if __name__ == "__main__":
    add_manual_image() 