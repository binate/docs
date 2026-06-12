# 9. Declarations and Scope

> **Status:** normative · **Maturity:** Stable  
> **Rule-ID prefix:** `decl`

A **declaration** binds a name to an entity — a constant, variable, type,
function, method, interface, or package. This chapter covers constant (§9.1),
variable (§9.2), and short-variable (§9.3) declarations, the `readonly`
modifier on a declaration (§9.4), lexical scope and shadowing (§9.5), the scope
levels and what may be declared at package scope (§9.6), statement scope and
temporary lifetime (§9.7), and declaration and initialization order (§9.8).
Type declarations are covered in §7.3–§7.4 and §7.12; functions, methods, and
`impl` in Ch.10–Ch.11; imports and package structure in Ch.16.

## 9.1 Constant declarations

`decl.const` — A `const` declaration binds a name to a **compile-time constant
value**. A constant has **no storage** and **no address** (`&` of a constant is
an error; §7.11), and its value is computed at compile time (Ch.6).

```
ConstDecl = "const" ConstSpec
          | "const" "(" { ConstSpec ";" } ")" ;   (* grouped — enables iota *)
ConstSpec = identifier [ Type ] "=" Expression
          | identifier ;   (* bare member: repeats the previous spec's type+expr, iota incremented *)
```

`decl.const.scalar-only` _(Constraint)_ — A constant's type shall be a **scalar**:
`bool`, `char`, an integer type, or a floating-point type (or a named-distinct
type over one of these). A non-scalar constant is rejected. Immutable *storage*
of a non-scalar value is expressed with a `readonly` variable instead (§9.4).

`decl.const.iota` — Within a grouped `const ( … )` block, **`iota`** is the
zero-based index of the current `ConstSpec`, starting at 0 and incrementing by
one per spec. It is the basis of the enumeration idiom (Ch.12). `iota` is
recognized **only** inside a grouped const block; referencing it anywhere else
(including a single non-grouped `const X = iota`) is an `undefined: iota` error.
It is not a universe-scope binding.

## 9.2 Variable declarations

`decl.var` — A `var` declaration binds a name to **storage** of a given type. A
variable has an address: `&x` yields `*T` (or `*readonly T` for a `readonly`
variable; §9.4).

```
VarDecl  = "var" VarSpec
         | "var" "(" { VarSpec ";" } ")" ;   (* grouped *)
VarSpec  = identifier Type [ "=" Expression ]
         | identifier "=" Expression ;
```

`decl.var.zero-init` — A variable declared without an initializer is
**zero-initialized**: numeric types to 0, `bool` to `false`, pointers and
function values to `nil`, slices to the empty (no-backing) value, and aggregates
field/element-wise. With an initializer `= e`, `e` shall be assignable to the
variable's type (Ch.8); the type may be omitted when it is inferred from `e`.

`decl.var.extern` — In a package interface file (`.bni`), a `var X T`
declaration with **no initializer** declares an exported variable whose storage
and initial value are provided by the package's implementation (`.bn`); it is a
declaration, not a definition (Ch.16).

`decl.var.redeclare` _(Constraint)_ — Declaring with `var` a name already
declared in the **same** block scope is an error ("redeclared in this scope").
(A declaration in an inner block may instead shadow an outer one; §9.5.) At
**package** scope, two top-level declarations with the same name — of any kind —
are likewise an error.

## 9.3 Short variable declarations

`decl.shortvar` — Inside a function, `:=` declares one or more variables with
types inferred from the right-hand side:

```
ShortVarDecl = IdentifierList ":=" ExpressionList ;
```

The left-hand side is a list of identifiers. A multi-valued right-hand side
(a single call returning several values) distributes positionally to the
left-hand names. A blank identifier `_` on the left is skipped — the
corresponding right-hand value is still evaluated, but no name is bound. Each
non-blank name is bound in the current scope with the right-hand value's
(default; Ch.6) type.

`decl.shortvar.no-new-name-rule` — Unlike Go, `:=` does **not** require that at
least one name on the left be new, and re-using a name already bound in the same
scope rebinds it rather than being an error. (The redeclaration error of
`decl.var.redeclare` applies only to the `var` form.)

