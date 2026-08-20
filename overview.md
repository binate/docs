# Binate in Two Pages

> **Status:** informative. The condensed version of the [guide](guide.md); the
> [specification](spec/00-index.md) is authoritative. Assumes you know Go —
> Binate has Go-family syntax and deliberately different semantics, and this
> page is mostly about the differences.

**Identity.** A systems language that is both **compiled** (`bnc` — LLVM and
native backends; 32-bit targets including bare-metal ARM) and **interpreted**
(`bni`, a bytecode VM) from one front end: both modes share identical type layouts and
one heap, so compiled and interpreted code call each other through ordinary
function values, no marshalling. Memory is **reference-counted** — no GC, no
borrow checker; raw pointers are the unsafe escape hatch. **Single-threaded**:
no goroutines, channels, or `select`. Targets C-free systems; C interop exists
only at the edges (`__c_call` / `__c_global` / `#[c_export]`, compiled mode
only). Errors are values; `panic` is a single-message unrecoverable abort.

## Syntax snapshot

```binate
package "pkg/demo"                          // package clause IS the import path

type Point struct { x int; y int }          // value type; no embedding/promotion

interface Shape { Area() float64 }          // nominal: methods alone never satisfy

func (p *readonly Point) Area() float64 {   // receivers: T, *T, *readonly T, @T, @readonly T
    return cast(float64, p.x * p.y)         // no implicit numeric conversions — cast()
}
impl *readonly Point : Shape                // explicit impl; may live in ANY package

func main() {                               // no params, no results; no init() anywhere
    var p @Point = make(Point)              // @T = managed (refcounted); &x is always raw *T
    p.x = 3                                 // '.' auto-derefs both pointer kinds; no ->
    var s @[]char = "hi"                    // owned copy; @[]readonly char would view static data
    for i, c in s { _ = i; _ = c }          // range keyword is `in`; ONE var binds the VALUE
    var sh *Shape = &Point{3, 4}            // interface value (2 words); construction borrows
    var area float64 = sh.Area()            // dynamic dispatch through the vtable
    _ = area                                // (printing lives in the fmt library)
}
```

## Types

- Scalars: `bool`, `int`/`uint` (word-sized; no `uintptr`), sized ints,
  `float32/64`, `char`. **`char` = `byte` = `uint8`** — one byte, not a rune.
  No `string`, no `rune`, no `complex`. Source and identifiers are ASCII
  (non-ASCII bytes only inside literals and comments, carried verbatim).
- **Two pointers**: `@T` managed (copy = refcount++), `*T` raw (plain
  address, C-style). **Two slices**: `@[]T` managed-owning (4 words), `*[]T`
  raw borrow (2 words); bare `[]T` is illegal. `@X → *X` decays implicitly
  (borrow); never the reverse. Interface values are `*I` / `@I`, function
  values `*func(int) int` / `@func(int) int` — bare `I` / `func(...)` are not
  value types. The `@`/`*` prefix always means owned/borrowed.
- Strings are char slices: a literal is `[N]readonly char`, defaulting to
  `@[]readonly char` (free view of static data); `@[]char` copies; no NUL
  terminator; adjacent literals concatenate at compile time; no `+`.
- No `map`, `append`, `cap`, or `copy` — library concerns (`make_slice(T, n)`
  is the only runtime-sized allocator; containers come from the stdlib via
  generics + `Hashable`).
- `type X U` is Go-style named-distinct (no method inheritance; `cast` to
  cross, except unnamed-composite underlyings assign freely); `type X = U` is
  an alias; `type X` forward-declares opaquely. Package-level only. Enums =
  `type` + `const`/`iota`, as in Go.
- `readonly` is a prefix type modifier binding to the type on its right
  (`*readonly int` = mutable handle, read-only int). Adding
  element-`readonly` is implicit; dropping needs `cast`. `const` is compile-time **scalars only**; immutable non-scalar
  storage is `var x readonly T`.
