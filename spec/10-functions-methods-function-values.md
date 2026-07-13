# 10. Functions, Methods, and Function Values

> **Status:** mixed · **Maturity:** Stable (functions/methods); function values — core Stable, a few interactions Provisional, one construct Draft (§10.8)  
> **Rule-ID prefix:** `func`

This chapter covers function and method declarations (§10.1), returns and
destructuring (§10.2), argument binding — variadic parameters and spread (§10.3),
method receivers (§10.4–§10.6), and method dispatch (§10.7). **Function values, closures, and
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

Type parameters (`[T Constraint, …]`; Ch.12) may be declared on free functions
and on types (structs, interfaces). A method may **not** declare its **own** type
parameters (`gen.no-generic-methods`), but a method **on a generic type** binds
the type's parameters through its receiver — `func (it *Cursor[T]) Next() (T, bool)`
(§12.1 `gen.method.generic-recv`).

`func.decl.params` — Each parameter is written **name before type** and is
**individually typed** (`name Type`). There is **no** same-type shorthand:
`a, b int` is rejected (after parameter `a` the parser expects a type but finds
`,`). Duplicate parameter names in one signature are an error. The **final**
parameter may be **variadic** (`name ...T`; §10.3), the one position where a
`...` precedes the type.

`func.sig.identity` — A function signature's **type identity** is determined
solely by its ordered parameter types and ordered result types (and whether the
final parameter is **variadic**; §10.3); parameter names are not part of the
type. For a method, the receiver is the first parameter of its signature. This
same identity is shared by named function types and function *value* types
(§10.8).

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

## 10.3 Argument binding: variadic parameters and spread

`func.call.apply` — At a call, arguments bind to parameters **positionally**. For
a **non-variadic** callee the argument count must **exactly** equal the parameter
count, and each argument must be **assignable** (Ch.8) to the corresponding
parameter type; a wrong count is a "wrong number of arguments" error and a type
mismatch is a "cannot assign" error. An **empty** parameter list requires exactly
zero arguments (`func f()` called as `f(1, 2)` is "too many arguments"). For a
**variadic** callee the leading arguments bind to the fixed parameters the same
way, and the remainder form the variadic argument (`func.variadic.pack` /
`func.variadic.spread`).

> _Note._ The only calls that accept a loose argument count are the predeclared
> **heterogeneous-variadic** forms `print`/`println` (§15.7), which are checked
> specially (each argument typed on its own, no fixed signature) and are **not**
> `...T` variadic functions. `panic` is a **fixed** single-parameter function
> (§15.7). General `...T` variadics (below) are **homogeneous** — every variadic
> argument has the one element type `T` — so they do not subsume `print`/`println`,
> whose arguments have no homogeneous concrete element type. (A `...*any` variadic
> *is* the intended long-term form for `print`/`println`, dispatching per argument
> via a type switch / reflection once those land — §15.7 `builtin.print`; it is
> simply not a homogeneous `...T` over a concrete type.)

`func.variadic.decl` — A function or method may declare its **final** parameter
as **variadic**, written `name "..." T` (`...` before the element type). At most
**one** variadic parameter is allowed and it must be **last**; a `...` on any
earlier parameter is an error. Inside the body the parameter has type **`*[]T`** —
a **raw slice** (a 2-word borrow; §7.13 `type.layout.slice-raw`; ownership per §7.6
`type.slice.ownership`), *not* a managed `@[]T`. The element type `T` is exactly as
written and may be any type (`@Foo`, `readonly char`, an interface value, …),
**including a type parameter** (`func f[T C](xs ...T)`): in each monomorphized
instance the element type is that instance's `T`, and packing and spread are
resolved per-instantiation exactly as a fixed `*[]T` parameter would be (§12).
Element-level `readonly` (`...readonly T` → `*[]readonly T`) is part of the element
type and thus of signature identity; an outer `readonly` on the parameter itself is
local read-only discipline only and is **not** part of identity (§7.11).

`func.variadic.identity` — Variadic-ness is part of a signature's **type
identity** (§10.1 `func.sig.identity`; §7.9 `type.func.kinds`). A variadic
signature is **distinct** from the otherwise-identical signature that takes a
plain `*[]T` parameter (`func f(xs ...int)` and `func g(xs *[]int)` are different
types, and a call binds their arguments differently). Identity propagates to
**function-value types**: `*func(...T)` and `@func(...T)` are variadic
function-value types (§10.8 `func.value.spelling` / `func.value.identity`), a
variadic `func` is assignable only to a matching variadic function-value type, and
an **interface** or **impl** method may itself be variadic (its variadic-ness is
compared like any signature type; §11.1 `iface.impl.coverage`). At every
**indirect** boundary — a call through a function value (§10.12) or an interface
method vtable slot (§10.7) — variadic-ness is a static/type-checking property that
is **erased at the ABI**: the caller performs the pack (`func.variadic.pack`) or
spread (`func.variadic.spread`) at the call site and the shim/slot receives a
plain `*[]T`, so an indirect variadic callee's calling convention is identical to
a fixed `*[]T` parameter.

`func.variadic.pack` — When the variadic argument is supplied as **individual
arguments** (`f(fixed…, a, b, c)`), the zero-or-more trailing arguments are each
assignable to `T` and are **packaged into a fresh `*[]T`** that views
**caller-materialized temporary storage** — a contiguous array of the argument
values that the caller materializes **before transferring control and tears down
after the call returns** (the enclosing statement strictly contains the call, so
the view is live for the whole call, including nested and re-entrant use). This
packing performs **no heap allocation**, and **no reference-count change on the
two-word slice header** itself. **Zero** variadic arguments yield the **empty** raw
slice `{null, 0}` (`len == 0`; §7.7 `type.slice.len0-no-backing`) — emptiness is
tested with `len(xs) == 0`, never a `nil` comparison (slices are not comparable,
§7.6). The order in which the trailing arguments are evaluated and stored into the
temporary array is **unspecified**, as for any argument list (operand evaluation
order is unspecified; §3.1).

