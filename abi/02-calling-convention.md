# 2. Calling convention (internal direct calls)

> **Status:** normative · **Maturity:** Provisional  
> **Rule-ID prefix:** `abi` (area `cc`)

This chapter defines how a **direct call between Binate functions** passes
arguments and results. Indirect calls (function values, interface methods,
cross-mode) use the dispatch convention (Ch.3); calls with C on the other side
use the C-boundary convention (Ch.4). `W` is the target word size (§1.5).

## 2.1 Base convention and deviations

`abi.cc.base` — On each target the internal convention **is the base platform
C convention** (§1.5) — its argument registers, stack discipline, alignment,
and return registers — with exactly the following deliberate, Binate-internal
deviations, each chosen to match what the LLVM backend emits (§1.2):

1. a by-value aggregate **larger than 16 bytes** is passed as a single
   pointer to **caller-owned memory holding the value**, the callee copying
   it at entry (§2.5), on **every** target — where SysV AMD64 and AAPCS32
   would pass it by value in memory/registers;
2. **multiple results** are returned field-per-register under a
   register-count rule that exceeds the platform C ABI (§2.7) — C has no
   multi-return, so this layer is Binate-defined;
3. sub-word scalars travel in **canonical extended form** with a two-sided
   defensive discipline (§2.3), stronger than the platform ABIs require;
4. on arm32-linux the base convention's (AAPCS-VFP) **HFA** argument/return
   rules are deliberately **not** applied — float-containing aggregates ride
   the soft-style path (§2.5, §4.7).

C code is insulated from deviations (1)–(3) by the C-boundary re-adaptation
(Ch.4, subject to its recorded gaps); deviation (4) is C-observable and
recorded as such (§4.7).

## 2.2 Type classes

`abi.cc.classes` — For calling-convention purposes every Binate type is either
a **scalar** or an **aggregate**:

- **Scalars**: integer types, `bool`, `char`, `float32`/`float64`, raw
  pointers `*T`, and **managed pointers `@T`** (one pointer word; the header
  is behind the pointer, §7.13.7). A scalar occupies one GP word — except
  float scalars, which occupy the float file where the target has one
  (§2.4, §2.9), and 64-bit scalars on ILP32, which occupy a register **pair**
  (§2.4).
- **Aggregates**: structs, arrays, raw slices `*[]T` (2 words),
  managed-slices `@[]T` (4 words), interface values (2 words), function
  values (2 words). An aggregate's size in words is `ceil(SizeOf / W)`.
- A **zero-size aggregate** (`struct{}`, `[0]T`) occupies no register, no
  stack word, and no return register anywhere in this spec: it is skipped and
  no cursor advances.

Named types, `readonly`, and transparent wrappers are peeled to the
representation type first (§7.13.10).

For the register-coercion, SSE, and HFA rules below and the dispatch-shape
classification (§3.2), a struct counts as **named at the ABI layer** if it
bears any name there — **including** the compiler-synthesized names given to
source-level anonymous struct types; the only nameless aggregate is the
multi-return result tuple. Arrays participate in those rules regardless of
naming. (This is distinct from the named-type *wrapper peeling* in the
preceding sentence.)

## 2.3 Sub-word canonical form

`abi.cc.subword` — A sub-word integer scalar (any integer type, `bool`, or
`char` narrower than `W`) held in a register or in a full stack slot is
carried in **canonical extended form**: the full-width **sign**-extension of
its value for signed types, the full-width **zero**-extension for unsigned
types, `bool`, and `char`. The discipline is two-sided:

- **Callers** place narrow scalar arguments as canonical full words — in the
  argument register, or as a full `W`-byte store to the stack slot (except
  Darwin natural-size stack slots, §2.4, which are stored at natural width).
- **Callees** re-canonicalize every narrow scalar **stack** argument
  unconditionally at the function's mangled entry (a natural-size load with
  sign/zero extension) on full-slot conventions — idempotent for internal
  callers, and it cleans a foreign caller's dirty high slot bytes.
