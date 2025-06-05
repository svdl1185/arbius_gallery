#!/usr/bin/env python
"""
Look specifically for submitSolution transactions in the engine contract
"""

import requests
import json

def find_submit_solution_transactions():
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    engine_address = '0x9b51Ef044d3486A1fB0A2D55A6e0CeeAdd323E66'
    
    # Focus on the active range we found
    start_block = 200000000
    end_block = 300000000
    
    print(f"Looking for submitSolution transactions in engine contract...")
    print(f"Engine address: {engine_address}")
    print(f"Block range: {start_block:,} to {end_block:,}")
    
    url = f'{base_url}?module=account&action=txlist'
    params = {
        'address': engine_address,
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
            print("No transactions found!")
            print(f"Response: {json.dumps(data, indent=2)}")
            return
            
        transactions = data['result']
        print(f"Found {len(transactions)} total transactions to engine contract")
        
        submit_solution_count = 0
        
        for i, tx in enumerate(transactions):
            input_data = tx.get('input', '')
            
            # Check if this is a submitSolution transaction (0x5f2a8b8d)
            if input_data.startswith('0x5f2a8b8d'):
                submit_solution_count += 1
                print(f"\n🎯 SubmitSolution #{submit_solution_count}:")
                print(f"  Hash: {tx['hash']}")
                print(f"  Block: {tx['blockNumber']}")
                print(f"  From: {tx['from']}")
                print(f"  Gas Used: {tx.get('gasUsed', 'N/A')}")
                print(f"  Input: {input_data[:100]}...")
                
                # Try to decode the CID
                try:
                    if len(input_data) > 10:
                        data_hex = input_data[10:]  # Remove 0x and function selector
                        
                        if len(data_hex) >= 64:
                            task_id = '0x' + data_hex[:64]
                            print(f"  Task ID: {task_id}")
                            
                            if len(data_hex) >= 128:
                                try:
                                    cid_offset = int(data_hex[64:128], 16) * 2
                                    if cid_offset < len(data_hex):
                                        cid_length = int(data_hex[cid_offset:cid_offset+64], 16) * 2
                                        cid_data = data_hex[cid_offset+64:cid_offset+64+cid_length]
                                        cid = bytes.fromhex(cid_data).decode('utf-8')
                                        print(f"  CID: {cid}")
                                        print(f"  IPFS URL: https://ipfs.arbius.org/ipfs/{cid}")
                                        print(f"  Image URL: https://ipfs.arbius.org/ipfs/{cid}/out-1.png")
                                except Exception as decode_error:
                                    print(f"  Could not decode CID: {decode_error}")
                                    
                except Exception as e:
                    print(f"  Error parsing transaction data: {e}")
            else:
                # Show what other function calls we're seeing
                if i < 10:  # Only show first 10
                    function_selector = input_data[:10] if len(input_data) >= 10 else 'N/A'
                    print(f"  TX {i+1}: {tx['hash'][:10]}... Function: {function_selector}")
        
        print(f"\n📊 Summary:")
        print(f"  Total transactions: {len(transactions)}")
        print(f"  SubmitSolution transactions: {submit_solution_count}")
        
        if submit_solution_count == 0:
            print("\n🤔 No submitSolution transactions found in engine contract.")
            print("   This might mean:")
            print("   1. Solutions are submitted differently than expected")
            print("   2. The function signature is different")
            print("   3. We need to look at a different block range")
            print("   4. The contract might use a different method")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_submit_solution_transactions() 