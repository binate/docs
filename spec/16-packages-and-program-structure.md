# 16. Packages and Program Structure

> **Status:** mixed · **Maturity:** Stable core (build constraints §16b are an arch/os MVP)  
> **Rule-ID prefix:** `pkg`

A **package** is the unit of compilation and the unit of namespacing. This
chapter covers source files and the package directory (§16.1), the package clause
(§16.2), imports (§16.3), the exported surface and visibility (§16.4), the `.bni`
interface-file contract (§16.5), and package resolution and identity (§16.6). The
annotation system, build constraints, and the foreign-function boundary are in
[§16.7–§16.9](16b-build-constraints.md). Program initialization, the `main` entry,
and termination are Ch.17.

## 16.1 Source files and the package directory

`pkg.files` — A package is a **directory of `.bn` implementation files**, a
single **`.bni` interface file** that sits beside that directory (same parent,
same base name), or **both**:

```
pkg/
  foo.bni        # the interface file (the package's public surface)
  foo/           # the implementation directory
    a.bn
    b.bn
```

All `.bn` files of a package declare the same package string (§16.2) and are
**merged** (in sorted filename order) into one logical package. A package needs at
least **one** of the two surfaces: a `.bni`-only package (no implementation
directory) and an implementation-only package (no `.bni`) are both valid; only
the absence of **both** is an error (a message of the form `package "<path>"
not found`).

`pkg.files.test` — A file whose name ends in `_test.bn` is **excluded** from its
package unless that package is being built for testing (Ch.20); test files thus
do not contribute to the normal package surface.

## 16.2 The package clause

`pkg.clause` —

```
SourceFile    = [ Annotation ] PackageClause ";" { ImportDecl ";" } { TopLevelDecl ";" } ;
PackageClause = "package" string_literal ;
```

Every source file begins with a package clause (after an optional leading
annotation block, §16.7 — the package-clause annotation slot is the build-constraint
file gate of §16.8; the canonical `binate.ebnf` carries this slot). The package name
is a **string literal** — the
package's **import path** — not an identifier: `package "pkg/binate/parser"`. The
string is the same one used to `import` the package; there is no separate short
package identifier (the qualifier used at a call site comes from the import path,
§16.3). A missing or misplaced package clause is a syntax error.

## 16.3 Import declarations

`pkg.import` —

```
ImportDecl = [ Annotation ] "import" ImportSpec
           | [ Annotation ] "import" "(" { ImportSpec ";" } ")" ;
ImportSpec = [ identifier ] string_literal ;
```

Imports appear after the package clause and before the top-level declarations
(file scope only — there is no block-scoped import). The import path is a string
literal equal to the imported package's package clause. An import may be written
singly or in a parenthesized group, and may carry an optional **alias**
identifier before the path string. An imported member is referenced
**qualified** as `name.Member`, where `name` is the import path's last segment (or
the alias, when given).

## 16.4 The exported surface and visibility

`pkg.export` — A package's **exported surface is its `.bni`**: a symbol is
visible to importers **iff it is declared in the package's `.bni`**. There are no
per-symbol visibility keywords (no `pub`), and — unlike Go — **identifier
capitalization carries no visibility meaning**. A symbol declared only in a `.bn`
is **package-private**: usable within its own package, but a cross-package
reference to it is a compile error ("undefined").

