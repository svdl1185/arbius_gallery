#!/usr/bin/env python
"""
Analyze actual submitSolution transaction to understand the format
"""

import requests
import re

def analyze_real_solution():
    # Real submitSolution transaction we found (different miner)
    solution_tx = "0x929e8b0e7df63e3033458270eba4a7ae81d9cdada3b740e2a2f7d6eff4e668ed"
    
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    print(f"=== Analyzing Real submitSolution Transaction ===")
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
                
                print(f"\nASCII representation (first 500 chars):")
                clean_text = ''.join(c for c in ascii_text if c.isprintable())
                print(f"{clean_text[:500]}...")
                
                # Look for CID patterns
                cid_pattern = r'Qm[1-9A-HJ-NP-Za-km-z]{44}'
                found_cids = re.findall(cid_pattern, ascii_text)
                
                print(f"\nCIDs found: {len(found_cids)}")
                for i, cid in enumerate(found_cids[:5]):  # Show first 5
                    print(f"  {i+1}. {cid}")
                    
                    # Check if this image exists
                    test_url = f"https://ipfs.arbius.org/ipfs/{cid}/out-1.png"
                    try:
                        head_response = requests.head(test_url, timeout=5)
                        accessible = "✅" if head_response.status_code == 200 else "❌"
                        size = head_response.headers.get('content-length', 'unknown')
                        print(f"     IPFS: {accessible} ({size} bytes)")
                    except:
                        print(f"     IPFS: ❓")
                
                # Try to extract task ID (usually at the beginning after function selector)
                print(f"\nAnalyzing transaction structure:")
                print(f"Function selector: {input_data[:10]}")
                
                # The data after function selector
                params_hex = input_data[10:]
                print(f"Parameters length: {len(params_hex)} hex chars")
                
                if len(params_hex) >= 64:
                    # First 32 bytes might be task ID
                    potential_task_id = params_hex[:64]
                    print(f"Potential task ID: 0x{potential_task_id}")
                    
                    # Look for this task ID in recent TaskSubmitted events
                    print(f"\nLooking for corresponding task submission...")
                    
                    # Search for TaskSubmitted events with this task ID
                    latest_url = f"{base_url}?module=proxy&action=eth_blockNumber&apikey={api_key}"
                    latest_response = requests.get(latest_url, timeout=30)
                    latest_data = latest_response.json()
                    latest_block = int(latest_data['result'], 16) if latest_data.get('result') else 344220000
                    
                    search_start = latest_block - 10000  # Look back 10k blocks
                    search_end = int(tx_data['blockNumber'], 16)  # Up to solution block
                    
                    # Search for TaskSubmitted events
                    logs_url = f"{base_url}?module=logs&action=getLogs"
                    logs_params = {
                        'address': '0x9b51ef044d3486a1fb0a2d55a6e0ceeadd323e66',
                        'fromBlock': search_start,
                        'toBlock': search_end,
                        'topic0': '0xc3d3e0544c80e3bb83f62659259ae1574f72a91515ab3cae3dd75cf77e1b0aea',
                        'topic1': f'0x{potential_task_id}',
                        'apikey': api_key
                    }
                    
                    logs_response = requests.get(logs_url, params=logs_params, timeout=30)
                    logs_data = logs_response.json()
                    
                    if logs_data.get('status') == '1' and logs_data.get('result'):
                        task_events = logs_data['result']
                        print(f"🎯 Found {len(task_events)} matching TaskSubmitted event(s)!")
                        
                        for event in task_events:
                            print(f"  Task TX: {event['transactionHash']}")
                            print(f"  Task Block: {int(event['blockNumber'], 16)}")
                            print(f"  Submitter: 0x{event['topics'][3][-40:]}")
                            
                            # Calculate time between task and solution
                            task_block = int(event['blockNumber'], 16)
                            solution_block = int(tx_data['blockNumber'], 16)
                            block_diff = solution_block - task_block
                            print(f"  Blocks between task and solution: {block_diff}")
                            
                    else:
                        print(f"❌ No matching TaskSubmitted event found")
                
            except Exception as e:
                print(f"Error decoding transaction: {e}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_real_solution() 