- Zero values as in Go; but `nil` is assignable **only** to pointers and
  function values — **slices and interface values are never nil** (a zero
  slice is empty).

## Memory

- Copy of a managed value = acquire; scope exit = release; destructors run
  **deterministically** at the last release — this replaces `defer` (there is
  none). Refcounts are never elided across function boundaries (dual-mode
  contract); reducing traffic is an ownership choice (borrow with `*T`), not
  an optimizer's job.
- Temporaries die at **end of statement**: `foo(@[]int{1,2,3})` is fine;
  `var s *[]int = @[]int{1,2,3}` dangles on the next line.
- **Cycles leak** (user error; break with raw pointers). A raw borrow outliving
  its owner is use-after-free — UB, exactly like C. Everything else is defined:
  bounds checks trap, over-release aborts, allocations are zero-initialized.
- Managed pointers come only from `make`/`box` (never `&`); a returned raw
  slice from an allocating function is a classic bug — return `@[]T`.

## Packages & program

- A package = directory of `.bn` files + a `.bni` interface file.
  **Visibility = `.bni` membership; capitalization means nothing.** Generic
  functions ship their bodies in the `.bni`; opaque types export as bare
  `type Foo`. `expose "pkg/x"` re-exports a whole package by identity.
- Package clause and imports use path strings; qualifier = last segment or
  alias; no dot-import; import graph acyclic.
