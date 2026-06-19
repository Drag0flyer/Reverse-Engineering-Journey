#!python3
"""
Crackme: Crackme Speedrun (Piggy63)
Description: Automated exploit patcher to bypass validation logic.
Author: Drag0flyer
Date: June 2026
"""

import os
import sys

ORIGINAL_BINARY = "crackme.exe"
PATCHED_BINARY = "crackme_pat.exe"

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

    file_offset = 0xA3B
    file_offset_1 = 0x8FA
    file_offset_2 = 0x913
    file_offset_3 = 0x92A
    file_offset_4 = 0x941
    file_offset_5 = 0x957
    file_offset_6 = 0x971
    
    if binary_data[file_offset] != 0x75:
        print("[-] Error: Byte mismatch at target offset.")
        print(f"    Expected 0x75 (JNZ), found 0x{binary_data[file_offset]:02X}.")
        print("    The patch might already be applied or the binary version differs.")
        sys.exit(1)

    print(f"[+] Found JNZ (0x75) at offset 0x{file_offset:X}.")

    if (binary_data[file_offset_1] != 0x74) or (binary_data[file_offset_2] != 0x74) or (binary_data[file_offset_3] != 0x74) or (binary_data[file_offset_4] != 0x74) or (binary_data[file_offset_5] != 0x74) or (binary_data[file_offset_6] != 0x74):
        print("[-] Error: Byte mismatch at target offset.")
        print(f"    Expected 0x74 (JZ), found a mismatch.")
        print("    The patch might already be applied or the binary version differs.")
        sys.exit(1)

    print(f"[+] Found JZ (0x74) at offset 0x{file_offset_1:X}, 0x{file_offset_2:X}, 0x{file_offset_3:X}, 0x{file_offset_4:X}, 0x{file_offset_5:X}, 0x{file_offset_6:X}.")
    
    binary_data[file_offset] = 0x90
    binary_data[file_offset + 1] = 0x90

    print("[+] Successfully replaced '75 0F' with '90 90' (No operation).")

    binary_data[file_offset_1] = 0x90
    binary_data[file_offset_1 + 1] = 0x90

    print("[+] Successfully replaced '74 7C' with '90 90' (No operation).")

    binary_data[file_offset_2] = 0x90
    binary_data[file_offset_2 + 1] = 0x90

    print("[+] Successfully replaced '74 63' with '90 90' (No operation).")

    binary_data[file_offset_3] = 0x90
    binary_data[file_offset_3 + 1] = 0x90

    print("[+] Successfully replaced '74 4C' with '90 90' (No operation).")

    binary_data[file_offset_4] = 0x90
    binary_data[file_offset_4 + 1] = 0x90

    print("[+] Successfully replaced '74 35' with '90 90' (No operation).")

    binary_data[file_offset_5] = 0x90
    binary_data[file_offset_5 + 1] = 0x90

    print("[+] Successfully replaced '74 1F' with '90 90' (No operation).")

    binary_data[file_offset_6] = 0x90
    binary_data[file_offset_6 + 1] = 0x90

    print("[+] Successfully replaced '74 05' with '90 90' (No operation).")
    

    try:
        with open(PATCHED_BINARY, "wb") as f:
            f.write(binary_data)
        
        os.chmod(PATCHED_BINARY, 0o755)
        print(f"[+] Clean exploit binary generated: '{PATCHED_BINARY}'")
        print("[*] Run it with: ./crackme_pat.exe")
        
    except Exception as e:
        print(f"[-] Error writing patched file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_patch()
