# Write-Up: Simple Crackme 3 (0xCiel)

## 1. Challenge Specifications
* **Author:** 0xCiel
* **Platform:** Crackmes.one
* **Architecture:** Windows x64 (64-bit PE Executable)
* **Global Difficulty:** 2.6/6
* **Analysis Environment:** Windows 10 (VM)
* **Tools Used:** IDA (Static Analysis), x64dbg (Dynamic Analysis), HxD (Patching) and Python 3 (Scripting)
---

## 2. Static Analysis & Resolution
Initial exploration of the binary required isolating the main validation function. Since the binary was opened directly on `main` in the disassembly environment, we bypass the generic C Runtime (CRT) initialization stubs and focus exclusively on the developer's core implementation logic.

The function signature confirms a standard 64-bit user-entry execution frame:
```c
int __fastcall main(int argc, const char **argv, const char **envp)
```

---

## 3. Advanced Analysis: Internal Structure & Decompilation Clean-up
Once inside `main`, IDA Pro's decompilation environment presented raw code that was heavily optimized, laden with Standard Template Library (STL) objects, and masked by generic types. Rigorous renaming and type reconstruction restored the original logical flow.

### Refactoring the Environment:
* **String Allocation & SSO (Small String Optimization):** The binary extensively utilizes `std::string` buffers (`Block`, `v90`, `user_input`). Decompilation reveals checks against a capacity threshold of `0xF` (15 bytes). If a string exceeds this size, the application allocates memory on the heap; otherwise, it utilizes a fast local stack buffer.
* **Heap Destructors:** The code contains recurrent compiler-generated cleanup blocks:
  ```c
  if ( block_capacity > 0xF ) { j_j_free(v14); }
  ```
  These were safely identified as structural overhead from the `std::string` destructors freeing heap memory when strings fall out of scope.
* **Resolving Interactive Streams:** The underlying API call `sub_1400032D0` taking `std::cin` as an argument along with `std::ios::widen` was successfully identified as the standard C++ input routine (`std::cin >> user_input;`).

### Global Algorithmic Logic:
The binary relies on a **Session-based Key Validation Framework**. Unlike classic static crackmes, this challenge does not have a single, universal password. The target value is generated dynamically on every execution.

```
[Program Startup]
       │
       ▼
1. sub_140001680(Block) ───► Generates 12 Pseudo-Random Characters (Mersenne Twister)
       │
       ▼
2. sub_140001490(v90)   ───► Computes 64-bit FNV-1a Hash of the 12 Characters
       │
       ▼
   Stores Target Hash   ───► Saved inside v80 (Our Session Target)
       │
       ▼
3. std::cin              ───► Halts and waits for User Password
       │
       ▼
4. Inline FNV-1a Loop    ───► Hashes User Input into v18
       │
       ▼
5. Validation Branch     ───► Is v18 (User Hash) == v9 (Target v80) ?
       │                                     │
       ▼ (Yes)                               ▼ (No)
 [Display "Correct!"]                [Display "Incorrect"]
```

If an analyst attempts to statically force or solve for this condition using SMT solvers like Z3, the program traps the execution path and overwrites `Block` with `0x797274206563696E`—the Little-Endian representation of the ASCII string **"nice try"**. This destroys the valid key derivation path.

#### B. Target Hash Construction (`sub_140001490`)
The generated 12-character key is processed by a secondary subroutine to compute a 64-bit FNV-1a non-cryptographic hash. The state is initialized to the FNV offset basis (`0xCBF29CE484222325uLL`), processed against the 12 characters, and stored in the global session variable `v80`.

#### C. User Saisie & Verification Loop
Inside a continuous `while(1)` loop, the user is prompted for a password via `std::cin`. The input is instantly hashed in an explicit inline assembly implementation of the 64-bit FNV-1a algorithm:
* **Initial State:** `v18 = 0xCBF29CE484222325uLL`
* **Iterative Step:** `v18 = 0x100000001B3LL * (Current_Char ^ v18);`
The resulting hash value is moved into `v9` and matched directly against the session target.

---

## 4. Hardening Bypass via Permanent Static Patching
To permanently neutralize the cryptographic session verification without having to attach a debugger or input a valid pre-image key at every execution, a physical static patch was designed to alter the control flow mechanics directly on disk.

### Instruction Engineering (Assembly Level):
Instead of attempting to break the PRNG sequence or brute-force the non-linear FNV-1a multiplication equations, the patch optimizes structural efficiency by targeting the final evaluation branch within the `main` loop. By modifying a single byte, we invert the validation logic so that any arbitrary, incorrect payload is treated as the correct key.

The mutation is executed at the virtual address corresponding to the global hash comparison:

* **Original Sequence (`0x14000236A`):** `0F 84 08 02 00 00`
  * Translation: `JZ loc_140002578` (Jump to the success path *only* if the Zero Flag is set to 1, meaning `v18 == v80`).
