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
* **Stack Initialization:** The standard function `_memset(password, 0, 0xf)` is called to clear a 15-byte array allocated on the stack, overwriting residual memory with null bytes (`0x00`).
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
