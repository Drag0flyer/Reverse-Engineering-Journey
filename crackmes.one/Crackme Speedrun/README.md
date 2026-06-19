# Write-Up: Crackme Speedrun (Piggy63)

## 1. Challenge Specifications
* **Author:** Piggy63
* **Platform:** Crackmes.one
* **Architecture:** Windows x86 (PE Executable)
* **Global Difficulty:** 2.3 / 6.0
* **Analysis Environment:** Windows 10 (VM)
* **Tools Used:** Ghidra/IDA (Static Analysis), x32dbg (Dynamic Analysis), HxD (Patching) and Python 3 (Scripting)

---

## 2. Static Analysis & Resolution
The initial exploration of the binary highlighted a blatant discrepancy in environment handling depending on the static analysis tool utilized. Unlike previous versions, the combined use of Ghidra and IDA Free bypassed the intricate initialization layers imposed by the Microsoft Visual C++ Runtime (MSVC CRT).

### Discovering and Isolating the `main` Function:
1. **Ghidra's Raw Approach (`entry`):** Upon opening the file in Ghidra, the disassembly defaults to the actual raw entry point of the PE header (`entry`). This block hosts no user-written code but initializes the *Stack Canaries* security mechanism via the `__security_init_cookie()` system call, before losing itself in the forest of the runtime's internal functions (CRT).
2. **IDA Free's Heuristic:** Unlike Ghidra, IDA Free's static analysis engine automatically identified the signatures of the MSVC initialization *boilerplate*. It successfully masked the internal plumbing to instantly position the analyst at the true logical **`main`** function of the application at the documented address.

---

## 3. Advanced Analysis: Internal Structure & Decompilation Clean-up
Once inside `main`, the decompilation environment reveals a streamlined structure that relies heavily on global variables and mathematical obfuscation through constant expressions.

```
[ sub_4016E0 ] (Printf)  --> Displays "Password : "
│
▼
[ sub_401720 ] (Scanf)   --> Captures input into Str2
│
▼
[ sub_401490 ] (Logic)   --> Calls sub_401040 (Key generation)
│                      Validates input via sub_4015A0 (Validation)
▼
[ strcmp(Str1, Str2) ]   --> Final string validation
│
├── (Equality == 0) ──► [ Displays "Correct !" ]
└── (Inequality)    ──► [ Displays "Incorrect !" ]
```

### Refactoring and Cleaning up the Environment:
* **Resolving Windows I/O Streams:** The `sub_4016E0` function internally calls `__acrt_iob_func(1u)` (the stream descriptor for `stdout`), confirming it encapsulates `printf`. Conversely, `sub_401720` requires `__acrt_iob_func(0)` (`stdin`), acting as a wrapper for user input (`scanf`).
* **The Ghidra Decompilation Artefact Trap:** Inside the main verification routine (`sub_401490`), Ghidra generated a raw, unreadable decompilation, translating MSVC's stack optimizations into complex raw pointer casts (`*(int *)(param_1 + 0x11c)`). Importing the binary into IDA Free resolved this graphical artefact by applying aggressive heuristic rules, exposing the underlying manipulation of a clean integer array (`v4[index]`).

### Global Algorithmic Logic:
The binary dynamically generates a reference key in memory and then validates user input character by character using an inverted verification routine.

#### A. Dynamic Hash Table Generation (`sub_401040`)
This function computes and fills a local array of 70 integers (`v5`) using heavy mathematical operations and calls to a local exponentiation function (`sub_401000`). Symbolic execution through our Python script resolved these fixed constraints to yield the exact byte assignments:
* **`v5[1]` (v6):** Resolution of bit shifts, multiplications, and divisions $\rightarrow$ ASCII value `102` (`'f'`).
* **`v5[41]`:** Core offset computation based on string array pointer values $\rightarrow$ ASCII value `114` (`'r'`).
* **`v5[40]`:** Evaluation of boolean conditions via `sub_401000` $\rightarrow$ ASCII value `115` (`'s'`).
* **`v5[55]`:** Validation array element increment $\rightarrow$ ASCII value `116` (`'t'`).
* **`v5[0]` (v2):** Character extraction from reference string and offset padding $\rightarrow$ ASCII value `101` (`'e'`).
* **`v5[69]` (stack):** Stack alignment calculation $\rightarrow$ ASCII value `97` (`'a'`).

