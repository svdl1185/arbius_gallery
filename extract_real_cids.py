#!/usr/bin/env python
"""
Extract and test actual IPFS CIDs from the discovered multihashes
"""

import requests
import base58

def extract_real_cids():
    # Transaction with the multihashes we discovered
    tx_hash = "0x929e8b0e7df63e3033458270eba4a7ae81d9cdada3b740e2a2f7d6eff4e668ed"
    
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    print("=== EXTRACTING REAL CIDs FROM MULTIHASHES ===")
    print(f"Analyzing transaction: {tx_hash}")
    
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
        
        # Convert to bytes for analysis
        all_bytes = bytes.fromhex(hex_data)
        
        print(f"Transaction data length: {len(all_bytes)} bytes")
        
        # Look for SHA2-256 multihash pattern (0x1220 + 32 bytes)
        pattern = bytes.fromhex('1220')  # SHA2-256, 32 bytes
        multihashes_found = []
        working_cids = []
        
        pos = 0
        while True:
            pos = all_bytes.find(pattern, pos)
            if pos == -1:
                break
                
            if pos + 34 <= len(all_bytes):  # 2 + 32 bytes
                multihash = all_bytes[pos:pos+34]
                multihashes_found.append((pos, multihash))
            
            pos += 1
        
        print(f"Found {len(multihashes_found)} SHA2-256 multihashes")
        
        # Test each multihash as a potential CID
        for i, (position, multihash) in enumerate(multihashes_found):
            if i >= 20:  # Test first 20 to avoid rate limiting
                break
                
            try:
                # Convert multihash to base58 (CIDv0 format)
                cid_candidate = base58.b58encode(multihash).decode()
                
                # CIDv0 should start with 'Qm' and be 46 characters
                if cid_candidate.startswith('Qm') and len(cid_candidate) == 46:
                    print(f"\nCandidate #{i+1} (position {position}):")
                    print(f"  Multihash: {multihash.hex()}")
                    print(f"  CID: {cid_candidate}")
                    
                    # Test if this CID works on IPFS
                    test_url = f"https://ipfs.arbius.org/ipfs/{cid_candidate}/out-1.png"
                    try:
                        head_response = requests.head(test_url, timeout=10)
                        if head_response.status_code == 200:
                            size = head_response.headers.get('content-length', 'unknown')
                            print(f"  🎯🎯🎯 WORKING CID FOUND! Size: {size} bytes")
                            print(f"  URL: {test_url}")
                            working_cids.append(cid_candidate)
                        else:
                            print(f"  ❌ Not accessible ({head_response.status_code})")
                    except Exception as e:
                        print(f"  ❓ Test failed: {e}")
                        
            except Exception as e:
                print(f"  Error processing multihash at {position}: {e}")
        
        # Summary
        print(f"\n=== SUMMARY ===")
        print(f"Total multihashes found: {len(multihashes_found)}")
        print(f"Working CIDs discovered: {len(working_cids)}")
        
        if working_cids:
            print(f"\n🎉 SUCCESS! Found working CIDs:")
            for cid in working_cids:
                print(f"  ✅ {cid}")
            
            # Now let's update our scanner to use this method!
            print(f"\n💡 This proves that CIDs are stored as raw multihashes in submitSolution transactions!")
            print(f"We can now implement automatic CID extraction in our scanner.")
        else:
            print(f"\n😞 No working CIDs found in the first 20 candidates")
            print(f"The pattern is correct but we may need to test more multihashes")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    extract_real_cids() 