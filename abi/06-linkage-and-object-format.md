# 6. Linkage and object format

> **Status:** normative · **Maturity:** Provisional  
> **Rule-ID prefix:** `abi` (area `obj`)

## 6.1 Symbol binding

`abi.obj.binding` — Function definitions bind **strong global** by default —
including package-private functions, which are namespaced only by mangling.
The following are emitted **weak** (ELF `STB_WEAK` / LLVM `weak_odr`, plus a
COMDAT group per symbol on ELF; Mach-O `N_WEAK_DEF`, no COMDAT) so that
per-translation-unit copies coalesce to one definition at link:

- generic instantiations, synthesized destructor/copy helpers, and
  value-receiver interface-dispatch adapter thunks (emitted into every
  consuming module);
- the function-value shim/vtable/handle triples (§3.4) and `__centry.`
  thunks (§4.5);
- interface vtables, TypeInfo records and identity tokens, satisfaction
  entries (§5.5);
- on the native backends, string managed-slice headers (§6.5).

Data globals bind per their role: package-level `var` storage and the
per-package satisfaction-graph node are **strong**; the cross-package
satisfaction-graph fallback leaf is weak (so a package's own strong node
overrides it); the per-package descriptor table nodes are weak (their
package-name blob local); TU-local blobs (string bytes, RTTI name/field
blobs) are **local** and invisible to resolution.

## 6.2 Resolution rules

`abi.obj.resolution` — Symbol resolution follows the classical model, and the
self-hosted linker implements exactly: a strong definition overrides any
number of weak definitions of the same name; two strong definitions are a
duplicate-symbol error; an undefined strong reference is an error; an
undefined **weak** reference resolves to address 0; locals do not participate.
Archive members may be selected by either strong or weak definitions of a
needed symbol.

## 6.3 Sections

`abi.obj.sections` — Emitted data is placed by content: executable code in
`text`; mutable data in `data`; relocation-free read-only bytes in `rodata`;
**read-only data containing any symbol-reference relocation** in
`rodata_relro` (constant after load-time fixups — this covers vtables,
TypeInfo, handles, satisfaction entries, string headers); zero-initialized
storage in `bss` — a format capability that today only LLVM-produced objects
populate (the native backends emit package-variable storage as explicit
zero-filled blobs in `data`). The abstract sections map to:

| Abstract | ELF | Mach-O |
|----------|-----|--------|
| text | `.text` | `__TEXT,__text` |
| rodata | `.rodata` | `__TEXT,__const` |
| rodata_relro | `.data.rel.ro` | `__DATA_CONST,__const` |
| data | `.data` | `__DATA,__data` |
| bss | `.bss` | `__DATA,__bss` |

ELF objects always carry an empty `.note.GNU-stack` (non-executable stack);
arm32 objects written by the self-hosted object writer carry
`.ARM.attributes` only when hard-float (declaring v7/VFPv3/VFP-register
argument passing); clang-produced (LLVM-backend) arm32 objects carry the
section under both float ABIs.

## 6.4 Relocations

`abi.obj.reloc` — The conventions an external tool can rely on:

- A word-sized **data symbol reference** (a vtable slot, a handle field, a
  TypeInfo pointer) is an absolute-address relocation (`R_X86_64_64` /
  `R_AARCH64_ABS64` / `R_ARM_ABS32` / `*_RELOC_UNSIGNED`) over zeroed
  placeholder bytes.
- **Addend transport**: RELA (x86-64, aarch64 ELF) carries the addend in the
  relocation record; REL (arm32 ELF) and Mach-O bake it into the patched
  field. x86-64 PC-relative relocations store `addend − 4` (the
  displacement is measured from the instruction end); arm32 branch
  relocations bake the −8 pipeline bias into the instruction.
- **PIE policy**: hosted x86-64/aarch64 links (and LLVM-backend
  arm32-linux links) are position-independent **executables**; the native
  arm32 backend emits an absolute code model and forces a non-PIE link. In
  PIE links a PC-relative reference to a *defined* symbol (weak included)
  binds to the image's own copy (ELF `PC32`), and only
  undefined-at-assembly targets use `PLT32`. A shared-object target would
  need the preemptible-symbol rules and is out of scope.
- **C globals** (`__c_global`, §4.8): on PIE links the address is loaded
  GOT-indirect (x86-64 `GOTPCREL`; aarch64 ADRP+LDR GOT pair); on the
  native arm32 backend's non-PIE links it is materialized with a MOVW/MOVT
  absolute pair and **no GOT**.

## 6.5 Static data conventions

`abi.obj.static-data` — String literals emit as a TU-local, NUL-**less** byte
blob (Binate text is length-carried, never NUL-terminated) plus a 4-word
static managed-slice header `{data, len, backing = null, backingLen = len}`
whose null backing makes it refcount-inert; the header is the value code
references. Package-level `var` storage is a strong, zeroed blob of
`SizeOf` bytes at `AlignOf` (initializers run at startup inside the package's
`__init`). A TypeInfo record's address is the program-wide identity token for
its type (one weak, coalesced record per concrete type); interface
satisfaction is a distributed registry of weak `__satentry.` records reached
from each package's satisfaction-graph node and built at program startup
(§6.7, including its _Status_ note on library builds) — it is deliberately
**not** part of the TypeInfo record.

## 6.6 The frame-pointer chain

`abi.obj.fp-chain` — Every compiled function maintains a walkable
frame-pointer chain — `[fp]` holds the caller's frame pointer, `[fp + W]`
(arm32: `[fp + 4]`) the return address — on every target and both backends
(the LLVM backend pins frame pointers on every function for this reason). The
runtime's stack-trace capture walks this chain. All other frame-layout
choices are backend-private (§1.6).

## 6.7 Program startup

`abi.obj.entry` — The linkage contract is the language spec's
`prog.entry.glue` (`bn_entry`, `bn_init`); its current realization:

- **Hosted**: the startup package exports the C `main` —
  `#[c_export("main")]` with signature `(argc int32, argv **char,
  envp **char) int32` (`int32` deliberately: C `int` is 32-bit on all
  supported targets while Binate `int` is word-width) — which captures
  Args/Env and calls `bn_entry`.
- **Bare metal**: a `crt0` `_start` establishes the stack and branches to
  `bn_entry`.
- **Library**: the host calls `bn_init` (idempotent; run-once guard).

A **program** artifact defines `bn_entry` and no `bn_init`; a **library**
artifact defines `bn_init` and no `bn_entry`. `bn_entry` builds the
interface-satisfaction registry, runs package initialization in dependency
order (through an internal dispatcher), then calls `main.main`
(language spec §17).

> _Status._ Two recorded divergences, both raised for the owner: the cited
> `prog.entry.glue` reads as if both glue symbols exist in every artifact
> and as if `bn_entry` reaches initialization through `bn_init`, neither of
> which the realization does; and a **library** build currently never
> builds the interface-satisfaction registry (`bn_init` runs package
> initializers only), so interface assertions inside a library miss.
