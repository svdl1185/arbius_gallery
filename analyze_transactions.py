#!/usr/bin/env python
"""
Analyze actual transactions to the engine contract to understand the data patterns
"""

import requests
import json
import re

def analyze_engine_transactions():
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    engine_address = '0x9b51Ef044d3486A1fB0A2D55A6e0CeeAdd323E66'
    
    # Get recent transactions
    start_block = 280000000
    end_block = 290000000
    
    print(f"Analyzing engine contract transactions...")
    print(f"Block range: {start_block:,} to {end_block:,}")
    
    url = f'{base_url}?module=account&action=txlist'
    params = {
        'address': engine_address,
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
            print("No transactions found!")
            return
            
        transactions = data['result']
        print(f"Analyzing {len(transactions)} transactions...\n")
        
        function_signatures = {}
        cid_candidates = []
        
        for i, tx in enumerate(transactions):
            input_data = tx.get('input', '')
            
            if len(input_data) >= 10:
                function_sig = input_data[:10]
                function_signatures[function_sig] = function_signatures.get(function_sig, 0) + 1
                
                # Look for IPFS CID patterns in the transaction data
                # CIDs typically start with Qm and are base58 encoded
                cid_pattern = r'Qm[1-9A-HJ-NP-Za-km-z]{44}'
                
                # Convert hex data to ASCII where possible
                try:
                    hex_data = input_data[2:]  # Remove 0x
                    # Try to decode hex to bytes and then to string
                    decoded_bytes = bytes.fromhex(hex_data)
                    ascii_parts = []
                    
                    # Extract printable ASCII sequences
                    current_ascii = ""
                    for byte in decoded_bytes:
                        if 32 <= byte <= 126:  # Printable ASCII
                            current_ascii += chr(byte)
                        else:
                            if len(current_ascii) > 10:  # Only keep longer sequences
                                ascii_parts.append(current_ascii)
                            current_ascii = ""
                    
                    if current_ascii and len(current_ascii) > 10:
                        ascii_parts.append(current_ascii)
                    
                    # Look for CIDs in the ASCII parts
                    for part in ascii_parts:
                        cids = re.findall(cid_pattern, part)
                        for cid in cids:
                            cid_candidates.append({
                                'cid': cid,
                                'tx_hash': tx['hash'],
                                'block': tx['blockNumber'],
                                'function': function_sig,
                                'full_ascii': part
                            })
                            
                except Exception as e:
                    pass
        
        print("📊 Function signature analysis:")
        for sig, count in sorted(function_signatures.items(), key=lambda x: x[1], reverse=True):
            print(f"  {sig}: {count} transactions")
        
        print(f"\n🔍 Found {len(cid_candidates)} potential CIDs:")
        for i, candidate in enumerate(cid_candidates[:10]):  # Show first 10
            print(f"\n  CID #{i+1}: {candidate['cid']}")
            print(f"    TX: {candidate['tx_hash']}")
            print(f"    Block: {candidate['block']}")
            print(f"    Function: {candidate['function']}")
            print(f"    Context: ...{candidate['full_ascii'][-50:]}...")
            print(f"    IPFS URL: https://ipfs.arbius.org/ipfs/{candidate['cid']}")
            print(f"    Image URL: https://ipfs.arbius.org/ipfs/{candidate['cid']}/out-1.png")
        
        if cid_candidates:
            print(f"\n🎉 SUCCESS! Found CID patterns in engine contract transactions!")
            print(f"   Most common function signature with CIDs: {cid_candidates[0]['function']}")
            
            # Test the first CID to see if it's a valid image
            if cid_candidates:
                test_cid = cid_candidates[0]['cid']
                test_url = f"https://ipfs.arbius.org/ipfs/{test_cid}/out-1.png"
                print(f"\n🧪 Testing first CID: {test_url}")
                
                try:
                    import requests
                    head_response = requests.head(test_url, timeout=10)
                    print(f"   Status: {head_response.status_code}")
                    if head_response.status_code == 200:
                        print(f"   ✅ Image exists and is accessible!")
                    else:
                        print(f"   ❌ Image not accessible")
                except Exception as e:
                    print(f"   ❓ Could not test: {e}")
        else:
            print("\n😞 No CID patterns found in transaction data")
            
        # Let's also look at specific transaction details
        print(f"\n🔬 Detailed analysis of most common function ({list(function_signatures.keys())[0]}):")
        for tx in transactions[:3]:
            if tx['input'].startswith(list(function_signatures.keys())[0]):
                print(f"\n  Transaction: {tx['hash']}")
                print(f"  Input length: {len(tx['input'])} characters")
                print(f"  Input sample: {tx['input'][:200]}...")
                break
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_engine_transactions() 