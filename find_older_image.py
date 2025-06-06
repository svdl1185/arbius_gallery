#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.services import ArbitrumScanner

# Search for the missing CID
missing_cid = "Qmd8bNTEmAdgUvpcxcP7WLvZvXp2xosZQZ42TjAMeuwzZL"

scanner = ArbitrumScanner()
latest_block = scanner.get_latest_block()

# Search in a much wider range (last 500,000 blocks = ~12-14 hours)
search_blocks = 500000
start_block = latest_block - search_blocks

print(f"🔍 Searching for CID {missing_cid} in blocks {start_block} to {latest_block}")

transactions = scanner.get_contract_transactions(start_block, latest_block)
print(f"Found {len(transactions)} total transactions")

found = False
for tx in transactions:
    input_data = tx.get('input', '')
    
    # Check both single and batch solution transactions
    if input_data.startswith(scanner.submit_solution_single_sig) or input_data.startswith(scanner.submit_solution_batch_sig):
        cids = scanner.extract_cids_from_solution(tx)
        
        for cid, task_id in cids:
            if cid == missing_cid:
                print(f"\n🎯 FOUND CID {cid} in transaction {tx['hash']}")
                print(f"   Block: {tx['blockNumber']} ({int(tx['blockNumber'], 16)})")
                print(f"   Timestamp: {tx['timeStamp']}")
                print(f"   Task ID: {task_id}")
                print(f"   Transaction type: {'Single' if input_data.startswith(scanner.submit_solution_single_sig) else 'Batch'}")
                found = True
                
                # Check IPFS accessibility
                is_accessible, gateway = scanner.check_ipfs_accessibility(cid)
                print(f"   IPFS accessible: {is_accessible}")
                
                if is_accessible:
                    # Save it manually
                    from gallery.models import ArbiusImage
                    from datetime import datetime
                    from django.utils import timezone
                    
                    if not ArbiusImage.objects.filter(cid=cid).exists():
                        # Try to get task information
                        block_num = int(tx['blockNumber'], 16)
                        task_info = scanner.get_task_information(block_num - 100000, block_num + 1000)
                        task_data = task_info.get(task_id, {})
                        
                        image = ArbiusImage.objects.create(
                            cid=cid,
                            transaction_hash=tx['hash'],
                            task_id=task_id,
                            block_number=block_num,
                            timestamp=datetime.fromtimestamp(int(tx['timeStamp']), tz=timezone.get_current_timezone()),
                            ipfs_url=f"{scanner.ipfs_gateways[0]}{cid}",
                            image_url=f"{scanner.ipfs_gateways[0]}{cid}/out-1.png",
                            miner_address=tx['from'],
                            gas_used=int(tx['gasUsed']) if tx.get('gasUsed') else None,
                            is_accessible=is_accessible,
                            ipfs_gateway=gateway or '',
                            model_id=task_data.get('model_id'),
                            prompt=task_data.get('prompt', ''),
                            input_parameters=task_data.get('input_parameters')
                        )
                        print(f"   ✅ Saved image to database!")
                    else:
                        print(f"   ⚠️ Image already exists in database")
                break
        
        if found:
            break

if not found:
    print(f"\n❌ CID {missing_cid} not found in the searched range")
    print("This could mean:")
    print("1. The transaction is older than 500,000 blocks (~12-14 hours)")
    print("2. The CID format in the transaction is different")
    print("3. It's a batch transaction that was processed differently") 