# 14.8–14.15 Control-flow statements

> **Status:** mixed · **Maturity:** language rules Stable (a few open semantic items flagged; defer §14.13 is Draft — ratified, not yet implemented)  
> **Rule-ID prefix:** `stmt`

This continues [Ch.14 Statements](14-statements.md) with the control-flow forms:
`if` (§14.8), `for` (§14.9), `switch` (§14.10), `return` (§14.11), `break` and
`continue` (§14.12), defer statements (§14.13), the terminating-statement
analysis (§14.14), and the deliberate absences (§14.15).

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
terminating-statement analysis, §14.14).

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
`iface.assert.absent`).

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
statement) on every path (§14.14).

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
no way to break out of an outer loop directly (§14.15).

## 14.13 Defer statements

> _Draft — ratified, not yet implemented (`proposal-defer`, 2026-09-02)._ The
> design is settled — function-scoped, with the loop restriction — and the
> `defer` keyword is reserved (§5.4); no implementation exists yet.

`stmt.defer` — A **defer statement** schedules a call to run when the
**enclosing function** exits (`stmt.defer.exit`):

```
DeferStmt = "defer" Expression ;
```

The call's **callee** — the function reference, the function value, or a
method's receiver — **and every argument are evaluated when the defer statement
executes**; the **call executes at function exit**. The evaluated values are
retained with the **function's lifetime**: they behave as anonymous
function-scope locals, released with the function's exit releases (§18.4)
**after all pending deferred calls have run** — *not* as statement temporaries
(§18.4 `mem.temporary`, §9.7). The deferred call **borrows** them as the
caller's references under the ordinary call contract (§18.5 `mem.param` — the
caller-side reference is unaffected by the call). Where an operand undergoes a
**managed→raw** conversion at the defer site (§8.4), the **pre-conversion
managed value** is what is retained, and the borrow is delivered at call time —
preserving the argument-borrow liveness guarantee. A raw operand value *not*
backed by a retained managed value is an ordinary borrow whose referent's
liveness at call time is the programmer's responsibility (§18.7 `mem.raw-uaf`).
The call's results, if any, are **discarded**; a discarded **managed** result is
released **immediately after the call returns**, before the next pending
deferred call runs. Because a defer statement cannot appear in a loop
(`stmt.defer.no-loop`) and the language has no `goto` (§14.15), each lexical
defer statement executes **at most once** per function activation, and the defer
statements that execute do so in **lexical order**. A defer statement inside a
**function literal** defers to that literal's own activation. A defer statement
is **not** a simple statement (§14.1) and requires an enclosing function; in the
REPL's immediate mode, a `defer` entered with no enclosing function is rejected.

`stmt.defer.call` _(Constraint)_ — The operand shall be a **call**: a function
call, a method call, or a function-value call (including a call of the
predeclared `panic`). A non-call expression, or a builtin-operation keyword form
(`make(…)`, `cast(…)`, …, §15.1 — special call shapes, not calls), is rejected.

`stmt.defer.no-loop` _(Constraint)_ — A defer statement shall not appear
**lexically inside a `for` statement** with no intervening function literal
between the defer statement and the `for` (a defer inside such a literal belongs
to the literal and is unrestricted). Rejected with a message of the form "defer
may not appear in a loop; wrap the loop body in a function or call the cleanup
explicitly".

> _Rationale._ The restriction keeps each lexical defer to at most one pending
> call — a fixed, statically-known set — so `defer` costs no hidden allocation
> (Go's function-scoped defer needs a runtime record list, unbounded in loops);
> it also removes Go's silent loop-accumulation wart. It is deliberately loud:
> the one Go idiom that does not transfer fails to compile rather than silently
> misbehaving.

`stmt.defer.exit` — Scheduled deferred calls run when the function exits
**normally**: at a `return`, or on falling off the end of the body. A `break`,
`continue`, or inner-block exit does **not** run deferred calls (they are
function-scoped), and does not affect the inner blocks' ordinary scope-exit
releases (§18.4 `mem.scope-exit`), which happen when those blocks exit. At the
function exit the pending deferred calls run in **reverse order of their
scheduling (LIFO)** — equivalently, reverse lexical order of the defer
statements that executed (`stmt.defer`) — and **then** the function's remaining
live managed locals are released. A deferred call therefore runs while the
function's still-open scopes' locals are live; no user code runs **between**
the releases themselves (§18.4, §21.5).

`stmt.defer.return` — On a `return`, the return operands are evaluated and each
**managed** result **acquires its owning reference first** (§18.5 `mem.return`);
the pending deferred calls then run (`stmt.defer.exit`); the function's locals
are then released and the retained results transfer to the caller. Deferred
code observes the post-evaluation state but **cannot change a returned managed
value** (results are unnamed and already retained).

> _Note._ A returned **raw** value that borrows state a pending deferred call
> releases or mutates dangles exactly as if that cleanup call were written
> textually before the `return` (§18.7 `mem.raw-uaf`); returning managed values
> is the safe pattern.

`stmt.defer.no-abort` — Deferred calls run on **normal function exits only**. A
defined non-recoverable panic (§17.5), a trap, or a runtime **exit** primitive
terminates the program **without running deferred calls** — and one occurring
**inside a deferred call** terminates the program immediately: the remaining
pending deferred calls, and the pending releases of the exit in progress, do
**not** run. (Deliberate divergence from Go, which runs the remaining deferred
functions while panicking and offers `recover`; a Binate panic is the program's
last action — §17.5, §14.15.)

## 14.14 Terminating statements

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

## 14.15 Statement-level deliberate absences

`stmt.absences` — The following control-flow constructs are **deliberately
absent** (rationale in Annex D / the Go-difference notes):

- **No `goto`** and **no labels** (hence no labeled `break`/`continue`).
- **No `fallthrough`** — switch cases never fall through (§14.10).
- **No `if`/`switch` init clause** (§14.8) — only `for` has init/post slots. (The
  **type switch** `switch v := x.(type)` is the one form that binds in its header;
  §14.10, §11.12.)
- **No `panic`/`recover` as recoverable control flow** — `panic(…)` exists only
  as an unrecoverable abort (Ch.15); there is no `recover`. Errors are values
  (Go-style multiple returns), not exceptions. Deferred calls (§14.13) do
  **not** run on a panic (`stmt.defer.no-abort`).
- **No goroutines, channels, or `select`** — execution is single-threaded.