* **Patched Sequence:** `0F 85 08 02 00 00`
  * Translation: `JNZ loc_140002578` (Jump if Not Zero).

### Mechanics of the Rel32 Logic Inversion:
In modern x64 architecture, a near conditional jump (`0F 84`) relies on a 32-bit relative displacement parameter (`rel32`). The original instruction uses `08 02 00 00`, which translates in Little-Endian to a forward jump of `0x00000208` bytes from the address of the next sequential instruction.

By replacing the opcode byte `84` (JZ) with `85` (JNZ), the spatial offset calculation (`0x208` bytes) remains perfectly preserved and structurally valid, ensuring the application does not crash due to an unaligned instruction pointer. However, the underlying CPU branching conditions are entirely inverted:

1. The analyst submits an arbitrary incorrect string (e.g., `"1234"`).
2. The inline FNV-1a routine hashes the input, yielding a value that diverges from the session target.
3. The comparison instruction `cmp r8, r12` fails, naturally setting the Zero Flag to zero (`ZF = 0`).
4. The modified `JNZ` instruction reads `ZF = 0`, evaluates the condition as true, and instantly takes the jump branch toward the success stubs (`loc_140002578`).

This subtle 1-bit mutation effectively turns the application's verification logic against itself. The program will now successfully validate any printable ASCII string, unless it accidentally matches the actual 64-bit dynamic session hash.

The automation of this binary patching process is handled via a dedicated deployment script (`patch.py`). To execute it and generate the autonomous cracked executable, run the following command in the target directory:

```bash
python3 patch.py
```

---

## 5. Dynamic Analysis & Runtime Control-Flow Manipulation

Because the verification target is tied to a cryptographically secure random seed generated at runtime, traditional static keygenning is rendered unviable. A dynamic audit of the binary was conducted using **x64dbg** to map out the application's runtime validation mechanics and hijack its evaluation states.

### x64 Architecture & Register Mapping
Unlike x86 32-bit architectures which rely on stack pushing for parameter passing, this 64-bit binary adheres strictly to the Microsoft x64 calling convention. The first four arguments are passed via registers (`RCX`, `RDX`, `R8`, `R9`).

During the inline user-input hashing routine, the CPU registers map directly to our static variables:
```assembly
.text:0000000140002350 48 0F BE 02      movsx   rax, byte ptr [rdx] ; Load input character
.text:0000000140002354 4C 33 C0         xor     r8, rax             ; v18 ^ Current_Char
.text:0000000140002357 4D 0F AF C4      imul    r8, r12             ; Hash * 0x100000001B3
```
* **`R8`** acts as the live accumulator for the user input hash (`v18`).
* **`R12`** holds the FNV prime multiplier (`0x100000001B3`).

### Runtime Control Flow Hijacking via EFLAGS Evasion
The validation check terminates at an explicit comparison boundary before triggering the success output. The session-target hash is retrieved from memory and placed into `R12`, while our input hash rests in `R8`.

```assembly
.text:0000000140002363 4C 8B 65 80      mov     r12, [rbp+60h+var_E0] ; Load session target v80
.text:0000000140002367 4D 3B C4         cmp     r8, r12               ; Compare Input vs Target
.text:000000014000236A 0F 84 08 02 00 00 jz      loc_140002578         ; Jump if correct
```

Two distinct methodologies were successfully deployed to subvert this constraint environment:

#### 1. In-Memory Key Extraction (Live Interception)
By placing a breakpoint immediately after the target hash computation, we can let the binaire generate its session key and halt execution inside the `main` loop. By reading the contents of `R12` (or tracking the output pointer of `sub_140001490` via `RAX`/`R9`), the precise 64-bit session hash value can be captured live (e.g., `0xF80ED153FE4D7157`). 

Feeding this exact hash into an inversion script or typing the matching pre-image string directly into the active console session fulfills the condition legally, forcing the application to branch into the success block.

#### 2. EFLAGS Flag Flipping (The Patchless Bypass)
Alternatively, the branching can be subverted using a dummy input payload (e.g., `"1234"`). When execution hits the evaluation phase:
1. Step onto the comparison instruction (`cmp r8, r12`). Because the hashes diverge, the CPU sets the **Zero Flag (`ZF = 0`)**.
2. Left to run natively, the conditional jump `jz` (Jump if Zero) will fail to trigger, causing the application to fall through to the access-denied stubs.
3. By manually double-clicking the **ZF** register inside x64dbg's register panel to toggle its state to **`1`**, we falsify the execution history.

The subsequent jump instruction at `0x14000236A` (`0F 84 08 02 00 00 | jz loc_140002578`) evaluates `ZF = 1` as absolute truth. The instruction pointer is hijacked, bypassing the validation logic entirely, and successfully driving the execution stream straight to the `"Correct!"` message box and success routine.
