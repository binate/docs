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
definition and internal callers are unaffected. The same return adaptation
applies to a callback reached through `__c_entry` (§4.5), not only to a
`#[c_export]` name.

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

The declared result may be **any type with a defined C-ABI layout**, or
`"void"` (language spec `pkg.ccall`): an aggregate result is returned per
the platform C ABI — a hidden sret buffer above the byval cutoff
(§7.13.11), register-coerced below it. Opaque-by-value types are rejected,
and on **arm32 hard-float** a homogeneous-float aggregate return is
rejected (the platform returns it in VFP registers, which the internal
convention does not use — §4.7; use a pointer out-parameter there).

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

> _Note._ One declaration-parity nuance: a plain-**alias** export's narrow scalar
> parameters are declared without extension attributes on the LLVM backend
> (an alias cannot carry them, and attributing the shared internal
> definition would miscompile internal callers). This is functionally
> correct — the callee re-extends — but not clang-parity for tools that
> read parameter attributes; thunk-form entries do declare them.

## 4.5 Inbound: `__c_entry`

`abi.cabi.centry` — `__c_entry(f)` yields a C-callable pointer to `f`
(language spec `pkg.centry`). The pointer is `f`'s mangled definition address
when f needs no C-boundary adaptation, or a **weak** `__centry.<mangled>`
thunk when it does — the SAME set of f's on **every** backend, so a
mixed-producer program hands out one pointer value for f
(`pkg.centry.identity`): the weak `__centry.` copies each referencing
translation unit emits coalesce to one address program-wide. A thunk is used
when f has a **narrow GP register parameter**, a **>16-byte by-value aggregate
parameter** whose C form diverges from the internal single pointer (§2.5), or
a **divergent multi-value return** (§4.2); it performs the §4.4 adaptation
then enters the mangled definition. On the LLVM backend a
narrow-register-parameter thunk is a pure **forwarder** — the LLVM calling
convention already re-extends narrow arguments through the mangled
definition, so the thunk is functionally redundant there and is emitted only
for the cross-producer identity; the native backends' thunk does the real
argument-register re-canonicalization (§2.3). Narrow **stack** arguments need
no thunk on any backend: every native function re-canonicalizes them
unconditionally at its mangled entry (§2.3).

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
(object-format prefix applied, §5.6). `T` may be any type with a defined
C-ABI layout (opaque-by-value rejected; language spec `pkg.cglobal`);
honoring the layout — including the reference-count discipline for a
managed-typed global — is the C side's responsibility, and the recovered
pointer is always raw. One symbol cannot be both a `__c_call` function and
a `__c_global` object in a program. The relocation form of the address load
is per §6.4's C-globals rule.
