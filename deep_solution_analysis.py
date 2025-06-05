#!/usr/bin/env python
"""
Deep analysis of submitSolution transactions to find CIDs with various patterns
"""

import requests
import re

def deep_solution_analysis():
    # All the solution transactions we found
    solution_txs = [
        "0xc4cfff13512cab8286d3ac27efa7d42860d6fabc103de6acb1e4d5777faee2fa",
        "0xd95b9f64ed11d0c6692dc31e84320ec2bbafd27bb0f2aeaff20093d28025d91c", 
        "0x929e8b0e7df63e3033458270eba4a7ae81d9cdada3b740e2a2f7d6eff4e668ed"
    ]
    
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    print(f"=== Deep Analysis of submitSolution Transactions ===")
    
    for i, solution_tx in enumerate(solution_txs):
        print(f"\n--- Analyzing Transaction #{i+1} ---")
        print(f"TX: {solution_tx}")
        
        # Get transaction details
        try:
            url = f"{base_url}?module=proxy&action=eth_getTransactionByHash&txhash={solution_tx}&apikey={api_key}"
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if not data.get('result'):
                print("Could not fetch transaction details")
                continue
                
            tx_data = data['result']
            input_data = tx_data['input']
            
            print(f"Block: {int(tx_data['blockNumber'], 16)}")
            print(f"From: {tx_data['from']}")
            print(f"Input length: {len(input_data)} characters")
            
            if len(input_data) > 10:
                hex_data = input_data[2:]  # Remove 0x
                
                try:
                    decoded_bytes = bytes.fromhex(hex_data)
                    
                    # Multiple decoding attempts
                    ascii_text = decoded_bytes.decode('utf-8', errors='ignore')
                    latin1_text = decoded_bytes.decode('latin1', errors='ignore')
                    
                    # Look for various CID patterns
                    patterns = [
                        r'Qm[1-9A-HJ-NP-Za-km-z]{44}',      # Standard CID
                        r'Qm[A-Za-z0-9]{44}',               # Relaxed CID
                        r'Qm[A-Za-z0-9]{40,50}',            # Variable length
                        r'Q[a-z][A-Za-z0-9]{42,50}',        # Other Q-prefixed
                    ]
                    
                    found_any = False
                    
                    for pattern_name, pattern in [
                        ("Standard CID", patterns[0]),
                        ("Relaxed CID", patterns[1]), 
                        ("Variable CID", patterns[2]),
                        ("Q-prefixed", patterns[3])
                    ]:
                        # Check ASCII
                        ascii_matches = re.findall(pattern, ascii_text)
                        if ascii_matches:
                            print(f"  {pattern_name} in ASCII: {ascii_matches[:3]}")
                            found_any = True
                            
                        # Check Latin1
                        latin1_matches = re.findall(pattern, latin1_text)  
                        if latin1_matches:
                            print(f"  {pattern_name} in Latin1: {latin1_matches[:3]}")
                            found_any = True
                    
                    # Look for raw "Qm" occurrences
                    qm_positions_ascii = [m.start() for m in re.finditer(r'Qm', ascii_text)]
                    qm_positions_latin1 = [m.start() for m in re.finditer(r'Qm', latin1_text)]
                    
                    if qm_positions_ascii:
                        print(f"  'Qm' found at ASCII positions: {qm_positions_ascii[:5]}")
                        # Show context around first few Qm occurrences
                        for pos in qm_positions_ascii[:3]:
                            start = max(0, pos - 10)
                            end = min(len(ascii_text), pos + 50)
                            context = ascii_text[start:end]
                            clean_context = ''.join(c if c.isprintable() else '?' for c in context)
                            print(f"    Context @ {pos}: ...{clean_context}...")
                        found_any = True
                    
                    if qm_positions_latin1:
                        print(f"  'Qm' found at Latin1 positions: {qm_positions_latin1[:5]}")
                        found_any = True
                    
                    # Look for hex-encoded CIDs
                    test_cid = "QmVxV7PdqK3V1VEA3nDiwcSK55N8Tq34fQxVFfSeLgc8hw"  # Known CID
                    test_cid_hex = test_cid.encode().hex()
                    
                    if test_cid_hex in hex_data:
                        print(f"  🎯 Found test CID {test_cid} in hex!")
                        found_any = True
                    
                    # Look for any base58-like strings
                    base58_pattern = r'[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{40,50}'
                    base58_matches = re.findall(base58_pattern, ascii_text)
                    if base58_matches:
                        print(f"  Base58-like strings: {base58_matches[:3]}")
                        found_any = True
                    
                    if not found_any:
                        print("  ❌ No CID patterns found with any method")
                        
                        # Show first 200 chars of each encoding
                        ascii_clean = ''.join(c if c.isprintable() else '?' for c in ascii_text[:200])
                        print(f"  ASCII sample: {ascii_clean}...")
                        
                        # Try to find any readable words
                        words = re.findall(r'[a-zA-Z]{4,}', ascii_text)
                        if words:
                            print(f"  Readable words found: {words[:10]}")
                    
                except Exception as e:
                    print(f"  Error decoding: {e}")
                    
        except Exception as e:
            print(f"Error analyzing transaction: {e}")

if __name__ == "__main__":
    deep_solution_analysis() 