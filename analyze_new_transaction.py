#!/usr/bin/env python
"""
Analyze the second transaction to understand the Arbius protocol better
"""

import requests
import json
import re

def analyze_new_transaction():
    # The new transaction data
    tx_hash = "0x3a2e652b7ed8809540a5d275d12b45440430e36f0dc70bd2ff9277944d01acaf"
    expected_cid = "QmSFiVCnGvP7dmNKfydagzwnQi6sUWjBEFrEYgFbWYFXMB"
    
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    print(f"=== Analyzing transaction {tx_hash} ===")
    print(f"Expected CID: {expected_cid}")
    
    # Get transaction details
    try:
        url = f"{base_url}?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={api_key}"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        if not data.get('result'):
            print("Could not fetch transaction details")
            return
            
        tx_data = data['result']
        
        print(f"\nTransaction details:")
        print(f"  Block: {int(tx_data['blockNumber'], 16)}")
        print(f"  From: {tx_data['from']}")
        print(f"  To: {tx_data['to']}")
        print(f"  Function signature: {tx_data['input'][:10]}")
        print(f"  Input length: {len(tx_data['input'])} characters")
        
        input_data = tx_data['input']
        
        # Decode the transaction data
        if len(input_data) > 10:
            hex_data = input_data[2:]  # Remove 0x
            
            try:
                decoded_bytes = bytes.fromhex(hex_data)
                ascii_text = decoded_bytes.decode('utf-8', errors='ignore')
                
                print(f"\nASCII representation:")
                print(f"{ascii_text[:200]}...")
                
                # Look for the expected CID
                if expected_cid in ascii_text:
                    print(f"\n✅ Found expected CID in transaction data!")
                    cid_start = ascii_text.find(expected_cid)
                    print(f"CID position: {cid_start}")
                    context_start = max(0, cid_start - 50)
                    context_end = min(len(ascii_text), cid_start + len(expected_cid) + 50)
                    context = ascii_text[context_start:context_end]
                    print(f"Context: ...{context}...")
                    
                    # This means this transaction SHOULD have been found by our scanner!
                    print(f"\n🤔 Why wasn't this found by the scanner?")
                    
                else:
                    print(f"\n❌ Expected CID not found in this transaction")
                    print("This confirms it's a task submission, not solution")
                
                # Look for any CID patterns
                cid_pattern = r'Qm[1-9A-HJ-NP-Za-km-z]{44}'
                found_cids = re.findall(cid_pattern, ascii_text)
                
                print(f"\nAll CID patterns found: {found_cids}")
                
                # If we found the CID, let's see what our scanner should have done
                if expected_cid in found_cids:
                    print(f"\n🔍 Scanner analysis:")
                    print(f"  - Function signature: {input_data[:10]}")
                    print(f"  - This should have been detected by extract_cids_from_transaction()")
                    print(f"  - The scanner should have created an ArbiusImage record")
                    print(f"  - Let's check if there are any bugs in the scanner logic")
                    
            except Exception as e:
                print(f"Error decoding transaction: {e}")
        
        # Now let's look for the corresponding solution transaction
        print(f"\n=== Looking for solution transaction ===")
        
        block_number = int(tx_data['blockNumber'], 16)
        start_block = block_number
        end_block = block_number + 1000  # Look forward in time
        
        print(f"Searching blocks {start_block} to {end_block} for solution...")
        
        url = f'{base_url}?module=account&action=txlist'
        params = {
            'address': '0x9b51ef044d3486a1fb0a2d55a6e0ceeadd323e66',
            'startblock': start_block,
            'endblock': end_block,
            'page': 1,
            'offset': 100,
            'sort': 'asc',
            'apikey': api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if data.get('result'):
            transactions = data['result']
            print(f"Found {len(transactions)} transactions to check")
            
            solution_found = False
            for tx in transactions:
                try:
                    hex_data = tx['input'][2:]
                    decoded_bytes = bytes.fromhex(hex_data)
                    ascii_text = decoded_bytes.decode('utf-8', errors='ignore')
                    
                    if expected_cid in ascii_text:
                        solution_found = True
                        print(f"\n🎯 Found solution transaction!")
                        print(f"  Hash: {tx['hash']}")
                        print(f"  Block: {tx['blockNumber']}")
                        print(f"  Function: {tx['input'][:10]}")
                        print(f"  From: {tx['from']}")
                        break
                except:
                    continue
            
            if not solution_found:
                print(f"\n❌ No solution transaction found yet")
                print("The CID might be in the task transaction itself!")
                
        else:
            print("Could not search for solution transactions")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_new_transaction() 