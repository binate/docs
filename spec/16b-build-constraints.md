# 16.7–16.9 Annotations, build constraints, and the FFI boundary

> **Status:** mixed · **Maturity:** the annotation/build-constraint surface is an `arch`/`os` MVP (most predicates deferred); `__c_call` is compiled-mode only  
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
  (§16.8); the FFI-export annotations `c_export` and the linker-placement
  `section` / `link_at` (§16.9) are unqualified/compiler-recognized too, but are
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
BuildExpr   = "is" "(" predicate "," string_literal ")"
            | "!" BuildExpr
            | BuildExpr "&&" BuildExpr
            | BuildExpr "||" BuildExpr
            | "(" BuildExpr ")" ;
```

An atomic clause is `is(predicate, "tag")` — true when the target's `predicate`
matches `tag`. Clauses combine only with `&&`, `||`, and `!`. (A *comparison*
operator such as `==` is **not** accepted — membership, not equality, because a
target belongs to overlapping descriptor sets.) The two predicates currently
defined are:

- **`arch`** — `"x64"`, `"aarch64"`, `"arm32"` (with the assembler aliases
  `"x86_64"` = `x64`, `"arm64"` = `aarch64`, `"arm"` = `arm32`).
- **`os`** — `"linux"`, `"darwin"`, `"baremetal"` (no aliases yet).

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
cleanly excludes its element; a constraint that **fails to evaluate** — an
unknown unqualified annotation, an unknown predicate or tag, a non-`is` call, a
comparison or other disallowed operator, a malformed expression — is a **hard
error that aborts the build**. A silent skip is never used: it would drop the
element's symbols and surface later as a confusing "undefined" far from the cause.

> _Note._ The active target (the `arch`/`os` values `is(...)` is tested against)
> is taken from the `pkg/builtins/build` package, which the build tooling
> resolves per host or `--target`; that package also exposes `IntSize`/`PtrSize`
> as compile-time constants. When no build configuration is resolved (e.g. the
> REPL, the bytecode tool, unit tests), gating is **inactive** and every file and
> declaration is kept.

> _Provisional._ `is` is the only predicate function and `arch`/`os` are the only
> predicates today. Further predicates (`triple`, `backend`, `libc`, `ptrsize`,
> `version`, `os.version`, an open `tag.*`) and ordered matchers (for numeric
> predicates) are **reserved for future work** — the stable surface is
> `is(arch|os, "tag")` combined with `&& || !`.

## 16.9 The foreign-function boundary

`pkg.extern` — An **extern** declaration is a `.bni` declaration with no body
(§16.5): a body-less function or an initializer-less `var`. Its implementation is
supplied by the package's `.bn`, or — for platform primitives (the `bootstrap`
package's I/O and allocation entry points) — by the runtime/host. There is no
`extern` keyword and no `#[extern]`/`#[no_mangle]` annotation; externness is
conferred by the body-less `.bni` form.

`pkg.ccall` — Calling a C function is done through the built-in `__c_call` (one
of the internal foreign-function primitives, §15.8): `__c_call("symbol", RetType,
args…)` calls the C symbol named by the string literal — emitted **verbatim**,
with **no name mangling** (the only such path; every other symbol is mangled from
its package path) — with the C signature given as explicit Binate types (a `...`
marker separates fixed from variadic arguments). Each argument, and the **return
type**, must be a C-ABI-passable **scalar or pointer** (pass a pointer for
slices, structs, and managed values) — **except** that a **void-returning** C
function is written with the **string literal `"void"`** in the return-type
position (where a Binate type would otherwise go). **Struct returns are not
supported** — pass a pointer to an out-parameter instead. `__c_call` is
**compiled-mode only**; the bytecode VM does not perform FFI.

> _Note (pending feature)._ The `"void"` return form is a **decided** feature
> still **in progress** (2026-06-19): until it lands, the current toolchain
> rejects a void return, and a void C function is called by declaring a
> throwaway scalar return and discarding it.

`pkg.cglobal` — Reading or writing a **C global variable** is done through the
built-in `__c_global` (another internal foreign-function primitive, §15.8):
`__c_global("symbol", T)` yields the **address** of the C global named by the
string literal — emitted **verbatim, with no name mangling** (like `__c_call`) —
as a **raw pointer `*T`**, where `T` is the variable's C type. Read the global with
`*p` and write it with `*p = …`. `T` must be a C-ABI-passable **scalar or pointer**
(the same constraint as `__c_call`'s arguments); the result is **always raw** (`*T`,
never `@T`) — the storage belongs to the C side and carries no reference-count
header. `__c_global` is **compiled-mode only** (the bytecode VM performs no FFI).
For example, POSIX `environ` has C type `char **` (Binate `**char`), so
`__c_global("environ", **char)` is a `***char` and `*` of it is the current
`**char`.

