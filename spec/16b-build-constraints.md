# 16.7–16.9 Annotations, build constraints, and the FFI boundary

> **Status:** mixed · **Maturity:** the annotation/build-constraint surface covers `arch`/`os` membership plus a compiler-`version` matcher (further predicates deferred); `__c_call` is compiled-mode only; `#[c_export]` is implemented; `__c_entry` is Draft (ratified, not yet implemented); linker-placement is **Draft/pending**  
> **Rule-ID prefix:** `pkg`

This continues [Ch.16 Packages and Program Structure](16-packages-and-program-structure.md)
with the annotation system (§16.7), build constraints (§16.8), and the
foreign-function boundary (§16.9).

## 16.7 The annotation system

`pkg.annotation` —

```
Annotation      = "#" "[" [ AnnotationEntry { "," AnnotationEntry } ] "]" ;
AnnotationEntry = AnnotationName [ "(" [ Expression { "," Expression } ] ")" ] ;
AnnotationName  = identifier { "." identifier } ;
```

An **annotation block** `#[ … ]` attaches metadata to the element it
**immediately precedes**. In the current implementation an annotation block may
lead the **package clause**, an **import**, or a **top-level declaration**. A
block holds comma-separated **entries**; each entry is a (possibly dotted) name
with an optional parenthesized list of expression arguments. (The parser tolerates
the degenerate empty forms `#[]` and `name()`; they carry no meaning.)

`pkg.annotation.namespace` — An annotation **name** is a dotted identifier, and
its first segment determines who must understand it:

- An **unqualified** name (no dot) is language-standard and **must be recognized**
  by the compiler — an unknown unqualified name is a **compile error** (this
  catches typos). The unqualified annotation implemented today is `build`
  (§16.8) and the FFI-export annotation `c_export` (§16.9); the linker-placement
  `section` / `link_at` (§16.9) are unqualified/compiler-recognized too, but remain
  **Draft / pending** (specified, not yet implemented). _Caveat (current impl):_ this typo check fires only where build
  constraints are evaluated — i.e. when a build configuration is resolved
  (§16.8). With no build configuration (the REPL, the bytecode tool, unit tests),
  annotation names are not currently validated, so a typo'd unqualified name is
  silently kept rather than diagnosed.
- A **namespaced** name (containing a dot — e.g. `tool.lint`, `compiler.inline`)
  is metadata for another tool and is **ignored** by the compiler.

`pkg.annotation.no-stack` — At most **one** annotation block precedes each
element; blocks do not stack. Combine multiple annotations as comma-separated
**entries within one block**, not as adjacent blocks.

> _Note._ A grouped declaration's annotation attaches to the **group**
> (`const ( … )`, `var ( … )`, `type ( … )`), not to its individual specs; a
> grouped import shares one annotation block across all of its specs. To
> annotate one member individually, write it ungrouped. The richer
> attachment positions of the design (struct fields, a type definition after its
> name) are reserved; current use is the package-clause / import / declaration
> positions above.

## 16.8 Build constraints

`pkg.build` — A `#[build(EXPR)]` annotation makes the element it annotates opt
in or out of compilation for the active target. `EXPR` is a single boolean
expression over **membership clauses**:

```
BuildExpr   = Clause
            | "!" BuildExpr
            | BuildExpr "&&" BuildExpr
            | BuildExpr "||" BuildExpr
            | "(" BuildExpr ")" ;
Clause      = ( "is" | "at_least" | "at_most" ) "(" predicate "," string_literal ")" ;
```

An atomic clause is a predicate call `<fn>(predicate, "tag")`. Clauses combine only
with `&&`, `||`, and `!` — a bare *comparison* operator such as `==` or `<` is
**not** accepted (see below). The predicates defined are:

- **`arch`** (*membership*) — `is(arch, "…")`: `"x64"`, `"aarch64"`, `"arm32"` (with
  the assembler aliases `"x86_64"` = `x64`, `"arm64"` = `aarch64`, `"arm"` = `arm32`).
- **`os`** (*membership*) — `is(os, "…")`: `"linux"`, `"darwin"`, `"baremetal"` (no
  aliases yet).
