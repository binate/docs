# 1. Scope and model

> **Status:** normative · **Maturity:** Provisional  
> **Rule-ID prefix:** `abi` (area `scope`)

## 1.1 Subject

`abi.scope.subject` — This specification defines the **binary contract** of
the Binate toolchain on each supported target: how function arguments and
results are passed (Ch.2, Ch.3), how the C boundary is crossed (Ch.4), how
symbols are named (Ch.5), how they bind and relocate in object files (Ch.6),
and what a compiled object requires of the runtime (Ch.7). It binds every
producer of machine code and every consumer of these conventions: the LLVM
backend, the native backends (x86-64, aarch64, arm32), the bytecode VM's
dispatch layer, C callers/callees at the declared interop points, and external
tools (linkers, debuggers, binding generators).

Where this spec and the language specification could be read to disagree, the
**language specification governs** — this spec describes a *conforming
realization* of it, never a loosening.

## 1.2 The interchangeability requirement

`abi.scope.cross-producer` — All code producers on a target shall be **fully
interchangeable**: an object emitted by the LLVM backend, an object emitted by
a native backend, and the bytecode VM's dispatch layer shall agree on every
convention in this spec, such that any of them can call into any other in one
process without either side knowing which produced the other. This is not
theoretical: the compiled↔interpreted dispatch seam (Ch.3) is a live
cross-producer boundary in every dual-mode process, and whole-program builds
by different backends must remain mutually link-compatible — sharing one
runtime, one startup contract, and one set of coalescing weak artifacts — so
that any mix of objects agreeing on this spec links into one correct
program.

> _Note._ This requirement is why several conventions below are pinned to what
> LLVM emits (e.g. the multi-return register rule, §2.7): the native backends
> replicate the LLVM backend's observable convention rather than inventing
> their own. Going forward this **spec** is the authority — if a future LLVM
> changes its lowering, that is a toolchain-conformance problem to fix, not a
> spec change.

## 1.3 The three convention layers

`abi.scope.layers` — The toolchain maintains three distinct calling
conventions, and every call site uses exactly one of them:

1. The **internal convention** (Ch.2) — direct calls between Binate
   functions. It is the platform C convention (§1.5) plus enumerated,
   deliberate Binate-internal deviations (large-aggregate passing,
   multi-return). C code never observes this layer.
2. The **C-boundary convention** (Ch.4) — the true, unmodified platform C ABI,
   used exactly where C is on the other side: `__c_call` call-outs, and entry
   *into* Binate code through a `#[c_export]` name or a `__c_entry` pointer.
   Where the internal convention deviates from the platform ABI, the boundary
   adapts (per-call-site reclassification outbound; normalization prefixes and
   thunks inbound).
3. The **dispatch convention** (Ch.3) — every indirect call through a function
   value, interface method, or across the compiled/interpreted seam. It is a
   Binate-specific uniform shim convention layered on the internal one,
   shared bit-for-bit by all producers (it *is* the cross-mode calling seam
   of language-spec §19.4).

## 1.4 Stability

`abi.scope.stability` — The conventions in this spec are **Provisional**: they
are implemented and normative for the current toolchain, but the ABI is **not
declared stable** — a future toolchain release may change them, and no
cross-version binary compatibility is promised. Within one toolchain version
they are binding on every producer (§1.2). Declaring any part Stable is an
explicit future decision.

## 1.5 Targets and base conventions

`abi.scope.targets` — Each supported target adopts a **base platform C
convention**, which Ch.2 then parameterizes:

| Target | Base convention | Word size | Notes |
|--------|-----------------|-----------|-------|
| x86-64 linux (ELF) | SysV AMD64 | 8 | |
| x86-64 darwin (Mach-O) | SysV AMD64 | 8 | identical convention; `_` symbol prefix only |
| aarch64 linux (ELF) | AAPCS64 | 8 | |
| aarch64 darwin (Mach-O) | Apple arm64 (DarwinPCS) | 8 | differs from AAPCS64 only in variadic placement and natural-size narrow stack args (§2.4, §2.8) |
| arm32 baremetal (ELF) | AAPCS (EABI), soft-float | 4 | strict alignment; AEABI helper calls (§2.10) |
| arm32 linux (ELF) | AAPCS-VFP, hard-float | 4 | VFP argument bank (§2.9); deliberate HFA divergence (§4.7) |

The word size `W` is the language spec's `TargetInfo.PointerSize`
(§7.13.1 `type.layout.target-info`); all layout inputs to this spec —
`SizeOf`, `AlignOf`, field offsets, the ≤16-byte by-value cutoff
(§7.13.11 `type.layout.byval-cutoff`) — are the language spec's, computed
once and consumed identically by every producer.

## 1.6 What this spec does not cover

- **Type layout** — owned entirely by language-spec §7.13.
- **Refcount semantics at call boundaries** — owned by language-spec Ch.18
  (`mem.param`, `mem.return`, `mem.no-leak`); this spec only realizes them.
- **Frame layout and register allocation inside a function** — backend-private
  and not contract, with one exception: the frame-pointer chain (§6.6).
- **The bytecode format** — VM-internal; only the VM's *dispatch seam* (Ch.3)
  is ABI.
- **The runtime function manifest** — gated on language-spec §20.2 (Ch.7).
