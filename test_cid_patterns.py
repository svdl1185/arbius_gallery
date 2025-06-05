#!/usr/bin/env python
"""
Test CID patterns with faster validation
"""

import requests
import base58
import time

def test_cid_patterns():
    # Known working CIDs to validate our approach
    known_working_cids = [
        'QmVxV7PdqK3V1VEA3nDiwcSK55N8Tq34fQxVFfSeLgc8hw',
        'QmSFiVCnGvP7dmNKfydagzwnQi6sUWjBEFrEYgFbWYFXMB'
    ]
    
    # Transaction with multihashes
    tx_hash = "0x929e8b0e7df63e3033458270eba4a7ae81d9cdada3b740e2a2f7d6eff4e668ed"
    
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    print("=== TESTING CID PATTERNS ===")
    
    # First, validate our known working CIDs
    print("\n1. Testing known working CIDs:")
    for cid in known_working_cids:
        print(f"Testing {cid}...")
        try:
            # Decode to multihash
            multihash = base58.b58decode(cid)
            print(f"  Multihash: {multihash.hex()}")
            
            # Test IPFS
            test_url = f"https://ipfs.arbius.org/ipfs/{cid}/out-1.png"
            response = requests.head(test_url, timeout=3)
            print(f"  Status: {response.status_code} ✅")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Now test our transaction
    print(f"\n2. Analyzing transaction {tx_hash}...")
    
    try:
        # Get transaction data
        url = f"{base_url}?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={api_key}"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        if not data.get('result'):
            print("❌ Could not fetch transaction data")
            return
            
        tx_data = data['result']
        input_data = tx_data['input']
        hex_data = input_data[2:]  # Remove 0x
        
        # Convert to bytes
        all_bytes = bytes.fromhex(hex_data)
        print(f"Transaction data length: {len(all_bytes)} bytes")
        
        # Look for our known CIDs as multihashes in the transaction
        print(f"\n3. Searching for known CIDs in transaction data:")
        
        for cid in known_working_cids:
            try:
                multihash = base58.b58decode(cid)
                pos = all_bytes.find(multihash)
                if pos != -1:
                    print(f"🎯 Found {cid} at position {pos}!")
                    print(f"   Multihash: {multihash.hex()}")
                else:
                    print(f"❌ {cid} not found in transaction")
            except Exception as e:
                print(f"Error processing {cid}: {e}")
        
        # Look for SHA2-256 pattern and test systematically
        print(f"\n4. Testing multihashes systematically:")
        pattern = bytes.fromhex('1220')  # SHA2-256, 32 bytes
        
        positions = []
        pos = 0
        while True:
            pos = all_bytes.find(pattern, pos)
            if pos == -1:
                break
            positions.append(pos)
            pos += 1
        
        print(f"Found {len(positions)} potential multihash positions")
        
        # Test a sample with very short timeout
        tested = 0
        working = 0
        
        for i, position in enumerate(positions):
            if tested >= 10:  # Test first 10 only
                break
                
            if position + 34 <= len(all_bytes):
                multihash = all_bytes[position:position+34]
                
                try:
                    cid_candidate = base58.b58encode(multihash).decode()
                    
                    if cid_candidate.startswith('Qm') and len(cid_candidate) == 46:
                        tested += 1
                        print(f"\nTesting #{tested}: {cid_candidate}")
                        
                        # Quick test with very short timeout
                        test_url = f"https://ipfs.arbius.org/ipfs/{cid_candidate}/out-1.png"
                        try:
                            response = requests.head(test_url, timeout=2)
                            if response.status_code == 200:
                                working += 1
                                size = response.headers.get('content-length', 'unknown')
                                print(f"  ✅ WORKING! Size: {size} bytes")
                            else:
                                print(f"  ❌ Status: {response.status_code}")
                        except requests.exceptions.Timeout:
                            print(f"  ⏱️ Timeout")
                        except Exception as e:
                            print(f"  ❓ Error: {e}")
                        
                        # Small delay to be nice
                        time.sleep(0.1)
                        
                except Exception as e:
                    print(f"Error at position {position}: {e}")
        
        print(f"\n=== SUMMARY ===")
        print(f"Multihash positions found: {len(positions)}")
        print(f"Valid CID candidates tested: {tested}")
        print(f"Working CIDs found: {working}")
        
        if working > 0:
            print(f"\n🎉 SUCCESS! The pattern works - we can extract CIDs from submitSolution transactions!")
        else:
            print(f"\n🤔 Pattern found but no working CIDs in sample. May need to:")
            print(f"   - Test more candidates")
            print(f"   - Check if these are different types of multihashes")
            print(f"   - Verify the transaction contains the expected content")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_cid_patterns() 