- **`version`** (*ordered*) — the **compiling compiler's own** version
  (`pkg.build.version`), **not** a target property. `at_least(version, "X.Y.Z")`
  (≥), `at_most(version, "X.Y.Z")` (≤), and `is(version, "X.Y.Z")` (exact); the
  remaining three relations come from `!` (`!at_least` = `<`, `!at_most` = `>`,
  `!is` = `≠`).

`arch` and `os` are **membership** predicates — a target belongs to overlapping
descriptor sets, so equality is meaningless; only `is` applies, which is why a bare
comparison operator is rejected. `version` is the one **ordered** predicate:
`at_least`/`at_most` apply **only** to it, and although they denote a real numeric
comparison they are still written as named calls, never with `<`/`>`.

`pkg.build.version` — The `version` predicate compares the **compiling compiler's
own** version against the literal — not the target (unlike `arch`/`os`), so it gates
an element on *which compiler is building it* (its use is bootstrap staging: a
declaration that must exist only once a new-enough compiler compiles it). The
literal is a strict **`X.Y.Z[-pre[N]]`**: exactly three dot-separated decimal
components, optionally followed by a **hyphenated** `-pre` and optional digits.
Anything else — a missing or 4th component, a non-digit component, a
**non-hyphenated** `preN`, or an unknown tag (`-rc1`, `beta`) — is a hard error
(`pkg.build.errors`); there is no best-effort parse. (A leading `bnc-` is
defensively tolerated and stripped — `bnc-0.0.11` parses as `0.0.11` — though the
compiler's own version string never carries that prefix.) The comparison
**discards** the
`-pre[N]` suffix, then compares `(major, minor, patch)` **numerically** (`0.0.11` >
`0.0.9`, not lexically). A prerelease therefore compares **equal** to its release:
on a `0.0.11-pre3` compiler, `at_least(version, "0.0.11")` **and** `is(version,
"0.0.11")` are both true — `is` is "exact" only up to the discarded prerelease
suffix. `at_least`/`at_most` apply only to `version` (an ordered matcher on
`arch`/`os` is a hard error), and the literal must be a single string (an
adjacent-concatenated `"0.0" ".11"` is rejected).

`pkg.build.gate` — The annotation gates at three granularities:

- **File-level** — on the **package clause**, dropping the **whole file** from
  the package. It selects which well-formed files contribute on a given target;
  every candidate file is still parsed (the gate runs after parsing, so it cannot
  carry syntax the parser would reject on another target).
- **Declaration-level** — on a top-level declaration, dropping just that
  declaration.
- **Import-level** — on an import, so a dependency is followed only on the
  targets it applies to.

`pkg.build.variants` — Because a non-matching constraint drops its element,
several **same-named** declarations gated to **disjoint** conditions coexist in
one package and exactly one survives for any target — with no duplicate-definition
error. (Overlapping conditions that leave two definitions live for some target is
a duplicate-definition error for that target.)

`pkg.build.errors` _(Constraint)_ — A constraint that evaluates to **false**
cleanly excludes its element; a constraint that **fails to evaluate** — an unknown
unqualified annotation, an unknown predicate or tag, an **unknown predicate
function** (only `is` / `at_least` / `at_most` exist), an **ordered matcher on a
non-`version` key** (`at_least(arch, …)`), a **malformed or adjacent-concatenated
`version` literal** (`pkg.build.version`), a comparison or other disallowed
operator, or a malformed expression — is a **hard error that aborts the build**. A
silent skip is never used: it would drop the element's symbols and surface later as
a confusing "undefined" far from the cause.

> _Note._ The active target (the `arch`/`os` values `is(...)` is tested against)
> is taken from the `pkg/builtins/build` package, which the build tooling
> resolves per host or `--target`; that package also exposes `IntSize`/`PtrSize`
> as compile-time constants. When no build configuration is resolved (e.g. the
> REPL, the bytecode tool, unit tests), gating is **inactive** and every file and
> declaration is kept.

> _Provisional._ The predicate functions are `is` (membership for `arch`/`os`,
> exact for `version`) and the ordered `at_least`/`at_most` (`version` only).
> Further predicates (`triple`, `backend`, `libc`, `ptrsize`, `os.version`, an open
> `tag.*`) are **reserved for future work** — the stable surface is `is(arch|os,
> "tag")` plus the `version` matchers, combined with `&& || !`.

## 16.9 The foreign-function boundary

`pkg.extern` — An **extern** declaration is a `.bni` declaration with no body
(§16.5): a body-less function or an initializer-less `var`. Its implementation is
supplied by the package's `.bn`, or — for a platform primitive — by the
runtime/host. There is no
`extern` keyword and no `#[extern]`/`#[no_mangle]` annotation; externness is
conferred by the body-less `.bni` form.

`pkg.ccall` — Calling a C function is done through the built-in `__c_call` (one
of the internal foreign-function primitives, §15.8): `__c_call("symbol", RetType,
args…)` calls the C symbol named by the string literal — emitted **verbatim**,
with **no name mangling** (the only such path; every other symbol is mangled from
its package path) — with the C signature given as explicit Binate types (a `...`
marker separates fixed from variadic arguments). Each **argument** may be **any
type with a defined C-ABI layout**: a scalar, a pointer, a struct **by value**, a
raw slice `*[]T` (its `{T*, ptrdiff_t}` header), a managed-slice `@[]T`, a managed
pointer `@T`, or an interface / function value — passed per the platform C ABI
(§7.13). The only type that **cannot** be passed is one with no layout: an
**opaque-by-value** type (§7.8; a pointer to an opaque type is fine). A **managed
argument** carries the **same parameter-ownership contract as a Binate call**
(§18.5 `mem.param`) — a borrow for `@T` / `@[]T` / `@func`, an owning delivery for
an interface value, a copy-with-`RefInc` for a by-value struct with managed fields
— with the C side performing any required `RefInc` / `RefDec` **by hand** (via the
runtime's reference-count entry points). The **return type** may be **any type
with a defined C-ABI layout** — the same widened set the arguments admit — or the
**string literal `"void"`** (written in the return-type position) for a
void-returning C function. An aggregate is returned per the platform C ABI: a
hidden **sret** buffer above the size cutoff (§7.13.11), **register-coerced** below
it (matching Binate's own aggregate-return convention, which is pinned to the C
cutoff). The only type that **cannot** be returned is an **opaque-by-value** type.
One exception: on **arm32 hard-float**, a homogeneous-float *aggregate* return
(a struct/array of 1–4 same-type floats) is rejected — a hard-float C callee
returns it in VFP registers (S0…/D0…), which Binate's internal arm32 return
convention does not yet match; return such a value through a pointer out-parameter
there (a bare `float`/`double` scalar return is fine — it rides S0/D0 correctly).
`__c_call` is **compiled-mode only**; the bytecode VM does not perform FFI.

`pkg.cglobal` — Reading or writing a **C global variable** is done through the
built-in `__c_global` (another internal foreign-function primitive, §15.8):
`__c_global("symbol", T)` yields the **address** of the C global named by the
string literal — emitted **verbatim, with no name mangling** (like `__c_call`) —
as a **raw pointer `*T`**, where `T` is the variable's C type. Read the global with
`*p` and write it with `*p = …`. `T` must have a **defined ABI layout** — any such
type maps to a C type the C side can declare, exactly the widened
C-representability `__c_call` admits for its arguments: a scalar, a pointer, a
struct or array by value, a raw or managed slice, an interface or function value.
The only rejection is an **opaque-by-value** type (its layout is unavailable here).
Honoring the ABI is the **C side's responsibility** — including the reference-count
discipline for a managed-typed global (e.g. an immortal managed pointer with a
valid header) — exactly as for a `__c_call` argument. The result is **always raw**
(`*T`, never `@T`) — the recovered pointer itself borrows C-side storage and is
never reference-counted. `__c_global` is **compiled-mode only** (the bytecode VM performs no FFI).
For example, POSIX `environ` has C type `char **` (Binate `**char`), so
`__c_global("environ", **char)` is a `***char` and `*` of it is the current
`**char`.

> _Note (implementation status)._ `__c_global` — the variable counterpart to
> `__c_call`, filling the gap the C-**function** escape hatch left for C
> **globals** — is **implemented in compiled mode** (2026-07-06): the default
> (LLVM) compiler backend lowers it, and the native backends lower it as well
> (GOT-indirect address loads on the PIE targets; an absolute relocation pair on
> the native arm32 non-PIE links). As specified above it remains **compiled-mode
> only** — the bytecode VM never executes it. (It is unrelated to
> `decl.var.extern` (§9.2), the Binate `.bni`/`.bn` interface/implementation
> split, which is not a C symbol.)

> _Note._ The recovered `*T` **borrows** foreign storage: the C global's lifetime is
> the C side's concern, and a raw pointer read through it — e.g. an `environ` entry
> that `setenv`/`putenv` may reallocate — can dangle. Copy out before mutating the
> environment; this is the ordinary raw-borrow discipline (§18.7 `mem.raw-uaf`).

### Exporting Binate functions to C (`#[c_export]`, `__c_entry`)

> _Status._ `pkg.cexport`, `pkg.cexport.eligible`, and `pkg.cexport.signature` are
> **implemented** (together with `bnc --library` and the `bn_init`/`bn_entry` glue of
> §17.3.2). `pkg.centry` and its sub-rules are **implemented** in compiled modes
> (the VM performs no FFI, per the rules themselves).
> `pkg.link-placement` remains **Draft / pending**, and its
> naming (`section`, `link_at`) is provisional. This subsection is the *outbound*
> counterpart to `__c_call`/`__c_global`: those call *into* C; these make Binate
> functions callable *from* C (and let the program's entry/startup glue be written in
> Binate — see §17).

`pkg.cexport.semantics` — A Binate function `f` made visible to C — under a
`#[c_export]` **name**, or through a pointer obtained with **`__c_entry`** (below) — is
callable from C with the C signature that `f`'s Binate signature maps to
(`pkg.cexport.signature`), and such a call **behaves as a call to `f`**. The C caller
assumes the **caller-side obligations of the language's call contract** — argument and
result ownership per §18.5 `mem.param` (e.g. an `@Iface` argument's caller-delivered
reference) — and the call must occur on the program's **single Binate thread of
execution** (§14.15; reference counting is non-atomic, §18): invocation from another
thread, or from an asynchronous signal context interrupting Binate code, is
**undefined** (Ch.21). **How** the implementation makes `f` callable from C is
deliberately **not specified**.

`pkg.cexport` — A `#[c_export("name")]` annotation on a **top-level function** declaration emits an
**additional, unmangled** C symbol `name` through which C code calls that function
(`pkg.cexport.semantics`); the function's mangled Binate
symbol is **unchanged** (Binate callers are unaffected, and multiple `#[c_export]` entries/arguments
produce multiple C names). The C symbol is emitted **verbatim, with no `bn_` mangling** — the same
verbatim-symbol path as `__c_call`/`__c_global`. `c_export` is an **unqualified, compiler-recognized**
annotation (§16.7 `pkg.annotation.namespace`), joining `build`.

`pkg.cexport.eligible` _(Constraint)_ — Only a **top-level function** may be `#[c_export]`'d;
the annotation on any other declaration (or on a method) is a compile error. Package visibility
is **not** required: a package-private function may be exported — a package wrapping a C library
legitimately hands that library a **callback** that is a private implementation detail, not part
of its Binate `.bni` surface.

`pkg.cexport.signature` — An exported function's signature must be **C-ABI-replicable**: because
Binate already uses the platform C ABI (§7.13), every parameter and result type maps to a C type the
C side can declare — a scalar → the matching C scalar; `*T` / `@T` → a pointer (a `@` form
additionally carries the refcount-borrow discipline of the Note below); a raw slice `*[]T` → a
2-word `{T* data; ptrdiff_t len}` (the slice `len` is a **signed** target-width int, §7.13.6 — not
C's unsigned `size_t`); a managed-slice `@[]T` → its 4-word `{data, len, backing, backingLen}`
(whose first two words match the raw-slice head, §7.13.6 `type.layout.slice-managed`); an interface
value → a 2-word `{data, vtable}`; a **function value**
→ a 2-word `{vtable, data}`, the **reverse** field order of an interface value
(§7.13.9 `type.layout.func-value`), which a C typedef must match; a struct by-value or by-reference
per the ≤16-byte cutoff (§7.13.11 `type.layout.byval-cutoff`); a multi-return as a struct
with the result fields, returned per the platform C ABI (by value or `sret`
as C dictates for that struct). Unlike `__c_call`/`__c_global` above (restricted to a scalar or
pointer), the *export* direction rejects **nothing** at the ABI level.

> _Note (managed-value discipline, not an ABI gate)._ A managed value handed to C follows the
> ordinary parameter-ownership contract (§18.5 `mem.param`): a `@T`/`@[]T`/`@func` argument is a
> **borrow** for the call (the callee acquires on entry), while an `@Iface` argument requires the
> **caller to deliver one reference**, which the callee releases — a C caller must supply it. A C caller
> that *retains* it beyond the call must balance the reference count via the runtime `RefInc`/`RefDec`
> entry points (whether/how those become C-visible is open; §20.2 `pkg/rt` review). Treating a managed
> value as an opaque struct/pointer is fine at the ABI level; the refcount contract is the caller's
> responsibility, not an export restriction. (A function-value **parameter** is likewise *passable*
> but awkward to *call* from C — it needs the trampoline: "hard to use," not "can't export.")

`pkg.centry` — `__c_entry(f)` yields a pointer through which **C code calls the declared
function `f`** (`pkg.cexport.semantics`), typed as the opaque raw pointer **`*uint8`**
(§7.8 `type.ptr.opaque-byte`) and suitable for passing to C (typically as a `__c_call`
argument) wherever C expects a function pointer of the corresponding C signature. The
result designates **code, not managed data**: it borrows no managed value
(§18.7 `mem.raw-uaf` is inapplicable), is never freed, and remains valid for
the life of the program. `__c_entry` is **compiled-mode only**, like `__c_call`/`__c_global` (the
bytecode VM performs no FFI).

`pkg.centry.eligible` _(Constraint)_ — The operand must be a **reference to a declared,
non-generic, top-level function** — a local identifier or a package-qualified selector;
public or, within the declaring package, package-private (`pkg.cexport.eligible`). A
method, a function *value*, a function literal, or a generic function is rejected — a C
function pointer carries no context slot, so a capturing value cannot become one (pass
context through the C API's `void* user_data` parameter, as C code does). `f`'s
signature must satisfy `pkg.cexport.signature`.

`pkg.centry.identity` — Every evaluation of `__c_entry(f)` for the same `f` in a
program yields the **same pointer value**, so C-side registration and deregistration by
pointer work. Whether it equals the address of a `#[c_export]` symbol for `f` is
**unspecified** — the guarantee is behavioral (`pkg.cexport.semantics`), not
positional.

> _Note (status)._ Ratified 2026-09-02 and since **implemented** (compiled
> modes). Ratified decisions: the name `__c_entry`; generic instantiations rejected
> (may be relaxed later if a use case appears); the signature rule shared with
> `#[c_export]`; the `*uint8` result (a dedicated C-function-pointer type could be
> layered on later without a breaking change).

`pkg.link-placement` — A **linker-placement** annotation on a top-level function directs the
backend/linker to place the emitted symbol in a named output section (`#[section(".init")]`) or, where
a target supports it, at an absolute load address (`#[link_at(addr)]`) — for a freestanding entry
point (§17) that a reset vector / linker script must find.

> _Status (`pkg.link-placement`)._ **Draft, semantics not fully pinned:** the exact spelling
> (`section` vs `link_at`), how the annotation reaches the backend/linker, and the division of labor
> with a baremetal linker script (which usually owns addresses) are open. Registered here so the
> *name* is a compiler-recognized unqualified annotation (§16.7); the *rule* firms up once those are
> decided.

> _Note._ Binate targets **C-free** systems: C is used only as the practical
> bridge to existing OS interfaces (system calls, allocation), not as an
> architectural dependency, and a pure-Binate system — OS interaction via direct
> syscalls or platform assembly — is a design goal (see Ch.1 and Ch.19 once
> authored). The C runtime is intended to shrink over time, with `__c_call`/extern
> as the FFI escape.
