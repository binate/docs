# 10.8–10.12 Function Values, Closures, and Method Values

> **Status:** mixed · **Maturity:** core **Stable** (implemented across all
> backends and execution modes; conformance-mixed — tracked defects at §10.12);
> tail-return / destructure *through* a function value Provisional (§10.2)  
> **Rule-ID prefix:** `func`  
> Part of Ch.10 ([Functions, Methods, and Function Values](10-functions-methods-function-values.md)).

A **function value** is a callable value: a `*func`/`@func` carrying a function
(possibly with captured state). This block specifies function-value types and
representation (§10.8), non-capturing literals and function references (§10.9),
closures (§10.10), method expressions and method values (§10.11), and equality,
indirect calls, and dual-mode dispatch (§10.12). The **core** feature is
**Stable** — implemented across all backends and execution modes and exercised by
the conformance suite; a few specific interactions (§10.2) remain
**Provisional**, and backend implementation-conformance defects are tracked
separately (Annex C).

## 10.8 Function-value types

`func.value.spelling` — A function-value type is written `*func(P…) R` (raw) or
`@func(P…) R` (managed). Parameters are types only (no names); a single result
is bare, multiple results parenthesized. A trailing `...T` in the parameter
position marks a **variadic** function-value type (`*func(...T)` /
`@func(A, ...T)`; §10.3 `func.variadic.identity`). A bare `func(…)` is **not** a
usable type — the `*`/`@` prefix is mandatory (paralleling `*[]T`/`@[]T` and
`*Iface`/`@Iface`).

`func.value.repr` — A function value of either kind is **two words**
`{vtable, data}` (§7.13 `type.layout.func-value`): the vtable is a `{dtor, call}`
record (slot 0 destructor — null when nothing to destruct; slot 1 the call
shim), and the data word points at the closure record (null for a non-capturing
value). The concrete shim/trampoline mechanics are in Annex B.

`func.value.identity` — Two function-value types are identical iff they have the
**same kind** (raw vs managed — `*func(…)` and `@func(…)` are never identical)
and structurally identical signatures (equal parameter and result counts,
pairwise-identical types, **and identical variadic-ness of the final parameter** —
a variadic signature is never identical to a fixed one, even one taking `*[]T`;
§10.3 `func.variadic.identity`); names ignored.

`func.value.smoothing` — A managed `@func(S)` is implicitly convertible to a raw
`*func(S)` of identical signature — a refcount-neutral **borrow** (the `*func`
borrows the `@func`'s record, owning nothing; §8.4). The reverse `*func → @func`
is **never** implicit.

`func.value.nillable` — Both function-value kinds are **nillable for assignment**
(a nil function value is both words zero; it is the default for a function-value
variable). A managed `@func` needs destruction; a raw `*func` does not. (Nil-ness
is not testable with `==`/`!=`; use `present` — §10.12.)

`func.value.named-nominal` — Named function-value types are **nominal** (§7.3):
a value of one function-value type does not implicitly assign into a distinct
named function-value type. A named function-value type is constructed from a
function *reference* or a function *literal* (§10.9) — **not** from a method
expression, nor by assigning an already-bound `*func`/`@func` value (both are of
function-value kind, which this nominal rule rejects).

## 10.9 Non-capturing function literals and function references

`func.ref.decay` — A reference to a named top-level function decays to a function
value of matching signature, assignable to a `*func` or `@func` destination —
including a **named** function-value type (`var f Fn = add`). The destination's
alias/named/`readonly` wrappers are peeled for the match; parameter names are
ignored.

`func.lit.noncapturing` — A function literal `func(P…) R { … }` in expression
position evaluates to a function value. A **non-capturing** literal (one that
references no enclosing local) carries a null data word and works in all
execution modes.

`func.lit.inferred-default` — A function literal takes its type from its
**destination**: the expected type where the literal is a variable initializer,
an assignment's right-hand side, a call argument, a `return` operand, or a
composite-literal field or element (the assignment boundaries of §8.8), or the
target type of a `cast` / `unsafe_cast` (§8.5, §8.7; not of a `bit_cast`, which
reinterprets its operand as it is). Alias and `readonly` wrappers on the
destination type are peeled, and signatures match as in `func.value.identity`
(names ignored). A raw `*func` destination of matching signature makes the
literal that `*func` (its closure record, if it captures, is kept in the
enclosing frame and borrowed by the destination; §10.10
`func.closure.allocation`). A **named** function-value destination of matching
signature (`var f Fn = func(…){…}`) gives the literal that named type — raw or
managed as `Fn`'s underlying type is (§7.3), with the corresponding closure
allocation. Otherwise — no destination (`:=`, `var f = …`, an operand), an
`@func` destination, or one whose type or signature does not match — a function
literal's (and a bare function reference's) type is the **managed** `@func(…)`
default, mirroring the `@[]T` default, and the destination's ordinary
assignability check applies.