- **Callees** do **not** re-extend narrow **register** arguments at the
  mangled entry: internal callers guarantee canonical form there. Every
  **C-visible entry** (a `#[c_export]` name, a `__c_entry` pointer)
  re-establishes register canonical form before control reaches the mangled
  entry (§4.4–§4.5).
- **Returns**: a callee returns a narrow scalar result in canonical
  full-width form in the return register. A **caller** nevertheless assumes
  only the platform guarantee (correct low bits) and re-canonicalizes a
  narrow scalar result after the call, because a foreign (C) callee may leave
  the high bits dirty.

> _Note._ The asymmetry is sound for direct calls: the only producer whose
> callees rely on register-argument canonical form is the native backends,
> and their direct callers are either code produced by the same backend or C
> entering through a normalizing entry (§4.4–§4.5). The LLVM backend's
> callees read only the low bits of a narrow parameter and so rely on
> nothing. This discipline governs **direct calls only** — on the dispatch
> seam (Ch.3) narrow slot and result words carry no canonical-form guarantee
> (§3.3, §3.7).

`abi.cc.subword.float32` — A `float32` occupying a 64-bit float register
(XMM*n*, D*n*) is defined only in its low 32 bits; the high 32 bits of the
register are unspecified and shall not be relied on.

## 2.4 Argument registers and stack arguments

`abi.cc.args` — Integer/pointer argument words and float scalar arguments are
assigned to two independent register files with independent cursors; when a
file is exhausted, arguments overflow to the stack:

| Target | GP argument registers | Float argument registers | Stack slot |
|--------|----------------------|--------------------------|------------|
| x86-64 | RDI, RSI, RDX, RCX, R8, R9 | XMM0–XMM7 | 8 bytes, 8-aligned |
| aarch64 | X0–X7 | D0–D7 | 8 bytes, 8-aligned (linux); natural size for fixed narrow scalars (darwin) |
| arm32 | R0–R3 | none (soft) / VFP S0–S15 (hard, §2.9) | 4 bytes, 4-aligned; 8-aligned for 8-aligned values |

Stack arguments are laid out in argument order at increasing offsets from the
stack pointer's outgoing-arguments area; the area is rounded up to the
target's call-boundary stack alignment (§2.11).

Target-specific argument rules:

- **arm32 even-pair rule** (AAPCS stage C.3): an 8-byte-aligned *argument*
  (`int64`, `uint64`, soft-float `float64`, or an 8-aligned aggregate) starts
  on an **even** core register, skipping an odd one; a 64-bit scalar occupies
  a lo/hi little-endian pair (R0:R1 or R2:R3) or an 8-aligned 8-byte stack
  slot. The even rule applies to **arguments only** — multi-return packing
  uses consecutive registers (§2.7).
- **Spill saturation**: on the splitting conventions (aarch64, arm32; AAPCS
  stage C.6), once any GP-class argument has taken a stack portion the GP
  cursor saturates — every later GP-class argument goes to the stack even if
  registers remain. Float-file overflow does not trigger GP saturation.
- **Darwin (aarch64) natural-size stack args**: a *fixed* (non-variadic)
  narrow scalar stack argument occupies its natural size at natural
  alignment; 8-byte scalars, aggregates, and all variadic arguments take full
  8-byte slots. All other targets use full slots for every stack argument.

## 2.5 Aggregate arguments

`abi.cc.agg.small` — A by-value aggregate of **1..16 bytes** is passed in
consecutive GP argument registers, one word per register, with the base
platform's boundary behavior:

- **aarch64, arm32**: the aggregate may **split** across the register/stack
  boundary — in-register-eligible words go to the remaining registers, the
  rest to the stack, and the GP cursor then saturates (§2.4).
- **x86-64**: all-or-nothing — if the aggregate's words do not all fit in the
  remaining GP registers it goes **entirely** to memory (the SysV MEMORY
  class, laid out on the outgoing stack), and the register cursor is left for
  later arguments. A register/stack straddle never occurs.
