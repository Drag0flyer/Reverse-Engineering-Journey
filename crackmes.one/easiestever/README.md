# Write-Up: simplecrackme (EasiestEver)

## 1. Challenge Specifications
* **Author:** BadEngineer / EasiestEver
* **Platform:** Crackmes.one
* **Architecture:** Windows x86-64 (PE Executable)
* **Global Difficulty:** 1.6 / 6.0
* **Analysis Environment:** Windows 10/11 (Native)
* **Tools Used:** Ghidra (Static Analysis), x64dbg (Dynamic Analysis), HxD (Patching) and Python 3 (Scripting)
---

## 2. Static Analysis & Resolution
The initial exploration of the binary allowed isolating the global validation logic without having to audit the entire codebase. Unlike a classic Linux binary indexed on `argc`/`argv`, this Windows crackme uses a standard interactive command prompt.

### Validation Mechanics:
1. **Interactive Input:** The program runs in a local loop, displaying a text prompt that waits for a password input via standard input (`stdin`).
2. **Encapsulation:** The verification logic is delegated to an isolated function called `PasswordCheck`. 
3. **Algorithmic Constraint:** The function analyzes the entered string. If the password is incorrect, it returns `0` (False) in the `RAX` register. If the password is valid, it returns `1` (True), triggering the success display (a Rickroll or a validation message).

---

## 3. Advanced Analysis: Internal Structure
Diving down to the architectural level to analyze the physical structure of instructions under Windows, several key constraints were identified:

* **Memory Addressing & ASLR:** Address Space Layout Randomization (ASLR) is active on this binary. The absolute address of the validation function changes at each reboot (e.g., `00007FF65E341490`). Technical analysis allowed isolating the **static offset** of the `PasswordCheck` function, precisely located at `0x1490` relative to the base of the `simplecrackme.exe` module.
* **File Offset Mapping:** When mapping the binary from RAM to disk (PE format), this virtual offset corresponds to a physical **File Offset** of `0xA90` within the raw file.
* **Stack Frame Enforcement:** When `PasswordCheck` is called, the return address to the `main` function (e.g., `00007FF65E3416D2`) is immediately pushed to the top of the stack, pointed to by the `RSP` register.

---

## 4. Hardening Bypass via Permanent Static Patching
To permanently neutralize the password verification without having to attach a debugger at every execution, a physical static patch was designed to rewrite the opcodes of the `PasswordCheck` function directly on disk.

### Instruction Engineering (Assembly Level):
Instead of modifying a conditional jump (`JNE` -> `JMP`), the patch directly overwrites the function's original prologue at offset `0xA90` to force an immediate return with a valid status.

* **Original Prologue:** `55 53 48 81 EC 88...` 
  * Translation: `PUSH RBP`, `PUSH RBX`, stack frame allocation.
* **Patched Sequence:** `B8 01 00 00 00 C3`
  * Translation: `MOV EAX, 1` followed immediately by `RET`.

This replacement transforms the verification function into a "stub" function that no longer reads memory or user input, but simply responds instantly to `main` that the password is correct.

The automation of this static patch is handled by the script `patch.py`. To execute it and generate the autonomous modified binary, use the following command:

```bash
python3 patch.py
```

---

## 5. Algorithmic Exploitation: Keygen Automation
Rather than modifying the binary or manipulating registers on the fly, a pure algorithmic exploitation approach was developed by reversing the mathematical validation rules discovered during decompilation in Ghidra.

### Cryptographic & Logic Constraints:
The verification routine validates the password by ensuring the presence of a specific set of characters distributed across 10 strict mathematical ASCII table intervals. 

Analysis of the routine revealed two major structural constraints on the password length:
1. **The Strict Upper Bound:** The password has an absolute maximum limit of **16 characters**. Any entry exceeding this size fails validation.
2. **Adaptive Behavior:** The script generates a string whose size varies dynamically between 10 and 16 characters to satisfy internal buffer constraints. If the chosen size exceeds 10, the remainder of the password is padded with random printable ASCII characters. 

