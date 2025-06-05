#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

import requests
import base58
from gallery.services import ArbitrumScanner

def test_cid_extraction():
    print("🧪 TESTING CID EXTRACTION ON RECENT TRANSACTIONS")
    
    scanner = ArbitrumScanner()
    api_key = scanner.api_key
    base_url = scanner.base_url
    
    # Get a recent submitSolution transaction
    latest_block = scanner.get_latest_block()
    start_block = latest_block - 5000  # Last 5000 blocks
    
    transactions = scanner.get_contract_transactions(start_block, latest_block)
    solution_txs = [tx for tx in transactions if tx.get('input', '').startswith(scanner.submit_solution_sig)]
    
    print(f"Found {len(solution_txs)} recent submitSolution transactions")
    
    if not solution_txs:
        print("❌ No recent solution transactions found")
        return
    
    # Test on first few transactions
    for i, tx in enumerate(solution_txs[:3]):
        print(f"\n🔍 Testing transaction {i+1}: {tx['hash']}")
        print(f"   Block: {tx['blockNumber']}")
        print(f"   Input length: {len(tx['input'])} chars")
        
        try:
            # Get full transaction data
            url = f"{base_url}?module=proxy&action=eth_getTransactionByHash&txhash={tx['hash']}&apikey={api_key}"
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if data.get('result'):
                full_tx = data['result']
                input_data = full_tx['input']
                
                print(f"   Full input length: {len(input_data)} chars")
                print(f"   Function sig: {input_data[:10]}")
                
                # Manual multihash search
                hex_data = input_data[2:]  # Remove 0x
                all_bytes = bytes.fromhex(hex_data)
                
                # Look for SHA2-256 multihash pattern (0x1220 + 32 bytes)
                pattern = bytes.fromhex('1220')
                
                positions = []
                pos = 0
                while True:
                    pos = all_bytes.find(pattern, pos)
                    if pos == -1:
                        break
                    if pos + 34 <= len(all_bytes):
                        positions.append(pos)
                    pos += 1
                
                print(f"   Found {len(positions)} multihash patterns")
                
                # Test first few positions
                for j, pos in enumerate(positions[:5]):
                    multihash = all_bytes[pos:pos+34]
                    try:
                        cid_candidate = base58.b58encode(multihash).decode()
                        print(f"     Position {pos}: {cid_candidate}")
                        
                        if cid_candidate.startswith('Qm') and len(cid_candidate) == 46:
                            print(f"     ✅ Valid CID format: {cid_candidate}")
                            
                            # Quick IPFS test
                            test_url = f"https://ipfs.arbius.org/ipfs/{cid_candidate}/out-1.png"
                            try:
                                ipfs_response = requests.head(test_url, timeout=3)
                                if ipfs_response.status_code == 200:
                                    print(f"     🎉 WORKING CID FOUND: {cid_candidate}")
                                else:
                                    print(f"     ❌ CID not accessible (status: {ipfs_response.status_code})")
                            except Exception as e:
                                print(f"     ❌ IPFS check failed: {e}")
                        else:
                            print(f"     ❌ Invalid CID format")
                            
                    except Exception as e:
                        print(f"     ❌ Base58 decode error: {e}")
                
                # Try our scanner method for comparison
                print(f"\n   🤖 Scanner method result:")
                scanner_cids = scanner.extract_cids_from_solution(full_tx)
                print(f"   Scanner found: {len(scanner_cids)} CIDs")
                for cid in scanner_cids:
                    print(f"     {cid}")
                    
        except Exception as e:
            print(f"   ❌ Error processing transaction: {e}")

    # Also test known working transaction
    print(f"\n🧪 Testing known working transaction...")
    known_tx = "0x929e8b0e7df63e3033458270eba4a7ae81d9cdada3b740e2a2f7d6eff4e668ed"
    
    try:
        url = f"{base_url}?module=proxy&action=eth_getTransactionByHash&txhash={known_tx}&apikey={api_key}"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        if data.get('result'):
            tx = data['result']
            print(f"Known tx block: {int(tx['blockNumber'], 16)}")
            
            scanner_cids = scanner.extract_cids_from_solution(tx)
            print(f"Known tx scanner result: {len(scanner_cids)} CIDs")
            for cid in scanner_cids:
                print(f"  {cid}")
                
    except Exception as e:
        print(f"Error testing known transaction: {e}")

if __name__ == "__main__":
    test_cid_extraction() 