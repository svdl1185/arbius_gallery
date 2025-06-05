#!/usr/bin/env python
"""
Track a specific task and look for its solution
"""

import requests
import json
import time
import os
import sys
import django

# Set up Django environment
sys.path.append('/Users/biba/Documents/Projects/arbius_gallery')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.models import ArbiusImage

def track_task_solution():
    # Your specific task data
    task_tx_hash = "0x3a2e652b7ed8809540a5d275d12b45440430e36f0dc70bd2ff9277944d01acaf"
    expected_cid = "QmSFiVCnGvP7dmNKfydagzwnQi6sUWjBEFrEYgFbWYFXMB"
    task_id = "A308F9A58F7943314909A0C5B7E1C01B1888B905F339AFE1F7B0D17F9FB178DB"  # From the TaskSubmitted event
    
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    engine_address = '0x9b51ef044d3486a1fb0a2d55a6e0ceeadd323e66'
    
    print(f"=== Tracking Task Solution ===")
    print(f"Task TX: {task_tx_hash}")
    print(f"Task ID: {task_id}")
    print(f"Expected CID: {expected_cid}")
    
    # 1. First check if image is available on IPFS
    ipfs_url = f"https://ipfs.arbius.org/ipfs/{expected_cid}/out-1.png"
    print(f"\n1. Checking IPFS availability: {ipfs_url}")
    
    try:
        response = requests.head(ipfs_url, timeout=10)
        if response.status_code == 200:
            print(f"✅ Image exists on IPFS! Size: {response.headers.get('content-length', 'unknown')} bytes")
        else:
            print(f"❌ Image not yet available on IPFS ({response.status_code})")
            return
    except Exception as e:
        print(f"❌ Error checking IPFS: {e}")
        return
    
    # 2. Look for submitSolution transaction
    print(f"\n2. Looking for submitSolution transaction...")
    
    # Get latest block
    try:
        url = f"{base_url}?module=proxy&action=eth_blockNumber&apikey={api_key}"
        response = requests.get(url, timeout=30)
        data = response.json()
        latest_block = int(data['result'], 16) if data.get('result') else 344220000
        print(f"Latest block: {latest_block}")
    except Exception as e:
        print(f"Error getting latest block: {e}")
        latest_block = 344220000
    
    # Search for solution in recent blocks (solutions should come after the task)
    task_block = 344220100  # From the task transaction
    search_start = task_block
    search_end = latest_block + 100  # Look a bit into the future
    
    print(f"Searching blocks {search_start} to {search_end} for submitSolution...")
    
    # Search in chunks
    chunk_size = 1000
    solution_found = False
    
    for chunk_start in range(search_start, search_end, chunk_size):
        chunk_end = min(chunk_start + chunk_size - 1, search_end)
        
        print(f"  Checking blocks {chunk_start} to {chunk_end}...")
        
        url = f'{base_url}?module=account&action=txlist'
        params = {
            'address': engine_address,
            'startblock': chunk_start,
            'endblock': chunk_end,
            'page': 1,
            'offset': 100,
            'sort': 'asc',
            'apikey': api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if not data.get('result'):
                continue
                
            transactions = data['result']
            print(f"    Found {len(transactions)} transactions")
            
            for tx in transactions:
                input_data = tx.get('input', '')
                
                # Check if this is a submitSolution transaction
                if input_data.startswith('0x5f2a8b8d'):  # submitSolution signature
                    print(f"    🎯 Found submitSolution: {tx['hash']}")
                    
                    # Check if it references our task ID
                    try:
                        hex_data = input_data[10:]  # Remove 0x and function selector
                        if len(hex_data) >= 64:
                            solution_task_id = '0x' + hex_data[:64]
                            print(f"       Task ID in solution: {solution_task_id}")
                            
                            if solution_task_id.lower() == ('0x' + task_id).lower():
                                print(f"    ✅ This solution is for our task!")
                                
                                # Extract CID from solution
                                try:
                                    decoded_bytes = bytes.fromhex(hex_data)
                                    ascii_text = decoded_bytes.decode('utf-8', errors='ignore')
                                    
                                    if expected_cid in ascii_text:
                                        print(f"    🎯 Found our CID in the solution!")
                                        print(f"       Transaction: {tx['hash']}")
                                        print(f"       Block: {tx['blockNumber']}")
                                        print(f"       From (Miner): {tx['from']}")
                                        print(f"       Gas Used: {tx.get('gasUsed', 'N/A')}")
                                        
                                        # Update our database entry with the correct solution transaction
                                        try:
                                            image = ArbiusImage.objects.get(cid=expected_cid)
                                            print(f"    📝 Updating database entry...")
                                            print(f"       Old TX: {image.transaction_hash}")
                                            print(f"       New TX: {tx['hash']}")
                                            
                                            # Update with solution transaction details
                                            image.transaction_hash = tx['hash']
                                            image.task_id = '0x' + task_id
                                            image.miner_address = tx['from']
                                            image.block_number = int(tx['blockNumber'])
                                            if tx.get('gasUsed'):
                                                image.gas_used = int(tx['gasUsed'])
                                            image.save()
                                            
                                            print(f"    ✅ Database updated successfully!")
                                            
                                        except ArbiusImage.DoesNotExist:
                                            print(f"    ❌ Image not found in database")
                                        except Exception as e:
                                            print(f"    ❌ Error updating database: {e}")
                                        
                                        solution_found = True
                                        break
                                    else:
                                        print(f"       Different CID in this solution")
                                except Exception as e:
                                    print(f"       Error extracting CID from solution: {e}")
                            else:
                                print(f"       Different task ID")
                    except Exception as e:
                        print(f"       Error parsing solution: {e}")
                
            if solution_found:
                break
                
        except Exception as e:
            print(f"  Error: {e}")
            continue
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
    
    if not solution_found:
        print(f"\n😞 Solution transaction not found yet")
        print(f"Possible reasons:")
        print(f"1. The solution hasn't been submitted to the blockchain yet")
        print(f"2. The solution is in a block range we haven't checked")
        print(f"3. The miner is still processing the task")
        print(f"4. The solution went to a different contract")
        
        print(f"\n💡 Since the image exists on IPFS, the task has been processed!")
        print(f"The solution transaction may appear later or use a different pattern.")
    else:
        print(f"\n🎉 Task solution tracking complete!")

if __name__ == "__main__":
    track_task_solution() 