#!/usr/bin/env python
"""
Debug recent transactions to see why the scanner isn't finding new images
"""

import requests
import json
import re

def debug_recent_transactions():
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    engine_address = '0x9b51ef044d3486a1fb0a2d55a6e0ceeadd323e66'
    
    # Get latest block
    print("=== Getting latest block ===")
    try:
        url = f"{base_url}?module=proxy&action=eth_blockNumber&apikey={api_key}"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        if data.get('result'):
            latest_block = int(data['result'], 16)
            print(f"Latest block: {latest_block}")
        else:
            print("Could not get latest block")
            return
    except Exception as e:
        print(f"Error getting latest block: {e}")
        return
    
    # Check recent transactions (last 1000 blocks)
    start_block = latest_block - 1000
    end_block = latest_block
    
    print(f"\n=== Checking recent transactions ===")
    print(f"Scanning blocks {start_block} to {end_block}")
    
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
            print(f"No transactions found! Response: {json.dumps(data, indent=2)}")
            return
            
        transactions = data['result']
        print(f"Found {len(transactions)} recent transactions")
        
        # Analyze each transaction
        cid_pattern = r'Qm[1-9A-HJ-NP-Za-km-z]{44}'
        function_signatures = {}
        transactions_with_cids = []
        
        for i, tx in enumerate(transactions):
            input_data = tx.get('input', '')
            function_sig = input_data[:10] if len(input_data) >= 10 else 'N/A'
            
            # Count function signatures
            function_signatures[function_sig] = function_signatures.get(function_sig, 0) + 1
            
            # Look for CIDs in transaction data
            try:
                if len(input_data) > 10:
                    hex_data = input_data[2:]  # Remove 0x
                    decoded_bytes = bytes.fromhex(hex_data)
                    ascii_text = decoded_bytes.decode('utf-8', errors='ignore')
                    
                    found_cids = re.findall(cid_pattern, ascii_text)
                    if found_cids:
                        transactions_with_cids.append({
                            'tx': tx,
                            'cids': found_cids,
                            'function': function_sig
                        })
                        print(f"\n🎯 Transaction #{i+1} has CIDs!")
                        print(f"  Hash: {tx['hash']}")
                        print(f"  Block: {tx['blockNumber']}")
                        print(f"  Function: {function_sig}")
                        print(f"  CIDs found: {found_cids}")
                        
                        # Test if these CIDs are accessible
                        for cid in found_cids:
                            test_url = f"https://ipfs.arbius.org/ipfs/{cid}/out-1.png"
                            print(f"  Testing: {test_url}")
                            try:
                                head_response = requests.head(test_url, timeout=5)
                                if head_response.status_code == 200:
                                    print(f"    ✅ Image exists!")
                                else:
                                    print(f"    ❌ Image not accessible ({head_response.status_code})")
                            except Exception as e:
                                print(f"    ❓ Could not test: {e}")
            except Exception as e:
                # Skip transactions that can't be decoded
                continue
        
        print(f"\n=== Summary ===")
        print(f"Total recent transactions: {len(transactions)}")
        print(f"Transactions with CIDs: {len(transactions_with_cids)}")
        
        print(f"\nFunction signatures found:")
        for sig, count in sorted(function_signatures.items(), key=lambda x: x[1], reverse=True):
            print(f"  {sig}: {count} transactions")
        
        # If we found CIDs, let's see why they weren't added by the scanner
        if transactions_with_cids:
            print(f"\n=== Why weren't these added? ===")
            
            # Import Django models to check
            import os
            import sys
            import django
            
            sys.path.append('/Users/biba/Documents/Projects/arbius_gallery')
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
            django.setup()
            
            from gallery.models import ArbiusImage
            
            for tx_data in transactions_with_cids:
                tx = tx_data['tx']
                cids = tx_data['cids']
                
                print(f"\nTransaction {tx['hash']}:")
                
                # Check if transaction exists
                exists_tx = ArbiusImage.objects.filter(transaction_hash=tx['hash']).exists()
                print(f"  Transaction in DB: {exists_tx}")
                
                # Check if CIDs exist
                for cid in cids:
                    exists_cid = ArbiusImage.objects.filter(cid=cid).exists()
                    print(f"  CID {cid} in DB: {exists_cid}")
        else:
            print("\n😞 No CIDs found in recent transactions")
            print("Possible issues:")
            print("1. Images are being generated on a different contract")
            print("2. The CID pattern has changed")
            print("3. Solutions are submitted to a different address")
            print("4. There's a delay between task submission and solution")
            
            # Let's also check the router contract
            router_address = '0xecAba4E6a4bC1E3DE3e996a8B2c89e8B0626C9a1'
            print(f"\n=== Checking router contract {router_address} ===")
            
            params['address'] = router_address
            try:
                response = requests.get(url, params=params, timeout=30)
                data = response.json()
                
                if data.get('result'):
                    router_transactions = data['result']
                    print(f"Found {len(router_transactions)} router transactions")
                    
                    # Look for CIDs in router transactions
                    router_cids = 0
                    for tx in router_transactions[:10]:  # Check first 10
                        try:
                            input_data = tx.get('input', '')
                            if len(input_data) > 10:
                                hex_data = input_data[2:]
                                decoded_bytes = bytes.fromhex(hex_data)
                                ascii_text = decoded_bytes.decode('utf-8', errors='ignore')
                                found_cids = re.findall(cid_pattern, ascii_text)
                                if found_cids:
                                    router_cids += 1
                                    print(f"  Router TX {tx['hash']} has CIDs: {found_cids}")
                        except:
                            continue
                    
                    if router_cids == 0:
                        print("  No CIDs found in router transactions either")
                else:
                    print("  No router transactions found")
            except Exception as e:
                print(f"  Error checking router: {e}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_recent_transactions() 