- No `init()`. Package-level `var`s initialize in dependency order — but only
  **direct** reads order them (reads inside called functions don't). `main` is
  `func main()`, args come from the `os` library. `#!` shebang + `bni` run
  a file as a script. `#[build(is(os, "linux"))]` gates files/decls per target.

## Interfaces & generics

- **Nominal.** `impl T : Iface` is required — matching methods are never
  enough; even a user-declared empty interface needs an impl. Only built-in
  `any` is universal. No orphan rule: the impl may live in any package that
  sees both (methods stay in the type's package).
- Construction needs a pointer-shaped source (`&t`, `@T`, or `box(t)` for
  `@Iface`) and **borrows** — a stored `*any` sees later mutations of its
  source. A plain value where a raw `*Iface` is expected auto-borrows (an
  implicit `&`): an addressable value anywhere `&x` is legal; a
  literal/expression result only at argument and `var`/`:=` positions.
- Assertions carry a mandatory recovery kind — `v.(@T)` retain / `v.(*T)`
  borrow / `v.(T)` copy (a raw `*I` source can't yield `@T`). Comma-ok never
  aborts; the bare expression form aborts on a miss, and there is **no
  recover**. Matching is exact nominal identity (`Celsius` ≠ `float64`;
  `List[int]` ≠ `List[uint]`); slices match as structural spellings
  (`@[]char` ≠ `@[]readonly char`). Type switch: `switch x := v.(type) { … }`,
  no `case nil` — test `present(v)` for "never set"; a boxed nil pointer is
  present (typed-nil).
- Generics **monomorphize** with **explicit** type arguments — `Sort[int](xs)`,
  no inference. A constraint is one named interface (or `any`), satisfied
  nominally by an impl; constraint calls compile to direct calls. Canonical
  constraints live in `pkg/builtins/lang`: `Stringer`, `Comparable`
  (`Compare`, not `<`, orders generic values), `Orderable`, `Hashable`.
  Methods on generic types bind the type's params (`func (v *Vec[T]) Get(i int) T`);
  methods can't add their own.

## Control flow & expressions

- `for` is the only loop: `for {}` / `for cond {}` / `for i := 0; …; i++ {}` /
  `for v in xs {}` — range uses **`in`**, over slices/arrays only, and a
  single variable is the **value**, not the index (`for i, v in xs` for both).
- No `goto`, no labels (no labeled break/continue), no `fallthrough` (cases
  never fall through), no `if`/`switch` init clause, no `defer`, no `recover`.
- Functions: no named results; every param typed individually (no `a, b int`);
  multiple returns and `x, y := f()` as in Go. A result-returning function
  needs a *syntactically* terminating tail — add the final `return` even when
  the branches look exhaustive. Variadic `...T` arrives as a raw `*[]T`
  borrow; spread `f(s...)` is exclusive and takes a slice (`arr[:]...`).
- Closures capture **by value** (snapshot); share state via a captured
  pointer; capturing `*func` lives on the stack (must not escape), `@func`
  heap-allocates. Recursive closures don't work — use a named function.
- Strict typing: operands of a binary op must be the *same* type — not even
  untyped-int→float coerces (`var x float64 = 3` errors; write `3.0`).
  `cast(T, v)` converts (and never launders constants: `cast(uint8, 256)` is
  a compile error); `bit_cast` reinterprets. `~` is complement, `^` XOR-only.
  **Precedence matches neither C nor Go**: distinct C-style levels
  (`* / %` > `+ -` > `<< >>` > `&` > `^` > `|`) but with ALL comparisons
  binding loosest (like Go, unlike C) — so `x << 1 + 2` is `x << 3` (unlike
  Go) and `a & b == c` is `(a & b) == c` (unlike C); parenthesize.
- Defined-everything arithmetic: overflow wraps; `/ 0`, `MIN/-1`, negative
  shifts panic; over-wide shifts give 0/sign-fill; float→int **saturates**
  (NaN → 0); float compares are IEEE (`x != x` tests NaN). `unsafe_*`
  builtins skip the guards.
- `:=` **rebinds silently** — no "one new variable" rule. Assignment is a
  statement; `x++`/`x--` are postfix statements.
- Comparability: `==` for scalars, pointers (incl. `p == nil`), and
  aggregates whose parts all compare. Slices, interface values, and function
  values **never** compare — use `len(s) == 0`, `present(x)` (is it set? —
  the only test for function values), and `same(a, b)` (same referent — the
  sentinel test; pointers, slices, and interface values only).

## Errors, panics, builtins

- Errors are values: `v, err := f(); if present(err) { return err }`
  (stdlib `@errors.Error`). `panic(msg)` — one `*[]readonly char` argument —
  aborts the program; a small defined set of runtime faults (bounds,
  divide-by-zero, failed bare assertion, nil-interface dispatch…) also
  aborts. Nothing is catchable.
- Builtins are **keywords**: `make(T)`→`@T` · `make_slice(T, n)`→`@[]T` ·
  `box(v)`→`@T` · `cast` · `bit_cast` · `len` · `sizeof`/`alignof` ·
  `present` · `same` · `unsafe_index`. There is **no predeclared
  `print`/`println`** — output is the `fmt` library
  (`fmt.Print`/`Println`/`Printf`); `panic` is the one predeclared function.

## Top traps (all compile-or-run differently than a Go eye expects)

1. `var s *[]int = @[]int{…}` — dangling at the next statement (temporary
   died); pass the literal directly or bind `@[]T`.
2. Closure captured a variable? It's a **snapshot** — mutations don't flow
   either way; capture a `@int`/pointer to share.
3. Right method set, no `impl` → does not satisfy the interface.
4. `v := x.(*T)` aborts on a miss; use `v, ok := x.(*T)`.
5. `x, err := …; x, err := …` — the second `:=` silently rebinds (no Go
   redeclare check).
6. `for v in xs` — `v` is the element, not the index.
7. `s == nil` / `err == nil` / `f == g` don't compile — use `len(s)`,
   `present(x)`, or `same(a, b)` (`present` is the only test for function
   values; `same` covers pointers/slices/interface values).
8. `x << 1 + 2` is `x << 3` — shift binds looser than `+` here.
9. A `*[]char` return from a function that allocated it borrows a dead
   temporary — return `@[]char`.
10. Package var init: only **direct** reads of other vars order
    initialization; a read hidden in a called function may see a zero.
