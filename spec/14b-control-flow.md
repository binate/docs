# 14.8–14.15 Control-flow statements

> **Status:** mixed · **Maturity:** language rules Stable (a few open semantic items flagged)  
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
be empty (the post not a short variable declaration: `stmt.for.post`).

`stmt.for.post` _(Constraint)_ — A C-style loop's post statement shall not be a
short variable declaration (`for i := 0; i < n; q := i { … }` is rejected): a variable
it declared would exist only from the second iteration on, after the body that would
use it had run once.

`stmt.for.scope` — A `for` statement is a scope of its own (§9.5): a variable its
C-style init statement declares is one variable for the whole loop, visible in the
condition, the post statement and the body, and out of scope after the loop, where a
same-named outer variable is visible again; storage the init statement keeps alive —
a raw-slice literal's backing (§13 `expr.composite.slice`) or an addressed composite
literal (§13 `expr.composite.lifetime`) — likewise lasts until the loop exits. The
body is a block per iteration: it exits (§14.13 `stmt.defer.exit` — its deferred
blocks run, then its managed locals are released) when it falls off its end, before
the post statement, and whenever a `break`, `continue` or `return` leaves it. A
range loop's variables (`stmt.for.in`) are bound anew for each iteration; they are
live while the body's deferred blocks run and are released when the iteration ends
(`stmt.for.in.ownership`).

