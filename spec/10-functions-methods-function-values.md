# 10. Functions, Methods, and Function Values

> **Status:** mixed · **Maturity:** Stable (functions/methods); function VALUES Provisional  
> **Rule-ID prefix:** `func`

This chapter covers function and method declarations (§10.1), returns and
destructuring (§10.2), the absence of variadics (§10.3), method receivers
(§10.4–§10.6), and method dispatch (§10.7). **Function values, closures, and
method values** — a recent, Provisional feature — are specified in the
companion section **[§10.8–§10.12, Function Values](10b-function-values.md)**.

## 10.1 Function and method declarations

`func.decl.form` — A function declaration is `func` *name* `(` parameters `)`
results *block*; a method inserts a parenthesized receiver before the name.
Functions and methods are declared at **package scope only** — there are no
nested or local function declarations; a `func` in expression position is a
function *literal* (§10.10).

```
FuncDecl   = "func" identifier [ TypeParams ] Signature Block ;
MethodDecl = "func" "(" identifier ReceiverType ")" identifier Signature Block ;
Signature  = "(" [ ParameterList ] ")" [ Result ] ;
Result     = Type | "(" TypeList ")" ;
```

Type parameters (`[T Constraint, …]`; Ch.12) may be declared on free functions;
generic methods are not supported.

`func.decl.params` — Each parameter is written **name before type** and is
**individually typed** (`name Type`). There is **no** same-type shorthand:
`a, b int` is rejected (after parameter `a` the parser expects a type but finds
`,`). Duplicate parameter names in one signature are an error.

`func.sig.identity` — A function signature's **type identity** is determined
solely by its ordered parameter types and ordered result types; parameter names
are not part of the type. For a method, the receiver is the first parameter of
its signature. This same identity is shared by named function types and function
*value* types (§10.8).

`func.decl.bni-match` — A free function declared in both a package's `.bni`
interface file and its `.bn` implementation must agree in parameter and result
counts and types; a mismatch is an error (Ch.16). The `.bni` carries only the
signature (the body is in the `.bn`), except for generic functions, whose body
travels in the `.bni` for cross-package monomorphization (Ch.12).

## 10.2 Returns and destructuring

`func.return.count` — A signature has zero, one, or many results. A single
result is written bare (`func f() T`); multiple results are parenthesized
(`func f() (T1, T2)`); zero results omit the result clause. A parenthesized
single type is equivalent to the bare form. **Named return values are not
supported** — result positions name types only.

`func.return.stmt` — A `return` statement carries a comma-separated expression
list with **no** surrounding parentheses; for a function with `N ≥ 1` results
the list supplies exactly `N` expressions, each assignable to the matching
result type. A bare `return` is valid only for a function with no results. A
wrong count is an error.

`func.return.missing` _(Constraint)_ — A function with at least one result must
**terminate on every control-flow path** (otherwise "missing return"). A
statement terminates if it is a `return`, a `panic(…)` call, an `if`/`else`
where both branches terminate, an infinite `for {}` with no `break`, a `switch`
with a `default` where every case terminates with no top-level `break`, or a
block whose last statement terminates. (Labels are unsupported, so any `break`
disqualifies its `for`/`switch`.)

`func.return.tail` — For a function with **more than one** result, a single
return expression that is itself a multi-result call whose result tuple matches
in count and per-position type is a permitted tail form: `return f(…)`. The
callee may be a function, a function value, or a multi-result interface-method
call. _(The function-value and interface-method cases are Provisional.)_

`func.destructure` — A single multi-result call may be **destructured** into
several targets: `a, b := f(…)` (short declaration) or `a, b = f(…)`
(assignment to existing targets — identifiers, `s[i]`, or `s.field`). The
result count must equal the number of targets, and each result must be
assignable to its target. A blank `_` target discards its result (the call is
still evaluated). _(Destructuring a function-value or interface-method call is
Provisional.)_

> _Note._ A function with multiple results returns them packed into a single
> (anonymous) struct; individual results are extracted by position. This
> representation is shared by functions, function values, and interface methods
> (Annex B). On destructuring, each extracted managed result acquires its own
> reference for the new owner (Ch.18).

## 10.3 Variadic parameters and spread (deferred)

`func.variadic.absent` — Binate has **no variadic parameters** and **no spread
operator** in the current language. A parameter is exactly `name Type`; there is
no `...T` last-parameter form, and a call's arguments are a plain comma-separated
list with no `...` to expand a slice. Both features are **deferred** (the
grammar reserves `...T`). A call to a function with **one or more** parameters
requires an **exact** argument count.

> _Note._ The `...` token appears in the language only in two unrelated places:
> the inferred-length array literal `[...]T{…}` (§13) and the `__c_call` C-ABI
> boundary marker (Annex D). Neither is a general variadic or spread facility.

