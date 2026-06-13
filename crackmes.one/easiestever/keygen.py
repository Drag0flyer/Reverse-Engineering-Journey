#!/usr/bin/env python3
"""
Crackme: EasiestEver (BadEngineer)
Description: Keygen.
Author: Drag0flyer
Date: June 2026
"""

import random
import string

def generate_perfect_copy_paste_password():
    intervals = [
        [chr(i) for i in range(48, 53)],
        [chr(i) for i in range(72, 79)],
        [chr(i) for i in range(116, 122)],
        [chr(i) for i in range(97, 103)],
        [chr(i) for i in range(33, 39)],
        [chr(i) for i in range(59, 64)],
        [chr(i) for i in range(106, 110)],
        [chr(i) for i in range(122, 126)],
        [chr(i) for i in range(111, 116)],
        [chr(i) for i in range(92, 97)]
    ]
    
    password_chars = [random.choice(inter) for inter in intervals]
    
    target_length = random.randint(10, 16)

    if target_length > 10:
        forbidden = ('\t', '\n', '\r', '\x0b', '\x0c')
        safe_ascii_pool = [c for c in string.printable if c not in forbidden]
        
        while len(password_chars) < target_length:
            password_chars.append(random.choice(safe_ascii_pool))
            
    random.shuffle(password_chars)
    
    return "".join(password_chars)

if __name__ == "__main__":
    print(generate_perfect_copy_paste_password())
