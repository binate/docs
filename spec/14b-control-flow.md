# 14.8–14.14 Control-flow statements

> **Status:** mixed · **Maturity:** language rules Stable (a few open semantic items flagged)  
> **Rule-ID prefix:** `stmt`

This continues [Ch.14 Statements](14-statements.md) with the control-flow forms:
`if` (§14.8), `for` (§14.9), `switch` (§14.10), `return` (§14.11), `break` and
`continue` (§14.12), the terminating-statement analysis (§14.13), and the
deliberate absences (§14.14).

A condition or tag in `if`, `for`, or `switch` is parsed with **composite
literals suppressed**, so a bare composite literal there is a syntax error; wrap
it in parentheses (`if (Point{1, 2}) == p { … }`). This is disambiguation rule
**D4** (§13.11) — the same rule as Go. (See `expr.disambiguation.d4-paren`, §13:
the documented parenthesized escape is itself currently defective.)

## 14.8 If statements

`stmt.if` —

```
IfStmt = "if" Expression Block [ "else" ( IfStmt | Block ) ] ;
```

The condition must be of **`bool`** type (a named type whose underlying is `bool`,
or an untyped boolean such as the result of `==`, qualifies; there is no
truthy/falsy coercion — `stmt.if.cond`). The `then` block runs when the condition
is true; an optional `else` runs a block or, for an `else if` chain, another `if`.
Only the selected branch executes; each branch is a block with its own scope.

`stmt.if.no-init` — Binate's `if` takes a **bare condition**: there is no Go-style
init clause (`if x := f(); cond`). A value needed by the condition is bound by a
preceding statement. (The same applies to `switch`, §14.10; only `for` has
init/post slots.)

## 14.9 For statements

`stmt.for` — `for` is the only loop. There is no `while` keyword (the
condition-only form is the while-style loop) and no do-while form.

```
ForStmt    = "for" ForClause Block ;
ForClause  = (* empty *)            (* infinite:    for { … }                *)
           | Expression             (* while-style: for cond { … }           *)
           | ForCClause             (* C-style:     for init; cond; post { … } *)
           | ForInClause ;          (* range:       for x in coll { … }      *)
ForCClause = SimpleStmt ";" [ Expression ] ";" SimpleStmt ;
ForInClause = IdentifierList "in" Expression ;
```

`stmt.for.clause` — The four forms are distinguished as follows (disambiguation
rule **D2**; the full D1–D11 set is consolidated in Annex A once authored): `{`
immediately after `for` is the infinite loop; a first simple
statement followed by `;` is the C-style form; an identifier list followed by
`in` is the range form; otherwise the clause is a while-style condition. In the
C-style and while-style forms the condition, when present, must be **`bool`**
(`stmt.for.cond`); the init and post slots are simple statements (§14.1) and may
be empty.