- **x86-64 SSE classification**: a ≤16-byte ABI-named struct or array
  (§2.2) that classifies with at least one SysV **SSE eightbyte** is split by eightbyte
  class — SSE eightbytes to the next XMM registers, INTEGER eightbytes to the
  next GP registers, the two files advancing independently, all-or-nothing
  across both files.
- **aarch64 HFA**: an ABI-named struct or array (§2.2) folding to 1–4
  same-width float members is passed in consecutive D registers, all-or-nothing (on overflow
  the whole aggregate goes to the stack and the float file closes). An HFA is
  exempt from the >16-byte rule below. (arm32 hard-float deliberately does
  **not** apply the HFA rule — §4.7.)

`abi.cc.agg.large` — A by-value aggregate **larger than 16 bytes** (notably
the 32-byte managed-slice on 64-bit targets, and any large struct) is passed
as a **single pointer** to the argument value, in the next free GP register or
one stack word; the pointer shall be aligned to at least the argument type's
`AlignOf`. The pointee is owned by the caller for the duration of the
call; by-value semantics are preserved by the **callee copying** the pointee
into its own frame at entry. This is the internal deviation §2.1(1): it
matches the LLVM backend's plain-pointer lowering (AAPCS64's C convention is
already this form; SysV AMD64 and AAPCS32 C conventions are not, and the
outbound C boundary re-adapts — §4.3; inbound entries do not yet, §4.4
_Status_). Where this pointer form **is** the platform C convention
(aarch64), one thing still changes at a C boundary: the pointee shall be a
**private per-call temporary**, because a platform-C callee performs no
entry copy and may mutate the pointee in place — internal calls tolerate
shared storage only because the internal callee copies at entry.

## 2.6 Single-result returns

`abi.cc.return.scalar` — A single scalar result returns in the first GP
return register (RAX / X0 / R0) — a 64-bit scalar on arm32 in R0:R1 — or, for
a float scalar, in the float return register (XMM0 / D0 / soft-float R0 or
R0:R1; hard-float arm32 S0/D0). Sub-word results are in canonical extended
form (§2.3).

`abi.cc.return.small-agg` — A single aggregate result that does not require
sret (below) returns packed by value: bytes 0..W−1 in the first GP return
register, bytes W..2W−1 in the second (x86-64: RAX then RDX; aarch64: X0 then
X1; arm32: R0, ≤4 bytes only). On x86-64, an aggregate with SSE eightbytes
returns by eightbyte class (SSE eightbytes in XMM0/XMM1, INTEGER in RAX/RDX,
independent cursors). On aarch64, an HFA result returns in D0..D3 regardless
of size and is never sret.

`abi.cc.return.sret` — A single **aggregate-kind** result larger than
**16 bytes** (64-bit targets) or **4 bytes** (ILP32) is returned through a
caller-allocated buffer (**sret**): the caller passes the buffer address in
the target's sret register before the call, and the callee writes the result
through it. The buffer shall be aligned to at least the result type's
`AlignOf`. Scalars are never sret (an ILP32 `int64` returns in R0:R1). The
sret register:

| Target | sret register | Effect on arguments | Buffer pointer returned? |
|--------|---------------|---------------------|--------------------------|
| x86-64 | RDI (first GP arg register) | every user argument shifts up one slot | yes, in RAX (per SysV) |
| aarch64 | X8 (dedicated) | none | no |
| arm32 | R0 (first GP arg register) | every user argument shifts up one slot | yes, in R0 |

Where the sret register is a GP argument register, the shift participates in
all argument classification (including the arm32 even-pair padding) as if a
pointer argument were prepended.

> _Status._ The arm32 "buffer pointer returned in R0" leg is pinned against
> clang/LLVM behavior; its grounding in the AAPCS document itself has not been
> re-verified. Treat it as the implemented contract.

## 2.7 Multiple-result returns

`abi.cc.multi-return` — A function with multiple results returns the packed
anonymous result struct (§10 of the language spec) **field-per-register by
class**, exactly as LLVM lowers a first-class aggregate return — *not* under
the platform's small-composite rule:

- Each non-float field fills `ceil(SizeOf/W)` consecutive GP **return**
  registers in field order (no even-pair bump on arm32; a 64-bit field takes
  a consecutive pair). Each float-scalar field fills the next float return
  register. The two cursors are independent. Zero-size fields consume
  nothing. Sub-word fields are stored back at their natural size at the
  tuple's field offset, so neighbors sharing a word are not clobbered.
- The tuple goes **sret** (same mechanics as §2.6) exactly when either file
  overflows its budget — a register-**count** rule, not a size rule:

| Target | GP return budget | Float return budget |
|--------|------------------|---------------------|
| x86-64 | 3 (RAX, RDX, RCX) | 2 XMM (XMM0, XMM1) + 2 x87 (ST0, ST1) |
| aarch64 | 8 (X0–X7) | 8 (D0–D7) |
| arm32 | 4 (R0–R3) | 0 (soft — float fields count as GP words) / 4 (hard: D0–D3) |

So on x86-64 `(int, int, int)` returns in RAX/RDX/RCX while the 8-byte
`(uint16, uint16, uint16, uint16)` is sret; the 3rd and 4th float fields of an
in-register x86-64 tuple travel on the x87 stack (callee loads in reverse
field order so the lower-indexed field ends on ST0).

> _Note._ This convention exists because C has no multi-return; it was derived
> empirically from LLVM/clang's first-class-aggregate return lowering and is
> now normative here (§1.2 Note). The **internal** form is not reachable from
> C; a C-visible entry adapts a multi-result export to the platform
> struct-return convention (§4.2).

## 2.8 Variadic calls

`abi.cc.variadic` — Binate variadic functions do not reach this layer: the
caller erases variadic-ness into an ordinary `*[]T` argument before any call
(language spec `func.variadic.identity`). Only **`__c_call`** produces a true
C-variadic call, with the platform rules:

- **x86-64**: AL carries the number of XMM registers actually used by the
  arguments (0–8) before the call; variadic floats still ride XMM per SysV.
- **aarch64 darwin**: every variadic argument, floats included, goes to the
  stack in 8-byte slots; **aarch64 linux** passes variadic arguments exactly
  like fixed ones.
- **arm32 hard-float**: variadic floats use the base (soft) standard — GP
  registers/stack, never the VFP bank.

No C **default argument promotions** are performed on a variadic tail: each
argument crosses at its own declared type. A variadic-tail argument shall
therefore already have its C-promoted type — `float64` (not `float32`), an
integer of at least `int` width (not a sub-word integer, `bool`, or `char`)
— else the C callee's `va_arg` mis-reads it; such arguments are **rejected
at compile time**.

## 2.9 arm32 hard-float (AAPCS-VFP) specifics

`abi.cc.vfp` — On arm32-linux, float scalar arguments use the VFP bank under
the AAPCS co-processor-register-candidate rule, **not** a monotonic cursor: a
`float32` takes the lowest free single S slot (back-filling holes left by
`float64` even-alignment), a `float64` the lowest free even S pair; the first
float argument that spills to the stack closes the bank for all later float
arguments. A single float result returns in S0/D0; float multi-return fields
use D0–D3 via the same allocator. Float-containing aggregates deliberately do
**not** use the VFP bank (§4.7).

## 2.10 arm32 AEABI helper calls

`abi.cc.aeabi` — On arm32, 64-bit integer multiply/divide/shift and all
soft-float arithmetic lower to ARM RT-ABI (`__aeabi_*`) helper calls with
their standard register conventions (e.g. `__aeabi_ldivmod`: numerator
R0:R1, denominator R2:R3 → quotient R0:R1, remainder R2:R3). A conforming
arm32 link therefore provides the AEABI helper surface; the baremetal runtime
provides it C-free.

## 2.11 Stack alignment

`abi.cc.stack-align` — The stack pointer is aligned at every public call
boundary to **16 bytes** on x86-64 and aarch64, **8 bytes** on arm32.
Frame-internal layout (spill slots, save areas, frame size rounding) is
backend-private and not contract (§1.6), with the frame-pointer-chain
exception in §6.6.
