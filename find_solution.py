#!/usr/bin/env python
"""
Find the solution transaction that contains the CID for the user's image
"""

import requests
import json

def find_solution_transaction():
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    contract_address = '0x9b51ef044d3486a1fb0a2d55a6e0ceeadd323e66'
    
    expected_cid = 'QmVxV7PdqK3V1VEA3nDiwcSK55N8Tq34fQxVFfSeLgc8hw'
    task_block = 344216552
    
    print(f"Looking for solution transaction with CID: {expected_cid}")
    print(f"Searching from block {task_block} onwards...")
    
    # Search in blocks after the task submission
    start_block = task_block
    end_block = task_block + 1000  # Search next 1000 blocks
    
    url = f'{base_url}?module=account&action=txlist'
    params = {
        'address': contract_address,
        'startblock': start_block,
        'endblock': end_block,
        'page': 1,
        'offset': 100,
        'sort': 'asc',
        'apikey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if not data.get('result'):
            print("No transactions found in the range")
            return None
            
        transactions = data['result']
        print(f"Analyzing {len(transactions)} transactions...")
        
        solution_found = False
        
        for i, tx in enumerate(transactions):
            input_data = tx.get('input', '')
            
            if len(input_data) > 10:
                try:
                    # Try to decode the transaction data
                    hex_data = input_data[2:]  # Remove 0x
                    decoded_bytes = bytes.fromhex(hex_data)
                    
                    # Convert to string and look for the CID
                    ascii_text = decoded_bytes.decode('utf-8', errors='ignore')
                    
                    if expected_cid in ascii_text:
                        solution_found = True
                        print(f"\n🎯 FOUND SOLUTION TRANSACTION!")
                        print(f"  Hash: {tx['hash']}")
                        print(f"  Block: {tx['blockNumber']}")
                        print(f"  Function: {input_data[:10]}")
                        print(f"  From (Miner): {tx['from']}")
                        print(f"  Gas Used: {tx.get('gasUsed', 'N/A')}")
                        print(f"  Timestamp: {tx.get('timeStamp', 'N/A')}")
                        
                        # Extract task ID if possible
                        try:
                            # Common pattern: first 32 bytes after function selector = task ID
                            if len(hex_data) >= 72:  # 8 (function) + 64 (task ID)
                                task_id = '0x' + hex_data[8:72]
                                print(f"  Task ID: {task_id}")
                        except:
                            pass
                        
                        # Show context around the CID
                        cid_pos = ascii_text.find(expected_cid)
                        if cid_pos != -1:
                            context_start = max(0, cid_pos - 30)
                            context_end = min(len(ascii_text), cid_pos + len(expected_cid) + 30)
                            context = ascii_text[context_start:context_end]
                            print(f"  CID Context: ...{context}...")
                        
                        return tx
                        
                except Exception as e:
                    # Skip transactions that can't be decoded
                    continue
        
        if not solution_found:
            print(f"\n❌ No solution transaction found with CID {expected_cid}")
            print("Possible reasons:")
            print("1. The solution hasn't been submitted yet (miners still processing)")
            print("2. The solution is in a later block range") 
            print("3. The solution goes to a different contract")
            print("4. The CID format is different than expected")
            
            # Show what function signatures we did find
            function_sigs = {}
            for tx in transactions:
                sig = tx.get('input', '')[:10]
                if sig != '0x':
                    function_sigs[sig] = function_sigs.get(sig, 0) + 1
            
            if function_sigs:
                print(f"\nFunction signatures found in this range:")
                for sig, count in sorted(function_sigs.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {sig}: {count} transactions")
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    find_solution_transaction() 