> _Note (managed elements)._ For a managed element type (`...@Foo`) each trailing
> argument is **acquired** as it is stored into the temporary array (`mem.copy`,
> Axiom 3), and those elements are ordinary managed **temporaries of the enclosing
> statement**, released by the **caller** at statement end (`mem.temporary`). The
> callee receives a raw `*[]T` **borrow** and — like any `*[]T` parameter —
> **neither acquires on entry nor releases at exit** (contrast the callee-owned
> discipline of a fixed managed parameter, `mem.param`); to retain an element it
> makes its own acquiring copy. The temporary array is **not** a managed-slice
> backing (it carries no `{refcount, free_fn}` header), so the backing-iteration
> release of `mem.destructor` does not apply to it.

`func.variadic.spread` _(Constraint)_ — Alternatively the variadic argument may
be supplied as a single **spread** `expr "..."` as the **final** argument, where
`expr` is a **slice** (raw or managed) **assignable to `*[]T`** (an `@[]T`
**decays** to `*[]T`, §7.6 `type.slice.decay`; element-`readonly` follows the
capability lattice — adding `readonly` is allowed, **dropping** it requires a
`cast`; §7.11 `type.readonly.lattice-element`). The operand must be a **slice**,
not an array — sub-slice an array first (`arr[:]...`; a string literal has array
type `[N]readonly char`, so spread it as `lit[:]...`). The spread **forwards the
slice's `{data, len}` directly** — no copy, no allocation; a `len == 0` slice
yields the same empty variadic argument as zero individual arguments. A spread is
**exclusive**: it supplies the **entire** variadic argument and **may not be
combined with individual variadic arguments** — `f(fixed…, s...)` is allowed, but
`f(fixed…, a, s...)` is an error. Only **fixed** (non-variadic) arguments may
precede a spread, and a spread supplies **only** the variadic parameter, never a
fixed one (`f(s...)` on a callee with unfilled fixed parameters is a "wrong number
of arguments" error). A spread into a **non-variadic** callee, or a `...` that is
not on the last argument, is an error.

`func.variadic.borrow` — The variadic `*[]T` is a **borrow**, identical to any
`*[]T` parameter (§7.6 `type.slice.ownership`; §18.1 `mem.managed-vs-raw`, whose
guidance is that returning a raw slice or pointer from a function is "almost always
wrong"): it is valid only for the **duration of the call**. Retaining it past the
call — storing it in a raw field, returning it, or escaping `&xs[0]` — is a
use-after-free and is **undefined behavior** (`mem.raw-uaf`), **not** a diagnosed
error (general raw-borrow escape is not statically decidable, so this is not a
Constraint). To keep the elements, copy them into an **owned `@[]T`** (`make_slice`
plus a per-element acquiring copy for a managed element type; `mem.copy`). This
borrow discipline is precisely what lets `func.variadic.pack` avoid a hidden heap
allocation.

> _Note (cross-mode)._ What the **cross-mode ABI contract** (§2.4) pins is that the
> variadic argument is passed **as a `*[]T`** of the standard 2-word slice layout
> (§7.13) — exactly like an ordinary raw-slice parameter — so a compiled caller and
> an interpreted callee (or vice versa) interoperate. The **mechanism** that
> materializes the caller-side backing array is a backend-private
> calling-convention detail, not part of the type/layout contract (dual-mode
> translates calling conventions, never types or layout; §19 `exec.interop.funcval`).
> The `...` C-varargs marker inside `__c_call` (§16.9) is a **separate** mechanism
> and is unaffected.

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
name may be `_`. If the base type is **generic**, the receiver binds its type
parameters as fresh names (`*Cursor[T]`; §12.1 `gen.method.generic-recv`).

## 10.5 Receiver smoothing and dispatch direction

`func.method.smoothing` — At a method call `x.M()`, the receiver value is
**smoothed one level** to the method's declared receiver kind, in the safe
(permissive → restrictive) direction only: a managed `@T` can reach any kind; a
raw `*T` can reach `*T`/`*readonly T`/value; a value can take its address to
reach `*T`/`*readonly T` — **but only when the receiver expression is
addressable** (`expr.addressable`, §13), because that adjustment is an implicit
`&x`. So a `*T`- or `*readonly T`-receiver call on a **non-addressable** receiver
— a field or element of a by-value call result (`getBox().inner.bump()`) or any
other computed value with no storage — is **rejected**, exactly as
`&getBox().inner` is (§13); the `*readonly T` case is rejected on that same
addressability ground even though a read-only temporary would be harmless — the
reject is deliberately uniform. The call is **accepted** when the receiver is
addressable: an addressable variable, a value reached **through a returned
pointer** (`getBoxPtr().inner.bump()`), or a **composite literal**
(`Point{1, 2}.bump()`) — a literal has a real backing alloca (§13), so the
implicit `&` addresses genuine storage, unlike the ephemeral nothing of a call
result. A method whose declared receiver is a plain **value** (needing no address
of the source) is always callable. A second rejected indirection is reaching a
**managed `@T`** receiver from a non-managed source (never value→`@T`, never
`*T`→`@T`) — it would fabricate a reference count; dropping object-`readonly`
(below) is a third.

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
