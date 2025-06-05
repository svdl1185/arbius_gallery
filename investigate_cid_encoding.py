#!/usr/bin/env python
"""
Comprehensive investigation of CID encoding in Arbius submitSolution transactions
"""

import requests
import re
import base64
import binascii
from typing import List, Dict, Any

def investigate_cid_encoding():
    # Real submitSolution transactions with known CID patterns
    test_transactions = [
        {
            'hash': '0x929e8b0e7df63e3033458270eba4a7ae81d9cdada3b740e2a2f7d6eff4e668ed',
            'description': 'Transaction with Qm fragments found',
            'qm_positions': [1415, 14001, 17098]
        },
        {
            'hash': '0xc4cfff13512cab8286d3ac27efa7d42860d6fabc103de6acb1e4d5777faee2fa',
            'description': 'First solution transaction found',
            'qm_positions': []
        },
        {
            'hash': '0xd95b9f64ed11d0c6692dc31e84320ec2bbafd27bb0f2aeaff20093d28025d91c',
            'description': 'Second solution transaction found',
            'qm_positions': []
        }
    ]
    
    # Known working CIDs for pattern matching
    known_cids = [
        'QmVxV7PdqK3V1VEA3nDiwcSK55N8Tq34fQxVFfSeLgc8hw',
        'QmSFiVCnGvP7dmNKfydagzwnQi6sUWjBEFrEYgFbWYFXMB'
    ]
    
    api_key = 'RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D'
    base_url = 'https://api.arbiscan.io/api'
    
    print("=== COMPREHENSIVE CID ENCODING INVESTIGATION ===")
    
    for tx_info in test_transactions:
        tx_hash = tx_info['hash']
        print(f"\n{'='*60}")
        print(f"Analyzing: {tx_info['description']}")
        print(f"TX: {tx_hash}")
        print(f"{'='*60}")
        
        try:
            # Get transaction data
            url = f"{base_url}?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={api_key}"
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if not data.get('result'):
                print("❌ Could not fetch transaction data")
                continue
                
            tx_data = data['result']
            input_data = tx_data['input']
            hex_data = input_data[2:]  # Remove 0x
            
            print(f"Function signature: {input_data[:10]}")
            print(f"Total input length: {len(input_data)} chars")
            print(f"Hex data length: {len(hex_data)} chars")
            print(f"Raw bytes length: {len(hex_data)//2} bytes")
            
            # Convert to raw bytes
            raw_bytes = bytes.fromhex(hex_data)
            
            # === METHOD 1: Direct Text Search ===
            print(f"\n--- METHOD 1: Direct Text Search ---")
            search_known_cids_in_data(raw_bytes, known_cids)
            
            # === METHOD 2: Encoding Detection ===
            print(f"\n--- METHOD 2: Multiple Encoding Analysis ---")
            analyze_multiple_encodings(raw_bytes, known_cids)
            
            # === METHOD 3: ABI Structure Analysis ===
            print(f"\n--- METHOD 3: ABI Structure Analysis ---")
            analyze_abi_structure(hex_data)
            
            # === METHOD 4: Compression Analysis ===
            print(f"\n--- METHOD 4: Compression Analysis ---")
            analyze_compression_patterns(raw_bytes, known_cids)
            
            # === METHOD 5: Fragment Reconstruction ===
            print(f"\n--- METHOD 5: Fragment Analysis ---")
            if tx_info['qm_positions']:
                analyze_qm_fragments(raw_bytes, tx_info['qm_positions'])
            else:
                find_and_analyze_fragments(raw_bytes)
            
            # === METHOD 6: Statistical Analysis ===
            print(f"\n--- METHOD 6: Statistical Patterns ---")
            analyze_statistical_patterns(raw_bytes)
            
        except Exception as e:
            print(f"❌ Error analyzing transaction: {e}")

