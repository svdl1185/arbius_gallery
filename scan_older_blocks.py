#!/usr/bin/env python3
"""
Script to scan for older Arbius images starting from the oldest block currently in the database.
This script works backwards from the oldest known image to find historical images.
Now includes optimized task lookup for immediate task data retrieval.
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
    Scan for older images starting from the oldest known block with optimized task lookup.
    
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
    print(f"   🎯 Using optimized task lookup (1-3 API calls vs 100+ per image)")
    
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
                # Use the optimized scan_blocks method that includes task lookup
                new_images = scanner.scan_blocks(start_block, end_block)
                chunk_new_images = len(new_images)
                total_new_images += chunk_new_images
                
                print(f"   ✅ Found {chunk_new_images} new images in this chunk")
                
                # Show some details about new images found with task data status
                if new_images:
                    print("   📸 New images found:")
                    for img in new_images[-3:]:  # Show last 3 images
                        prompt_preview = img.prompt[:30] + "..." if img.prompt and len(img.prompt) > 30 else (img.prompt or "No prompt")
                        task_status = "✅ with prompt" if img.prompt else "⚠️ no prompt"
                        submitter_status = f" by {img.task_submitter[:10]}..." if img.task_submitter else ""
                        print(f"      • {img.cid[:12]}... - \"{prompt_preview}\" ({task_status}){submitter_status}")
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
                        
                        # In dry run, show what task lookup would find
                        if not exists and not dry_run:
                            block_number = int(tx['blockNumber'], 16) if tx['blockNumber'].startswith('0x') else int(tx['blockNumber'])
                            task_data = scanner.find_task_by_id_optimized(task_id, block_number)
                            if task_data and task_data.get('prompt'):
                                prompt_preview = task_data['prompt'][:30] + "..." if len(task_data['prompt']) > 30 else task_data['prompt']
                                print(f"         🎯 Would find prompt: \"{prompt_preview}\"")
            
            # Move to the next chunk (further back in time)
            current_block = start_block - 1
            
            # Small delay to avoid API rate limits
            import time
            time.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ Error processing chunk {chunk_num + 1}: {e}")
            continue
    
    print(f"\n🎉 Historical scan complete!")
    print(f"   📊 Found {total_new_images} new images")
    
    if not dry_run and total_new_images > 0:
        total_images = ArbiusImage.objects.count()
        oldest = ArbiusImage.objects.order_by('block_number').first()
        newest = ArbiusImage.objects.order_by('-block_number').first()
        images_with_prompts = ArbiusImage.objects.filter(prompt__isnull=False).exclude(prompt='').count()
        
        print(f"   📈 Database now has {total_images} total images")
        print(f"   📅 Image range: block {oldest.block_number} to {newest.block_number}")
        print(f"   💬 Images with prompts: {images_with_prompts} ({images_with_prompts/total_images*100:.1f}%)")
    
    return total_new_images

def main():
    parser = argparse.ArgumentParser(description='Scan for older Arbius images with optimized task lookup')
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
        
        if not args.dry_run:
            print(f"\n🎯 Efficiency: Task data retrieved with optimized lookup")
            print(f"   • 1-3 API calls per image (vs 100+ with old method)")
            print(f"   • Progressive search: 1k → 5k → 10k blocks")
            print(f"   • No separate backfill needed!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Scan interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during scan: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 