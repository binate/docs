# 4. The C boundary

> **Status:** normative · **Maturity:** Provisional  
> **Rule-ID prefix:** `abi` (area `cabi`)

The language spec defines *which* C interop points exist and what types may
cross them (§16.9: `pkg.ccall`, `pkg.cglobal`, `pkg.cexport.*`,
`pkg.centry.*`); all of them are compiled-mode-only (`exec.divergence`). This
chapter defines the **binary form** of those crossings.

## 4.1 Principle

`abi.cabi.principle` — Wherever C is on the other side of a call, the **true,
unmodified platform C convention** (§1.5) applies. Where the internal
convention deviates from it (§2.1), the boundary adapts: outbound `__c_call`
sites reclassify per the platform rules (§4.3), and inbound C-visible entries
normalize before control reaches internal code (§4.4–4.6). C code never
observes the internal deviations — subject to the recorded gaps and the one
deliberate deviation (§4.4 _Status_, §4.7).

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
| multiple results | the platform C ABI for a struct with the result fields — see below |

A **multi-result** function's C form is the platform struct return of its
packed result tuple. The **internal** convention (§2.7) is not that — its
register form and its sret trigger (register-count, not size) both differ —
so the C-visible entry **adapts**: where the C ABI srets a
register-returned tuple, the entry stores the register result through the
caller's sret buffer; where both sides return in registers but placements
differ, the entry presents the platform's coerced form; where the internal
convention srets a tuple that C returns in registers, the entry hands the
definition a local buffer and re-loads it packed. Tuples on which the two
conventions already agree are entered directly (§4.4). The mangled
definition and internal callers are unaffected.

> _Status._ `__c_entry` of a multi-result function does not yet route
> through this adaptation — the callback pointer presents the internal
> convention to its C caller. Raised; the decided fix extends the
> `__centry.` thunk (§4.5) with the same return adaptation.

## 4.3 Outbound: `__c_call`

`abi.cabi.ccall` — A `__c_call` targets the **verbatim, unmangled** C symbol
(plus the object-format prefix, §5.6) and classifies its arguments under the
platform C convention. In particular, a by-value aggregate **larger than
16 bytes** — internally a single pointer (§2.5) — re-adapts per target:
on x86-64 it is laid out by value on the outgoing stack (SysV MEMORY,
consuming no GP register); on arm32 it is passed by value split across
R0–R3 and the stack (AAPCS); on aarch64 the internal pointer form already
**is** the platform convention and nothing changes. A variadic `__c_call` is
a true C-variadic call (§2.8, including its no-default-promotions rule).

The declared result must be a scalar, a pointer, or `void`
(language spec `pkg.ccall`).

> _Status._ Aggregate `__c_call` **returns** (an sret out-call to C) are
> unsupported — a tracked follow-up; the pointer-out-parameter idiom is the
> workaround the language spec documents.

## 4.4 Inbound: `#[c_export]`

`abi.cabi.export` — A `#[c_export("name")]` function is a **strong global**
under each export name, regardless of the function's own visibility. The
export name is an entry to the same code as the mangled symbol. Where the
function's C form (§4.2) coincides with its internal convention, the name is
a plain alias (LLVM) or label (native) of the mangled definition; where they
differ, the name leads through a per-function **adapting entry** — a C-ABI
thunk on the LLVM backend, an adapter trampoline on the native backends —
that re-marshals the divergent pieces and forwards to the mangled
definition: narrow GP register parameters are re-extended (§2.3), a
>16-byte by-value parameter arriving per the platform convention (by value
in memory/registers on x86-64/arm32) is re-materialized as the internal
pointer-to-copy form (§2.5; the aarch64 conventions coincide), and a
multi-result return is adapted per §4.2. Internal callers enter at the
mangled symbol and pay none of this.

> _Note._ Export signatures are not yet *validated* against the C mapping —
> a tracked follow-up — but the shapes above are adapted, not mis-ABI'd.
> One declaration-parity nuance: a plain-**alias** export's narrow scalar
> parameters are declared without extension attributes on the LLVM backend
> (an alias cannot carry them, and attributing the shared internal
> definition would miscompile internal callers). This is functionally
> correct — the callee re-extends — but not clang-parity for tools that
> read parameter attributes; thunk-form entries do declare them.

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

> _Status._ The same-pointer identity currently holds **within one
> producer's program**: for the same narrow-parameter `f`, the LLVM lowering
> yields the mangled definition address while the native lowering yields the
> `__centry.` thunk address, so a mixed-producer program would violate
> `pkg.centry.identity` — raised for harmonization.

## 4.6 Sub-word values at the C boundary

`abi.cabi.subword` — At every C-visible entry and return, sub-word
integer/`bool` values are **callee-extended to the canonical full word**
(§2.3): inbound, the adapting entries (§4.4–§4.5) and the unconditional
narrow-stack-argument canonicalization establish it; outbound (a C caller
reading a Binate function's result), the return is produced in canonical
extended form, and the LLVM backend marks narrow scalar returns of
C-visible functions — exported or `__c_entry`-reached — with the platform's
extension attributes so an optimizing C caller may rely on the extension.
Symmetrically, a narrow scalar **fixed-position argument** of a `__c_call`
crosses in the platform's expected caller-extended form (the LLVM backend
declares and emits the extension attributes; the native backends pass
canonical full words). Variadic-tail arguments are instead governed by the
no-promotions rule (§2.8): the programmer passes pre-promoted values.

## 4.7 Known deliberate deviation: arm32 hard-float HFAs

`abi.cabi.hfa-arm32` — On arm32-linux (AAPCS-VFP), a homogeneous
float-aggregate struct/array is **not** passed or returned in the VFP bank as
the platform C ABI specifies; it uses the soft-style path (GP-coerced
argument, size-based sret return) on both the native and LLVM sides.
Binate↔Binate calls are self-consistent, but a C boundary crossing such a
type on arm32-linux mis-matches a conforming C peer. This is a deliberate,
recorded deferral (C-interop fidelity only); until it is lifted, do not pass
HFA types across the arm32-linux C boundary by value.

## 4.8 `__c_global`

`abi.cabi.cglobal` — `__c_global("sym", T)` is an **address materialization,
not a call**: the verbatim symbol becomes an undefined **data** external
(object-format prefix applied, §5.6), with `T` restricted to a scalar or
pointer (language spec `pkg.cglobal`), and one symbol cannot be both a
`__c_call` function and a `__c_global` object in a program. The relocation
form of the address load is per §6.4's C-globals rule.
