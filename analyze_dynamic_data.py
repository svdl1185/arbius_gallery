#!/usr/bin/env python
"""
Focused analysis of dynamic data sections in submitSolution transactions
"""

import requests
import re
import struct

def analyze_dynamic_data():
    # Transaction with the most promising dynamic data
    tx_hash = "0x929e8b0e7df63e3033458270eba4a7ae81d9cdada3b740e2a2f7d6eff4e668ed"
    
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    print("=== FOCUSED DYNAMIC DATA ANALYSIS ===")
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
        
        print(f"Function signature: {input_data[:10]}")
        print(f"Total hex length: {len(hex_data)} chars")
        
        # Parse ABI structure
        function_selector = hex_data[:8]
        params_data = hex_data[8:]
        
        print(f"\n=== ABI PARAMETER ANALYSIS ===")
        
        # First parameter: offset to dynamic data (should be 64)
        offset1_hex = params_data[:64]
        offset1 = int(offset1_hex, 16)
        print(f"First parameter (offset): {offset1}")
        
        # Second parameter: another offset 
        offset2_hex = params_data[64:128]
        offset2 = int(offset2_hex, 16)
        print(f"Second parameter (offset): {offset2}")
        
        # Third parameter: length or another value
        param3_hex = params_data[128:192]
        param3 = int(param3_hex, 16)
        print(f"Third parameter: {param3}")
        
        # Analyze dynamic data at offset 64 (128 hex chars from start of params)
        print(f"\n=== DYNAMIC DATA AT OFFSET {offset1} ===")
        
        byte_offset = offset1 * 2  # Convert to hex chars
        if byte_offset < len(params_data):
            # First 32 bytes at offset should be length
            length_hex = params_data[byte_offset:byte_offset+64]
            data_length = int(length_hex, 16)
            print(f"Data length: {data_length} bytes")
            
            # Actual data starts after length
            data_start = byte_offset + 64
            data_end = data_start + (data_length * 2)
            
            if data_end <= len(params_data):
                data_hex = params_data[data_start:data_end]
                data_bytes = bytes.fromhex(data_hex)
                
                print(f"Raw data ({data_length} bytes):")
                print(f"  Hex: {data_hex[:100]}...")
                
                # Try different interpretations
                analyze_data_structure(data_bytes, "Primary Data")
        
        # Analyze second dynamic data section
        if offset2 > offset1 and offset2 * 2 < len(params_data):
            print(f"\n=== DYNAMIC DATA AT OFFSET {offset2} ===")
            
            byte_offset2 = offset2 * 2
            length_hex2 = params_data[byte_offset2:byte_offset2+64]
            data_length2 = int(length_hex2, 16)
            print(f"Data length: {data_length2} bytes")
            
            data_start2 = byte_offset2 + 64
            data_end2 = data_start2 + (data_length2 * 2)
            
            if data_end2 <= len(params_data):
                data_hex2 = params_data[data_start2:data_end2]
                data_bytes2 = bytes.fromhex(data_hex2)
                
                analyze_data_structure(data_bytes2, "Secondary Data")
        
        # Look for specific patterns that might indicate IPFS content
        print(f"\n=== IPFS PATTERN ANALYSIS ===")
        analyze_ipfs_patterns(params_data)
        
    except Exception as e:
        print(f"❌ Error: {e}")

def analyze_data_structure(data_bytes: bytes, section_name: str):
    """Analyze the structure of a data section"""
    print(f"\n--- {section_name} Structure Analysis ---")
    
    # Basic info
    print(f"Length: {len(data_bytes)} bytes")
    print(f"First 50 bytes (hex): {data_bytes[:50].hex()}")
    
    # Try to decode as text
    try:
        text = data_bytes.decode('utf-8', errors='ignore')
        clean_text = ''.join(c for c in text if c.isprintable())
        if clean_text:
            print(f"As text: '{clean_text[:100]}...'")
    except:
        pass
    
    # Look for 32-byte boundaries (common in Ethereum)
    print(f"\n32-byte chunk analysis:")
    for i in range(0, min(len(data_bytes), 128), 32):  # First 4 chunks
        chunk = data_bytes[i:i+32]
        if len(chunk) == 32:
            # Try as integer
            try:
                int_val = int.from_bytes(chunk, 'big')
                print(f"  Chunk {i//32}: {chunk.hex()}")
                if int_val < 10**10:  # Reasonable number
                    print(f"           As int: {int_val}")
                # Try as address
                if chunk[:12] == b'\x00' * 12:  # Address-like (padded)
                    addr = '0x' + chunk[12:].hex()
                    print(f"           As addr: {addr}")
            except:
                pass
            
            # Try as text
            try:
                chunk_text = chunk.decode('utf-8', errors='ignore').strip('\x00')
                if chunk_text and len(chunk_text) > 2:
                    clean = ''.join(c for c in chunk_text if c.isprintable())
                    if clean:
                        print(f"           As text: '{clean}'")
            except:
                pass
    
    # Look for specific IPFS patterns
    print(f"\nIPFS pattern search:")
    
    # Search for CID patterns
    text = data_bytes.decode('utf-8', errors='ignore')
    
    # Look for 'Qm' patterns
    qm_positions = [m.start() for m in re.finditer(r'Qm', text)]
    if qm_positions:
        print(f"  Found 'Qm' at positions: {qm_positions}")
        for pos in qm_positions[:3]:
            context = text[max(0,pos-10):pos+50]
            print(f"    Context: '{context}'")
    
    # Look for hash-like patterns (32 bytes)
    for i in range(0, len(data_bytes)-32, 4):
        chunk = data_bytes[i:i+32]
        # Check if this looks like a hash (high entropy)
        if len(set(chunk)) > 20:  # Good entropy
            # Check if next 32 bytes might be related
            if i + 64 <= len(data_bytes):
                next_chunk = data_bytes[i+32:i+64]
                print(f"  Potential hash at {i}: {chunk.hex()}")
                print(f"    Next 32 bytes: {next_chunk.hex()}")
                
                # Try to decode as IPFS multihash
                if chunk[0] in [0x12, 0x16, 0x1B]:  # Common multihash prefixes
                    print(f"    Possible multihash (prefix: 0x{chunk[0]:02x})")
                break
    
    # Look for base58-encoded data
    try:
        # Find longest base58-like sequence
        base58_chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        base58_sequences = re.findall(f'[{re.escape(base58_chars)}]{{20,}}', text)
        if base58_sequences:
            print(f"  Base58-like sequences: {base58_sequences[:3]}")
    except:
        pass

