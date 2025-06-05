#!/usr/bin/env python
"""
Test different block ranges to find engine contract transactions
"""

import requests
import json

def test_block_ranges():
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    engine_address = '0x9b51Ef044d3486A1fB0A2D55A6e0CeeAdd323E66'

    # Test different block ranges
    block_ranges = [
        (0, 1000000),
        (1000000, 10000000), 
        (10000000, 50000000),
        (50000000, 100000000),
        (100000000, 200000000),
        (200000000, 300000000),
        (300000000, 344000000)
    ]

    for start_block, end_block in block_ranges:
        print(f'Scanning blocks {start_block:,} to {end_block:,}...')
        
        url = f'{base_url}?module=account&action=txlist'
        params = {
            'address': engine_address,
            'startblock': start_block,
            'endblock': end_block,
            'page': 1,
            'offset': 10,
            'sort': 'desc',
            'apikey': api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if data.get('result') and len(data['result']) > 0:
                transactions = data['result']
                print(f'  ✅ Found {len(transactions)} transactions!')
                
                for i, tx in enumerate(transactions[:3]):
                    print(f'  TX {i+1}: {tx["hash"]}')
                    print(f'    Block: {tx["blockNumber"]}')
                    print(f'    From: {tx["from"]}')
                    print(f'    Input: {tx["input"][:20]}...')
                    
                    # Check if submitSolution
                    if tx["input"].startswith('0x5f2a8b8d'):
                        print(f'    🎯 This is submitSolution!')
                
                # If we found transactions, let's focus on this range
                if len(transactions) > 0:
                    return start_block, end_block
                        
            else:
                print(f'  ❌ No transactions found')
                if data.get('message'):
                    print(f'      Message: {data["message"]}')
                    
        except Exception as e:
            print(f'  💥 Error: {e}')
    
    return None, None

if __name__ == "__main__":
    print("Testing different block ranges for Arbius Engine contract...")
    start, end = test_block_ranges()
    
    if start and end:
        print(f"\n🎉 Found active range: {start:,} to {end:,}")
    else:
        print("\n😞 No transactions found in any range")

    # Let's also check the specific transaction from the example
    print("\n=== Testing specific transaction ===")
    tx_hash = '0xbf7bd853d81302cea51ee212215701f6b4201ea02816dc3dd43302700215c8ee'
    
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    url = f'{base_url}?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={api_key}'
    
    try:
        response = requests.get(url, timeout=30)
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"Error: {e}") 