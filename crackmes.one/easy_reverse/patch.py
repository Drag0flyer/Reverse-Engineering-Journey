#!/usr/bin/env python3
"""
Crackme: easy_reverse (cbm-hackers)
Description: Automated exploit patcher to bypass validation logic.
Author: Drag0flyer
Date: June 2026
"""

import os
import sys

ORIGINAL_BINARY = "rev50_linux64-bit"
PATCHED_BINARY = "rev50_linux64-bit_patched"

def apply_patch():
    print("[*] Starting automated patch for easy_reverse...")

    if not os.path.exists(ORIGINAL_BINARY):
        print(f"[-] Error: Target binary '{ORIGINAL_BINARY}' not found in current directory.")
        print("[*] Please make sure the crackme file is named correctly.")
        sys.exit(1)

    try:
        with open(ORIGINAL_BINARY, "rb") as f:
            binary_data = bytearray(f.read())
    except Exception as e:
        print(f"[-] Error reading file: {e}")
        sys.exit(1)

    file_offset = 0x11d7 
    
    if binary_data[file_offset] != 0x75:
        print("[-] Error: Byte mismatch at target offset.")
        print(f"    Expected 0x75 (JNZ), found 0x{binary_data[file_offset]:02X}.")
        print("    The patch might already be applied or the binary version differs.")
        sys.exit(1)

    print(f"[+] Found JNZ (0x75) at offset 0x{file_offset:X}.")
    
    binary_data[file_offset] = 0xEB
    binary_data[file_offset + 1] = 0x2F
    
    print("[+] Successfully replaced '75 7E' with 'EB 2F' (Unconditional Jump).")

    try:
        with open(PATCHED_BINARY, "wb") as f:
            f.write(binary_data)
        
        os.chmod(PATCHED_BINARY, 0o755)
        print(f"[+] Clean exploit binary generated: '{PATCHED_BINARY}'")
        print("[*] Run it with: ./rev50_linux64-bit_patched <any_input>")
        
    except Exception as e:
        print(f"[-] Error writing patched file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_patch()