## 10.10 Closures

`func.closure.capture` — A function literal that references an enclosing local is
a **closure**. Capture is **always by value** — a snapshot taken when the literal
is evaluated; later writes to the original variable are not visible to the
closure. There are no capture lists; captured variables are inferred by
free-variable analysis. Each call of the closure starts with its own copy of the
captured values: a write to a captured name inside the body changes only that
copy, not the original variable or the closure record, so the next call starts
from the record's values again. (A `*func` closure's record is shared by every
value its site has produced in the frame, and each evaluation of the site
re-snapshots into it — `func.closure.allocation`.) **Shared mutable state is
expressed by capturing a pointer** (the pointer is snapshotted; the pointee is
shared).

`func.closure.captured` — Only ordinary local variables are captured. References
to package-level functions, constants, types, packages, and interfaces are not
captured (they are static entities). The closure record holds its own reference
to each captured managed value (`@T`, `@[]T`, `@func`, `@Iface`, or a struct or
array value with managed fields), released when the record's captures are
replaced or the record is destroyed (`func.closure.allocation`).

`func.closure.allocation` — A capturing **`*func`** closure — a function literal,
or a method value (§10.11) — keeps its closure record in the **frame** of the
innermost function or function literal whose body contains it: one frame per call
of that function or literal. The record lives until the frame ends, after that
frame's deferred calls have run (§14.13 `stmt.defer.exit`), however deeply nested
the block in which the closure is evaluated. There is **one record per closure
site per frame**, where the site is the literal or method-value selector as
written: evaluating the same site again in that frame re-snapshots into that
record, releasing the captures it held, so every `*func` value the site has
produced in the frame calls with the latest captures. (So a closure that
captures an earlier `*func` value from its own site captures a pointer to its own
record, and calling that value calls the closure itself; compare
`func.closure.recursion`.) The captures the record holds when the frame ends are
released then. A method value evaluated directly in a package-level variable
initializer, outside any function literal, has no enclosing frame; its record
lives for the rest of the program. Calling a capturing `*func` closure after the
frame that holds its record has ended is a use-after-free of the record, which is
**undefined behavior** (§18.7 `mem.raw-uaf`; Ch.21).

A capturing **`@func`** literal heap-allocates a fresh, reference-counted record
on each evaluation. `*func` does **not** auto-promote to `@func`: a closure that
must outlive its frame, or that must not share its captures with other closures
from the same site (one per loop iteration, say), shall be typed `@func`
directly. A method value is always `*func` (§10.11); where a bound method must
outlive its frame or be independent per evaluation, write an `@func` literal that
calls the method.

