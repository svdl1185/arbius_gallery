#!/usr/bin/env python3
"""
Script to scan for older Arbius images starting from the oldest block currently in the database.
This script works backwards from the oldest known image to find historical images.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.services import ArbitrumScanner
from gallery.models import ArbiusImage, ScanStatus
from datetime import datetime
from django.utils import timezone
import argparse
import sys

def scan_older_blocks(start_from_block=None, chunk_size=5000, max_chunks=10, dry_run=False):
    """
    Scan for older images starting from the oldest known block.
    
    Args:
        start_from_block: Block to start scanning backwards from (default: oldest in DB)
        chunk_size: Number of blocks to scan in each chunk
        max_chunks: Maximum number of chunks to process in this run
        dry_run: If True, only report what would be found without saving
    """
    scanner = ArbitrumScanner()
    
    # Get the oldest block currently in database if not specified
    if start_from_block is None:
        oldest_image = ArbiusImage.objects.order_by('block_number').first()
        if not oldest_image:
            print("❌ No images found in database. Run the regular scanner first.")
            return 0
        start_from_block = oldest_image.block_number
        print(f"📊 Oldest image in database is from block {start_from_block}")
    
    print(f"🔍 Starting historical scan backwards from block {start_from_block}")
    print(f"   Chunk size: {chunk_size} blocks")
    print(f"   Max chunks: {max_chunks}")
    print(f"   Dry run: {dry_run}")
    
    total_new_images = 0
    current_block = start_from_block
    
    for chunk_num in range(max_chunks):
        # Calculate the range for this chunk (scanning backwards)
        end_block = current_block - 1  # Start from one block before our current position
        start_block = max(0, end_block - chunk_size + 1)  # Don't go below block 0
        
        if start_block >= end_block:
            print(f"✅ Reached the beginning of the blockchain (block 0)")
            break
        
        print(f"\n📦 Chunk {chunk_num + 1}/{max_chunks}: Scanning blocks {start_block} to {end_block}")
        
        try:
            # Check if we already have images in this range
            existing_images_in_range = ArbiusImage.objects.filter(
                block_number__gte=start_block,
                block_number__lte=end_block
            ).count()
            
            print(f"   Found {existing_images_in_range} existing images in this range")
            
            if not dry_run:
                # Scan this chunk
                new_images = scanner.scan_blocks(start_block, end_block)
                chunk_new_images = len(new_images)
                total_new_images += chunk_new_images
                
                print(f"   ✅ Found {chunk_new_images} new images in this chunk")
                
                # Show some details about new images found
                if new_images:
                    print("   📸 New images found:")
                    for img in new_images[-3:]:  # Show last 3 images
                        prompt_preview = img.prompt[:30] + "..." if img.prompt and len(img.prompt) > 30 else (img.prompt or "No prompt")
                        print(f"      • {img.cid[:12]}... - \"{prompt_preview}\"")
            else:
                # Dry run - just get transactions to see what's there
                transactions = scanner.get_contract_transactions(start_block, end_block)
                single_solutions = [tx for tx in transactions if tx.get('input', '').startswith(scanner.submit_solution_single_sig)]
                print(f"   📊 Would process {len(single_solutions)} single solution transactions")
                
                # Sample a few to show what we'd find
                for i, tx in enumerate(single_solutions[:3]):
                    cids = scanner.extract_cids_from_single_solution(tx)
                    if cids:
                        cid, task_id = cids[0]
                        # Check if we already have this
                        exists = ArbiusImage.objects.filter(cid=cid).exists()
                        status = "EXISTS" if exists else "NEW"
                        print(f"      • Transaction {tx['hash'][:12]}... -> CID {cid[:12]}... ({status})")
            
            # Move to the next chunk (further back in time)
            current_block = start_block - 1
            
            # If this chunk had no activity, we can skip forward more aggressively
            if not dry_run and chunk_new_images == 0 and existing_images_in_range == 0:
                print(f"   ⏭️  No activity in this range, jumping back {chunk_size * 2} blocks")
                current_block = start_block - chunk_size * 2
            
        except Exception as e:
            print(f"   ❌ Error scanning chunk {chunk_num + 1}: {e}")
            continue
    
    print(f"\n🎉 Historical scan complete!")
    print(f"   Scanned up to {max_chunks} chunks backwards from block {start_from_block}")
    if not dry_run:
        print(f"   Found {total_new_images} new historical images")
    else:
        print(f"   This was a dry run - no images were saved")
    
    return total_new_images

def main():
    parser = argparse.ArgumentParser(description='Scan for older Arbius images')
    parser.add_argument('--start-block', type=int, help='Block to start scanning backwards from (default: oldest in DB)')
    parser.add_argument('--chunk-size', type=int, default=5000, help='Number of blocks per chunk (default: 5000)')
    parser.add_argument('--max-chunks', type=int, default=10, help='Maximum chunks to process (default: 10)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be found without saving')
    parser.add_argument('--production-start', action='store_true', help='Start from block 344402436 (oldest known in production)')
    
    args = parser.parse_args()
    
    start_block = args.start_block
    if args.production_start:
        start_block = 344402436
        print("🚀 Using production database oldest block: 344402436")
    
    try:
        new_images = scan_older_blocks(
            start_from_block=start_block,
            chunk_size=args.chunk_size,
            max_chunks=args.max_chunks,
            dry_run=args.dry_run
        )
        
        if not args.dry_run and new_images > 0:
            print(f"\n📈 Database now has {ArbiusImage.objects.count()} total images")
            oldest = ArbiusImage.objects.order_by('block_number').first()
            newest = ArbiusImage.objects.order_by('-block_number').first()
            print(f"📅 Image range: block {oldest.block_number} to {newest.block_number}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Scan interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during scan: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 