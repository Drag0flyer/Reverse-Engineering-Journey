#!/usr/bin/env python3
"""
Crackme: EasiestEver (BadEngineer)
Description: Automated exploit patcher to bypass validation logic.
Author: Drag0flyer
Date: June 2026
"""

import os
import sys

ORIGINAL_BINARY = "simplecrackme.exe"
PATCHED_BINARY = "simplecrackme_patched.exe"

def apply_patch():
    print("[*] Starting automated patch for EasiestEver...")

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

    file_offset = 0xA90 
    
    if binary_data[file_offset] != 0x55:
        print("[-] Error: Byte mismatch at target offset.")
        print(f"    Expected 0x55 (PUSH), found 0x{binary_data[file_offset]:02X}.")
        print("    The patch might already be applied or the binary version differs.")
        sys.exit(1)

    print(f"[+] Found PUSH (0x55) at offset 0x{file_offset:X}.")
    
    binary_data[file_offset] = 0xB8
    binary_data[file_offset + 1] = 0x01
    binary_data[file_offset + 2] = 0x00
    binary_data[file_offset + 3] = 0x00
    binary_data[file_offset + 4] = 0x00
    binary_data[file_offset + 5] = 0xC3
    
    print("[+] Successfully replaced '55 53 48 81 EC 88' with 'B8 01 00 00 00 C3'.")

    try:
        with open(PATCHED_BINARY, "wb") as f:
            f.write(binary_data)
        
        os.chmod(PATCHED_BINARY, 0o755)
        print(f"[+] Clean exploit binary generated: '{PATCHED_BINARY}'")
        print("[*] Run it with: ./simplecrackme_patched.exe")
        
    except Exception as e:
        print(f"[-] Error writing patched file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_patch()