> _Note._ A function with an **empty** parameter list likewise requires an
> exact (zero) argument count: a user `func f()` called as `f(1, 2)` is a "too
> many arguments" error. The loose arity check is restricted to the variadic
> builtins `print`/`println`/`panic` (§15), which alone accept extra arguments.

## 10.4 Method receivers

`func.method.receiver-kinds` — A method receiver `(name T)` takes exactly one of
**five** kinds, and the receiver type alone states whether the method needs a
mutable or read-only object (there are no separate const-method annotations):

| Receiver | Object | Handle |
|----------|--------|--------|
| `(r T)` | value (a copy) — read-only (§10.6) | — |
| `(r *T)` | mutable | raw |
| `(r *readonly T)` | read-only | raw |
| `(r @T)` | mutable | managed |
| `(r @readonly T)` | read-only | managed |

A value receiver may also be written `(r readonly T)`; it is accepted but
redundant with `(r T)` (a value copy is read-only regardless).

`func.method.receiver-base` _(Constraint)_ — A method's receiver base must be a
**named type declared in the same package** as the method. Aliases, predeclared
/ builtin types, anonymous types, and types imported from other packages may not
be receivers (§7.3). The one carve-out is the intrinsic package
`pkg/builtins/lang`, which may declare methods on the universe primitives
`int`/`float`/`bool` (§20.1); aliases remain rejected even there. The receiver
name may be `_`.

## 10.5 Receiver smoothing and dispatch direction

`func.method.smoothing` — At a method call `x.M()`, the receiver value is
**smoothed one level** to the method's declared receiver kind, in the safe
(permissive → restrictive) direction only: a managed `@T` can reach any kind; a
raw `*T` can reach `*T`/`*readonly T`/value; a value can take its address to
reach `*T`/`*readonly T`. The only rejected **indirection** is reaching a
**managed `@T`** receiver from a non-managed source (never value→`@T`, never
`*T`→`@T`) — that would fabricate a reference count. (The separate
object-`readonly` direction below is the other rejection.)

`func.method.object-const` — Dispatch keys off **object** read-only-ness, not
handle read-only-ness (§7.11). A read-only handle to a mutable object
(`readonly @Box`) may call any method; a read-only **object** (`@readonly Box`,
`*readonly Box`, or a `readonly Box` value) may call only read-only-receiver
methods. Adding object-`readonly` is allowed; dropping it is rejected.

`func.method.impl-receiver` — An `impl T : Iface` (and its `*T`/`@T`/`readonly`
variants) states that the receiver shape satisfies the interface; the impl's
receiver kind is validated against each method's declared receiver kind by the
same safe-direction smoothing (Ch.11).

## 10.6 One method per name; auto-dereference; value receivers

`func.method.one-per-name` _(Constraint)_ — At most **one** method may be
declared per (receiver base type, name) pair. There is **no overloading on
receiver kind** — a name is defined once on a type whether its receiver is a
value, `*T`, or `@T`. A duplicate is an error.

`func.method.auto-deref` — `x.M()` resolves the receiver base by looking **one
level** through a pointer/managed wrapper (and through alias/`readonly`); it does
not chase multi-level indirection. The `.` operator auto-dereferences a single
pointer level (there is no `->`; §7.8).

`func.method.value-recv` — A value receiver `(r T)` receives a **copy** of the
object; the method operates on the copy, so it cannot affect the caller's value.

> _Open / known gap._ The design intent is that a value receiver is **read-only**
> (mutating a discarded copy is pointless). The checker does **not** currently
> enforce this — it does not reject `r.field = …` in a value-receiver body; the
> "always read-only" guarantee is only the *semantic* consequence of the copy
> being discarded, not a diagnosed rule (`func.method.value-recv-readonly`,
> `claude-todo.md`).

## 10.7 Static and dynamic dispatch

`func.dispatch.static` — When the receiver's type is a statically-known concrete
named type (or a universe primitive under `pkg/builtins/lang`), a method call is
dispatched **directly** to that type's method, with the smoothed receiver as the
first argument. (Mechanics: Annex B.)

`func.dispatch.vtable` — When the receiver is an **interface value** (`*Iface` /
`@Iface`), dispatch is **dynamic**: the method slot is resolved at compile time
and the implementation is loaded from the value's vtable and invoked at run time
with the value's data pointer as the receiver. There is no receiver smoothing on
this path (it was validated when the impl was declared). A `readonly` wrapper on
an interface value is peeled before dispatch. The observable result is normative;
the vtable layout is informative (§11, Annex B). _(Interface dispatch is part of
the Provisional interface-value machinery; Ch.11.)_

`func.dispatch.routing` — A call `x.M(args)` of selector shape (after builtin
and generic-instantiation calls are resolved) is routed in this precedence: (1) if
the callee is a **function-value-typed** selector or index (e.g. a struct field
of function-value type), it is an **indirect call** (§10.12) — a function-value
field is never mistaken for a method; (2) an interface-value receiver dispatches
by vtable; (3) an in-scope value head is a static method call; (4) a
package-alias head is a qualified free-function call.
