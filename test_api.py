#!/usr/bin/env python
"""
Simple test script to verify Arbiscan API connectivity
"""

import requests
import json

def test_arbiscan_api():
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = "https://api.arbiscan.io/api"
    engine_address = '0x9b51Ef044d3486A1fB0A2D55A6e0CeeAdd323E66'
    
    # Test 1: Get latest block
    print("=== Test 1: Latest Block ===")
    try:
        url = f"{base_url}?module=proxy&action=eth_blockNumber&apikey={api_key}"
        response = requests.get(url, timeout=30)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if data.get('result'):
            latest_block = int(data['result'], 16)
            print(f"Latest block number: {latest_block}")
        else:
            print("No result field found")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Get recent transactions for engine contract
    print("\n=== Test 2: Engine Contract Transactions ===")
    try:
        # Get last 100 blocks worth of transactions
        latest_block = 320000000  # Approximate recent block number
        start_block = latest_block - 100
        
        url = f"{base_url}?module=account&action=txlist"
        params = {
            'address': engine_address,
            'startblock': start_block,
            'endblock': latest_block,
            'page': 1,
            'offset': 10,  # Limit to 10 for testing
            'sort': 'desc',
            'apikey': api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if data.get('result'):
            transactions = data['result']
            print(f"Found {len(transactions)} transactions")
            
            for i, tx in enumerate(transactions[:3]):  # Show first 3
                print(f"\nTransaction {i+1}:")
                print(f"  Hash: {tx.get('hash')}")
                print(f"  Block: {tx.get('blockNumber')}")
                print(f"  From: {tx.get('from')}")
                print(f"  To: {tx.get('to')}")
                print(f"  Input: {tx.get('input', '')[:50]}...")
                
                # Check if it's a submitSolution call
                input_data = tx.get('input', '')
                if input_data.startswith('0x5f2a8b8d'):
                    print(f"  -> This is a submitSolution transaction!")
        else:
            print(f"No transactions found: {json.dumps(data, indent=2)}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_arbiscan_api() 