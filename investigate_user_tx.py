#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.services import ArbitrumScanner
import requests

def investigate_transaction():
    scanner = ArbitrumScanner()
    tx_hash = '0xe9e87ee1efbac0610749e3ac7fb29c81cd232995e80145b177647847741a5dfd'
    target_cid = 'QmbyvKZWwbQvePx8eMz9XhGS9t239D4Rprxd4EgkE4Jhf7'

    print(f'🔍 Investigating transaction: {tx_hash}')
    print(f'🎯 Looking for CID: {target_cid}')
    
    # Get transaction details
    url = f'{scanner.base_url}?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={scanner.api_key}'
    response = requests.get(url, timeout=30)
    data = response.json()

    if data.get('result'):
        tx = data['result']
        block_number = int(tx["blockNumber"], 16)
        print(f'📦 Block number: {block_number}')
        print(f'📬 To address: {tx["to"]}')
        print(f'🏭 Engine address: {scanner.engine_address}')
        print(f'📝 Function signature: {tx["input"][:10]}')
        print(f'🔧 submitSolution sig: {scanner.submit_solution_sig}')
        print(f'🔧 submitTask sig: {scanner.submit_task_sig}')
        
        print(f'\n📊 Transaction Analysis:')
        is_engine = tx["to"].lower() == scanner.engine_address.lower()
        is_submit_solution = tx["input"].startswith(scanner.submit_solution_sig)
        is_submit_task = tx["input"].startswith(scanner.submit_task_sig)
        
        print(f'  ✅ To engine contract: {is_engine}')
        print(f'  ✅ Is submitSolution: {is_submit_solution}')
        print(f'  ✅ Is submitTask: {is_submit_task}')
        
        if is_submit_solution:
            print(f'\n🔍 Extracting CIDs from submitSolution...')
            cids = scanner.extract_cids_from_solution(tx)
            print(f'📈 CIDs extracted: {len(cids)}')
            
            if cids:
                print(f'🎯 First 10 CIDs:')
                for i, cid in enumerate(cids[:10]):
                    marker = " ⭐ TARGET!" if cid == target_cid else ""
                    print(f'  {i+1}: {cid}{marker}')
                
                if target_cid in cids:
                    print(f'\n✅ SUCCESS! Found target CID: {target_cid}')
                    print(f'📍 Position in list: {cids.index(target_cid) + 1}')
                else:
                    print(f'\n❌ FAILURE! Target CID {target_cid} NOT found in extracted CIDs')
                    
                    # Check if it's a partial match issue
                    partial_matches = [cid for cid in cids if target_cid[:20] in cid or cid[:20] in target_cid]
                    if partial_matches:
                        print(f'🔍 Partial matches found: {partial_matches}')
            else:
                print(f'❌ No CIDs extracted!')
                
        elif is_submit_task:
            print(f'\n💡 This is a submitTask transaction (task creation), not submitSolution')
            print(f'   submitTask contains the prompt, not the CID')
            print(f'   We need to wait for the corresponding submitSolution transaction')
            
        elif is_engine:
            print(f'\n🤔 Transaction to engine contract but unknown function signature')
            print(f'   Input data: {tx["input"][:100]}...')
            
        else:
            print(f'\n❌ Transaction not to engine contract or unrecognized')
            
        # Check if our scanner would have seen this block
        latest_scanned = scanner.get_latest_block()
        print(f'\n📊 Block Status:')
        print(f'  📦 Transaction block: {block_number}')
        print(f'  🔍 Latest block: {latest_scanned}')
        print(f'  📍 Blocks behind: {latest_scanned - block_number}')
        
        if latest_scanned >= block_number:
            print(f'  ✅ This block should have been scanned')
        else:
            print(f'  ⏳ This block is too new, not scanned yet')
            
    else:
        print(f'❌ Transaction not found or API error: {data}')

if __name__ == "__main__":
    investigate_transaction() 