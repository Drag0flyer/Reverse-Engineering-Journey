#!/usr/bin/env python3
"""
Crackme: EasiestEver (BadEngineer)
Description: Keygen.
Author: Drag0flyer
Date: June 2026
"""

import random
import string

def generate_valid_key():

    forbidden_chars = ('\t', '\n', '\r', '\x0b', '\x0c')
    even_numbers = ['0','2','4','6','8']

    charset = [c for c in string.printable if c not in forbidden_chars]
    
    key_chars = [random.choice(charset) for i in range(14)]
    
    key_chars[4] = '-'
    key_chars[9] = '-'
    key_chars[10] = 'R'

    for i in range(4):
        key_chars[i] = random.choice(string.digits)
        key_chars[i+5] = random.choice(even_numbers)
    
    valid_key = "".join(key_chars)
    return valid_key

def main():
    
    generated_key = generate_valid_key()
    
    print(f"[+] Generated Valid Key : {generated_key}")

if __name__ == "__main__":
    main()
