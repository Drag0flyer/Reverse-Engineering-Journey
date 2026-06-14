# Write-Up: Keygen me Quick! (Legacyy)

## 1. Challenge Specifications
* **Author:** Legacyy
* **Platform:** Crackmes.one
* **Architecture:** Windows x86 (32-bit PE Executable)
* **Global Difficulty:** 1.9/6
* **Analysis Environment:** Windows 10 (VM)
* **Tools Used:** Ghidra (Static Analysis)
---

## 2. Static Analysis & Resolution
Initial exploration of the binary required traversing the standard initialization layers of the compiler before isolating the main validation function. Unlike stripped binaries, the executable integrates the opaque plumbing of the Microsoft Visual C++ Runtime (MSVC CRT).

### Discovering the Virtual Entry Point:
1. **The Illusion of `entry`:** Upon opening the file in Ghidra, the disassembly defaults to the actual entry point (`entry`). This zone contains no user code, but initializes the *Stack Canaries* security mechanism via the `___security_init_cookie()` system call.
2. **The Runtime Forest (CRT):** An unconditional jump (`JMP`) then leads to the internal function `FUN_0040721e`. This assembly block configures the execution environment through the `___scrt_initialize_crt`, `__initterm_e`, and `__initterm` routines.
3. **Isolating `main`:** The transition to the code written by the developer occurs at the very end of this initialization function. The standard environment variables (`envp`, `argv`, `argc`) are retrieved via three consecutive stubs (`thunk_`), then pushed onto the stack (the standard argument-passing convention in 32-bit architecture) right before a decisive call:

   ```c
   unaff_ESI = thunk_FUN_00406f40(*puVar9, uVar2, uVar8);
   ```
Analysis of the target address `FUN_00406f40` confirms that this is the actual **`main`** of the application.

---

## 3. Advanced Analysis: Internal Structure & Decompilation Clean-up
Once inside `main`, Ghidra's decompilation environment presented raw code that was heavily optimized and masked by generic types. Rigorous renaming and type reconstruction restored the original logical flow.

### Refactoring the Environment:
* **Stack Initialization:** The standard function `_memset(password, 0, 0xf)` is called to clear a 15-byte stack buffer allocated on the stack, overwriting residual memory with null bytes (`0x00`).
* **Resolving Windows Streams:** The opaque instruction `stdin = ___acrt_iob_func(0)` was identified as the macro to retrieve the standard input stream (`stdin`, index 0 under the Microsoft Runtime architecture).
* **Identifying Saisie (Input):** The underlying function `thunk_FUN_00414d71`, taking the buffer, maximum size (`0xf`), and the input stream as parameters, was legitimately renamed to `fgets`.

### Global Algorithmic Logic:
The binary relies on a strict and sequential validation pipeline composed of four autonomous logical barriers. If any of these functions returns 0 (False) in the EAX register, the program branches to a failure message. Absolute success requires every evaluation function to return a non-zero value.

```
[User Input] 
     │
     ▼
 1. formatVerifier() ───( Returns 0 )───► [Invalid key format]
     │
(Returns 1)
     ▼
 2. checkOne()      ───( Returns 0 )───► [Check one failed]
     │
(Returns 1)
     ▼
 3. checkTwo()      ───( Returns 0 )───► [Check two failed]
     │
(Returns 1)
     ▼
 4. checkThree()    ───( Returns 0 )───► [Check three failed]
     │
(Returns 1)
     ▼
[Congrats, you did it!]
```

Here is the mathematical analysis of the constraints extracted from the reversed subroutines:

#### A. Global Mask Validation (`formatVerifier`)
This function calculates the length of the entered string via `_strlen`. It imposes two major structural constraints:
* The absolute length of the key must be **14 characters** (represented by the hexadecimal value `0xe`).
* Physical dash separators (`'-'`) must be positioned precisely at indices `password[4]` and `password[9]`. The expected structure is therefore configured as `XXXX-XXXX-XXXX`.

#### B. First Block Validation (`checkOne`)
An iterative loop analyzes indices `0` to `3` (the first block of 4 characters). The routine compares the raw ASCII value of each byte:
* Each character must fall inclusively between ASCII `'0'` (decimal `48`) and ASCII `'9'` (decimal `57`). This block only accepts purely **numeric** characters.

#### C. Second Block Validation (`checkTwo`)
The loop inspects the central segment located between indices `5` and `8`. The evaluation utilizes a bitwise AND operator (`Bitwise AND`):
* The instruction `if ((password[i] & 1U) != 0)` performs a mask on the least significant bit of the byte. If this bit is `1`, the number is mathematically odd and the function fails. By deduction, all characters in this block must possess an **even** ASCII value (limiting valid inputs to the numeric characters `0`, `2`, `4`, `6`, and `8`).

