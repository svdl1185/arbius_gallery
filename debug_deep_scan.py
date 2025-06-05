#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.services import ArbitrumScanner
from gallery.models import ScanStatus

def debug_deep_scan():
    print("🔍 DEEP DEBUGGING: Why aren't we finding hundreds of images?")
    
    scanner = ArbitrumScanner()
    
    # Get current state
    latest_block = scanner.get_latest_block()
    print(f"Latest block: {latest_block}")
    
    # Calculate what block range we should scan for last few weeks
    blocks_per_day = 7200  # Arbitrum: ~1 block per 12 seconds  
    blocks_3_weeks = 3 * 7 * blocks_per_day  # ~151,200 blocks
    blocks_6_weeks = 6 * 7 * blocks_per_day  # ~302,400 blocks
    
    start_block_3w = latest_block - blocks_3_weeks
    start_block_6w = latest_block - blocks_6_weeks
    
    print(f"3 weeks ago would be block: {start_block_3w}")
    print(f"6 weeks ago would be block: {start_block_6w}")
    print(f"Current block range for 3 weeks: {start_block_3w} to {latest_block}")
    
    # Test smaller chunks to see where the issue is
    test_ranges = [
        ("Last 1000 blocks", latest_block - 1000, latest_block),
        ("10k blocks ago", latest_block - 10000, latest_block - 9000), 
        ("50k blocks ago", latest_block - 50000, latest_block - 49000),
        ("100k blocks ago", latest_block - 100000, latest_block - 99000),
    ]
    
    for name, start, end in test_ranges:
        print(f"\n🔍 Testing {name} (blocks {start} to {end})...")
        
        try:
            transactions = scanner.get_contract_transactions(start, end)
            print(f"  Found {len(transactions)} total transactions")
            
            if transactions:
                # Count submitSolution transactions
                solution_txs = [tx for tx in transactions if tx.get('input', '').startswith(scanner.submit_solution_sig)]
                print(f"  Found {len(solution_txs)} submitSolution transactions")
                
                if solution_txs:
                    # Test CID extraction on first few
                    for i, tx in enumerate(solution_txs[:3]):
                        print(f"    Testing solution tx {i+1}: {tx['hash']}")
                        try:
                            cids = scanner.extract_cids_from_solution(tx)
                            print(f"      Raw CIDs found: {len(cids)}")
                            for j, cid in enumerate(cids[:2]):  # Show first 2
                                print(f"        CID {j+1}: {cid}")
                        except Exception as e:
                            print(f"      CID extraction error: {e}")
                
                # Show function signature breakdown
                sigs = {}
                for tx in transactions:
                    sig = tx.get('input', '')[:10]
                    sigs[sig] = sigs.get(sig, 0) + 1
                
                print(f"  Function signatures:")
                for sig, count in sorted(sigs.items(), key=lambda x: x[1], reverse=True):
                    if count > 0:
                        status = "✅" if sig == scanner.submit_solution_sig else "  "
                        print(f"    {status} {sig}: {count}")
                        
                if len(solution_txs) > 0:
                    print(f"  ✅ FOUND SOLUTION TRANSACTIONS IN {name}!")
                    return True
                    
        except Exception as e:
            print(f"  ❌ Error testing {name}: {e}")
    
    print(f"\n🤔 No solution transactions found in recent ranges...")
    print(f"Let me check the engine contract address: {scanner.engine_address}")
    
    # Test with a known working transaction hash to verify our method
    print(f"\n🧪 Testing with a known working transaction...")
    known_tx_hashes = [
        "0x929e8b0e7df63e3033458270eba4a7ae81d9cdada3b740e2a2f7d6eff4e668ed",
        "0xc4cfff13512cab8286d3ac27efa7d42860d6fabc103de6acb1e4d5777faee2fa"
    ]
    
    for tx_hash in known_tx_hashes:
        print(f"Testing known transaction: {tx_hash}")
        try:
            # Get transaction details
            url = f"{scanner.base_url}?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={scanner.api_key}"
            import requests
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if data.get('result'):
                tx = data['result']
                print(f"  Block: {int(tx['blockNumber'], 16)}")
                print(f"  Function sig: {tx['input'][:10]}")
                
                if tx['input'].startswith(scanner.submit_solution_sig):
                    cids = scanner.extract_cids_from_solution(tx)
                    print(f"  CIDs extracted: {len(cids)}")
                    if len(cids) > 0:
                        print(f"  First CID: {cids[0]}")
                        print("  ✅ CID extraction method is working!")
                        
        except Exception as e:
            print(f"  Error testing known tx: {e}")
    
    return False

if __name__ == "__main__":
    found_solutions = debug_deep_scan()
    if not found_solutions:
        print("\n❌ PROBLEM: Not finding submitSolution transactions in recent blocks")
        print("This suggests either:")
        print("1. The engine contract address is wrong")  
        print("2. Solution transactions are in different block ranges")
        print("3. There's an issue with the API query")
    else:
        print("\n✅ Found solution transactions! The method works.") 