> _Note._ Capitalizing exported names (and lower-casing private ones) is the
> recommended **style**, but it is a convention only — the compiler determines
> visibility solely from `.bni` membership. A package with no `.bni` exports
> nothing through an interface (its surface is taken from the `.bn` directly only
> where that is the package's sole surface).

## 16.5 The `.bni` interface-file contract

`pkg.bni` — The `.bni` declares the package's public API. It is parsed like a
`.bn` with **one** difference (§16.5.1), and each declaration kind has a defined
meaning at the boundary:

- **`type`** — A type fully defined in the `.bni` is the **authoritative**
  definition (it is not redefined in the `.bn`). A body-less `type Foo` is a
  **forward / opaque** declaration (`pkg.bni.opaque`, §7.12): the full definition
  is private to the `.bn`, and importers may hold a `@Foo`/`*Foo` but cannot
  access its fields or take its size.
- **`const`** — A `const` is declared in **exactly one** of the `.bni` (→
  exported) or the `.bn` (→ package-private), **never both**: there is **no
  extern `const`** (a constant has no storage to link — it resolves at each use
  site). A `.bni` `const` carries its full initializer expression, which may
  reference sibling constants of the same package.
- **`var`** — A `.bni` `var X T` (with **no initializer**) is an **extern**
  declaration: the storage lives in the package's `.bn`, which must define `X`
  with an **identical** type (including any `readonly` modifier). (So `var` *can*
  be extern; `const` cannot.) _Unenforced:_ the current compiler does not diagnose
  a stray initializer on a `.bni` `var` — it is silently ignored (a conforming
  implementation should reject it).
- **`func`** — A non-generic function is **signature-only** in the `.bni` (its
  body lives in the `.bn`). A **generic** function carries its full **source-text
  body** in the `.bni` (§16.5.1).
- **`interface`** — declared in the `.bni` as part of the surface. An **`impl`**
  may also appear in a `.bni`, but a type's `impl` is commonly supplied by a `.bn`
  (often in a *different* package from the interface — the impl-split pattern,
  Ch.11).

`pkg.bni.consistency` _(Constraint)_ — The `.bn` definition must **match** its
`.bni` declaration. A return-type or extern-var-type mismatch between the two is a
compile error (an importer reads the type from the `.bni`, so a divergent `.bn`
would be misread).

### 16.5.1 Generic bodies travel in the `.bni`

`pkg.bni.generic` — The single parse-time difference between a `.bni` and a `.bn`
is that a **generic** declaration carries its body in the `.bni` while a
non-generic function does not. A consumer **monomorphizes** an imported generic
from that source-text body (Ch.12) — the "template in the header" model. This is
the **one exception to binary-only distribution**: a package can otherwise ship
as interface + compiled library with no source, but a package exporting a generic
must ship that generic's body in its `.bni`.

### 16.5.2 Whole-package re-export (`expose`)

`pkg.expose` — An `expose` declaration in a package's `.bni` re-exports another
package's **entire exported surface** as part of this package's surface:

```
ExposeDecl = "expose" string_literal ;
```

Written `expose "P"` in package **A**'s `.bni`, it makes every member of package
**P**'s exported surface (§16.4) part of A's surface, so a consumer that
`import`s A may reference P's member `X` as `A.X`. `expose` is a **contextual
keyword**: it is recognized only as the lead-in of a top-level declaration and
is an ordinary identifier everywhere else, so it reserves nothing language-wide
(§5). A **forwarder** — a `.bni` with one or more `expose` declarations and no
implementation directory — is a valid `.bni`-only package (§16.1); a package may
equally combine its own declarations with `expose`s to present several packages
as one surface (an aggregator). The two motivating uses are **refactor/rename**
(promote `pkg/stdx/foo` to `pkg/std/foo` and leave `pkg/stdx/foo.bni` as
`expose "pkg/std/foo"`, so existing `import "pkg/stdx/foo"` consumers keep
compiling against the same entities and migrate at leisure) and **internal
structuring**.

`pkg.expose.bni-only` _(Constraint)_ — `expose` is permitted **only in a
`.bni`** — it defines part of the package's public surface, which lives in the
`.bni` (§16.4). An `expose` in a `.bn` is a compile error (a message of the form
`expose is permitted only in .bni interface files`).

`pkg.expose.identity` — Re-export is by **identity, never a copy**: the member
reached as `A.X` **is** P's original entity `X` — the same *type identity* for a
type, the same *storage* for a `var`, the same *symbol* for a `func`, the same
*value* for a `const`. Consequently code written against `A.X` and code written
against `P.X` name one entity and interoperate. (An exposed **interface** is
re-exported through the interface-identity form; a type's `impl`s dispatch
through the exposed type without re-export, since impl and type identity already
key on the resolved target package, Ch.11.)

`pkg.expose.surface` — `expose` extends **only A's exported surface**; it does
**not** bring P's names into A's own scope. It is **not** an import, and Binate
has no dot-import — references are always qualified (§16.3). If A's
implementation needs to *use* P, it writes an ordinary `import "P"` separately.
An exposed package's names therefore can never collide with A's package-private
(`.bn`-only) names.

`pkg.expose.flat` — Re-exported members appear **flat**: a consumer sees `A.X`,
not `A.P.X` (a package is neither a value nor a member of another package).

`pkg.expose.transitive` — `expose` is **transitive**: if P exposes Q, then a
package A that exposes P also re-exports Q's members. Injection proceeds in
dependency order, so a chain `A → P → Q` surfaces Q's members through A.

`pkg.expose.conflict` _(Constraint)_ — A name reachable through **two** `expose`
declarations, or through an `expose` **and** A's own exported declaration of the
same name, is a **compile error**; the diagnostic names both origins. (Because
`expose` is surface-only, A's private names are never involved in a collision.)

`pkg.expose.dep` — `expose "P"` makes A **depend on** P: P is loaded, checked,
and initialized before A, exactly as an `import` edge would (Ch.17). `expose`
and `import` edges share one import graph, so a cycle involving an `expose` is
rejected by the acyclicity constraint (§16.6, `pkg.acyclic`). A **pure forwarder
emits no code, no storage, and no initializer**: importing A only adds the
dependency edge to P, and every `A.X` resolves to P's entity, so the forwarder
has no runtime footprint of its own.

`pkg.expose.reflect` — An exposed member is reflected under its **home
package**: `A.X` is described by P's reflection descriptor entry for `X`
(Ch.20), not by a copy synthesized in A — a direct consequence of
`pkg.expose.identity` (a pure forwarder emits no descriptor entries for the
members it exposes).

## 16.6 Package resolution and identity

`pkg.resolve` — An import path is resolved to files on disk by searching a list
of **roots**. The interface (`.bni`) and the implementation directory are
resolved on **two independent search paths** (so a package's interface and
implementation may come from different roots), each **first-match-wins**. The
**project root** is highest priority, so a project-local package **shadows** an
external one of the same path.

`pkg.resolve.public` — By convention, an import path beginning with **`pkg/`**
names a **searchable ("public")** package found via the full search path; a
non-`pkg/` path names a package that is **local** to the project. This is a
layout convention realized by where the search roots point, not a rule the loader
hard-codes.

`pkg.identity` — A package's identity — and therefore the identity of the types
it declares and the symbols it links — is its **full import path**, not the
path's last segment. Two packages whose paths share a last segment (e.g.
`pkg/alpha/widget` and `pkg/beta/widget`) are **distinct**, and a type named
`Box` in one package is a different type from a `Box` in another
(`main.Box ≠ pkg/dep.Box`); a cross-package assignment between same-named,
different-package types is rejected (§7).

`pkg.acyclic` _(Constraint)_ — The package **import graph must be acyclic**. An
import cycle is a compile error (a message of the form `import cycle: <path>`).

`pkg.package-accessor` — Every package additionally has a compiler-synthesized
`__Package()` accessor — present in every package without any `.bni` declaration —
that returns the package's reflection descriptor (Ch.20). (The `main` package and
program entry are Ch.17.)

> _Implementation note._ The `__Package()` accessor is currently emitted only as a
> native function, so the bytecode VM cannot reach it for user/standard-library
> packages (it works for the built-in packages); the reflection descriptor it
> returns is otherwise mode-agnostic (`claude-todo.md`).