`stmt.for.in` — A range loop `for … in coll` iterates a **slice, managed-slice,
or array**; ranging over any other type is an error ("cannot range over
non-iterable type"). It **always declares new variables**, scoped to the loop
block:

- `for v in coll` binds **`v` to the element value** at each iteration.
- `for i, v in coll` binds **`i` to the index** (type `int`) and **`v` to the
  value**.

> _Note._ A single range variable binds the **value**, not the index — the
> opposite of Go's `for i := range coll` (where a single variable is the index).
> Drop the index when you do not need it: `for v in coll`. A blank value
> `for _ in coll` binds nothing.

`stmt.for.in.ownership` — When the element type is managed, the value variable
**copy-owns** its binding: the element is retained on bind and released at the end
of **each iteration** (a range loop over N managed elements performs N retains and
N releases, balanced across `continue` and `break`). The index variable is a
non-managed `int`. (The reference-counting rules are §18.)

## 14.10 Switch statements

`stmt.switch` —

```
SwitchStmt = "switch" [ Expression ] "{" { CaseClause } "}" ;
CaseClause = ( "case" ExpressionList | "default" ) ":" { Statement ";" } ;
```

`stmt.switch.tag` — The switch **tag is optional**. With a tag, each case
expression must be **assignable to the tag's type** (`ct.AssignableTo(tag)`), and
the first case whose value equals the tag is selected. A **tagless** `switch { … }`
is the condition-less form (equivalent to Go's `switch true`): its cases are
boolean conditions and the first true one is selected; it is the idiomatic
replacement for a long `if`/`else if` chain.

`stmt.switch.case` — A `case` may list **several values** (`case 1, 2, 3:`),
matching any of them. Each case body is its own lexical scope. There is **at most
one** matching case body executed.

`stmt.switch.no-fallthrough` — There is **no fallthrough**: a case body runs to
its end and control leaves the `switch` — it never flows into the next case. There
is no `fallthrough` keyword at all (stricter than Go, which provides one to opt
in). Consequently no `break` is needed to end a case.

`stmt.switch.default` — A `default` clause (no `case` keyword) runs when no case
matches. Switch **exhaustiveness is not checked**, there is **no duplicate-case
check**, and `default` is not required (except as it bears on the
terminating-statement analysis, §14.13).

`stmt.switch.tagless-bool` _(Constraint)_ — The case expressions of a **tagless**
switch must be **boolean** — each case expression is itself the condition (the
`switch true` form), so `switch { case 3: … }` is rejected (`3` is not a boolean
condition). With a tag present, the case-vs-tag assignability rule
`stmt.switch.tag` applies instead.

`stmt.switch.break` — A `break` inside a switch case exits the **switch**
(Go-like); an enclosing loop, if any, **continues**. A case never falls through,
so `break` is only needed for an early exit from the middle of a case body;
statements after it in the same case do not run.

`stmt.type-switch` — A **type switch** is the second `switch` form; it dispatches
on the **dynamic type** of an interface-value scrutinee:

```
SwitchStmt     = … | "switch" [ identifier ":=" ] PostfixExpr "." "(" "type" ")"
                   "{" { TypeCaseClause } "}" ;
TypeCaseClause = ( "case" TypeList | "default" ) ":" { Statement ";" } ;
```

Each `case` lists **types** (each with a `*`/`@`/value recovery kind), not
expressions; a concrete-type case matches by exact dynamic-type identity and an
interface-type case by explicit `impl`. There is **no fallthrough**
(`stmt.switch.no-fallthrough`) and the first match wins; `default` runs when no
case matches and also catches an **unset** scrutinee. There is **no `case nil`**
— interface values are not nil-comparable (test with `present`, §15.5). The
optional `v :=` binds the recovered value **per case**. The scrutinee and target
rules, the recovery-kind legality, and the typed-nil / unset semantics are
specified in **§11.12** (`iface.typeswitch`, `iface.assert.kind`,
`iface.assert.absent`). _(Draft; not yet implemented — §11.12.)_

## 14.11 Return statements

`stmt.return` —

```
ReturnStmt = "return" [ ExpressionList ] ;
```

`stmt.return.arity` — The number of returned expressions must equal the function's
result count. A **bare `return`** is legal exactly when the function has **no
results** (there are no named results, so a bare return cannot stand in for
result values). For a multi-result function, a single call whose results match the
declared tuple is a permitted **tail-call return** (`return f(…)` where `f`
returns the matching results — `stmt.return.tailcall`). Each returned value must
be **assignable** to the corresponding declared result type (Ch.8).

`stmt.return.ownership` — A returned managed value transfers an **owning
reference** to the caller (the return path retains each managed result; the
function's locals are released as it unwinds — the ownership-transfer rule of
§18). A value-returning function must reach a `return` (or other terminating
statement) on every path (§14.13).

## 14.12 Break and continue

`stmt.break` —

```
BreakStmt    = "break" ;
ContinueStmt = "continue" ;
```

`break` exits the innermost enclosing **loop** (and is also accepted inside a
`switch`, see §14.10). `continue` proceeds to the next iteration of the innermost
enclosing **loop**; it is **not** valid in a `switch` that is not inside a loop. A
`break` or `continue` with no enclosing loop (or, for `break`, no loop or switch)
is a compile error. There are **no labels**: break and continue take no operand
and always target the innermost construct — there is no labeled break/continue and
no way to break out of an outer loop directly (§14.14).

## 14.13 Terminating statements

`stmt.terminating` — A function with **one or more results** must **terminate on
every path**: its body must end in a *terminating statement*, else "missing
return". The analysis is **syntactic** (not value-aware); a statement terminates
iff it is one of:

- a `return` statement;
- a call to the built-in `panic(…)` as an expression statement;
- a block whose **last** statement terminates;
- an `if` with an `else` where **both** branches terminate (an `if` with no
  `else` never terminates);
- a `for` with **no condition** and no `break` targeting it (an unconditional
  `for { … }` infinite loop);
- a `switch` with a `default` clause in which **every** case body terminates.

Because the analysis is syntactic, some functions a reader sees as exhaustive are
still rejected — e.g. an `if`/`else if` chain with no final `else`, a `switch`
without `default`, or a `for cond { … }` whose condition is constant-true. Write
an explicit terminating tail (a final `return`, or an `else`/`default`) in those
cases. A function with **no** results is never subject to this analysis.

## 14.14 Statement-level deliberate absences

`stmt.absences` — The following control-flow constructs are **deliberately
absent** (rationale in Annex D / the Go-difference notes):

- **No `goto`** and **no labels** (hence no labeled `break`/`continue`).
- **No `defer`** — scope-exit destructors handle cleanup (§18), RAII-style.
- **No `fallthrough`** — switch cases never fall through (§14.10).
- **No `if`/`switch` init clause** (§14.8) — only `for` has init/post slots. (The
  **type switch** `switch v := x.(type)` is the one form that binds in its header;
  §14.10, §11.12.)
- **No `panic`/`recover` as recoverable control flow** — `panic(…)` exists only
  as an unrecoverable abort (Ch.15); there is no `recover`. Errors are values
  (Go-style multiple returns), not exceptions.
- **No goroutines, channels, or `select`** — execution is single-threaded.
