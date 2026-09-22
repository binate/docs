# 7. The runtime at the ABI level

> **Status:** normative · **Maturity:** Draft — the authoritative runtime
> function **manifest** is owned by language-spec §20.2 (`pkg0.rt`), which is
> gated on the runtime-surface review and not yet authored. This chapter pins
> only the linkage-level facts compiled objects already rely on.  
> **Rule-ID prefix:** `abi` (area `rt`)

## 7.1 The runtime is an ordinary linked package

`abi.rt.linkage` — Every compiled module implicitly depends on
`pkg/builtins/rt`; its entry points are **ordinary mangled `bn_F` symbols
with the ordinary calling convention** (Ch.2) — there is no special runtime
calling convention and no magic linkage. A generated object may therefore
reference runtime entry points exactly as it references any package's
functions. The runtime contains **no C code** (it is Binate plus per-target
assembly); note, though, that the **hosted** runtime's raw layer reaches the
platform through `__c_call`, so hosted object sets carry undefined externals
such as `malloc`, `calloc`, `free`, `write`, and `abort` — only the
bare-metal backend is C-free.

> _Note (informative)._ The entry points generated code currently references
> include allocation (`Alloc`, `Box`, `MakeManagedSlice`), reference counting
> (`RefInc`, `RefDec`, `ZeroRefDestroy`, `Free`), checks and aborts
> (`BoundsCheck`/`BoundsFail`, `DivCheck`, `ShiftCheck`, `Panic`,
> `AssertFail`, `Abort`), stack-trace capture (`CaptureNativeFrames`), and
> the satisfaction registry (`BuildSatRegistry`, `SatLookup`). The normative
> manifest — the guaranteed-minimal set and its exact signatures — is §20.2's
> to define.

## 7.2 Reference-count operations

`abi.rt.refcount` — The reference-count contract compiled code realizes: the
managed header is the language spec's two words `{refcount, free_fn}`
immediately before the payload (§7.13.7); a **negative** refcount marks an
immortal (static) allocation — reference-count operations on it are no-ops
and it is never freed (static managed data is emitted with the sentinel value
−1073741824); a null pointer is likewise a no-op. Destructor arguments passed
to the runtime are function-value **handles** (§3.4), never raw code
addresses, so destruction dispatches mode-independently. A producer may
inline the count fast path (calling out only when a decrement reaches zero)
or call the runtime's count operations out-of-line; the two are
observationally equivalent under the language spec's memory rules and both
are in use today.

## 7.3 Declared non-symbols

`abi.rt.magics` — A small set of names declared in the runtime's interface
are **compiler-recognized primitives, not linkable symbols**: the cross-mode
dispatch magics (`_call_shim_scalar`, `_call_shim_scalar64`,
`_call_shim_aggregate`) and the handle-call magics (`_call_dtor`,
`_call_free_fn`). The compiler lowers calls to them directly (§3.5); no
object defines or may reference them as symbols.

## 7.4 Per-target assembly members

`abi.rt.asm` — Runtime-owned assembly reaches a build through two
arrangements. Members of an ordinary runtime package ride the general
**package assembly-file** mechanism (§6.8; language spec §16.10) — e.g. the
aarch64 `MemZero`, a build-gated assembly file in the runtime package whose
object ships beside the package's compiled object in every artifact, plain
compile-to-objects sets included, with no per-symbol knowledge in the
compiler. The arm32 bare-metal **platform floor**, by contrast, is still
supplied as per-target link-time runtime files: the startup glue, the
semihosting members (mangled Binate symbols defined in assembly for a
`.bni`-only package), and the **AEABI helper set** under its standard
unmangled `__aeabi_*` names with the AEABI register conventions (§2.10).
To callers, assembly definitions are indistinguishable from Binate
definitions under either arrangement; both are implementation
arrangements, not additional ABI surface.