#### D. Third Block Validation (`checkThree`)
The final routine isolates the trailing block using pointer arithmetic, targeting the address `password + 10`.
* The program loads the reference string `"R3KT"` into local memory using the optimized `builtin_strncpy` function.
* A call to `_strncmp(passwordPart, password + 10, 1)` compares only the **first byte** (length of 1) of the last segment with the first character of the stored pattern. Index `password[10]` must therefore imperatively be the uppercase letter **`R`**. Indices `11`, `12`, and `13` are not subjected to any comparison and accept any printable ASCII character.

---

## 4. Hardening Bypass via Permanent Static Patching
To permanently neutralize the serialization verification without having to attach a debugger or input a valid key at every execution, a physical static patch was designed to alter the control flow mechanics directly on disk.

### Instruction Engineering (Assembly Level):
Instead of patching the prologues of individual validation subroutines (`checkOne`, `checkTwo`, `checkThree`), the patch optimizes efficiency by targeting the fundamental conditional branch within the `main` function. This single modification entirely bypasses the validation sequence.

The mutation is executed at the file offset corresponding to the initial global format check evaluation:

* **Original Sequence (`0x00406F94`):** `74 4C`
  * Translation: `JZ LAB_00406fe2` (Jump to the "Invalid key format" failure path if `formatVerifier` returns `0`).
* **Patched Sequence:** `EB 3D`
  * Translation: `JMP 0x00406FD3` (Unconditional Short Jump).

### Mathematical Offset Derivation:
In x86 assembly, relative short jumps (`EB`) calculate their destination displacement from the address of the **next sequential instruction**. The calculation for this patch is derived as follows:

$$\text{Current Instruction Address} = \text{0x00406F94}$$
$$\text{Instruction Length (JZ)} = 2 \text{ bytes}$$
$$\text{Next Instruction Address} = \text{0x00406F94} + \text{0x2} = \text{0x00406F96}$$
$$\text{Target Destination (Congrats PUSH)} = \text{0x00406FD3}$$

$$\text{Required Displacement Offset} = \text{0x00406FD3} - \text{0x00406F96} = \text{0x3D}$$

Injecting `EB 3D` effectively short-circuits the application's runtime flow. The CPU completely skips over every algorithmic constraint check and lands cleanly on the stack preparation routine for the success message. 

Furthermore, renaming the generated executable to avoid strings like `_patched` ensures that the Windows User Account Control (UAC) Installer Detection heuristcs do not force unnecessary elevated administrative token demands or spawn unmapped transient terminal contexts.

The automation of this static patch is handled by the script `patch.py`. To execute it and generate the autonomous modified binary, use the following command:

```bash
python3 patch.py
```

---

## 5. Algorithmic Exploitation: Keygen Automation
Rather than modifying the binary or manipulating registers on the fly, a pure algorithmic exploitation approach was developed by reversing the structural and mathematical validation rules discovered during static analysis in Ghidra.

### Algorithmic & Structural Constraints:
The verification routine evaluates the serial key by breaking it down into distinct segments, validating specific character sets, positioning physical delimiters, and enforcing strict data type restrictions. 

Analysis of the reversed routines revealed four critical constraints required to forge a perfectly legitimate serial key:

1. **The Strict Mask Boundary (`formatVerifier`):** The password must have an absolute length of exactly **14 characters** (`0xe` bytes). Furthermore, physical dash separators (`'-'`) must reside at indices `[4]` and `[9]`, dictating a precise `XXXX-XXXX-XXXX` topology.
2. **Strict Numerical Constraint (`checkOne`):** The first block (indices `[0]` through `[3]`) must consist entirely of standard numerical digits, forcing individual byte values to fall inclusively between ASCII `0` (decimal `48`) and ASCII `9` (decimal `57`).
3. **Parity Bitmask Enforcement (`checkTwo`):** The secondary block (indices `[5]` through `[8]`) is subject to a strict mathematical parity filter. The application applies a bitwise AND operation (`& 1U`) on each byte to ensure the least significant bit is zero. Consequently, only characters with an **even ASCII value** are permitted (limiting the workspace to the digits `0`, `2`, `4`, `6`, and `8`).
4. **Hardcoded Substring Match (`checkThree`):** The final block uses pointer arithmetic targeting `password + 10` and leverages a substring check. The first byte of this trailing segment (index `[10]`) must explicitly match the uppercase letter **`R`** (extracted from the internal reference token `"R3KT"`). The final three indices (`[11]`, `[12]`, and `[13]`) are completely unverified by the comparison routine and accept any printable ASCII padding.