`stmt.for.in` — A range loop `for … in coll` iterates a **slice, managed-slice,
or array**; ranging over any other type is an error ("cannot range over
non-iterable type"). A **string literal** operand is an array: it is ranged with
its natural type `[N]readonly char` (§6.6), over its `N` bytes. The loop **always
declares new variables**, scoped to the loop block:

- `for v in coll` binds **`v` to the element value** at each iteration.
- `for i, v in coll` binds **`i` to the index** (type `int`) and **`v` to the
  value**.

> _Note._ A single range variable binds the **value**, not the index — the
> opposite of Go's `for i := range coll` (where a single variable is the index).
> Drop the index when you do not need it: `for v in coll`. A blank value
> `for _ in coll` binds nothing.

`stmt.for.in.duplicate` _(Constraint)_ — The index and value variables must have
different names: `for i, i in coll` is an error. Either may be `_`
(`for _, _ in coll`).

`stmt.for.in.operand` — The operand is evaluated **once**, before the first
iteration, into a hidden variable that lives until the loop exits — as if by
`tmp := coll` (§9.3), whatever the operand: a variable, a field, an element, a
dereference, a call result or a composite literal. The loop ranges over that
variable. So an **array** operand is copied: a write to the original array
during the loop is not seen by the loop. A **slice** operand's length is fixed
when the loop starts, and its elements are read through its data pointer at
each iteration: a write to a later element of the same backing is seen. A
**managed** operand is held by the hidden variable (released when the loop exits,
however it exits), so reassigning the variable the operand came from, or a
managed pointer through which it was reached, during the loop does not free
what the loop ranges over. Any temporary the operand's evaluation produced and
the operand borrows from (the managed-slice behind a raw view `view(mk())`)
likewise lives until the loop exits.

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

`stmt.switch.default.single` _(Constraint)_ — A switch has **at most one**
`default` clause; a second is rejected, in an expression switch and in a type
switch alike.

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
(`stmt.switch.no-fallthrough`) and the first match wins; `default` — at most one
(`stmt.switch.default.single`) — runs when no case matches and also catches an
**unset** scrutinee. There is **no `case nil`**
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
reference** to the caller (the return path retains each managed result; then,
as it unwinds, each block it leaves runs its deferred blocks and releases its
locals, §14.13 `stmt.defer.return` — the ownership-transfer rule of §18). A
value-returning function must reach a `return` (or other terminating
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
is a compile error. A function literal's body is a function of its own: a loop or
switch around the literal does not enclose a `break` / `continue` in its body, and
one around a deferred block does not enclose one in the deferred block (§14.13
`stmt.defer.block`). There are **no labels**: break and continue take no operand
and always target the innermost construct — there is no labeled break/continue and
no way to break out of an outer loop directly (§14.15).

## 14.13 Defer statements

`stmt.defer` — A **defer statement** schedules its **block** to run when the
**innermost enclosing block** exits (`stmt.defer.exit`) — the block the defer
statement is directly a statement of: a function or function-literal body, a
`{ … }` block, an `if` / `else` or loop body, a switch or type-switch case clause's
body, or another deferred block.

```
DeferStmt = "defer" Block ;
```

Executing a defer statement evaluates **nothing**: the deferred block is ordinary
code at the defer statement's position, run later. It refers to the variables in
scope at the defer statement (§9.5) — a later declaration in the same block,
including a `:=` that rebinds a name already bound there (`stmt.shortvar.rebind`),
introduces a variable the deferred block does not see — and reads and writes those
variables as they are **when it runs**. Its statements have the ordinary statement
temporaries (§18.4 `mem.temporary`), and a composite literal in it lives as any
literal does (§13 `expr.composite.lifetime`). A deferred block is scheduled only
when its defer statement executes, and only for the current execution of the
enclosing block: a defer statement control did not reach schedules nothing, and
each execution of a block — each iteration of a loop body — starts with nothing
scheduled. A defer statement inside a **function literal** belongs to that
literal's body. A defer statement is **not** a simple statement (§14.1), and it is
never a terminating statement (§14.14), even when its block ends in `panic(…)`.

> _Rationale._ The block makes the late evaluation visible — the deferred code
> runs at the exit, as an `if`'s body runs when its condition holds — and keeps
> `defer` consistent with the other control-flow statements, which take blocks. It
> also sets the construct apart from Go's `defer f(x)`, which evaluates `f` and `x`
> at the defer statement.

> _Note._ The block is required: `defer f()`, without one, is a syntax error;
> `defer { f() }` is the defer statement it means.

`stmt.defer.block` _(Constraint)_ — A deferred block shall not contain a `return`
statement, nor a `break` or `continue` that would transfer control out of the
deferred block; a `break` / `continue` targeting a loop or switch inside the
deferred block, and anything in a function literal's body, are unaffected.

`stmt.defer.repl` _(Constraint)_ — In the REPL's immediate mode, a defer statement
at the prompt's top level has no enclosing block to wait for and is rejected; one
in a block typed at the prompt is not.

`stmt.defer.exit` — A block **exits** when control falls off its end or a `break`,
`continue` or `return` transfers control out of it; here and in §18.4, a switch or
type-switch case clause's body (§14.10 `stmt.switch.case`) counts as a block. At
each exit, the deferred blocks scheduled on the block run in **reverse order of
their scheduling** (last first), and **then** the block's managed locals are
released (§18.4 `mem.scope-exit`). A transfer out of several nested blocks does
this for each of them, **innermost first**. Every variable the deferred code can
name is still live when it runs. A loop body is a block per iteration (§14.9
`stmt.for.scope`), so a defer in a loop body runs at the end of every iteration,
including one ended by `continue` or `break`. A defer statement in a deferred block
schedules its block on that deferred block.

> _Rationale._ Which defer statements have executed at an exit is known from the
> program text — there is no `goto` (§14.15), and a block's statements run in order
> — so `defer` costs no hidden allocation and no runtime record, in a loop as
> anywhere else.

`stmt.defer.return` — On a `return`, the return operands are evaluated and each
**managed** result **acquires its owning reference first** (§18.5 `mem.return`);
the return statement's own temporaries are then released; then each block the
`return` leaves exits (`stmt.defer.exit`), innermost first; the results then
transfer to the caller. Deferred code observes the post-evaluation state but
**cannot change a returned value** (results are unnamed and already evaluated),
though it can change an object a returned pointer refers to.

> _Note._ A returned **raw** value that borrows state a deferred block releases or
> mutates dangles exactly as if that code were written textually before the
> `return` (§18.7 `mem.raw-uaf`); returning managed values is the safe pattern.

`stmt.defer.no-abort` — Deferred blocks run on **normal** block exits only. A
defined non-recoverable panic (§17.5), a trap, or a runtime **exit** primitive
terminates the program **without running deferred blocks** — and one occurring
**inside a deferred block** terminates the program immediately: the remaining
pending deferred blocks, and the pending releases of the exit in progress, do
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
- a `switch` with a `default` clause in which **every** case body terminates and
  no `break` targets the switch (one nested in an `if` or block counts; one a
  nested loop or switch consumes does not).

An empty statement (`stmt.empty`, §14.2) is a statement like any other: a block
whose last statement is empty — a `return` followed by a stray `;` before the
`}`, as in `return 1;;` — does not terminate.

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
  (Go-style multiple returns), not exceptions. Deferred blocks (§14.13) do
  **not** run on a panic (`stmt.defer.no-abort`).
- **No goroutines, channels, or `select`** — execution is single-threaded.
