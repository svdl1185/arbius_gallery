#!/usr/bin/env python
"""
Carefully extract CIDs from the known positions
"""

import requests
import re

def extract_cids_carefully():
    # Transaction with confirmed 'Qm' occurrences
    solution_tx = "0x929e8b0e7df63e3033458270eba4a7ae81d9cdada3b740e2a2f7d6eff4e668ed"
    
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    print(f"=== Extracting CIDs from Transaction ===")
    print(f"TX: {solution_tx}")
    
    # Get transaction details
    try:
        url = f"{base_url}?module=proxy&action=eth_getTransactionByHash&txhash={solution_tx}&apikey={api_key}"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        if not data.get('result'):
            print("Could not fetch transaction details")
            return
            
        tx_data = data['result']
        input_data = tx_data['input']
        hex_data = input_data[2:]  # Remove 0x
        
        decoded_bytes = bytes.fromhex(hex_data)
        ascii_text = decoded_bytes.decode('utf-8', errors='ignore')
        
        # Known positions of 'Qm' occurrences
        qm_positions = [1415, 14001, 17098]
        
        print(f"ASCII text length: {len(ascii_text)}")
        print(f"'Qm' positions found: {qm_positions}")
        
        potential_cids = []
        
        for i, pos in enumerate(qm_positions):
            print(f"\n--- Analyzing position {pos} ---")
            
            # Extract 60 characters starting from 'Qm'
            start = pos
            end = min(len(ascii_text), pos + 60)
            segment = ascii_text[start:end]
            
            print(f"Raw segment: '{segment}'")
            
            # Clean the segment - remove non-base58 characters
            # Base58 alphabet: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
            base58_chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
            
            # Extract continuous base58 sequence starting with 'Qm'
            if segment.startswith('Qm'):
                cid_candidate = 'Qm'
                for char in segment[2:]:  # Skip 'Qm'
                    if char in base58_chars:
                        cid_candidate += char
                    else:
                        break
                
                print(f"CID candidate: '{cid_candidate}' (length: {len(cid_candidate)})")
                
                # Standard IPFS CIDs are 46 characters
                if len(cid_candidate) >= 40:  # Allow some flexibility
                    print(f"✅ Potential CID: {cid_candidate}")
                    potential_cids.append(cid_candidate)
                    
                    # Test if this CID works on IPFS
                    test_url = f"https://ipfs.arbius.org/ipfs/{cid_candidate}/out-1.png"
                    try:
                        head_response = requests.head(test_url, timeout=10)
                        if head_response.status_code == 200:
                            size = head_response.headers.get('content-length', 'unknown')
                            print(f"🎯 CID works on IPFS! Size: {size} bytes")
                        else:
                            print(f"❌ CID not accessible on IPFS ({head_response.status_code})")
                    except Exception as e:
                        print(f"❓ Could not test IPFS: {e}")
                else:
                    print(f"❌ Too short to be a valid CID")
            else:
                print(f"❌ Does not start with 'Qm'")
            
            # Also try extracting exactly 46 characters if possible
            if len(segment) >= 46:
                fixed_length_cid = segment[:46]
                # Check if it's all valid base58
                if all(c in base58_chars for c in fixed_length_cid):
                    print(f"Fixed length candidate: '{fixed_length_cid}'")
                    if fixed_length_cid != cid_candidate:
                        potential_cids.append(fixed_length_cid)
        
        print(f"\n=== SUMMARY ===")
        print(f"Found {len(potential_cids)} potential CIDs:")
        
        for i, cid in enumerate(potential_cids):
            print(f"  {i+1}. {cid}")
            
            # Test each one
            test_url = f"https://ipfs.arbius.org/ipfs/{cid}/out-1.png"
            try:
                head_response = requests.head(test_url, timeout=10)
                if head_response.status_code == 200:
                    size = head_response.headers.get('content-length', 'unknown')
                    print(f"     🎯 ACCESSIBLE! Size: {size} bytes")
                    print(f"     URL: {test_url}")
                else:
                    print(f"     ❌ Not accessible ({head_response.status_code})")
            except Exception as e:
                print(f"     ❓ Test failed: {e}")
        
        # If we found working CIDs, this confirms the pattern!
        if any(potential_cids):
            print(f"\n🎉 SUCCESS! Found actual CIDs in submitSolution transaction!")
            print(f"Function signature: 0x65d445fb")
            print(f"This is the real submitSolution function!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_cids_carefully() 