The Python generation script safely filters out non-printable control characters (such as line feeds, tabs, or carriage returns) to prevent clipboard payload corruption when copying and pasting keys directly into the Windows host terminal emulator.

The `keygen.py` script automatically assembles these rules to generate fully compliant, mathematically sound keys on demand.

To generate a valid serial key, execute the automation script using the following command:

```bash
python3 keygen.py
```

---

## 6. Dynamic Analysis & Runtime Control-Flow Manipulation

In addition to static patching and algorithmic keygenning, a dynamic audit of the binary was conducted using x32dbg to map out the application's runtime validation mechanics and evaluate its behavior under active process manipulation.

### Dynamic Execution Mapping & Environmental Divergence
When executing the target binary natively from a standard Windows file explorer context, a significant behavioral anomaly was observed: appending a `_patched` string to the binary name triggers the Windows User Account Control (UAC) Installer Detection heuristics. This forces an elevated administrative token request and isolates the execution within a transient console context that terminates immediately upon process exit. Neutralizing this artifact requires renaming the binary (e.g., using a `_r` or `_pat` suffix) to maintain execution stability inside an existing shell environment.

Under the debugger, because the application compiles with **Address Space Layout Randomization (ASLR)** enabled, the base address of the image dynamically relocates at runtime (e.g., mapping the base to `0x008A0000` instead of the standard `0x00400000`). Consequently, the relative virtual address (RVA) offset of the user-space entry point must be derived dynamically:

$$\text{Active Entry Address} = \text{Base Address} + \text{Static Ghidra Offset} = \text{0x008A0000} + \text{0x6F40} = \text{0x008A6F40}$$

### x86 Stack Framing & Argument Passing Mechanics
Unlike x64 architectures that leverage volatile registers (`RCX`, `RDX`, etc.) for fast parameter passing, this 32-bit binary strictly complies with standard stack-driven calling conventions. Prior to triggering the validation subroutines, the application must explicitly provision the stack frame to expose the local variables:

```assembly
00406F86   8D 55 EC         LEA EDX, dword ptr ss:[EBP - 0x14]
00406F89   52               PUSH EDX
00406F8A   E8 FA C1 FF FF   CALL formatVerifier
```

The `LEA` instruction computes the effective address of the destination `password` storage array—located exactly 20 bytes (`0x14`) below the current base pointer (`EBP`)—and places the raw memory pointer into `EDX`. The subsequent `PUSH EDX` operation drops this address reference directly onto the top of the stack (`ESP`), allowing the callee subroutine to extract and read the user-supplied string buffer.

### Runtime Control Flow Hijacking via EFLAGS Evasion
The application chains its security validation checks within a logical AND (`&&`) framework inside `main`. This implementation relies on conditional evaluation short-circuiting: if any check fails, the execution stream is directed immediately to the failure termination routines. This branching logic was subverted during active runtime analysis by placing hardware breakpoints on the conditional jumps and manually toggling the CPU's core processing flags.

The specific manipulation path to bypass the conditional logic with a single-character dummy key (`"a"`) is detailed below:

1. **`formatVerifier` Bypass (Address `0x008A6F94`):** The invalid key length causes the routine to return `0`, prompting `TEST EAX, EAX` to set the Zero Flag (`ZF = 1`). The subsequent `JE` (*Jump if Equal*) instruction prepares to pivot to the global failure path (`0x008A6FE2`). Double-clicking the flag registry to clear it (`ZF = 0`) misleads the CPU, forcing it to fall through into the success block and output `"Key in correct format."`.
2. **`checkOne` Bypass (Address `0x008A6FB1`):** The non-numeric payload fails the first numerical constraint check, logging `"Check one failed."` internally and clearing `EAX`. The conditional `JE` branch is neutralized by manually forcing `ZF = 0`, preserving the sequential execution flow.
3. **`checkTwo` Evaluation (Address `0x008A6FC1`):** At this instruction boundary, the environmental state of the registers naturally leaves `ZF` at `0`. As a result, the conditional `JE` branch evaluates as false without manual intervention, allowing the instruction pointer to step cleanly past the obstacle into the final verification logic.
4. **`checkThree` Bypass (Address `0x008A6FD1`):** The missing substring match triggers an internal `"Check three failed."` string output. Modifying the resulting validation flag a final time (`ZF = 0`) completely breaks out of the short-circuit constraint window. 

The CPU passes directly to the success path at address `0x008A6FD3`:

```assembly
008A6FD3   68 84 60 90 00   PUSH keygenme_1.906084    ; "Congrats, you did it!\n"
```

This active manipulation induces a hybrid execution state, demonstrating that the underlying core logic can be entirely manipulated in memory by directly controlling the CPU flags, successfully forcing the application to print the success message alongside the internal error logs.