#### B. Sequential Validation Pipeline (`sub_4015A0`)
The `sub_401490` function transmits elements of the calculated array to the `sub_4015A0` validation routine. This routine uses a global variable `counter` as an index that auto-increments with each call (`++counter`).

The internal validation constraint is dictated by the pointer formula:
```c
return a1 == Str2[5 - a2];
```

This structure indicates an index inversion (a Bottom-Up selection of the generated key compared against a Top-Down reading of the ```Str2``` string). The evaluation order of the arguments within the conditional ```if``` block reconstructs the password in reverse order of its reading:

| Call Sequence (counter) | Evaluated Element (v4[index]) | Calculated Value (ASCII) | Targeted Index in Password |
| :---: | :--- | :--- | :--- |
| **0** | `v4[41]` | 114 ('r') | `Str2[5]` |
| **1** | `v4[0]`  | 101 ('e') | `Str2[4]` |
| **2** | `v4[55]` | 116 ('t') | `Str2[3]` |
| **3** | `v4[40]` | 115 ('s') | `Str2[2]` |
| **4** | `v4[69]` | 97 ('a')  | `Str2[1]` |
| **5** | `v4[1]`  | 102 ('f') | `Str2[0]` |

The global variable `dword_41F980` (named `isCorrect` or `dword_41F980`) toggles to `1` when the index reaches the flag value calculated by `14h >> 2` (which is `5`), serving as an integrity check to prevent loop bypass via register tampering.

### Flag Resolution:
By reversing the extraction order imposed by the index subtraction (`5 - counter`), the characters realign to form the valid password. The Python resolution script mathematically confirms the byte alignment:

```text
Str2[0] = 'f'
Str2[1] = 'a'
Str2[2] = 's'
Str2[3] = 't'
Str2[4] = 'e'
Str2[5] = 'r'
```

---

## 4. Hardening Bypass via Permanent Static Patching
To permanently neutralize the serialization verification without having to input a valid key at every execution, a physical static patch was designed to alter the control flow mechanics directly on disk using HxD. 

### Instruction Engineering (Assembly Level):
Instead of simply bypassing a single check, a dual-layer patch strategy was engineered to completely decouple the success path from the user input. By applying `NOP` (*No Operation*) chains at key decision points, the binary is forced to flow naturally into the victory routines.

#### A. Neutralizing the Character Evaluation Loop (`sub_401490`)
The initial validation pipeline relies on an aggregated `if` condition checking sequential returns from `sub_4015A0`. By replacing the conditional branches (`JZ` / `JNZ`) following these evaluations with `NOP` instructions (`0x90`), the application blindly bypasses the validation constraints and triggers the internal `sub_4012D0()` setup function.

#### B. Overriding the Final String Comparison (`main`)
The ultimate logical barrier resides within the `main` routine, where a standard `strcmp` evaluates the user's entry against the generated buffer. 

* **Original Sequence:** The compiler emits a conditional jump instruction right after the comparison to pivot to the failure branch (`sub_4016E0((int)aIncorrectHintD);`) if the strings do not match.
* **Patched Sequence:** The critical conditional jump opcodes were overwritten with a series of `0x90` (`NOP`) instructions. 

### Resulting Control Flow Behavior:
As a consequence of this instruction elimination, the CPU slides straight through the conditional checks without evaluating the registers. Testing the patched binary with arbitrary one-character inputs (such as `'a'`) instantly yields a successful execution path, confirming that the crackme's security model has been permanently and statically defeated.
