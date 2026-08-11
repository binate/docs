# A Guide to Binate (for Go Programmers)

> **Status:** informative — the [language specification](spec/00-index.md) is the
> authority wherever this guide and the spec could disagree. This guide describes
> the language as specified and skips per-feature maturity notes; a few recently
> added features carry Draft/Provisional markers in the spec (some of which lag
> behind their already-landed, conformance-tested implementations — the spec's
> per-rule notes are the word on stability, not availability).

Binate is a systems programming language with **Go-family syntax and very
un-Go semantics**. That resemblance is the number-one hazard for a Go
programmer: most lines of Binate *look* like Go, and a good fraction of them
mean something different. This guide is organized around the differences.

What Binate is, in four sentences. It is a statically-typed, compiled **and**
interpreted language: one front end and one typed IR feed both a native-code
compiler (`bnc`) and a bytecode VM (`bni`), which share identical type layouts
and one heap, so compiled and interpreted code can call each other through
ordinary function values with no marshalling. Memory is **reference-counted**
— no GC, no ownership/borrow checker — with raw pointers as the explicit,
unsafe escape hatch. It targets small systems (32-bit first, 64-bit
supported), down to bare metal with no OS, no filesystem, and no C library:
the core language deliberately assumes none of those exist. There is **no
concurrency in the language** — no goroutines, no channels — execution is
single-threaded.

## 0. The one-minute delta

| Go | Binate |
|---|---|
| garbage collector | reference counting; cycles leak (yours to break, with raw pointers) |
| `[]T` slice | two kinds: `*[]T` raw borrow (2 words) / `@[]T` managed, owning (4 words) |
| `string` | no string type — `@[]readonly char` etc.; `char` = `uint8` = `byte` |
| `map[K]V`, `append`, `cap` | none — library concerns (`make_slice` + stdlib containers) |
| exported = Capitalized | exported = declared in the package's `.bni` interface file |
| structural interfaces | **nominal**: explicit `impl T : Iface`; interface values are `*I` / `@I` |
| `defer` | none — deterministic scope-exit destructors (RAII) |
| `for i := range xs` | `for v in xs` — a single variable is the **value**, not the index |
| `panic`/`recover` | `panic(msg)` aborts, unconditionally; errors are values; no `recover` |
| goroutines, channels, `select` | none; single-threaded |
| `T(x)` conversions | `cast(T, x)` and `bit_cast(T, x)` builtins |
| `s == nil`, `err == nil` | slices/interface/func values aren't comparable — `present(x)`, `len(s)`, `same(a, b)` |
| `func(int) int` as a type | function-value types are `*func(int) int` / `@func(int) int` |
| closures capture variables | closures capture **by value** (snapshot); share state via a captured pointer |
| generics with inference | monomorphized generics, **explicit** type args: `Sort[int](xs)` |
| `go build` package = dir of `.go` | package = `.bn` implementation dir + `.bni` interface file; `package "path/string"` |

The rest of the guide expands on each of these, roughly in the order you'd hit
them writing a program.

## 1. Programs, packages, visibility

A package is a **directory of `.bn` implementation files** plus a single
**`.bni` interface file** beside it (same parent, same base name):

```
pkg/
  foo.bni      # the package's public surface
  foo/
    a.bn
    b.bn
```

The package clause is a **string literal** — the import path itself, not an
identifier:

```binate
package "pkg/binate/parser"

import "pkg/binate/buf"
import lx "pkg/binate/lexer"    // alias
import _ "pkg/side/effects"     // blank import: initialization only
```

References are always qualified by the path's last segment (or the alias):
`buf.Concat(...)`. There is no dot-import. The import graph must be acyclic.

**Visibility is `.bni` membership, not capitalization.** A symbol is visible
to importers iff it is declared in the package's `.bni`. Capitalizing exported
names is a style convention only — the compiler attaches no meaning to case.
The `.bni` is a real, checked contract, not a header-file convention:

- a full `type` in the `.bni` is authoritative (not repeated in the `.bn`);
  a body-less `type Foo` exports Foo **opaquely** (importers hold `*Foo`/`@Foo`
  but can't touch fields or take its size);
- a `func` appears signature-only — except **generic** functions, whose full
  source body travels in the `.bni` (consumers monomorphize from it, the
  C++-templates-in-headers model); this is the one exception to binary-only
  package distribution;
- `var X T` (no initializer) in the `.bni` is an extern declaration whose
  storage lives in the `.bn`; `const` lives in exactly one of the two files
  (there is no extern const).

A `.bni` may also `expose "pkg/other"` — re-export another package's entire
surface as part of its own (by identity, not by copy; used for package
renames and aggregation). No Go analog.

**Program shape:** execution starts at `func main()` in package `"main"` — no
parameters, no results; command-line arguments come from a library (`os`
package), not from `main`. Package-level `var` initializers run in dependency
order before `main` (a `var` whose initializer *directly reads* another var
runs after it; reads hidden behind a named-function call don't count and may
observe zero values; initializer cycles are compile errors). **There is no
`init()` function** — do setup explicitly from `main`.

Files may start with `#!` on the first line (shebang; `bni -x script.bn args…`
runs a single file as a script), and `#[...]` annotations gate declarations,
files, and imports by target: `#[build(is(os, "linux") && is(arch, "aarch64"))]`.
`#` is the annotation sigil, **not** a comment; comments are `//` and `/* */`
as in Go.

## 2. Types: what exists, what doesn't

Scalars: `bool`, `int`/`uint` (target word size — 32 or 64 bits; there is no
`uintptr`, `uint` fills that role), `int8/16/32/64`, `uint8/16/32/64`,
`float32/64`, and `char`. **`char`, `byte`, and `uint8` are the same type**
under three spellings — a char is one byte, not a rune. There is no `rune`, no
`complex`, and **no `string`** (§3).

Source is ASCII (identifiers too); non-ASCII bytes are legal only inside
literals and comments, carried verbatim (UTF-8 is a convention the language
doesn't interpret).

Type declarations are Go-shaped, package-level **only** (no function-local
`type`):

```binate
type Celsius float64          // named-distinct type: cast() to cross
type byte2 = uint16           // alias: interchangeable, no methods
type Handle                   // forward/opaque declaration
type Point struct { x int; y int }
```

Named-distinct types work like Go defined types: transparent to operators,
indexing, and field access, but they inherit **no methods**, and crossing a
named boundary needs `cast` — except the Go-style rule that a value crosses
implicitly when exactly one side is named and its underlying is an *unnamed
composite* (`type Buf @[]int` assigns freely to/from `@[]int`; `Celsius` ↔
`float64` does not).

**Structs have no embedding.** There is no field/method promotion; composition
is explicit fields. Anonymous struct types exist and are structural. There are
no map literals and no map type. Arrays `[N]T` are value types, as in Go.

**No implicit numeric conversions, anywhere.** Binary operators require both
operands to be the *same* type — no signed↔unsigned, no width mixing, and
(stricter than Go) not even untyped-int-to-float: `var x float64 = 3` is an
error; write `3.0` or `cast(float64, 3)`. Untyped constants otherwise behave
much like Go's — they coerce to any type that can represent their value, with
defaults `int` / `float64` / `bool` / `@[]readonly char` — but constant
arithmetic is **fixed-width** (the `int64` ∪ `uint64` range), not bignum: an
intermediate result outside that range is a compile error even when the final
value would fit.

`const` declarations are **scalar-only** (no storage, no address; `iota` works
in grouped blocks exactly as in Go). For immutable non-scalar data, use a
`readonly`-typed `var` (§6). Enums are Go's idiom, not a feature:

```binate
type Opcode uint8
const ( OpAdd Opcode = iota; OpSub; OpMul )
```

## 3. Strings without a string type

A string literal is an untyped constant of natural type `[N]readonly char`
(exactly the bytes written — **no NUL terminator**; add `"\0"` explicitly for
C). Its default type is `@[]readonly char` — a managed-slice view of the
literal's static storage, costing no allocation. Permitted targets:

```binate
var a @[]readonly char = "hi"   // view of static data (default) — free
var b *[]readonly char = "hi"   // raw borrow of static data — free
var c @[]char = "hi"            // allocate + copy: mutable, owned
var d [2]char = "hi"            // array copy into a fixed buffer
```

`*[]char` is *not* a permitted target (a mutable raw view of read-only static
data would be unsound). "String" APIs conventionally take `*[]readonly char`
(borrow) or return `@[]char` (owned); adjacent string literals concatenate at
compile time (C-style) — there is no `+` on strings. `len("abc")` is 3. Text
processing is byte-oriented; there is no Unicode machinery in the language.

## 4. Slices: two kinds, and ownership is the point

Go's `[]T` splits into two distinct types, and the bare spelling `[]T` is
illegal:

- `*[]T` — **raw slice**: `{data, len}`, two words. A borrow. No reference
  count; something else must keep the backing alive.
- `@[]T` — **managed-slice**: `{data, len, backing, backingLen}`, four words.
  Owns its backing via refcount.

`@[]T` converts to `*[]T` implicitly (a borrow — the first two words are
layout-identical); never the reverse. At API boundaries the kind states
intent: `*[]T` = "I just need to look at it during this call", `@[]T` = "I
will retain it". **Returning a raw slice from a function that allocated it is
almost always a bug** — the backing dies with the function's managed
temporary; return `@[]T`.

What's missing, deliberately: **no `append`**, **no `cap`**, no capacity
argument to `make_slice` — growable collections are a library concern
(`strings.Builder`-style buffers, `vec.Vec[T]`, containers in the stdlib).
`make_slice(T, n)` is the only runtime-sized allocator and yields `@[]T`,
zero-initialized.

Sub-slicing `s[lo:hi]` preserves the kind (`@[]T` sub-slices share and retain
the backing); sub-slicing an *array* yields a raw `*[]T` borrow. Indexing and
sub-slicing are always bounds-checked (a defined panic, not UB);
`unsafe_index(s, i)` is the unchecked opt-out.

**Slices are never `nil` and never comparable.** `s == nil`, `s = nil`, and
`s1 == s2` are all compile errors. A zero slice is *empty* (`{null, 0, …}`);
test with `len(s) == 0` (or `present(s)`), and test "same view" with
`same(a, b)`. An empty slice always has no backing — there is no Go-style
distinction between nil and empty.

Slice literals: `@[]int{1, 2, 3}` allocates a fresh managed backing. A raw
slice literal is allowed only with constant elements (`*[]readonly T{…}` —
static data); otherwise build managed.

## 5. Pointers and memory: refcounting, not GC

Two pointer types:

- `@T` — **managed** pointer: copying it increments the referent's reference
  count; when the count reaches zero the destructor runs *immediately* and the
  memory is freed. Deterministic.
- `*T` — **raw** pointer: a plain address. No count, no safety net. This is
  the C-style escape hatch, and it's how you break reference cycles (a raw
  "weak" reference).

A managed pointer `@T` comes **only** from `make(T)` (zero-initialized) or
`box(v)` (heap copy of a value); managed-slices come from `make_slice(T, n)`
and slice/string literals (§3–4), and a capturing `@func` literal
heap-allocates its captures (§7). **`&x` always yields a raw `*T`**, even when
`x` is managed — there is no address-of that produces a managed pointer. `.` auto-dereferences one level for both kinds (no `->`).

The rules the compiler enforces (the "axioms"):

- every copy of a managed value — assignment, argument, return, field or
  element store — **acquires** (RefInc); every scope exit **releases**
  (RefDec); `x = v` acquires `v` before releasing the old `x` (self-assignment
  is safe);
- when a count reaches zero, the destructor runs, releasing managed fields
  recursively — this replaces `defer` for cleanup and is why Binate has none;
- temporaries live to the **end of the statement**: `foo(@[]int{1,2,3})` is
  safe even though `foo` takes `*[]int`, but `var s *[]int = @[]int{1,2,3}`
  leaves `s` dangling on the next line — the managed temporary died at the
  semicolon.

Refcounting is **transparent and deterministic by design**: counts are never
elided across function boundaries (that would break compiled↔interpreted
interop), and the fix for excess refcount traffic is an ownership decision —
borrow with `*T` — not a compiler optimization you wait for. Hot paths use raw
pointers/slices; that's idiomatic, not a smell.

Two things are on you, by contract: **cycles leak** (refcounting doesn't
collect them; break cycles with raw pointers), and a **raw borrow used after
its owner released** is use-after-free — undefined behavior, exactly like C.
Everything else memory-ish is defined: over-release aborts, fresh allocations
are zero-initialized, bounds checks trap.

Value semantics follow from the model: structs are value types; copying a
struct with managed fields acquires each of them. A struct is heap-managed by
putting it behind `@T` (`make(Point)`), never "embedded managed".

## 6. `readonly` and `const` are different things

`const` = compile-time scalar constant (no storage). `readonly` = a **type
modifier**: "not writable through this access path". It binds leftward-out,
reading left to right:

```binate
readonly *int      // read-only handle to a mutable int
*readonly int      // mutable handle to a read-only int
*[]readonly char   // slice of read-only chars (the "string borrow" type)
var V readonly *[]readonly char = "v1"   // immutable global storage
```

The capability lattice: **adding** element-level `readonly` is implicit
(`*T → *readonly T`, `@[]T → @[]readonly T`); **dropping** it requires `cast`.
Outermost `readonly` is freely convertible both ways (it's about the location,
not the value), and on a *parameter* it is local discipline only — not part of
the function's signature. `readonly` is shallow (one level, as written) and
layout-free.

Method calls dispatch on **object** const-ness, not handle const-ness: a
`readonly @Box` (read-only handle, mutable object) can call any method; a
`@readonly Box` / `*readonly Box` (read-only object) can call only methods
declared with a read-only receiver. There are no `const`-method annotations —
the receiver type *is* the statement.

## 7. Functions, function values, closures

Go-shaped declarations, with less sugar: every parameter is typed
individually (no `a, b int`), there are **no named results**, and a bare
`return` is legal only in a void function. Multiple returns, `x, y := f()`
destructuring, and tail-call `return f(...)` all work as in Go. A function
with results must end in a syntactically terminating statement (`return`,
`panic(...)`, an exhaustive `if/else`, a `default`-ed `switch`, or `for {}`)
— the analysis is syntactic, so add a final `return` even when you "know"
the chain is exhaustive.

**Variadics:** `func f(xs ...T)` — inside the body `xs` is a **raw `*[]T`
borrow** over caller stack storage (zero heap): don't store or return it;
copy out to retain. Spread is `f(s...)` (exclusive — no mixing with
individual args), and the operand must be a slice (`arr[:]...` for an array).

**Function values** are typed `*func(int) int` (raw) or `@func(int) int`
(managed) — bare `func(...)` is not a type. Both are two words. A named
function decays to a function value (`var f *func(int) int = add`); function
literals work as in Go, with one huge exception:

> **Closures capture by value.** A capture is a snapshot at the point the
> literal is evaluated. Writes to the original afterward are invisible inside;
> writes inside are invisible outside. To share mutable state, capture a
> pointer (the pointer is snapshotted; the pointee is shared) — e.g. capture a
> `@int` from `make(int)`. Recursive closures (`g := func(){ …g… }`) don't
> work — the capture would snapshot the pre-assignment `g`; use a named
> function.

A capturing `*func` keeps its captures in the enclosing stack frame — it must
not outlive it (returning one is a lint warning and a dangling value). A
capturing `@func` heap-allocates its captures and may escape freely. Choose
the kind by lifetime, as with slices.

Method values (`x.M`, receiver captured) and method expressions (`T.M`,
receiver becomes the first parameter) both exist and produce function values.

Function values are not comparable (`present(f)` tests set-ness); calling
through one is mode-transparent — this is the compiled↔interpreted seam.

## 8. Methods and receivers

Methods are declared Go-style, outside the type, but only in the type's own
package, only on named non-alias types. Five receiver kinds:

```binate
func (r Box) a()             // value copy
func (r *Box) b()            // raw pointer, mutable — the workhorse
func (r *readonly Box) c()   // raw pointer, read-only — the other workhorse
func (r @Box) d()            // managed — for methods that retain the receiver
func (r @readonly Box) e()   // managed, read-only
```

One method per name per base type — no overloading, including on receiver
kind. At a call site the receiver is smoothed one step in the safe direction
(`@Box` can call any of these; a value can call `*Box` methods if it's
addressable — note `Point{1,2}.bump()` works, composite literals are
addressable) — but never raw→managed and never mutable-through-read-only.

## 9. Interfaces: nominal, explicit, two-word values

The single biggest semantic gap from Go. Declaring the methods is **not
enough** — a type satisfies an interface only through an explicit `impl`:

```binate
interface Shape {
    Area() float64
}

type Circle struct { r float64 }

func (c *readonly Circle) Area() float64 { return 3.14159 * c.r * c.r }

impl *readonly Circle : Shape
```

- `interface` is its own top-level declaration form (there is no
  `type X interface{…}` and no anonymous interfaces). Extension is
  `interface Child : Parent1, Parent2 { extra() }`; `impl T : Child`
  satisfies the ancestors transitively.
- **There is no orphan rule**: the `impl` may live in the type's package, the
  interface's package, or any third package that sees both. (Methods
  themselves still live in the type's package.)
- Even an **empty user interface requires an impl** — "zero methods" does not
  mean "everything satisfies it". The one universal interface is the built-in
  `any`, satisfied by every type with no impl.
- An interface *value* is spelled `*Shape` (raw) or `@Shape` (managed) — two
  words `{data, vtable}`; bare `Shape` is not a value type. Raw borrows the
  underlying object; managed retains it.
- `Self` in an interface method signature means "the implementing type";
  methods using `Self` outside receiver position can't be called through an
  interface value (use a generic constraint instead).

**Constructing** an interface value never copies implicitly: the source must
be pointer-shaped (`&t` or a `@T`; `box(t)` to get a managed one from a
value), with one convenience — a plain value used where a **raw** `*Iface` is
expected takes an **implicit borrow** (an auto-`&`; for a non-addressable
value like a literal, a statement/binding-scoped temporary), permitted at
argument and initializer positions. Construction **borrows rather than
copies** — a stored `*any` sees later mutations of its source, and dangles if
it outlives it, exactly like any raw borrow. `@Iface` from a value always
requires an explicit `box(t)`.

Dynamic dispatch is vtable-based. Dispatching through an unset interface
value is a defined abort — check `present(iv)` first. Interface values are
not comparable and not nil-comparable: `present` distinguishes "never set";
a boxed nil pointer (Go's typed-nil) is *present* and matches its type.

**Assertions and type switches** need a mandatory *recovery kind* on the
target — `@T` (retain), `*T` (borrow), or `T` (copy out) — legal per the
source (`*I` can't yield `@T`; you can't mint a refcount from a borrow):

```binate
var v @any = box(makeSomething())   // @any: all three recovery kinds legal below
n, ok := v.(*int)             // comma-ok; never aborts
switch x := v.(type) {
case *int:      useInt(*x)
case @Circle:   use(x)
case *[]readonly char: write(x)   // slice targets: structural identity
case *Shape:    x.Area()          // interface target: satisfaction
default:        write("?")
}
```

Concrete targets match by **exact nominal identity** (a boxed `Celsius` does
not match `.(float64)`; `List[int]` ≠ `List[uint]`); slices are the one
composite target, matched by exact structural identity (`@[]char`,
`*[]char`, `@[]readonly char`, `*[]readonly char` are four distinct dynamic
types). The expression form `v.(*int)` **aborts on a miss** — and there is no
recover — so prefer comma-ok. There is no `case nil`.

Four canonical interfaces ship with the language (`pkg/builtins/lang`):
`Stringer` (`String() @[]char`), `Comparable` (`Compare(other Self) int`),
`Orderable` (zero-method marker extending Comparable), and `Hashable`
(`Hash() uint`). All primitives implement them; `(42).String()` works without
an import. `Compare`, not `<`, is how generic code orders values.

## 10. Generics: monomorphized and explicit

```binate
func Sort[T lang.Orderable](xs *[]T) { … }
type Vec[T any] struct { … }

Sort[int](xs)            // type arguments are ALWAYS explicit — no inference
var v Vec[@[]char]
```

- A constraint is a single named interface (or `any`); combine by declaring a
  combined interface. Constraints are satisfied **nominally** — the concrete
  type needs a visible `impl`. No Go-style type sets, unions, or `~T`.
- Everything monomorphizes: each instantiation is its own code and its own
  distinct type; a constraint method call compiles to a **direct** call, no
  vtable. There is no runtime generic dispatch and no dictionary passing.
- Methods on a generic type bind the type's parameters through the receiver
  (`func (v *Vec[T]) Get(i int) T`); a method may not introduce its **own**
  type parameters (use a free function).
- Generic bodies ship in the `.bni` (source), so cross-package instantiation
  works without the package's implementation sources.

## 11. Control flow

`if`, `for`, `switch` — with meaningful deltas:

- **No init clause** in `if`/`switch` (`if x := f(); …` doesn't parse); bind
  on the previous line. Conditions must be `bool`.
- `for` is the only loop: `for {}` / `for cond {}` / `for init; cond; post {}`
  / **`for v in xs {}`**. The range form uses the keyword **`in`**, iterates
  slices and arrays only, and — opposite of Go — a single variable is the
  **element value**; `for i, v in xs` adds the index. (No maps or channels to
  range over; strings are slices already.)
- `switch` never falls through and has no `fallthrough` keyword; a `case` can
  list multiple values; tagless `switch { case cond: … }` is the
  if-else-chain form. No duplicate-case or exhaustiveness checking.
- **No `goto`, no labels** — no labeled break/continue; restructure nested
  loops (helper function, flag, or early return).
- **No `defer`** — destructors run at scope exit deterministically; RAII
  covers what `defer` covers in Go.

## 12. Expressions and arithmetic: defined, strict

- Operands of a binary op must be the same type (§2). `~` is bitwise
  complement (Go's unary `^`); `^` is XOR only. **Precedence is not Go's**:
  like Go, all bitwise/shift operators bind tighter than comparisons — but the
  levels are C's distinct ladder (`* / %` > `+ -` > `<< >>` > `&` > `^` > `|`),
  not Go's collapsed one. So `x << 1 + 2` is `x << 3` (Go: `(x << 1) + 2`) and
  `x & 3 + 1` is `x & 4` (Go: `(x & 3) + 1`) — parenthesize mixed
  shift/arithmetic expressions.
- Assignment is a statement (no `a = b = c`); `x++`/`x--` are statements,
  postfix only. Parallel assignment `a, b = b, a` works (RHS evaluated
  first). `:=` **rebinds silently** — there is no "at least one new variable"
  rule, so a stray `x, err := …` that Go would reject (or split) simply
  rebinds both.
- Comparison never chains, aggregates compare `==`/`!=` element-wise iff all
  parts are comparable, and relational `<` never applies to aggregates — nor
  to generic type parameters (use `Compare`).
- Arithmetic is **defined everywhere Go leaves gaps**: signed and unsigned
  overflow wrap (two's-complement, spec-guaranteed); `/`/`%` by zero and
  `MIN/-1` are defined panics; shifts by ≥ width give the mathematical result
  (0 / sign-fill — *not* hardware-masked), negative shift counts panic;
  float→int conversion **saturates** (`NaN` → 0); float compares are IEEE
  (`x != x` tests NaN). The `unsafe_div` / `unsafe_rem` / `unsafe_shl` /
  `unsafe_shr` builtins are the guard-free versions.
- `cast(T, x)` is the value conversion (wrap/truncate/extend/saturate; also
  the sanctioned way to drop `readonly`). **`cast` does not launder
  constants**: `cast(uint8, 256)` and even `cast(int8, cast(int, 200))` are
  compile errors — constants must fit, period; mask (`& 0xff`) or `bit_cast`
  when you mean bits. `bit_cast(T, x)` reinterprets same-sized bits (int↔float,
  pointer↔`*uint8` — the `void*` of Binate).

## 13. Errors and panics

Errors are values, Go-style — multiple returns, check-and-return. The stdlib
convention is an `@errors.Error` last result tested with `present`:

```binate
v, err := parse(input)
if present(err) {
    return zero, err
}
```

`panic(msg)` takes a single `*[]readonly char` message and **aborts the
program**. There is no `recover`, no unwinding, no exception path — a defined
small set of runtime conditions (out-of-bounds, divide-by-zero, negative
shift, failed expression-form assertion, nil-interface dispatch…) also
aborts. If a condition is recoverable, it must be an error value; the
comma-ok forms exist so you never *have* to risk an abort.

## 14. Builtins (keywords, not functions)

`make(T)`→`@T` · `make_slice(T, n)`→`@[]T` · `box(v)`→`@T` · `cast(T, e)` ·
`bit_cast(T, e)` · `len(e)`→`int` · `sizeof(T)`/`alignof(T)`→`uint`
(compile-time, target-dependent) · `present(x)`→`bool` (is a
pointer/slice/interface/function value set?) · `same(a, b)`→`bool` (identity
of pointers/slices/interface values — the `io.EOF`-sentinel test) ·
`unsafe_index(c, i)` (unchecked `c[i]`). These are reserved words — `make` is
not the map/channel factory it is in Go (one type argument, no size), and
none can be shadowed. There is **no predeclared `print`/`println`** — console
and formatted output is the `fmt` library (`fmt.Print`/`Println`/`Printf`,
ordinary `...*any` variadics; `panic` is the one predeclared function).

## 15. What isn't in the language (and where it went)

| Absent | Instead |
|---|---|
| goroutines, channels, `select`, `sync` | nothing — single-threaded semantics; the compiler won't assume single-threading for optimization, and OS threads with your own locking are possible but outside the language |
| GC | refcounting + destructors; raw pointers for cycles and hot paths |
| `defer`, `recover`, exceptions | destructors; error values; unrecoverable `panic` |
| `string`, `map`, `append`, `cap`, `copy` | char slices; library containers (via `Hashable`/generics); `make_slice` + explicit loops or library helpers |
| struct embedding, `init()`, named results, labels, `goto` | explicit fields, explicit setup from `main`, explicit returns, restructured loops |
| operator overloading, sum types, first-class enums | interfaces/generics; `type` + `const`/`iota` |
| Unicode source, runes | ASCII source; bytes; UTF-8 by convention in libraries |

## 16. The systems side

**Dual-mode execution** is a first-class design constraint, not an
implementation detail: every type's byte layout (struct offsets, the 2-word
raw slice, 4-word managed-slice, 2-word interface and function values, the
2-word refcount header at negative offset) is a language-level contract shared
by the compiler and the VM, so values flow between compiled and interpreted
code with no translation, and a function value is the only seam (one extra
indirection at the boundary). This is also why refcounting is never elided
across calls, and why layout is specified rather than left to the backend.

**C interop** exists but is quarantined to the edges — Binate targets systems
with no C at all, and uses C only to reach existing OS interfaces:

```binate
var n int = __c_call("write", int, fd, bit_cast(*uint8, p), nbytes)
var ep ***char = __c_global("environ", **char)
#[c_export("my_entry")] // export a Binate function under an unmangled C name
```

`__c_call`/`__c_global` take verbatim symbol names, scalar/pointer types
only, compiled mode only (the VM does no FFI). Bare-metal targets are
first-class: no OS, no allocator, no process — the core spec assumes none of
them, and the entry point, startup glue, and even the runtime are Binate code
placed by annotations, not a C runtime.

**Toolchain**, briefly: `bnc` compiles (LLVM and native backends,
cross-compilation, 32-bit targets including bare-metal ARM), `bni` interprets
the same sources on a bytecode VM (also `--test`, a REPL, and `-x` script
mode), `bnfmt` formats, `bnlint` lints — the compiler itself emits errors
only, never warnings; all advisory diagnostics (unused imports, suspicious
escapes, shadowing) live in the linter.

## 17. Reading code: a checklist of false friends

Things that parse fine and mean something else than in Go — the review traps:

1. `var s *[]int = @[]int{1,2,3}` — dangling: the managed temporary dies at
   end of statement. (`foo(@[]int{...})` is fine; binding to a raw local is
   not.)
2. `f := func() { count++ }` — `count` was captured **by value**; the
   increment is invisible outside. Capture a `@int` and write through it.
3. `impl`-less types never satisfy interfaces, however right their method
   sets look.
4. `v, ok := x.(*T)` is safe; `v := x.(*T)` **aborts the program** on a miss.
5. `x, err := step1(); x, err := step2()` — the second `:=` silently rebinds;
   there's no Go-style redeclaration error to catch a typo'd variable name.
6. `for v in xs` — `v` is the element, not the index.
7. A returned `*[]char` (raw) from an allocating function is a bug; the owner
   was a temporary. Return `@[]char`.
8. `s == nil` / `err == nil` / `f == fn2` don't compile — use
   `len`/`present`/`same`.
9. `getStruct().field.Mutate()` — rejected if `Mutate` needs `*T`: a call
   result isn't addressable (same rule as Go, but Binate's smoothing makes it
   look like it might work).
10. Package-level `var a = f()` where `f` reads var `b` — the read is
    invisible to init ordering (only *direct* reads order); `b` may still be
    zero. Make the dependency direct, or initialize explicitly in `main`.

---

*Next steps: the [specification](spec/00-index.md) for precision (each rule
has a stable ID like `mem.raw-uaf` — grep for it), `explorations/binate-coding-guide.md`
in the workspace for idiom-level guidance, and the conformance suite for
hundreds of small, runnable examples.*
