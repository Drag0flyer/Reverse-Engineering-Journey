## 1. Binary Specifications & Environmental Audit
Initial reconnaissance of the target challenge binary was conducted using standard Linux CLI utilities to map out the execution context and active kernel-space defenses.

### Mitigation Check (Checksec):
* **Architecture:** ELF 32-bit LSB executable. Parameter passing adheres to the legacy stack-driven calling convention.
* **Stack Canary:** `No canary found`. The application lacks stack cookies, permitting unhindered manipulation of the function's return state and local stack variables.
* **NX (No-Execute):** `NX enabled`. The stack segment is non-executable, neutralizing traditional shellcode injection attempts.
* **PIE (Position Independent Executable):** `No PIE`. The binary's code section maps to static, immutable virtual memory addresses.
* **ASLR (Address Space Layout Randomization):** `OFF`. Global memory layout consistency is maintained across sequential process instantiations.

---

## 2. Static Analysis & Source Code Review
The software's logic was evaluated via its provided C source code (`ch13.c`). The binary instantiates three critical components within its `main` function stack frame:

```c
int var;
int check = 0x04030201;
char buf[40];
```

### Vulnerability Identification:
The security flaw lies within the input ingestion layer. The program utilizes the `fgets` routine to capture user parameters from the standard input stream (`stdin`):

```c
fgets(buf, 45, stdin);
```

While the target stack destination buffer `buf` is statically allocated a capacity of exactly **40 bytes**, the `fgets` configuration explicitly allows up to **45 bytes** of data to be read into memory. This programmatic mismatch induces a classic **Stack-based Buffer Overflow** constraint window, allowing an operator to overflow the spatial boundaries of `buf` by up to 5 bytes.

### Target Constraints:
To alter the application's runtime execution path and invoke the privileged system routine, the conditional evaluation must be satisfied:

```c
if (check == 0xdeadbeef) {
    setreuid(geteuid(), geteuid());
    system("/bin/bash");
}
```

Because variables allocated sequentially within a function block are stacked contiguously in memory, the `check` integer variable is positioned immediately adjacent to the upper boundary of the `buf` array.

---

## 3. Exploitation Strategy & Payload Engineering

### Memory Alignment & Endianness:
Exploitation requires filling the 40-byte storage area of `buf` with arbitrary padding bytes before immediately overwriting the memory bytes corresponding to the `check` storage tracker. 

Due to the underlying Intel x86 architecture, the CPU processes data using **Little-Endian byte ordering** (least significant byte stored at the lowest memory address). Consequently, the target hexadecimal value `0xDEADBEEF` must be transmitted across the input stream in reverse byte sequence:


**Target DWORD :** `0xDEADBEEF` $\longrightarrow$ **Byte Stream Pattern :** `\xef\xbe\xad\xde`


### Exploit Orchestration:
The automated attack payload leverages a nested subshell structure. An initial Python string generation operation provides the static padding and the Little-Endian byte injection. 

This stream is concatenated with an active `cat` session inside a pipe (`|`) to prevent an immediate End-Of-File termination signal, keeping the newly spawned privileged bash process open and responsive to interactive terminal entries:

```bash
(python -c "print('A' * 40 + '\xef\xbe\xad\xde')"; cat) | ./ch13
```

Executing the chain successfully compromises the local state tracking, hijacking the internal conditional evaluation framework to grant the operator a local shell context running under the elevated privileges of the binary's SUID owner (`app-systeme-ch13-cracked`), allowing for the acquisition of the secure storage flags.