def search_known_cids_in_data(raw_bytes: bytes, known_cids: List[str]):
    """Search for known CIDs in various encodings"""
    print("Searching for known CIDs in raw data...")
    
    # Try different text encodings
    encodings = ['utf-8', 'latin1', 'ascii', 'utf-16', 'utf-32']
    
    for encoding in encodings:
        try:
            text = raw_bytes.decode(encoding, errors='ignore')
            for cid in known_cids:
                if cid in text:
                    pos = text.find(cid)
                    print(f"🎯 Found CID '{cid}' in {encoding} at position {pos}!")
                    return True
        except:
            continue
    
    # Try hex search (CID encoded as hex)
    for cid in known_cids:
        cid_hex = cid.encode().hex()
        if cid_hex in raw_bytes.hex():
            pos = raw_bytes.hex().find(cid_hex)
            print(f"🎯 Found CID '{cid}' as hex at position {pos//2}!")
            return True
    
    print("❌ No known CIDs found in direct search")
    return False

def analyze_multiple_encodings(raw_bytes: bytes, known_cids: List[str]):
    """Try various encoding schemes"""
    print("Testing multiple encoding schemes...")
    
    # Base64 variants
    try:
        b64_data = base64.b64decode(raw_bytes, validate=True)
        for cid in known_cids:
            if cid.encode() in b64_data:
                print(f"🎯 Found CID '{cid}' in base64 decoded data!")
                return True
    except:
        pass
    
    # Try base32
    try:
        # Base32 typically requires padding
        padded_data = raw_bytes + b'=' * (8 - len(raw_bytes) % 8)
        b32_data = base64.b32decode(padded_data, casefold=True)
        for cid in known_cids:
            if cid.encode() in b32_data:
                print(f"🎯 Found CID '{cid}' in base32 decoded data!")
                return True
    except:
        pass
    
    # Try interpreting as different number bases
    try:
        # Look for base58-like patterns (IPFS CIDs are base58)
        text = raw_bytes.decode('utf-8', errors='ignore')
        base58_pattern = r'[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{40,50}'
        matches = re.findall(base58_pattern, text)
        if matches:
            print(f"📍 Found base58-like strings: {matches[:5]}")
            
            # Test if any are valid CIDs
            for match in matches[:10]:  # Test first 10
                if len(match) == 46 and match.startswith('Qm'):
                    print(f"🎯 Potential CID found: {match}")
                    # Test on IPFS
                    test_url = f"https://ipfs.arbius.org/ipfs/{match}/out-1.png"
                    try:
                        head_response = requests.head(test_url, timeout=5)
                        if head_response.status_code == 200:
                            print(f"✅ WORKING CID: {match}")
                            return True
                    except:
                        pass
    except:
        pass
    
    print("❌ No CIDs found in alternative encodings")
    return False

