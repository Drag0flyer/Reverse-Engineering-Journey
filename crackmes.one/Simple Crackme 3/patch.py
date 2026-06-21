#! python3
"""
Crackme: Simple Crackme 3 (0xCiel)
Description: Automated exploit patcher to bypass validation logic.
Author: Drag0flyer
Date: June 2026
"""

import os
import sys

ORIGINAL_BINARY = "Crackme3.exe"
PATCHED_BINARY = "Crackme3_pat.exe"

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

    file_offset = 0x176A 
    
    if binary_data[file_offset] != 0x0F:
        print("[-] Error: Byte mismatch at target offset.")
        print(f"    Expected 0x0F, found 0x{binary_data[file_offset]:02X}.")
        print("    The patch might already be applied or the binary version differs.")
        sys.exit(1)

    print(f"[+] Found JZ (0x0F84) at offset 0x{file_offset:X}.")
    
    binary_data[file_offset] = 0x0F
    binary_data[file_offset + 1] = 0x85
    
    print("[+] Successfully replaced '0F 84' with '0F 85'.")

    try:
        with open(PATCHED_BINARY, "wb") as f:
            f.write(binary_data)
        
        os.chmod(PATCHED_BINARY, 0o755)
        print(f"[+] Clean exploit binary generated: '{PATCHED_BINARY}'")
        print("[*] Run it with: .\Crackme3_pat.exe")
        
    except Exception as e:
        print(f"[-] Error writing patched file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_patch()
