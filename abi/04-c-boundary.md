# 4. The C boundary

> **Status:** normative · **Maturity:** Provisional  
> **Rule-ID prefix:** `abi` (area `cabi`)

The language spec defines *which* C interop points exist and what types may
cross them (§16.8–16.9: `pkg.ccall`, `pkg.cglobal`, `pkg.cexport.*`,
`pkg.centry.*`); all of them are compiled-mode-only (`exec.divergence`). This
chapter defines the **binary form** of those crossings.

## 4.1 Principle

`abi.cabi.principle` — Wherever C is on the other side of a call, the **true,
unmodified platform C convention** (§1.5) applies. Where the internal
convention deviates from it (§2.1), the boundary adapts: outbound `__c_call`
sites reclassify per the platform rules (§4.3), and inbound C-visible entries
normalize before control reaches internal code (§4.4–4.6). C code never
observes the internal deviations.

## 4.2 The C type mapping

`abi.cabi.mapping` — A Binate type crossing the C boundary presents as
(coordinate authority: language spec `pkg.cexport.signature`):

| Binate type | C form |
|-------------|--------|
| integer/float scalar, `bool`, `char` | the matching C scalar type |
| `*T`, `@T` | a pointer |
| raw slice `*[]T` | `struct { T* data; ptrdiff_t len; }` — `len` is **signed**, target-word-width (never `size_t`) |
| managed-slice `@[]T` | its 4-word struct `{ data, len, backing, backingLen }` |
| interface value | `struct { void* data; void* vtable; }` |
| function value | `struct { void* vtable; void* data; }` — the **reverse** field order |
| struct / array by value | per the platform C ABI, with the ≤16-byte by-value cutoff (§7.13.11) |
| multiple results | the packed anonymous result struct, or its sret form (§2.6) |

## 4.3 Outbound: `__c_call`

`abi.cabi.ccall` — A `__c_call` targets the **verbatim, unmangled** C symbol
(plus the object-format prefix, §5.6) and classifies its arguments under the
platform C convention. In particular, a by-value aggregate **larger than
16 bytes** — internally a single pointer (§2.5) — re-adapts per target:
on x86-64 it is laid out by value on the outgoing stack (SysV MEMORY,
consuming no GP register); on arm32 it is passed by value split across
R0–R3 and the stack (AAPCS); on aarch64 the internal pointer form already
**is** the platform convention and nothing changes. A variadic `__c_call` is
a true C-variadic call (§2.8).

The declared result must be a scalar, a pointer, or `void`
(language spec `pkg.ccall`).

> _Status._ Aggregate `__c_call` **returns** (an sret out-call to C) are
> unsupported — a tracked follow-up; the pointer-out-parameter idiom is the
> workaround the language spec documents.

## 4.4 Inbound: `#[c_export]`

`abi.cabi.export` — A `#[c_export("name")]` function is a **strong global**
under each export name, regardless of the function's own visibility. The
export name is an entry to the same code as the mangled symbol: the LLVM
backend emits the name as an alias of the mangled definition (the definition
itself is the C entry); the native backends emit the name as a label followed
by a **normalization prefix** — sign/zero-extension of each narrow GP register
parameter (§2.3) — that falls through or jumps to the mangled entry, so
internal callers entering at the mangled symbol skip the prefix.

> _Status._ Export signatures are not yet validated against the C mapping
> (§4.2); in particular a >16-byte by-value parameter on an exported function
> currently presents the **internal** pointer convention (§2.5) to a C caller
> on x86-64/arm32 — a known mis-ABI, raised for prioritization (a C caller
> following the platform convention will not match it). aarch64 is unaffected
> (the conventions coincide).

## 4.5 Inbound: `__c_entry`

`abi.cabi.centry` — `__c_entry(f)` yields a C-callable pointer to `f`
(language spec `pkg.centry`). On the LLVM backend the value is `f`'s mangled
definition address (that definition is already the C entry). On the native
backends, if `f` has any narrow GP register parameter the value is a **weak**
thunk `__centry.<mangled>` — emitted by every referencing translation unit
and coalesced by the linker to one address program-wide, which realizes the
same-pointer identity of `pkg.centry.identity` — performing the §4.4
normalization then jumping to the mangled entry; otherwise it is the mangled
entry itself. Narrow **stack** arguments need no thunk on any backend: every
native function re-canonicalizes them unconditionally at its mangled entry
(§2.3).

## 4.6 Sub-word values at the C boundary

`abi.cabi.subword` — At every C-visible entry and return, sub-word
integer/`bool` values are **callee-extended to the canonical full word**
(§2.3): inbound, the normalization prefixes/thunks and the unconditional
narrow-stack-argument canonicalization establish it; outbound (a C caller
reading a Binate function's result), the return is produced in canonical
extended form, and the LLVM backend additionally marks narrow scalar returns
of exported functions with the platform's extension attributes so an
optimizing C caller may rely on the extension.

> _Status._ Suspected gap (raised, unverified end-to-end): a function reached
> **only** through `__c_entry` (not also `#[c_export]`) does not receive the
> LLVM return-extension attributes, the same defect class as the fixed
> exported-function bug.

## 4.7 Known deliberate deviation: arm32 hard-float HFAs

`abi.cabi.hfa-arm32` — On arm32-linux (AAPCS-VFP), a homogeneous
float-aggregate struct/array is **not** passed or returned in the VFP bank as
the platform C ABI specifies; it uses the soft-style path (GP-coerced
argument, size-based sret return) on both the native and LLVM sides.
Binate↔Binate calls are self-consistent, but a C boundary crossing such a
type on arm32-linux mis-matches a conforming C peer. This is a deliberate,
recorded deferral (C-interop fidelity only); until it is lifted, do not pass
HFA types across the arm32-linux C boundary by value.
