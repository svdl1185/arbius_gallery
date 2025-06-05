#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

import requests
from gallery.services import ArbitrumScanner

def find_active_blocks():
    print("🔍 FINDING ACTIVE ARBIUS BLOCKS")
    print("This will scan wider ranges to find where the real activity is...")
    
    scanner = ArbitrumScanner()
    latest_block = scanner.get_latest_block()
    
    print(f"Latest block: {latest_block}")
    print(f"Engine contract: {scanner.engine_address}")
    print(f"Looking for submitSolution signature: {scanner.submit_solution_sig}")
    
    # Test progressively wider ranges
    test_ranges = [
        (1000, "last 1k blocks"),
        (10000, "last 10k blocks"), 
        (50000, "last 50k blocks"),
        (100000, "last 100k blocks"),
        (200000, "last 200k blocks - ~1 month"),
        (500000, "last 500k blocks - ~2.5 months"),
        (1000000, "last 1M blocks - ~5 months")
    ]
    
    for blocks_back, description in test_ranges:
        start_block = latest_block - blocks_back
        end_block = latest_block
        
        print(f"\n🔍 Testing {description} (blocks {start_block} to {end_block})...")
        
        try:
            # Test in chunks of 10k blocks to avoid API limits
            chunk_size = 10000
            total_transactions = 0
            solution_transactions = 0
            
            for chunk_start in range(start_block, end_block, chunk_size):
                chunk_end = min(chunk_start + chunk_size - 1, end_block)
                
                transactions = scanner.get_contract_transactions(chunk_start, chunk_end)
                total_transactions += len(transactions)
                
                if transactions:
                    solutions = [tx for tx in transactions if tx.get('input', '').startswith(scanner.submit_solution_sig)]
                    solution_transactions += len(solutions)
                    
                    if solutions:
                        print(f"  📍 FOUND ACTIVITY in chunk {chunk_start}-{chunk_end}!")
                        print(f"     Total transactions: {len(transactions)}")
                        print(f"     Solution transactions: {len(solutions)}")
                        print(f"     First solution: {solutions[0]['hash']}")
                        
                        # Test CID extraction on first solution
                        test_tx = solutions[0]
                        print(f"     Testing CID extraction...")
                        cids = scanner.extract_cids_from_solution(test_tx)
                        print(f"     CIDs found: {len(cids)}")
                        if cids:
                            print(f"     First CID: {cids[0]}")
                            print(f"  🎉 SUCCESS! Found active block range with images!")
                            return chunk_start, chunk_end
                        
            print(f"  Total across range: {total_transactions} transactions, {solution_transactions} solutions")
            
            if solution_transactions > 0:
                print(f"  ✅ Found {solution_transactions} solution transactions in {description}!")
                return start_block, end_block
                
        except Exception as e:
            print(f"  ❌ Error testing {description}: {e}")
            continue
    
    print("\n❌ No solution transactions found in any tested range!")
    print("This suggests either:")
    print("1. The engine contract address is incorrect")
    print("2. Arbius activity is older than 5 months")
    print("3. There's an API or configuration issue")
    
    # Test with known working transaction to verify our method
    print(f"\n🧪 Testing with known working transaction...")
    known_tx_hash = "0x929e8b0e7df63e3033458270eba4a7ae81d9cdada3b740e2a2f7d6eff4e668ed"
    
    try:
        url = f"{scanner.base_url}?module=proxy&action=eth_getTransactionByHash&txhash={known_tx_hash}&apikey={scanner.api_key}"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        if data.get('result'):
            tx = data['result']
            block_num = int(tx['blockNumber'], 16)
            print(f"Known working tx is in block: {block_num}")
            print(f"That's {latest_block - block_num} blocks ago")
            
            # Test around that block
            test_start = block_num - 1000
            test_end = block_num + 1000
            print(f"Testing around known working block ({test_start} to {test_end})...")
            
            transactions = scanner.get_contract_transactions(test_start, test_end)
            solutions = [tx for tx in transactions if tx.get('input', '').startswith(scanner.submit_solution_sig)]
            
            print(f"Found {len(transactions)} transactions, {len(solutions)} solutions around known block")
            
            if solutions:
                print("✅ Method works! The issue is we're looking in the wrong time range.")
                return test_start, test_end
            
    except Exception as e:
        print(f"Error testing known transaction: {e}")
    
    return None, None

if __name__ == "__main__":
    start, end = find_active_blocks()
    if start and end:
        print(f"\n🎯 FOUND ACTIVE RANGE: blocks {start} to {end}")
        print(f"📅 You should scan this range to find hundreds of images!")
    else:
        print(f"\n❓ Need to investigate further...") 