`func.closure.escape-lint` — Escape of a frame-bound capturing `*func` is a
**lint warning** (`func-value-escape`), not a hard type error: `*func` is an
opt-in escape hatch whose lifetime is the programmer's responsibility, and the
warning steers toward `@func`. Detection is best-effort: it covers a capturing
function literal (not a method value) written directly as a `return` operand or
assigned through a pointer- or managed-rooted destination, not every escape
path. Separately, an `@func` literal
that captures a **raw pointer** is flagged `managed-func-raw-capture` (the
`@func` can outlive the raw pointer's source).

`func.closure.recursion` — A recursive **anonymous** closure is unsupported:
because capture is by value, a closure that refers to its own binding would
snapshot a pre-binding (nil/stale) value. The single-binding forms
(`var g = func(){…g…}`, `g := func(){…g…}`) are hard compile errors (`g` is not
in scope within its own initializer); the reassignment form
(`g = func(){…g…}`) is flagged by the lint warning `recursive-closure-capture`.
The idiom for recursion is a named top-level function.

## 10.11 Method expressions and method values

`func.method-expr` — A **method expression** `T.M` (`T` a named type — including
a named-distinct scalar such as `type Celsius int` — with method `M`) is a
function value whose signature is `M`'s **full** signature *including* the
receiver as the first parameter (in `M`'s declared receiver kind). Its type is a
raw `*func(recv, args…) results`. It is a non-capturing function reference. If
`M` is **variadic**, the method-expression type is correspondingly variadic (its
final `args` element is `...T`; §10.3).

`func.method-value` — A **method value** `x.M` (`x` a value whose base type has
method `M`, with no same-named field — fields take precedence) is a function
value whose signature is `M`'s signature **minus** the receiver, which is
captured at the selector site. Its type is a raw `*func(args…) results` (even when
the captured receiver is managed), correspondingly **variadic** when `M` is
variadic (§10.3). The receiver base is the type **as written** (a named-distinct
type uses its own method set; §7.3).

`func.method-value.capture` — The receiver is captured in the form `M` declares,
bridging `x`'s shape to `M`'s receiver shape: a value receiver captures a copy; a
`*T` receiver captures `&x` (mutations visible); a `@T` receiver captures the
managed pointer (reference-counted). Capturing a value receiver via the managed/
raw form takes a snapshot. The captured receiver is held in the method value's
closure record, under `func.closure.allocation`: the record lives until the
enclosing frame ends (for the rest of the program when evaluated directly in a
package-level variable initializer), and evaluating the same selector again in
that frame re-captures the receiver into it, for every value the selector has
produced there.

## 10.12 Equality, indirect calls, and dual-mode dispatch

`func.value.equality` — Function values **cannot be compared** with `==` or `!=`
against anything, **including `nil`** (this differs from pointers, where
`p == nil` is allowed). Test a function value's presence with `present(fv)`
(§15) — the same idiom slices use (§7.6).

`func.value.indirect-call` — Calling **through** a function value invokes the
function it holds; the callee signature comes from the function-value type. An
indirect call is reached when the callee is a function-value-typed variable,
field, or element (routed ahead of method dispatch; §10.7). When the
function-value type is **variadic**, the caller packs the individual trailing
arguments into a `*[]T` (`func.variadic.pack`) or forwards a spread's `{data, len}`
(`func.variadic.spread`) at the call site, *before* the single indirection; the
call shim receives a plain `*[]T`, so variadic-ness is **erased at the ABI
boundary** (§10.3 `func.variadic.identity`). (Lowering: Annex B.)

`func.value.dual-mode` — An indirect call through a function value is
**mode-transparent**: the same call site dispatches correctly whether the target
is compiled or interpreted code, in either direction, through the value's call
shim. This is the mechanism by which compiled and interpreted code call each
other (Ch.19); a function value carries its own interpreter handle inline.

> _Implementation-conformance gaps._ The function-value feature has known,
> tracked backend-specific defects that **do not change the language rules** —
> they are implementation-conformance issues, not design holes (`conf.defect`).
> Examples: VM-mediated indirect-call argument-word limits and certain
> native-backend closure / method-value floating-point-return or
> register-overflow shapes. (An earlier cross-package **small-multi-return**
> shim-ABI conflict — a native-emitted vs LLVM-emitted `vtable.call` shim
> disagreeing on the return convention — was resolved by unifying every
> producer on the retbuf-for-any-multi-return shim convention, now specified
> in the ABI spec's dispatch chapter.) Remaining defects are test-pinned,
> tracked for Annex C.
