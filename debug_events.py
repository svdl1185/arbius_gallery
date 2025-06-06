import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.services import ArbitrumScanner

scanner = ArbitrumScanner()

# Get a recent transaction from the engine to see its events
print("🔍 Getting recent transactions to examine events...")

current_block = scanner.get_latest_block()
print(f"Current block: {current_block}")

# Get recent transactions
transactions = scanner.get_contract_transactions(current_block - 1000, current_block)
print(f"Found {len(transactions)} recent transactions")

if transactions:
    # Look at a few recent transactions
    for i, tx in enumerate(transactions[:5]):
        print(f"\n📋 Transaction {i+1}: {tx['hash']}")
        print(f"   Block: {tx['blockNumber']}")
        print(f"   Input: {tx['input'][:50]}...")
        
        # Get transaction receipt to see events
        try:
            response = requests.get(f"https://api.arbiscan.io/api?module=proxy&action=eth_getTransactionReceipt&txhash={tx['hash']}&apikey={scanner.api_key}")
            if response.status_code == 200:
                receipt_data = response.json()
                if receipt_data.get('result'):
                    receipt = receipt_data['result']
                    logs = receipt.get('logs', [])
                    print(f"   Events: {len(logs)} logs found")
                    
                    for j, log in enumerate(logs):
                        print(f"     Log {j+1}: Contract {log['address']}")
                        if len(log['topics']) > 0:
                            print(f"       Topic0: {log['topics'][0]}")
                            if log['topics'][0] == '0xc3d3e0544c80e3bb83f62659259ae1574f72a91515ab3cae3dd75cf77e1b0aea':
                                print("       🎯 FOUND TaskSubmitted event!")
                                # Try to parse it
                                try:
                                    task_data = scanner.parse_task_submitted_event(log)
                                    if task_data:
                                        print(f"         Parsed: {task_data}")
                                except Exception as e:
                                    print(f"         Parse error: {e}")
                        
        except Exception as e:
            print(f"   Error getting receipt: {e}")

# Also try searching for events with different parameters
print(f"\n🔍 Searching for events in last 100 blocks...")
task_info = scanner.get_task_information(current_block - 100, current_block)
print(f"Found {len(task_info)} TaskSubmitted events")

for task_id, data in task_info.items():
    print(f"Task {task_id}: {data}") 