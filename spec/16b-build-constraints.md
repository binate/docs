# 16.7–16.9 Annotations, build constraints, and the FFI boundary

> **Status:** mixed · **Maturity:** the annotation/build-constraint surface is an `arch`/`os` MVP (most predicates deferred); `__c_call` is compiled-mode only  
> **Rule-ID prefix:** `pkg`

This continues [Ch.16 Packages and Program Structure](16-packages-and-program-structure.md)
with the annotation system (§16.7), build constraints (§16.8), and the
foreign-function boundary (§16.9).

## 16.7 The annotation system

`pkg.annotation` —

```
Annotation      = "#" "[" AnnotationEntry { "," AnnotationEntry } "]" ;
AnnotationEntry = AnnotationName [ "(" Expression { "," Expression } ")" ] ;
AnnotationName  = identifier { "." identifier } ;
```

An **annotation block** `#[ … ]` attaches metadata to the element it
**immediately precedes**. In the current implementation an annotation block may
lead the **package clause**, an **import**, or a **top-level declaration**. A
block holds one or more comma-separated **entries**; each entry is a (possibly
dotted) name with an optional parenthesized list of expression arguments.

`pkg.annotation.namespace` — An annotation **name** is a dotted identifier, and
its first segment determines who must understand it:

- An **unqualified** name (no dot) is language-standard and **must be recognized**
  by the compiler — an unknown unqualified name is a **compile error** (this
  catches typos). The only unqualified annotation currently defined is `build`
  (§16.8).
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

- **File-level** — on the **package clause**, gating the **whole file** before it
  is parsed (so it can hide target-specific *syntax*).
- **Declaration-level** — on a top-level declaration, dropping just that
  declaration (after parsing — it can hide *semantics*, not syntax).
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
of the internal built-ins, §15.8): `__c_call("symbol", RetType, args…)` calls the
C symbol named by the
string literal — emitted **verbatim**, with **no name mangling** (the only such
path; every other symbol is mangled from its package path) — with the C signature
given as explicit Binate types (a `...` marker separates fixed from variadic
arguments). Each argument must be a C-ABI-passable type (a scalar or pointer;
pass a pointer for slices, structs, and managed values). `__c_call` is
**compiled-mode only**; the bytecode VM does not perform FFI.

> _Note._ Binate targets **C-free** systems: C is used only as the practical
> bridge to existing OS interfaces (system calls, allocation), not as an
> architectural dependency, and a pure-Binate system — OS interaction via direct
> syscalls or platform assembly — is a design goal (see Ch.1 and Ch.19 once
> authored). The C runtime is intended to shrink over time, with `__c_call`/extern
> as the FFI escape.
