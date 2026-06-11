#!/usr/bin/env python3
"""
Crackme: easy_reverse (cbm-hackers)
Description: Keygen targeting length and specific character constraints.
Author: Drag0flyer
Date: June 2026
"""

import random
import string

def generate_valid_key():
    """
    Generates a key based on the binary constraints:
    1. Total length must be 10 characters.
    2. The 5th character must be '@'.
    """

    forbidden_chars = ('\t', '\n', '\r', '\x0b', '\x0c', ' ', '"', "'", '`', ';')

    charset = [c for c in string.printable if c not in forbidden_chars]
    
    key_chars = [random.choice(charset) for i in range(10)]
    
    key_chars[4] = '@'
    
    valid_key = "".join(key_chars)
    return valid_key

def main():
    print("[*] Crackme easy_reverse - Key Generator")
    print("[*] Binary constraints:")
    print("    [-] Length == 10")
    print("    [-] Password[4] == '@'")
    print("-" * 40)
    
    generated_key = generate_valid_key()
    
    print(f"[+] Generated Valid Key : {generated_key}")
    print("-" * 40)

if __name__ == "__main__":
    main()