def analyze_abi_structure(hex_data: str):
    """Analyze as Ethereum ABI-encoded data"""
    print("Analyzing ABI structure...")
    
    # Skip function selector (first 4 bytes = 8 hex chars)
    function_selector = hex_data[:8]
    params_data = hex_data[8:]
    
    print(f"Function selector: 0x{function_selector}")
    print(f"Parameters data length: {len(params_data)} hex chars")
    
    # Parse as 32-byte chunks (ABI encoding standard)
    chunks = []
    for i in range(0, len(params_data), 64):  # 64 hex chars = 32 bytes
        chunk = params_data[i:i+64]
        if len(chunk) == 64:
            chunks.append(chunk)
    
    print(f"Found {len(chunks)} 32-byte parameter chunks")
    
    # Analyze each chunk
    for i, chunk in enumerate(chunks[:10]):  # Show first 10
        # Try to interpret as different types
        try:
            # As integer
            int_val = int(chunk, 16)
            # As address (last 20 bytes)
            addr = '0x' + chunk[-40:] if chunk[-40:] != '0' * 40 else None
            # As bytes
            chunk_bytes = bytes.fromhex(chunk)
            text = chunk_bytes.decode('utf-8', errors='ignore').strip('\x00')
            
            print(f"  Chunk {i:2d}: {chunk[:16]}...")
            if int_val < 10**6:  # Reasonable number
                print(f"           As int: {int_val}")
            if addr and addr != '0x' + '0' * 40:
                print(f"           As addr: {addr}")
            if text and len(text) > 3:
                clean_text = ''.join(c for c in text if c.isprintable())
                if clean_text:
                    print(f"           As text: '{clean_text[:30]}...'")
                    
        except:
            continue
    
    # Look for dynamic data patterns (offset pointers)
    print("\nLooking for dynamic data patterns...")
    for i, chunk in enumerate(chunks[:5]):
        try:
            offset = int(chunk, 16)
            if offset > 0 and offset < len(params_data)//2:  # Valid offset
                # Look at data at this offset
                byte_offset = offset * 2  # Convert to hex chars
                if byte_offset < len(params_data):
                    length_chunk = params_data[byte_offset:byte_offset+64]
                    if length_chunk:
                        try:
                            data_length = int(length_chunk, 16)
                            if data_length > 0 and data_length < 1000:  # Reasonable
                                data_start = byte_offset + 64
                                data_end = data_start + (data_length * 2)
                                if data_end <= len(params_data):
                                    data_hex = params_data[data_start:data_end]
                                    data_bytes = bytes.fromhex(data_hex)
                                    data_text = data_bytes.decode('utf-8', errors='ignore')
                                    
                                    print(f"  Dynamic data at offset {offset}:")
                                    print(f"    Length: {data_length} bytes")
                                    print(f"    Data: {data_hex[:60]}...")
                                    if data_text:
                                        clean = ''.join(c for c in data_text if c.isprintable())
                                        print(f"    Text: '{clean[:50]}...'")
                                    
                                    # Check if this contains a CID
                                    cid_pattern = r'Qm[1-9A-HJ-NP-Za-km-z]{44}'
                                    cids = re.findall(cid_pattern, data_text)
                                    if cids:
                                        print(f"    🎯 Found CIDs: {cids}")
                        except:
                            continue
        except:
            continue

def analyze_compression_patterns(raw_bytes: bytes, known_cids: List[str]):
    """Look for compression patterns"""
    print("Analyzing potential compression...")
    
    # Try common compression algorithms
    import zlib
    import gzip
    import bz2
    
    compression_methods = [
        ('zlib', lambda x: zlib.decompress(x)),
        ('gzip', lambda x: gzip.decompress(x)),
        ('bz2', lambda x: bz2.decompress(x)),
    ]
    
    for name, decompress_func in compression_methods:
        try:
            # Try decompressing the whole thing
            decompressed = decompress_func(raw_bytes)
            text = decompressed.decode('utf-8', errors='ignore')
            
            # Look for CIDs in decompressed data
            for cid in known_cids:
                if cid in text:
                    print(f"🎯 Found CID '{cid}' in {name} decompressed data!")
                    return True
            
            # Look for CID patterns
            cid_pattern = r'Qm[1-9A-HJ-NP-Za-km-z]{44}'
            cids = re.findall(cid_pattern, text)
            if cids:
                print(f"🎯 Found CID patterns in {name} decompressed data: {cids[:3]}")
                return True
                
        except:
            continue
    
    # Try partial decompression (maybe only part is compressed)
    print("Trying partial decompression...")
    for start in range(0, len(raw_bytes), 100):
        for end in range(start + 100, min(len(raw_bytes), start + 1000), 100):
            segment = raw_bytes[start:end]
            for name, decompress_func in compression_methods:
                try:
                    decompressed = decompress_func(segment)
                    text = decompressed.decode('utf-8', errors='ignore')
                    for cid in known_cids:
                        if cid in text:
                            print(f"🎯 Found CID '{cid}' in {name} decompressed segment [{start}:{end}]!")
                            return True
                except:
                    continue
    
    print("❌ No CIDs found in compressed data")
    return False

