# 14. Statements

> **Status:** mixed · **Maturity:** language rules Stable; two MAJOR implementation defects flagged (parallel assignment §14.4, inc/dec on a non-identifier lvalue §14.5)  
> **Rule-ID prefix:** `stmt`

**Statements** specify the executable behavior of a function body. This chapter
covers the statement taxonomy and blocks (§14.1), the empty statement (§14.2),
expression statements (§14.3), assignment (§14.4), increment/decrement (§14.5),
short variable declarations (§14.6), and local declarations (§14.7). The
control-flow statements — `if`, `for`, `switch`, `return`, `break`, `continue`,
and the terminating-statement analysis — are in
[§14.8–§14.14](14b-control-flow.md).

Statements appear **only inside function bodies**. A source file is purely
declarative (`pkg.decl`, Ch.16); there are no top-level statements. (The REPL's
immediate mode evaluates statements interactively, Ch.19, but that is not part of
a compiled program's grammar.) Statements are separated by semicolons, almost all
of which are supplied by **automatic semicolon insertion** (§5.13), so source
rarely contains an explicit `;`.

> _Temporary lifetime._ Each statement establishes an implicit innermost scope
> for the managed temporaries produced while evaluating it; they are released at
> the end of the statement (`decl.scope.statement`, §9.7; the full
> reference-counting rules are `mem.temporary`, §18).

## 14.1 Statements and blocks

`stmt.kinds` — The statement forms are:

```
Statement     = BlockDecl | SimpleStmt | ReturnStmt | BreakStmt
              | ContinueStmt | Block | IfStmt | ForStmt | SwitchStmt ;
BlockDecl     = VarDecl | ConstDecl ;                      (* §14.7 *)
SimpleStmt    = EmptyStmt | ExpressionStmt | Assignment
              | ShortVarDecl | IncDecStmt ;
```

`stmt.simple` — A **simple statement** is one of the five `SimpleStmt` forms. The
simple statements are exactly the forms permitted in a `for` clause's init and
post slots (§14.9); the other statement forms (blocks, `if`/`for`/`switch`,
`return`, `break`, `continue`, and `var`/`const` declarations) are **not** simple
statements and cannot appear there.

`stmt.block` — A **block** is a brace-delimited statement sequence:

```
Block = "{" { Statement ";" } "}" ;
```

A block introduces a **new lexical scope** (`decl.scope.block`, §9.5); names
declared in it are visible from their declaration to the end of the block, and
may shadow names from enclosing scopes. The trailing `;` before `}` is optional
(and normally ASI-supplied). On exit, a block releases the managed locals it
declared, in the reference-counting model of §18.

`stmt.no-local-type` _(Constraint)_ — A `type` declaration is package-level only;
writing one inside a function body is a parse error (§7.3, §9.6). Hence
`BlockDecl` admits only `var` and `const`.

## 14.2 Empty statement

`stmt.empty` —

```
EmptyStmt = (* nothing *) ;
```

An empty statement does nothing. It arises chiefly from an omitted `for`-clause
slot (`for ; cond ; { … }`) rather than being written explicitly.

## 14.3 Expression statements

`stmt.expr` —

```
ExpressionStmt = Expression ;
```

An expression used as a statement is evaluated for its **side effects** and its
value, if any, is discarded. **Any** expression is permitted as a statement —
not only calls — and a value-producing expression statement is **not**
diagnosed.

> _Open (notes vs. implementation)._ A pure, effect-free expression statement
> (for example a bare `x + 1`) is silently accepted; the checker has no
> "evaluated but not used" diagnostic (unlike Go). Whether such a statement
> should be a warning or error is unspecified (`stmt.expr.unused`).

## 14.4 Assignment statements

```
Assignment   = ExpressionList "=" ExpressionList
             | Expression compound_assign_op Expression ;
compound_assign_op = "+=" | "-=" | "*=" | "/=" | "%="
                   | "&=" | "|=" | "^=" | "<<=" | ">>=" ;
```

Assignment is a **statement, not an expression** — there is no `x = y = 5` and no
assignment in expression position.

`stmt.assign.simple` — In a simple assignment `L = R`, each left-hand operand is
an assignable location (an addressable variable, a slice or array element `s[i]`,
a struct field `s.f`, or a pointer dereference `*p`), and the right-hand value
must be **assignable** to it (Ch.8). A **constant** target — an unqualified
`const` name, a package-qualified `pkg.C`, or a location of `readonly` (const)
type — is rejected (`stmt.assign.const-target`; "cannot assign to const …").

`stmt.assign.compound` — A compound assignment `L op= R` requires **exactly one**
operand on each side. It is defined as `L = L op R` evaluated once: the operand
typing is exactly that of the binary operator `op` — `%` (§13.3), the bitwise
operators, and the shifts (§13.5) require integer operands, and the shift forms
apply the guarded-shift semantics of §13.5. The same const-target rejection
applies (`stmt.assign.compound.const`).

`stmt.assign.multi` — A **multiple assignment** distributes a single
multi-valued right-hand side across several targets: when the right-hand side is
one call returning N values (a free function, a `*func`/`@func` value, or an
interface method), `t1, …, tN = call(…)` assigns each result to the
corresponding target (`x, err = f()`). Each target is an arbitrary assignable
location (`x, arr[0] = f()`; `h.field, n = g()`), and each result must be
assignable to its target. The result count must equal the target count, else
"assignment count mismatch".

`stmt.assign.blank` — A **blank** target `_` discards its value: the right-hand
side is still evaluated (for side effects and, for a multi-valued call, to
produce all results), but nothing is bound, and a discarded **managed** value is
released at end of statement (no leak).

`stmt.assign.store` — A store follows the **acquire-before-release** discipline:
the new value is retained before the prior occupant is released, which makes
self-aliasing stores such as `x = x` and `s[i] = s[i]` safe (the copy-then-destroy
rule of §18).

> _Open._ The right-hand side is evaluated **before** the left-hand designator's
> address is computed — the reverse of the common "evaluate the lvalue, then the
> value" intuition. This is observable only when the designator and the value
> share a side effect; whether this order is normatively guaranteed is not yet
> pinned (`stmt.assign.eval-order`).

> _Open (MAJOR — implementation defect)._ **Parallel assignment with more than
> one expression on each side is silently miscompiled.** The grammar permits
> `ExpressionList "=" ExpressionList`, and the checker accepts a matched-arity
> form such as `a, b = 1, 2` or the swap idiom `a, b = b, a` (it checks each pair
> assignable). But code generation lowers only the single-target and
> single-call-destructure shapes; the matched-arity multi-expression case emits
> **no stores at all**, so `a, b = 1, 2` and `a, b = b, a` compile to a **no-op**
> with no diagnostic. Idiomatic Binate forms tuples via multiple **return**
> (`stmt.assign.multi`, one call) and is unaffected. The resolution is an open
> language decision: **(A)** support parallel assignment (evaluate all
> right-hand expressions, then store all targets, so the swap works), or **(B)**
> reject a multi-expression right-hand side at the checker (multiple assignment
> requires a single multi-valued call). Either way the present accept-then-drop
> is a defect (`stmt.assign.parallel`, MAJOR, `claude-todo.md`).

## 14.5 Increment and decrement

`stmt.incdec` —

```
IncDecStmt = Expression ( "++" | "--" ) ;
```

`x++` and `x--` add or subtract one in place. They are **postfix and
statement-only** (there is no prefix `++x` and no use in expression position; cf.
§13). The operand must be of **integer** type, and a `const` operand is rejected
(a constant has no storage to mutate).

> _Open (MAJOR — implementation defect)._ `++`/`--` on a **non-identifier**
> lvalue — `a[i]++`, `p.field++`, `(*p)++` — type-checks clean but generates
> **no code** (a silent no-op): the checker accepts any integer lvalue, while
> code generation lowers only the identifier case. Common idioms such as
> `counts[i]++` and `node.count++` therefore do nothing, with no diagnostic. The
> fix is to lower the index/field/dereference lvalue forms (as assignment already
> does); these are legitimate lvalue mutations, not forms to forbid
> (`stmt.incdec.lvalue`, MAJOR, `claude-todo.md`).

## 14.6 Short variable declarations

`stmt.shortvar` —

```
ShortVarDecl = IdentifierList ":=" ExpressionList ;
```

Inside a function, `:=` declares one or more variables with types inferred from
the right-hand side (the full rule is `decl.shortvar`, §9.3). The left-hand side
is a list of plain identifiers; each non-blank name is bound in the current scope
with the right-hand value's default type (a string literal binds its default
`@[]readonly char`, §6.6). A multi-valued call distributes positionally
(`q, r := divmod(…)`), and a blank `_` evaluates its value but binds nothing.

`stmt.shortvar.rebind` — Unlike Go, `:=` does **not** require that at least one
left-hand name be new, and re-using a name already bound in the same scope
**rebinds** it (the redeclaration error of `decl.var.redeclare` applies only to
the `var` form, §14.7). Re-declaring a name in an inner scope shadows the outer
binding.

## 14.7 Local declarations

`stmt.decl` — A `var` or `const` declaration may appear as a statement
(`BlockDecl`); its rules are those of §9.1–§9.2.

`stmt.decl.redeclare` _(Constraint)_ — Declaring with `var` a name already
declared in the **same** block scope (including a function parameter, which lives
in the body scope) is an error ("redeclared in this scope"). Shadowing a name
from an **enclosing** scope is permitted (§9.5). A function-local `type`
declaration is a parse error (`stmt.no-local-type`, §14.1).