def analyze_ipfs_patterns(params_data: str):
    """Look for IPFS-specific patterns in the parameter data"""
    print("Searching for IPFS content identifiers...")
    
    # Convert to bytes for analysis
    try:
        all_bytes = bytes.fromhex(params_data)
        
        # Look for multihash prefixes
        multihash_prefixes = {
            0x12: "SHA2-256",
            0x16: "SHA3-256", 
            0x1B: "SHA2-512",
            0x13: "SHA1"
        }
        
        print("\nMultihash prefix search:")
        for i in range(len(all_bytes) - 34):  # Minimum hash size
            byte_val = all_bytes[i]
            if byte_val in multihash_prefixes:
                # Check if next byte is reasonable length
                if i + 1 < len(all_bytes):
                    length = all_bytes[i + 1]
                    if length in [32, 20, 64]:  # Common hash lengths
                        hash_end = i + 2 + length
                        if hash_end <= len(all_bytes):
                            hash_data = all_bytes[i:hash_end]
                            print(f"  Found {multihash_prefixes[byte_val]} hash at position {i}")
                            print(f"    Length: {length} bytes")
                            print(f"    Hash: {hash_data.hex()}")
                            
                            # Try to construct CID
                            try:
                                # Simple CIDv0 construction (base58)
                                import base58
                                cid_candidate = base58.b58encode(hash_data).decode()
                                if cid_candidate.startswith('Qm') and len(cid_candidate) == 46:
                                    print(f"    Potential CID: {cid_candidate}")
                                    
                                    # Test it!
                                    test_url = f"https://ipfs.arbius.org/ipfs/{cid_candidate}/out-1.png"
                                    try:
                                        head_response = requests.head(test_url, timeout=5)
                                        if head_response.status_code == 200:
                                            print(f"    🎯 WORKING CID FOUND: {cid_candidate}")
                                            return cid_candidate
                                    except:
                                        pass
                            except ImportError:
                                print("    (base58 module not available for CID construction)")
                            except:
                                pass
        
        # Look for the specific pattern: 0x1220 followed by 32 bytes (SHA2-256 multihash)
        print("\nSearching for SHA2-256 multihash pattern (0x1220 + 32 bytes):")
        pattern = bytes.fromhex('1220')  # SHA2-256, 32 bytes
        pos = 0
        while True:
            pos = all_bytes.find(pattern, pos)
            if pos == -1:
                break
                
            if pos + 34 <= len(all_bytes):  # 2 + 32 bytes
                multihash = all_bytes[pos:pos+34]
                print(f"  SHA2-256 multihash at position {pos}: {multihash.hex()}")
                
                # Try to construct CID
                try:
                    import base58
                    # Add CIDv0 prefix (0x00 for raw binary)
                    cid_bytes = multihash
                    cid_candidate = base58.b58encode(cid_bytes).decode()
                    print(f"    Candidate CID: {cid_candidate}")
                    
                    if len(cid_candidate) >= 44:  # Reasonable CID length
                        # Test it
                        test_url = f"https://ipfs.arbius.org/ipfs/{cid_candidate}/out-1.png"
                        try:
                            head_response = requests.head(test_url, timeout=5)
                            if head_response.status_code == 200:
                                print(f"    🎯🎯 VALID CID DISCOVERED: {cid_candidate}")
                                return cid_candidate
                        except:
                            pass
                except ImportError:
                    print("    (base58 module not available)")
                except:
                    pass
            
            pos += 1
    
    except Exception as e:
        print(f"Error in IPFS analysis: {e}")
    
    return None

if __name__ == "__main__":
    analyze_dynamic_data() 