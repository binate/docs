# 16. Packages and Program Structure

> **Status:** mixed · **Maturity:** Stable core (aliased imports are flagged broken; build constraints §16b are MVP)  
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
the absence of **both** is an error ("package not found").

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
file gate of §16.8; the reference grammar still lacks this slot). The package name
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

> _Open (implementation defect)._ **Aliased imports do not work end-to-end.**
> `import a "pkg/foo"` parses, but a cross-package call through the alias
> (`a.Fn()`) is name-mangled with the **alias** rather than the package path,
> producing an undefined symbol at link time. The feature is latent (no in-tree
> code uses an alias) and the conformance case is expected-fail in every mode
> (`pkg.import.alias`, `claude-todo.md`). Until fixed, import without an alias.

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
  be extern; `const` cannot.)
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
import cycle is a compile error ("import cycle").

`pkg.package-accessor` — Every package additionally has a compiler-synthesized
`_Package()` accessor — present in every package without any `.bni` declaration —
that returns the package's reflection descriptor (Ch.20). (The `main` package and
program entry are Ch.17.)

> _Implementation note._ The `_Package()` accessor is currently emitted only as a
> native function, so the bytecode VM cannot reach it for user/standard-library
> packages (it works for the built-in packages); the reflection descriptor it
> returns is otherwise mode-agnostic (`claude-todo.md`).
