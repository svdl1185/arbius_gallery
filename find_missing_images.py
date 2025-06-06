#!/usr/bin/env python3
import os
import django
import requests
import re
import base58

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.services import ArbitrumScanner

def search_for_cids_in_transactions(scanner, target_cids, start_block, end_block):
    """Search for specific CIDs in transaction data"""
    print(f"🔍 Searching for CIDs in blocks {start_block} to {end_block}")
    
    transactions = scanner.get_contract_transactions(start_block, end_block)
    print(f"Found {len(transactions)} total transactions")
    
    for tx in transactions:
        input_data = tx.get('input', '')
        
        # Check both single and batch solution transactions
        if input_data.startswith(scanner.submit_solution_single_sig) or input_data.startswith(scanner.submit_solution_batch_sig):
            # Extract CIDs from this transaction
            cids = scanner.extract_cids_from_solution(tx)
            
            for cid, task_id in cids:
                if cid in target_cids:
                    print(f"🎯 FOUND CID {cid} in transaction {tx['hash']}")
                    print(f"   Block: {tx['blockNumber']}")
                    print(f"   Timestamp: {tx['timeStamp']}")
                    print(f"   Task ID: {task_id}")
                    print(f"   Transaction type: {'Single' if input_data.startswith(scanner.submit_solution_single_sig) else 'Batch'}")
                    
                    # Try to get task information for this task ID
                    if task_id:
                        task_info = scanner.get_task_information(int(tx['blockNumber'], 16) - 1000, int(tx['blockNumber'], 16))
                        task_data = task_info.get(task_id, {})
                        if task_data:
                            print(f"   Prompt: {task_data.get('prompt', 'No prompt found')}")
                        else:
                            print(f"   No task data found for task {task_id}")
                    
                    return True, tx, cid, task_id
    
    return False, None, None, None

# Your target CIDs
target_cids = [
    "QmWTk8qAv3qTYqcbe9GLB2V4M7szjFJ79h7ptxVhXxkMhd",  # Just now
    "QmeWKQKQhXmHdwE8RdgjMEvSKXUWzMS9HnmgX5Bv5jpKbc",  # 1 hour ago
    "Qmd8bNTEmAdgUvpcxcP7WLvZvXp2xosZQZ42TjAMeuwzZL"   # 8 hours ago
]

scanner = ArbitrumScanner()
latest_block = scanner.get_latest_block()
print(f"Latest block: {latest_block}")

# Search in recent blocks (last 300,000 blocks should cover about 6-8 hours)
search_blocks = 300000
start_block = latest_block - search_blocks

print(f"\nSearching for your CIDs:")
for cid in target_cids:
    print(f"  - {cid}")

found, tx, found_cid, task_id = search_for_cids_in_transactions(scanner, target_cids, start_block, latest_block)

if found:
    print(f"\n✅ Found at least one CID! Now let's see why it wasn't processed...")
    
    # Check if this transaction type is being filtered out
    input_data = tx.get('input', '')
    if input_data.startswith(scanner.submit_solution_batch_sig):
        print("❌ This is a BATCH solution - these are currently being skipped!")
        print("The scanning logic is set to skip bulk submissions, but your image might be in one.")
    elif input_data.startswith(scanner.submit_solution_single_sig):
        print("✅ This is a SINGLE solution - should be processed")
        
        # Check if task information is missing
        task_info = scanner.get_task_information(int(tx['blockNumber'], 16) - 1000, int(tx['blockNumber'], 16))
        task_data = task_info.get(task_id, {})
        if not task_data or not task_data.get('prompt'):
            print("❌ No prompt found - this is why it's being skipped!")
            print("The scanning logic requires a prompt to save an image.")
        else:
            print("✅ Prompt found - this should have been saved")
else:
    print("\n❌ None of your CIDs found in recent transactions")
    print("This might mean:")
    print("1. The transactions are in blocks older than we searched")
    print("2. The CIDs are in a different format in the transaction data")
    print("3. The transactions haven't been mined yet") 