The generation script also excludes non-printable control characters (such as tabs or carriage returns) that would corrupt the input when copying and pasting into the Windows console.

The 10 validated intervals are as follows:
* `[48, 52]` (Digits from 0 to 4)
* `[72, 78]` (Uppercase letters from H to N)
* `[116, 121]` (Lowercase letters from t to y)
* `[97, 102]` (Lowercase letters from a to f)
* `[33, 38]` (Special characters from ! to &)
* `[59, 63]` (Special characters from ; to ?)
* `[106, 109]` (Lowercase letters from j to m)
* `[122, 125]` (Special characters / letters from z to })
* `[111, 115]` (Lowercase letters from o to s)
* `[92, 96]` (Characters from \ to `)

The `keygen.py` script mathematically and randomly generates a perfectly legitimate password, with a compliant length between 10 and 16 characters, which is natively accepted by the original crackme.

To generate a valid and secure key for the terminal emulator, use the following command:

```bash
python3 keygen.py
```

---

## 6. Exploitation & Manual Patching (Runtime)
In parallel with the automated solutions, a control flow hijacking technique was manually validated in RAM within x64dbg to study the dynamic behavior of the stack during an **Early Return**.

### Interception Mechanics:
1. A breakpoint is manually set at the absolute address calculated via the machine code of the original prologue of passwordCheck `55 53 48 81 EC 88`.
2. Once the breakpoint is hit upon password submission, execution freezes. The state of the registers and the stack are then directly modified from the graphical interface:
   * **`RAX = 1`** : The return value is forced to `1` (True) to simulate a successful validation.
   * **`RIP = [RSP]`** : The instruction pointer is redirected directly to the return address in `main` (`00007FF65E3416D2`), stored at the top of the stack. The x64dbg evaluator accepts and resolves this address via the expression `[rsp]`.
   * **`RSP = RSP + 8`** : The stack pointer is manually incremented by 8 bytes to discard the return address from the Stack (simulating the effect of a real `RET`) and maintain stack alignment.

This direct manipulation of hardware structures short-circuits the verification algorithm. As soon as execution is resumed, the program skips past the security restrictions and instantly displays the success message.

---

## 7. Advanced Exploitation: Stack Buffer Overflow via Persistent Memory Corruption

In addition to static patching and algorithmic reverse engineering, dynamic auditing of the binary revealed a critical Stack-based Buffer Overflow vulnerability within the `main` function. This flaw allows an attacker to corrupt the CPU's control structures and hijack the execution flow.

### Vulnerability Identification & Stack Topology
During the initialization phase of the `main` function, the compiler allocates the stack frame and reserves space for local variables using the following instruction:
```assembly
sub rsp, 40     ; Allocate 64 bytes (0x40) on the stack
```

Within this allocation, a local buffer named `password` of type `char` is given a strict size of **16 bytes**, located at the relative address `RBP - 0x10`. The physical alignment of the stack in x64dbg exposes the following downward topology (from lower addresses to higher addresses):

* **Current `RSP` (`RBP - 0x40`):** Top of the stack (lowest allocated boundary).
* **`RBP - 0x10` (x64dbg offset `$-10`):** Starting address of the 16-byte `password` buffer.
* **`RBP + 0x00` (x64dbg offset `$+0`):** Saved Base Pointer (*Saved RBP*, 8 bytes).
* **`RBP + 0x08` (x64dbg offset `$+8`):** Return address to the Windows runtime (8 bytes, critical target).

The vulnerability stems from the use of the unsafe `__mingw_scanf("%s", password)` function. This routine reads user input from `stdin` without any upper-bound verification, writing data from top to bottom (from lower addresses to higher addresses).

---

### Exploitation Strategy: Persistent State Corruption
The binary implements an interactive validation loop structured as a `while(true)` block. If the password check fails, the program prints an error message and waits for a new input via `scanf`.

While a classic exploitation technique would involve a "One-Shot" payload combining a valid password and the overflow string in a single prompt, a **persistent memory corruption** approach was successfully validated in two distinct phases, exploiting the fact that the stack memory is not reinitialized between loop iterations.

#### Phase 1: Arming the Stack (Iteration 1)
A raw 32-character string is submitted into the terminal:
`1234567890123456AAAAAAAABBBBBBBB`

1. **Buffer Saturation (Characters 1 to 16):** The bytes from `"1234567890123456"` completely fill the legitimate space allocated for `password` (offsets `$-10` and `$-8`).
2. **Control Frame Overwrite (Characters 17 to 24):** Eight 'A's (`0x4141414141414141`) entirely overwrite the *Saved RBP* at offset `$+0`.
3. **Target Overwrite (Characters 25 to 32):** Eight 'B's (`0x4242424242424242`) replace the original return address at offset `$+8`.

*Phase 1 Result:* The `PasswordCheck` routine logically fails since the input string does not satisfy the mathematical constraints. The program prints *"Wrong Password, Try again"* and loops back to the second `scanf`. Crucially, the corrupted return address remains persistently written in RAM.

#### Phase 2: Triggering the Payload (Iteration 2)
During the second iteration of the loop, a perfectly valid password is submitted.
1. Because this valid password is short, `scanf` writes it at the beginning of the buffer (`$-10`) without altering the lower stack offsets (`$+0` and `$+8`), which still retain the scars from the first round.
2. `PasswordCheck` validates the input and returns `1` in `RAX`.
3. The `break` condition evaluates to true, causing the program to instantly exit the loop. It executes `ShellExecuteA` (loading the network DLLs required to open the success URL) and reaches the `main` function's epilogue.

---

### Crash Analysis & Hardware Reaction
When the processor reaches the very last instruction of the `main` function at the absolute address `simplecrackme.00007FF65E341723`, it executes the return instruction:
```assembly
ret              ; Pop the address at the top of the stack into RIP
```

The CPU attempts to load the address stored at offset $+8 into the RIP register to return control to the operating system. This hijacking triggers an immediate access violation exception, captured in the x64dbg logs:
```
EXCEPTION_DEBUG_INFO:
   ExceptionCode: C0000005 (EXCEPTION_ACCESS_VIOLATION)
   ExceptionAddress: simplecrackme.00007FF65E341723
   ExceptionInformation[01]: FFFFFFFFFFFFFFFF Inaccessible Address
```

#### Technical Note on RBP Register Instability & Windows Runtime Behavior:
The appearance of the crash address `FFFFFFFFFFFFFFFF` (or a residual system address) instead of the expected pure `0x4242424242424242` is tied to the stack-unwinding mechanisms of the Windows environment. 

Two distinct experiments were conducted to isolate this behavior:
1. **Direct RBP Restoration:** By setting a breakpoint at the very beginning of the function's epilogue (`add rsp, 40`) and manually reconstructing a valid `Saved RBP` directly in memory, the `RBP` register was successfully restored to its pristine state prior to the `pop rbp` execution. 
2. **Runtime Stack Shifting:** Even with a perfectly clean `RBP`, the final `ret` instruction still attempts to pull its destination from an altered `RSP` context (`0x...FC48`). This behavior occurs because intermediate conditional branch operations and external API invocations—specifically the `ShellExecuteA` call sequence used to spawn the browser—dynamically allocate and shift the stack boundaries beyond the initial standard frame configurations.

Consequently, while manual runtime manipulation successfully patches hardware register states, achieving a deterministic jump directly to the payload's `0x42424242` value without system-driven offsets requires a "One-Shot" script-driven automated execution flow, bypassing interactive intermediate terminal loops entirely. Nonetheless, the control flow hijacking remains fully validated as a successful memory corruption exploit.