> _Note (grammar disambiguation)._ A statement beginning with an expression list
> is parsed as an expression list first; the `:=` token then reinterprets the
> left-hand expressions as declared names (disambiguation rule D1, Annex A).

## 9.4 The `readonly` modifier on declarations

`decl.readonly.var` — A variable may be declared `var x readonly T = …`: it has
storage and an address (`&x` → `*readonly T`) but the value at that location is
**not writable through that variable** — `x` cannot be reassigned or mutated
through `x`. This is how immutable *storage* of any type (including non-scalars,
which `const` cannot express) is written. `readonly` here is the type modifier
(§7.11), not the `const` declaration.

`decl.readonly.param` — The **outermost** `readonly` on a function **parameter**
type is local discipline only: it documents that the parameter is not reassigned
in the body and is **not** part of the function's signature (it is ignored for
signature matching and function-value assignability; §7.11). Element-level
`readonly` inside a parameter type *is* significant.

## 9.5 Blocks and lexical scope

`decl.scope.block` — A **block** is a (possibly empty) sequence of declarations
and statements in braces; function bodies and the bodies of `if`, `for`, and
`switch` are blocks (Ch.14). The scope of a name declared in a block extends
from the declaration to the end of the innermost enclosing block.

`decl.scope.shadow` — A declaration in an inner block may **shadow** a name from
an enclosing scope (including a predeclared universe name); within the inner
block the inner name is the one in scope. Shadowing is permitted and is **not
currently diagnosed**.

> _Open (notes vs. implementation)._ The design intent is that shadowing is
> permitted but the compiler emits a **suppressible warning by default**
> (`claude-notes.md`, scoping). The current toolchain does not yet diagnose
> shadowing; this rule describes the implemented behavior.

## 9.6 Scope levels and package-scope declarations

`decl.scope.levels` — There are these scope levels, innermost last:

- **universe** — the predeclared scalar **type** names (Ch.5), the predeclared
  interface `any` (Ch.7), and the predeclared functions `print`, `println`, and
  `panic` — all of which may be shadowed by an inner declaration. (The constant
  keywords `true`/`false`/`nil` and the builtin-operation keywords such as
  `make`/`len` are reserved, not shadowable; and `iota` is recognized only inside
  a grouped const block, not a universe binding; §9.1.)
- **package** — the names declared at the top level of a package, visible
  throughout the package (and, if in the `.bni`, exported; Ch.16).
- **block** — names declared inside a function body or a nested block (§9.5).

`decl.scope.package-decls` — At **package scope** the permitted declarations are:
type declarations (§7.3–§7.4, §7.12), function and method declarations and `impl`
declarations (Ch.10–Ch.11), interface declarations (Ch.11), `const` and `var`
declarations (§9.1–§9.2), and (at file scope) `import` declarations (Ch.16).

`decl.type.package-only` _(Constraint)_ — `type` declarations are package-level
only; a function-local `type` declaration is a parse error (§7.3).

## 9.7 Statement scope and temporary lifetime

`decl.scope.statement` — Each statement establishes an implicit innermost scope
for the **temporaries** produced while evaluating it. A temporary managed value
created during a statement lives until the end of that statement, at which point
it is released (its destructor runs; Ch.18). This statement boundary is the unit
of temporary lifetime.

> _Note._ The full reference-counting semantics of temporaries — including that
> a raw borrow of a temporary's backing must not outlive the statement (a
> use-after-free is programmer error, not suppressed) — are specified in Ch.18
> (`mem.temporary`).

## 9.8 Declaration and initialization order

`decl.order.forward` — Within a package, declarations may appear in any order; a
declaration may refer to a name declared later in the package. Forward
references resolve through the retained/deferred-validation model rather than
requiring prototypes (Ch.17). A non-interactive program is fully validated
before execution begins.

`decl.order.init` — Packages are initialized in **dependency order** (a package's
imports are initialized before it; the dependency graph is acyclic). There is
**no `init()` function**: a package has no implicit initializer hook beyond the
initialization of its package-level variables. Program startup and the `main`
entry point are specified in Ch.17.
