#!/usr/bin/env python
"""
Broad search across contracts and time ranges to find solution transactions
"""

import requests
import json
import re
import time

def broad_search_for_solutions():
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    # Contracts to check
    contracts = {
        'engine': '0x9b51ef044d3486a1fb0a2d55a6e0ceeadd323e66',
        'router': '0xecAba4E6a4bC1E3DE3e996a8B2c89e8B0626C9a1'
    }
    
    cid_pattern = r'Qm[1-9A-HJ-NP-Za-km-z]{44}'
    
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
    
    # Search in multiple time ranges
    search_ranges = [
        (latest_block - 100, latest_block),      # Last 100 blocks
        (latest_block - 1000, latest_block - 100), # 100-1000 blocks ago
        (latest_block - 5000, latest_block - 1000), # 1000-5000 blocks ago
    ]
    
    all_cids_found = []
    
    for contract_name, contract_address in contracts.items():
        print(f"\n=== Searching {contract_name} contract: {contract_address} ===")
        
        for start_block, end_block in search_ranges:
            print(f"\nChecking blocks {start_block} to {end_block}...")
            
            url = f'{base_url}?module=account&action=txlist'
            params = {
                'address': contract_address,
                'startblock': start_block,
                'endblock': end_block,
                'page': 1,
                'offset': 50,
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
                print(f"  Found {len(transactions)} transactions")
                
                cids_in_range = []
                function_sigs = {}
                
                for tx in transactions:
                    input_data = tx.get('input', '')
                    if len(input_data) > 10:
                        function_sig = input_data[:10]
                        function_sigs[function_sig] = function_sigs.get(function_sig, 0) + 1
                        
                        try:
                            hex_data = input_data[2:]
                            decoded_bytes = bytes.fromhex(hex_data)
                            ascii_text = decoded_bytes.decode('utf-8', errors='ignore')
                            
                            found_cids = re.findall(cid_pattern, ascii_text)
                            if found_cids:
                                for cid in found_cids:
                                    cid_info = {
                                        'cid': cid,
                                        'tx_hash': tx['hash'],
                                        'block': tx['blockNumber'],
                                        'function': function_sig,
                                        'contract': contract_name,
                                        'from': tx['from'],
                                        'timestamp': tx.get('timeStamp', '0')
                                    }
                                    cids_in_range.append(cid_info)
                                    all_cids_found.append(cid_info)
                                    
                                    print(f"    🎯 CID found: {cid}")
                                    print(f"       TX: {tx['hash']}")
                                    print(f"       Function: {function_sig}")
                                    print(f"       Block: {tx['blockNumber']}")
                        except Exception as e:
                            continue
                
                if cids_in_range:
                    print(f"  ✅ Found {len(cids_in_range)} CIDs in this range")
                else:
                    print(f"  ❌ No CIDs found")
                
                # Show function signatures
                if function_sigs:
                    print(f"  Function signatures: {list(function_sigs.keys())}")
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  Error: {e}")
                continue
    
    # Summary
    print(f"\n=== FINAL SUMMARY ===")
    print(f"Total CIDs found: {len(all_cids_found)}")
    
    if all_cids_found:
        print(f"\nAll CIDs discovered:")
        for i, cid_info in enumerate(all_cids_found[-10:]):  # Show last 10
            print(f"{i+1}. CID: {cid_info['cid']}")
            print(f"   Contract: {cid_info['contract']}")
            print(f"   Function: {cid_info['function']}")
            print(f"   TX: {cid_info['tx_hash']}")
            print(f"   Block: {cid_info['block']}")
            
            # Test if image exists
            test_url = f"https://ipfs.arbius.org/ipfs/{cid_info['cid']}/out-1.png"
            try:
                head_response = requests.head(test_url, timeout=5)
                accessible = "✅" if head_response.status_code == 200 else "❌"
                print(f"   Image: {accessible} {test_url}")
            except:
                print(f"   Image: ❓ Could not test")
            print()
        
        # Analyze patterns
        contracts_used = set(c['contract'] for c in all_cids_found)
        functions_used = set(c['function'] for c in all_cids_found)
        
        print(f"Contracts with CIDs: {list(contracts_used)}")
        print(f"Functions with CIDs: {list(functions_used)}")
        
        # Most recent CID
        if all_cids_found:
            most_recent = max(all_cids_found, key=lambda x: int(x['block']))
            print(f"\nMost recent CID: {most_recent['cid']}")
            print(f"Block: {most_recent['block']}")
            print(f"Function: {most_recent['function']}")
            print(f"Contract: {most_recent['contract']}")
    else:
        print("\n😞 No CIDs found in any contract or time range")
        print("This suggests:")
        print("1. Solutions might be submitted to a different contract entirely")
        print("2. The CID encoding has changed") 
        print("3. There's a longer delay between task and solution")
        print("4. Solutions might be submitted off-chain or differently")

if __name__ == "__main__":
    broad_search_for_solutions() 