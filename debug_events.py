import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.services import ArbitrumScanner

scanner = ArbitrumScanner()

# Get recent task submissions directly
print("🔍 Getting TaskSubmitted events and their transaction inputs...")

current_block = scanner.get_latest_block()
print(f"Current block: {current_block}")

# Get TaskSubmitted events from recent blocks
start_block = current_block - 500
logs = scanner.get_contract_logs(start_block, current_block, scanner.task_submitted_topic)
print(f"Found {len(logs)} TaskSubmitted events")

if logs:
    # Examine the first few logs and their transaction inputs
    for i, log in enumerate(logs[:3]):
        print(f"\n📋 TaskSubmitted Event {i+1}:")
        print(f"   Block: {log['blockNumber']}")
        print(f"   TxHash: {log['transactionHash']}")
        print(f"   Task ID: {log['topics'][1]}")
        
        # Get the full transaction data
        try:
            response = requests.get(f"https://api.arbiscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={log['transactionHash']}&apikey={scanner.api_key}")
            if response.status_code == 200:
                tx_data = response.json()
                if tx_data.get('result'):
                    tx = tx_data['result']
                    print(f"   Transaction input length: {len(tx['input'])} chars")
                    print(f"   Transaction input (first 200 chars): {tx['input'][:200]}...")
                    
                    # Try to extract the input parameter which should contain the prompt
                    input_data = tx['input']
                    if input_data.startswith('0x'):
                        # Remove function signature (first 10 characters including 0x)
                        param_data = input_data[10:]
                        print(f"   Function signature: {input_data[:10]}")
                        print(f"   Parameters length: {len(param_data)} chars")
                        
                        # For submitTask, parameters should be: version, owner, model, fee, input
                        # Each parameter is 64 hex chars (32 bytes), except dynamic data
                        if len(param_data) >= 320:  # At least 5*64 chars for the basic params
                            version = param_data[0:64]
                            owner = param_data[64:128]
                            model = param_data[128:192]
                            fee = param_data[192:256]
                            input_offset = param_data[256:320]
                            
                            print(f"   Version: 0x{version}")
                            print(f"   Owner: 0x{owner}")
                            print(f"   Model: 0x{model}")
                            print(f"   Fee: 0x{fee}")
                            print(f"   Input offset: 0x{input_offset}")
                            
                            # The input offset tells us where the dynamic data starts
                            try:
                                offset = int(input_offset, 16) * 2  # Convert to hex chars
                                print(f"   Input data starts at offset: {offset}")
                                
                                if len(param_data) > offset + 64:
                                    # Next 64 chars are the length of the input data
                                    input_length_hex = param_data[offset:offset+64]
                                    input_length = int(input_length_hex, 16) * 2  # Convert to hex chars
                                    print(f"   Input data length: {input_length} hex chars")
                                    
                                    # Extract the actual input data
                                    input_hex_start = offset + 64
                                    input_hex = param_data[input_hex_start:input_hex_start+input_length]
                                    print(f"   Input hex (first 200 chars): {input_hex[:200]}...")
                                    
                                    if input_hex:
                                        input_bytes = bytes.fromhex(input_hex)
                                        input_string = input_bytes.decode('utf-8', errors='ignore')
                                        print(f"   Input string: {input_string[:300]}...")
                                        
                                        # Try to parse as JSON
                                        import json
                                        try:
                                            input_params = json.loads(input_string)
                                            print(f"   Parsed JSON keys: {list(input_params.keys()) if isinstance(input_params, dict) else 'Not a dict'}")
                                            if isinstance(input_params, dict):
                                                prompt = input_params.get('prompt', 'No prompt key')
                                                print(f"   🎯 PROMPT: {prompt[:100]}..." if len(str(prompt)) > 100 else f"   🎯 PROMPT: {prompt}")
                                        except Exception as e:
                                            print(f"   JSON parse error: {e}")
                            except Exception as e:
                                print(f"   Offset parse error: {e}")
                    
        except Exception as e:
            print(f"   Error getting transaction: {e}")

# Also try searching for events with different parameters
print(f"\n🔍 Searching for events in last 100 blocks...")
task_info = scanner.get_task_information(current_block - 100, current_block)
print(f"Found {len(task_info)} TaskSubmitted events")

for task_id, data in task_info.items():
    print(f"Task {task_id}: {data}") 