> _Note (implementation status)._ `__c_global` — the variable counterpart to
> `__c_call`, filling the gap the C-**function** escape hatch left for C
> **globals** — is **implemented in compiled mode** (2026-07-06): the default
> (LLVM) compiler backend lowers it, so it works on every hosted compiled target
> that links libc. The direct `--backend native` backends do **not** yet lower it
> (they reject `__c_global` at code-generation rather than mis-compile it);
> native support is forthcoming. As specified above it remains **compiled-mode
> only** — the bytecode VM never executes it. (It is unrelated to
> `decl.var.extern` (§9.2), the Binate `.bni`/`.bn` interface/implementation
> split, which is not a C symbol.)

> _Note._ The recovered `*T` **borrows** foreign storage: the C global's lifetime is
> the C side's concern, and a raw pointer read through it — e.g. an `environ` entry
> that `setenv`/`putenv` may reallocate — can dangle. Copy out before mutating the
> environment; this is the ordinary raw-borrow discipline (§18.7 `mem.raw-uaf`).

### Exporting Binate functions to C (`#[c_export]`)

> _Status (Draft / pending)._ The rules in this subsection (`pkg.cexport`,
> `pkg.cexport.eligible`, `pkg.cexport.signature`, `pkg.link-placement`) are **specified but
> not yet implemented**. They are the *outbound* counterpart to `__c_call`/`__c_global`: those
> call *into* C, `#[c_export]` makes a Binate function callable *from* C (and lets the program's
> entry/startup glue be written in Binate — see §17). Design: `explorations/design-ffi-export.md`.
> Naming (`c_export`, `section`, `link_at`) is provisional.

`pkg.cexport` — A `#[c_export("name")]` annotation on a **top-level function** declaration emits an
**additional, unmangled** C symbol `name` aliasing that function; the function's mangled Binate
symbol is **unchanged** (Binate callers are unaffected, and multiple `#[c_export]` entries/arguments
produce multiple C names). The C symbol is emitted **verbatim, with no `bn_` mangling** — the same
verbatim-symbol path as `__c_call`/`__c_global`. `c_export` is an **unqualified, compiler-recognized**
annotation (§16.7 `pkg.annotation.namespace`), joining `build`.

`pkg.cexport.eligible` _(Constraint)_ — Only a **package-public** function — one declared in the
package's `.bni` (§16.4) — may be `#[c_export]`'d: a two-level gate (package-visible, then C-named).
`#[c_export]` on a package-private declaration, or on a non-function declaration, is a compile error.

`pkg.cexport.signature` — An exported function's signature must be **C-ABI-replicable**: because
Binate already uses the platform C ABI (§7.13), every parameter and result type maps to a C type the
C side can declare — a scalar → the matching C scalar; `*T`/`@T` → a pointer; a raw slice `*[]T` →
a 2-word `{T* data; size_t len}`; a managed-slice `@[]T` → its 4-word
`{data, len, backing, backingLen}` (whose first two words match the raw-slice head, §7.13
`type.layout.slice-managed`); an interface value → a 2-word `{data, vtable}`; a **function value**
→ a 2-word `{vtable, data}`, the **reverse** field order of an interface value
(§7.13.9 `type.layout.func-value`), which a C typedef must match; a struct by-value or by-reference
per the ≤16-byte cutoff (§7.13.11 `type.layout.byval-cutoff`); a multi-return as its packed
anonymous result struct or `sret`. Unlike `__c_call`/`__c_global` above (restricted to a scalar or
pointer), the *export* direction rejects **nothing** at the ABI level.

> _Note (managed-value discipline, not an ABI gate)._ A managed value (`@T`/`@[]T`/`@Iface`) handed
> to C is a **borrow** for the call — the same ownership rule a Binate callee has (§18). A C caller
> that *retains* it beyond the call must balance the reference count via the runtime `RefInc`/`RefDec`
> entry points (whether/how those become C-visible is open; §20.2 `pkg/rt` review). Treating a managed
> value as an opaque struct/pointer is fine at the ABI level; the refcount contract is the caller's
> responsibility, not an export restriction. (A function-value **parameter** is likewise *passable*
> but awkward to *call* from C — it needs the trampoline: "hard to use," not "can't export.")

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
