#!/usr/bin/env python
"""
Search specifically for the CID across all recent transactions
"""

import requests
import json
import re
import time

def search_for_specific_cid():
    target_cid = "QmSFiVCnGvP7dmNKfydagzwnQi6sUWjBEFrEYgFbWYFXMB"
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    print(f"=== Searching for CID: {target_cid} ===")
    
    # Get latest block
    try:
        url = f"{base_url}?module=proxy&action=eth_blockNumber&apikey={api_key}"
        response = requests.get(url, timeout=30)
        data = response.json()
        latest_block = int(data['result'], 16) if data.get('result') else 344220000
        print(f"Latest block: {latest_block}")
    except Exception as e:
        print(f"Error getting latest block: {e}")
        latest_block = 344220000
    
    # Search across multiple contracts and block ranges
    contracts_to_search = [
        ('engine', '0x9b51ef044d3486a1fb0a2d55a6e0ceeadd323e66'),
        ('router', '0xecAba4E6a4bC1E3DE3e996a8B2c89e8B0626C9a1')
    ]
    
    # Search in wide ranges
    search_ranges = [
        (latest_block - 200, latest_block),           # Last 200 blocks
        (latest_block - 1000, latest_block - 200),   # 200-1000 blocks ago
        (latest_block - 5000, latest_block - 1000),  # 1000-5000 blocks ago
        (344216000, 344220000),                       # Around the time of first image
    ]
    
    cid_found_in = []
    
    for contract_name, contract_address in contracts_to_search:
        print(f"\n=== Searching {contract_name} contract ===")
        
        for start_block, end_block in search_ranges:
            print(f"Checking blocks {start_block} to {end_block}...")
            
            url = f'{base_url}?module=account&action=txlist'
            params = {
                'address': contract_address,
                'startblock': start_block,
                'endblock': end_block,
                'page': 1,
                'offset': 100,
                'sort': 'desc',
                'apikey': api_key
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                data = response.json()
                
                if not data.get('result'):
                    print(f"  No transactions found")
                    continue
                    
                transactions = data['result']
                print(f"  Checking {len(transactions)} transactions...")
                
                for tx in transactions:
                    try:
                        input_data = tx.get('input', '')
                        if len(input_data) > 10:
                            # Check for CID in hex encoding
                            cid_hex = target_cid.encode().hex()
                            if cid_hex in input_data[2:]:
                                cid_found_in.append({
                                    'contract': contract_name,
                                    'tx_hash': tx['hash'],
                                    'block': tx['blockNumber'],
                                    'function': input_data[:10],
                                    'from': tx['from'],
                                    'encoding': 'hex'
                                })
                                print(f"    🎯 Found CID (hex encoding)!")
                                print(f"       TX: {tx['hash']}")
                                print(f"       Block: {tx['blockNumber']}")
                                print(f"       Function: {input_data[:10]}")
                            
                            # Check for CID in ASCII encoding
                            try:
                                hex_data = input_data[2:]
                                decoded_bytes = bytes.fromhex(hex_data)
                                ascii_text = decoded_bytes.decode('utf-8', errors='ignore')
                                
                                if target_cid in ascii_text:
                                    cid_found_in.append({
                                        'contract': contract_name,
                                        'tx_hash': tx['hash'],
                                        'block': tx['blockNumber'],
                                        'function': input_data[:10],
                                        'from': tx['from'],
                                        'encoding': 'ascii'
                                    })
                                    print(f"    🎯 Found CID (ASCII encoding)!")
                                    print(f"       TX: {tx['hash']}")
                                    print(f"       Block: {tx['blockNumber']}")
                                    print(f"       Function: {input_data[:10]}")
                                    
                                    # Show context
                                    cid_pos = ascii_text.find(target_cid)
                                    context_start = max(0, cid_pos - 30)
                                    context_end = min(len(ascii_text), cid_pos + len(target_cid) + 30)
                                    context = ascii_text[context_start:context_end]
                                    print(f"       Context: ...{context}...")
                            except:
                                pass
                                
                    except Exception as e:
                        continue
                
                # Small delay to avoid rate limiting
                time.sleep(0.3)
                
            except Exception as e:
                print(f"  Error: {e}")
                continue
    
    # Summary
    print(f"\n=== SEARCH RESULTS ===")
    if cid_found_in:
        print(f"🎉 Found CID in {len(cid_found_in)} transaction(s)!")
        
        for i, result in enumerate(cid_found_in):
            print(f"\nMatch #{i+1}:")
            print(f"  Contract: {result['contract']}")
            print(f"  Transaction: {result['tx_hash']}")
            print(f"  Block: {result['block']}")
            print(f"  Function: {result['function']}")
            print(f"  From: {result['from']}")
            print(f"  Encoding: {result['encoding']}")
            
            # Test if image is accessible
            test_url = f"https://ipfs.arbius.org/ipfs/{target_cid}/out-1.png"
            try:
                head_response = requests.head(test_url, timeout=5)
                accessible = "✅" if head_response.status_code == 200 else "❌"
                print(f"  Image accessible: {accessible}")
            except:
                print(f"  Image accessible: ❓")
        
        # If we found it, let's understand why the scanner missed it
        print(f"\n🤔 Why didn't the scanner find this?")
        print(f"Possible reasons:")
        print(f"1. The scanner wasn't running when this transaction occurred")
        print(f"2. The block range wasn't covered by the scanner")
        print(f"3. There's a bug in the scanner logic")
        print(f"4. The transaction was filtered out somehow")
        
    else:
        print(f"😞 CID not found in any transaction")
        print(f"This means:")
        print(f"1. The solution hasn't been submitted to the blockchain yet")
        print(f"2. The solution goes to a different contract we're not monitoring")
        print(f"3. The CID encoding is different than expected")
        print(f"4. There's a significant delay between task and solution")
        print(f"5. Solutions might be submitted off-chain initially")
        
        # Let's test if the image exists on IPFS anyway
        test_url = f"https://ipfs.arbius.org/ipfs/{target_cid}/out-1.png"
        print(f"\nTesting image accessibility: {test_url}")
        try:
            head_response = requests.head(test_url, timeout=10)
            if head_response.status_code == 200:
                print(f"✅ Image exists on IPFS! Size: {head_response.headers.get('content-length', 'unknown')} bytes")
                print(f"This suggests the solution was processed, but not recorded on-chain yet")
            else:
                print(f"❌ Image not accessible ({head_response.status_code})")
        except Exception as e:
            print(f"❓ Could not test image: {e}")

if __name__ == "__main__":
    search_for_specific_cid() 