def analyze_qm_fragments(raw_bytes: bytes, qm_positions: List[int]):
    """Analyze known Qm fragment positions"""
    print(f"Analyzing Qm fragments at positions: {qm_positions}")
    
    text = raw_bytes.decode('utf-8', errors='ignore')
    
    for pos in qm_positions:
        if pos < len(text):
            # Look at surrounding context
            start = max(0, pos - 50)
            end = min(len(text), pos + 100)
            context = text[start:end]
            
            print(f"\nFragment at position {pos}:")
            print(f"Context: '{context}'")
            
            # Try to find patterns that might indicate encoding
            # Look for repeated patterns, delimiters, etc.
            fragment = text[pos:pos+50]
            
            # Check if this could be a partially encoded CID
            print(f"Fragment analysis:")
            print(f"  Raw: '{fragment}'")
            print(f"  Hex: {fragment.encode().hex()}")
            
            # Look for patterns in surrounding bytes
            byte_pos = pos
            surrounding = raw_bytes[max(0, byte_pos-20):byte_pos+50]
            print(f"  Surrounding hex: {surrounding.hex()}")
            
            # Try to decode surrounding area as different bases
            try:
                # Maybe it's split across multiple encoding schemes
                for i in range(max(0, pos-10), min(len(text), pos+10)):
                    test_segment = text[i:i+46]
                    if len(test_segment) >= 40 and 'Qm' in test_segment:
                        # Try to clean it up
                        base58_chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
                        cleaned = ''.join(c for c in test_segment if c in base58_chars)
                        if len(cleaned) >= 40 and cleaned.startswith('Qm'):
                            print(f"  Cleaned candidate: '{cleaned}'")
            except:
                pass

def find_and_analyze_fragments(raw_bytes: bytes):
    """Find any Qm fragments in the data"""
    text = raw_bytes.decode('utf-8', errors='ignore')
    qm_positions = [m.start() for m in re.finditer(r'Qm', text)]
    
    if qm_positions:
        print(f"Found Qm fragments at positions: {qm_positions[:10]}")
        analyze_qm_fragments(raw_bytes, qm_positions[:5])  # Analyze first 5
    else:
        print("No Qm fragments found")

def analyze_statistical_patterns(raw_bytes: bytes):
    """Look for statistical patterns that might indicate CIDs"""
    print("Analyzing statistical patterns...")
    
    # Entropy analysis
    from collections import Counter
    byte_freq = Counter(raw_bytes)
    entropy = -sum((freq/len(raw_bytes)) * __import__('math').log2(freq/len(raw_bytes)) 
                  for freq in byte_freq.values())
    
    print(f"Data entropy: {entropy:.2f} bits/byte")
    print(f"Total unique bytes: {len(byte_freq)}")
    
    # Look for repeated patterns
    pattern_counts = {}
    for length in [4, 8, 16, 32]:  # Different pattern lengths
        for i in range(len(raw_bytes) - length):
            pattern = raw_bytes[i:i+length]
            if pattern in pattern_counts:
                pattern_counts[pattern] += 1
            else:
                pattern_counts[pattern] = 1
    
    # Find most common patterns
    common_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"\nMost common patterns:")
    for pattern, count in common_patterns:
        if count > 1:
            print(f"  {pattern.hex()[:20]}... (appears {count} times)")
    
    # Look for base58-like character distribution
    text = raw_bytes.decode('utf-8', errors='ignore')
    base58_chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    base58_count = sum(1 for c in text if c in base58_chars)
    base58_ratio = base58_count / len(text) if text else 0
    
    print(f"\nBase58 character analysis:")
    print(f"  Base58 chars: {base58_count}/{len(text)} ({base58_ratio:.1%})")
    
    if base58_ratio > 0.7:  # High concentration of base58 chars
        print("  🎯 High base58 concentration - possible encoded CIDs!")

if __name__ == "__main__":
    investigate_cid_encoding() 