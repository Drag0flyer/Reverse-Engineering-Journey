## 1. Binary Specifications & Environmental Audit
Initial reconnaissance of the target challenge binary was conducted using standard Linux CLI utilities to map out the execution context and active kernel-space defenses.

### Mitigation Check (Checksec / Objdump):
* **Architecture:** ELF 32-bit LSB executable (Intel 80386). Parameter passing adheres to the legacy stack-driven calling convention.
* **Stack Canary:** `Canary found`. The application implements stack cookies (`__stack_chk_fail`), neutralizing traditional stack-based buffer overflow attempts targeting the return address.
* **NX (No-Execute):** `NX enabled`. The stack segment is non-executable, preventing shellcode execution from memory segments.
* **PIE (Position Independent Executable):** `No PIE`. The binary's code section maps to static, immutable virtual memory addresses.
* **SUID Layer:** The binary operates with the Set Owner User ID (`SUID`) flag active, allowing the process to inherit the elevated filesystem privileges of its owner during runtime execution to access restricted assets.

---

## 2. Static Analysis & Source Code Review
The software's logic was evaluated via its provided C source code. The binary instantiates a local storage array and a file descriptor reference within its `main` function stack frame:

```c
#include <stdio.h>
#include <unistd.h>

int main(int argc, char *argv[]){
        FILE *secret = fopen("/[restricted_path]/.passwd", "rt");
        char buffer[32];
        fgets(buffer, sizeof(buffer), secret);
        printf(argv[1]);
        fclose(secret);
        return 0;
}
```

### Vulnerability Identification:
The critical flaw resides within the output logging layer. The program invokes the `printf` routine by passing the user-controlled command-line argument `argv[1]` directly as the format string parameter without an explicit format specifier:

```c
printf(argv[1]);
```

Because an operator can inject arbitrary format string specifiers (such as `%x` or `%p`), the `printf` function can be coerced into treating values stored sequentially on the stack frame as its own arguments. This programmatic oversight induces a **Format String Leak Vulnerability**, granting unauthenticated read access to the local stack layout.

---

## 3. Memory Layout & Stack Mapping
Because the binary utilizes an uncontrolled format string, a dynamic stack mapping strategy was employed via the command-line interface to locate the structural position of the target local variable `buffer`.

By passing an extended sequence of hexadecimal format parameters (`%x`), the application was forced to dump the raw 32-bit words residing on its stack frame:

```bash
./ch5 "`python -c "print('%x ' * 40)"`"
```

### Stack Frame Evaluation & Layout:
The execution output generated a deterministic sequence of hex values. Analyzing the initial dwords revealed the localized state of the stack memory:
* **Index 1–10:** Internal execution states, pointers related to the `glibc` initialization layer, and file stream tracking configurations.
* **Index 11–14:** A sequence of distinct hexadecimal constants that do not align with standard virtual memory address ranges:
  * `0x39617044`
  * `0x28293664`
  * `0x6d617045`
  * `0xbf000a64`

The invariant nature of these data blocks across multiple process instantiations confirmed that these fields represented the static string data loaded into the local `buffer` array by the `fgets` routine.

---

## 4. Exploitation Strategy & Information Leak Extraction

### Memory Alignment & Endianness:
Data extraction requires reversing the byte-ordering constraints imposed by the underlying Intel x86 architecture. In a **Little-Endian** storage configuration, bytes within a 32-bit word are structured from the least significant to the most significant byte.

The targeted variable boundary is strictly defined by the presence of the newline (`\n` -> `0x0a`) and null-terminator (`\0` -> `0x00`) control bytes, signaling the physical end of the file data captured by `fgets`. 

The data parsing matrix is orchestrated as follows:

| Stack Index | Raw Hex (DWORD) | Little-Endian Reversal | ASCII Translation |
| :--- | :--- | :--- | :--- |
| **Index 11** | `0x39617044` | `44 70 61 39` | `Dpa9` |
| **Index 12** | `0x28293664` | `64 36 29 28` | `d6)(` |
| **Index 13** | `0x6d617045` | `45 70 61 6d` | `Epam` |
| **Index 14** | `0xbf000a64` | `64 0a 00 bf` | `d\n\0...` |

### Exploit Orchestration & Flag Retrieval:
Because direct pointer dereferencing via the `%s` modifier on non-pointer values induces a memory access violation (`Segmentation fault`), the extraction was achieved entirely via precise positional indexing (`%$`).

By reconstituting the aligned character output from Index 11 up to the `0x0a` terminator detected within Index 14, the secure authentication flag was successfully exfiltrated from the isolated filesystem context:

```text
Flag: Dpa9d6)(Epamd
```
