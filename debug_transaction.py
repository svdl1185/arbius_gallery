#!/usr/bin/env python
"""
Debug the specific transaction to understand the Arbius protocol
"""

import requests
import json

def decode_arbius_transaction():
    # The transaction data from the user's recent image generation
    tx_hash = "0xad80415aeccc8b31f224531a78e51453fbdc1e71e790501071c400b27dbc0899"
    expected_cid = "QmVxV7PdqK3V1VEA3nDiwcSK55N8Tq34fQxVFfSeLgc8hw"
    
    # Raw input data from the transaction
    input_data = "0x08745dd100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000708816d665eb09e5a86ba82a774dabb550bc8af5a473c70e9d7c872ac948d20546bc79db55fa64ca325a4b229aaffddb7f86aae0000000000000000000000000000000000000000000000000000c6f3b40b6c0000000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000000000000000000000000000000000000000006d7b2270726f6d7074223a2022756e64657267726f756e6420636f636b206669676874696e67204164646974696f6e616c20696e737472756374696f6e3a204d616b65207375726520746f206b65657020726573706f6e73652073686f727420616e6420636f6e736963652e227d00000000000000000000000000000000000000"
    
    print("=== Arbius Transaction Analysis ===")
    print(f"TX Hash: {tx_hash}")
    print(f"Expected CID: {expected_cid}")
    print(f"Function signature: {input_data[:10]}")
    print(f"To address: 0x9b51ef044d3486a1fb0a2d55a6e0ceeadd323e66")
    
    # Remove 0x and function selector
    hex_data = input_data[10:]
    
    print(f"\nData length: {len(hex_data)} hex characters")
    print(f"Data: {hex_data[:100]}...")
    
    # Try to decode the data
    try:
        decoded_bytes = bytes.fromhex(hex_data)
        print(f"\nDecoded bytes length: {len(decoded_bytes)}")
        
        # Look for the CID in the decoded data
        ascii_text = ""
        for byte in decoded_bytes:
            if 32 <= byte <= 126:  # Printable ASCII
                ascii_text += chr(byte)
            else:
                ascii_text += "."
        
        print(f"\nASCII representation:")
        print(f"{ascii_text}")
        
        # Look for the expected CID
        if expected_cid in ascii_text:
            print(f"\n✅ Found expected CID in transaction data!")
            cid_start = ascii_text.find(expected_cid)
            print(f"CID position: {cid_start}")
            print(f"Context: ...{ascii_text[max(0, cid_start-20):cid_start+len(expected_cid)+20]}...")
        else:
            print(f"\n❌ Expected CID not found in transaction data")
            print("This might be a submitTask transaction, not a solution submission")
            
        # Look for any IPFS CID patterns
        import re
        cid_pattern = r'Qm[1-9A-HJ-NP-Za-km-z]{44}'
        found_cids = re.findall(cid_pattern, ascii_text)
        
        print(f"\nFound CID patterns: {found_cids}")
        
        # Decode the JSON prompt if present
        if '"prompt"' in ascii_text:
            try:
                json_start = ascii_text.find('{')
                json_end = ascii_text.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = ascii_text[json_start:json_end]
                    print(f"\nFound JSON data:")
                    print(json.dumps(json.loads(json_str), indent=2))
            except Exception as e:
                print(f"Could not parse JSON: {e}")
                
    except Exception as e:
        print(f"Error decoding: {e}")

    # Now let's check if this is actually a solution transaction by looking for the corresponding task
    print(f"\n=== Looking for corresponding solution transaction ===")
    
    # The CID suggests there should be a solution transaction somewhere
    # Let's check transactions around the same time
    
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    # Get transactions around the same block
    block_num = 344216552
    start_block = block_num - 100
    end_block = block_num + 100
    
    print(f"Checking blocks {start_block} to {end_block} for solution transactions...")
    
    url = f'{base_url}?module=account&action=txlist'
    params = {
        'address': '0x9b51ef044d3486a1fb0a2d55a6e0ceeadd323e66',
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
        
        if data.get('result'):
            transactions = data['result']
            print(f"Found {len(transactions)} transactions in the range")
            
            for tx in transactions:
                input_data = tx.get('input', '')
                if len(input_data) > 10:
                    function_sig = input_data[:10]
                    
                    # Look for different function signatures that might contain CIDs
                    if expected_cid.encode().hex() in input_data[2:]:  # Look for CID in hex
                        print(f"\n🎯 Found transaction with CID!")
                        print(f"  Hash: {tx['hash']}")
                        print(f"  Function: {function_sig}")
                        print(f"  Block: {tx['blockNumber']}")
                        
                    # Also check for the CID in ASCII form
                    try:
                        decoded = bytes.fromhex(input_data[2:])
                        if expected_cid in decoded.decode('utf-8', errors='ignore'):
                            print(f"\n🎯 Found transaction with CID (ASCII)!")
                            print(f"  Hash: {tx['hash']}")
                            print(f"  Function: {function_sig}")
                            print(f"  Block: {tx['blockNumber']}")
                    except:
                        pass
        
    except Exception as e:
        print(f"Error searching for solution transaction: {e}")

if __name__ == "__main__":
    decode_arbius_transaction() 