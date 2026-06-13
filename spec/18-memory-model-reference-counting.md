# 18. Memory Model: Reference Counting and Object Lifetime

> **Status:** mixed · **Maturity:** Stable axioms (the ownership-transfer convention is DECIDED); move is an optimization, not a guarantee  
> **Rule-ID prefix:** `mem`

Binate manages memory by **reference counting** — not a garbage collector, and
not ownership/borrowing. A **managed** value (`@T`, `@[]T`, `@func`, `@Iface`)
owns a reference to a reference-counted allocation; a **raw** value (`*T`,
`*[]T`, `*func`) **borrows** and holds **no** count. This chapter defines the
object lifecycle (§18.1–§18.2), copy and assignment semantics (§18.3), temporary
and scope lifetime (§18.4), ownership transfer (§18.5), the move optimization
(§18.6), and the no-leak contract with its user-error escape hatches (§18.7). The
byte layout of the management header is §7.13; this chapter specifies behavior.

Where a rule is most error-prone, prose is supplemented by an **operational**
rule over an abstract machine state — a heap of managed allocations with a
reference count `rc(o)` per allocation `o`. Where both are given, **the prose is
authoritative** (§4.6).

## 18.1 The reference-counting invariant and the axioms

`mem.invariant` — The governing invariant is **`rc(o) == 0` means dead**: every
live reference to a managed allocation `o` is reflected in `rc(o)` (except an
**immortal** static-managed allocation, whose count is a fixed sentinel — §18.2).
An allocation
with any live reference has `rc(o) > 0`; when `rc(o)` reaches 0 the allocation is
destroyed (§18.2). A fresh allocation (`make`, `make_slice`, `box`) begins with
`rc = 1`.

`mem.axioms` — The model rests on five axioms; the compiler emits reference-count
operations so they always hold:

1. **Alive → positive count.** A managed allocation with any live reference has
   `rc > 0`. After `make(T)`, `rc = 1`.
2. **Zero count → destroy.** When `rc` reaches 0, the destructor **must** run
   (release managed fields, then free); this is not optional and cannot be
   skipped.
3. **Copy → acquire.** Whenever a managed value is **copied** — variable
   declaration, assignment, argument passing, return, and field or element store
   — the copy is *acquired* (its referent's count is incremented, or, for an
   aggregate, its managed fields are). There are no exceptions (the "slow path").
4. **Move → release the source.** The only way to elide a copy is a **move**,
   which transfers the existing reference to the destination and leaves the
   source with no live reference to release. Moves are an **optimization** (§18.6).
5. **Assignment is copy-then-destroy.** `x = v` acquires `v` and then destroys
   the value previously in `x`, **in that order** (§18.3).

`mem.managed-vs-raw` — A **managed** value owns one reference for as long as it is
live; copying it adjusts the referent's count (§18.3). A **raw** value is a
borrow that holds **no** count — it does not keep its referent alive and does not
participate in reference counting (§7.8). Returning a freshly-allocated raw slice
or pointer from a function is therefore almost always wrong: the allocation it
borrows is released when the owning managed value dies.

## 18.2 Object lifecycle: allocation, header, destruction

`mem.header` — Every managed allocation carries a two-word **management header**
— `{refcount, free_fn}` — stored immediately before the payload, at a negative
offset (the layout is `type.layout.header`, §7.13). There is **no destructor
pointer** in the header: a value's destructor is determined by its static type
(or, for an interface value, carried in its vtable), while `free_fn` is the
allocator's deallocation step. The payload of a fresh allocation is
**zero-initialized**.

`mem.refinc` — Acquiring a reference increments the count. Acquiring a `nil`
reference, or one to an **immortal** allocation (`mem.immortal`), is a no-op.

`mem.refdec` _(operational)_ — Releasing a reference is, for a non-nil, non-immortal
allocation `o`:

```
rc(o) := rc(o) - 1
if rc(o) == 0:
    destroy(o)      # run o's destructor (mem.destructor)
    free(o)         # o's free_fn deallocates the header+payload
```

Releasing `nil` or an immortal allocation is a no-op. Releasing an allocation
whose count is **already 0** is a defined abort (an over-release / double-release
detector), not silent corruption.

`mem.destructor` — When `rc` reaches 0, the **destructor** runs **before** the
allocation is freed. It **recursively releases** the allocation's managed
contents — each managed field of a struct, each managed element of an array, and
— when a managed-slice **backing's** last reference is released — each managed
element across the **backing length** (§7.6, §7.13) — which may cascade further
destructions. The freeing step then returns
the memory. Destruction is **deterministic**: it happens exactly when the last
reference is released, not at some later collection point.

> _Note._ A managed-slice's element destruction is tied to the **backing's** last
> reference: sub-slices share one backing and one count, so the elements are
> released once, when that shared backing's count reaches 0 (§7.6). A length-0
> slice has **no backing** (§7.7) and therefore no reference and a no-op
> destructor.

`mem.immortal` — **Static-managed** allocations — values emitted into the program
image rather than heap-allocated, such as string-literal backing (§6.6) and
package descriptors (§16.6) — carry an **immortal** sentinel count (a negative
refcount). Acquire and release both short-circuit on an immortal count (no
increment, no decrement, no free), so such a value is never mutated and never
freed.

## 18.3 Copy semantics and assignment

`mem.copy` — Per Axiom 3, every place a managed value crosses into a new
location — `var`/`:=` initialization, assignment, argument passing, `return`, and
stores into struct fields and slice/array elements — **acquires** it: a managed
scalar's referent is reference-incremented, and an aggregate with managed fields
is copied field-wise (acquiring each managed field). This is unconditional in the
slow path; a move (§18.6) may elide the acquire only for an expiring source.

`mem.assign.copy-then-destroy` _(operational)_ — A store into an already-occupied
managed location follows **acquire-before-release**:

```
acquire(v)             # retain the new value first
old := *slot
release(old)           # then release the prior occupant (mem.refdec)
*slot := v
```

Acquiring before releasing makes a self-aliasing store safe: in `x = x` or
`s[i] = s[i]` the new value is the old value, and retaining it before the release
prevents it from being freed mid-store (the counts net to zero). Initializing a
**fresh** location (a `var`/`:=` declaration, a literal element, a range-variable
bind) has no prior occupant and so **skips the release** half.

## 18.4 Temporary and scope lifetime

`mem.temporary` — A managed value produced while evaluating a statement but not
bound to a named location (a `make`/`box`/`make_slice` result or a managed call
result used as a temporary) is an unnamed local of that statement's implicit
scope; it is **released at the end of the statement** (§9.7). A discarded managed
call result is therefore released, not leaked.

`mem.scope-exit` — A managed local is released when its **block** scope exits
(§9.5). On a normal exit, each managed local declared in the block is released; on
an exit via `return`/`break`/`continue`, the terminating construct performs the
equivalent release (the `return` path releases all live managed locals as it
unwinds, §18.5). A managed local created and dropped inside a loop body is thus
balanced each iteration.

> _Note._ The order in which a scope's managed locals are released is not
> observable: a destructor's only effect is to release further references (§18.2),
> so release order does not affect the result. The implementation releases them in
> declaration order.

## 18.5 Ownership transfer

`mem.ownership.transfer` — Each managed value carries its reference count as the
number of live references. When a value is passed between contexts — **return**,
**assignment**, **argument** — ownership of one reference is transferred, leaving
the invariant (`mem.invariant`) intact on both sides.

`mem.return` — A `return` of a managed value delivers **exactly one** owning
reference to the caller; after the return the caller owns that reference. The
callee's own locals are released as it unwinds (§18.4). Two consequences worth
naming:

- Returning a **package global** (or any value that outlives the function) is a
  **copy**: it acquires a new reference for the caller (the global keeps its own).
- Returning a **freshly allocated** value transfers its sole reference (a move,
  §18.6) — no extra acquire.

`mem.param` — For the duration of a function body, the callee **owns** a reference
to each managed parameter, which it releases at scope exit (unless the parameter
is returned, `mem.return`). The **caller** passes a **borrow** — its own reference
is unaffected by the call — and each side's references are independently balanced.
(Mechanically, the callee acquires that reference on entry for `@T`/`@[]T`/`@func`;
for an `@Iface` parameter the caller instead delivers exactly one reference at the
call site, which the callee releases at exit. The observable net contract is the
same either way.)

`mem.borrow-arg` — A managed value passed where a **raw** parameter is expected
(`@T` → `*T`, §8.4) is passed as a **borrow**: no count is taken, and the value
must remain alive for the **duration of the call**, which the caller's own
reference guarantees.

## 18.6 The move optimization

`mem.move` — A **move** transfers an existing reference from source to destination
without an acquire/release pair, eliminating a redundant increment-then-decrement.
A move is valid **only when the source is expiring** — it will not be used again
— which holds for a statement temporary and for the last use of a local at a
`return`. It is **never** valid for a value used again, a shared reference, or a
package global.

`mem.move.optimization` — A move is an **optimization, not a language
guarantee**: the **observable behavior — when an allocation is freed — is
identical** to the slow path; only **intermediate** reference-count values (as
read by reflection) may differ. Whether to expose move as a first-class language
operation is an open question; a `move` built-in has been proposed but is not
part of the language.

## 18.7 The no-leak contract and the escape hatches

`mem.no-leak` _(Constraint)_ — A conforming implementation **must never** generate
code that leaks: every managed allocation that is created is eventually released.
Reference-count operations are **never elided across a function boundary** — the
acquire on a managed parameter and the acquire on a returned value are emitted
unconditionally (the slow path), and a value's destructor is reached through a
type-independent handle — so that a value created in one execution mode and
released in another carries its own counting and cleanup correctly (the dual-mode
interop contract, §19).

`mem.cycles` — Reference counting does **not** collect cycles: a cycle of managed
references keeps its own counts positive and **leaks**. This is **user error**
(Binate is not garbage-collected), and the only acceptable "leak" a program may
exhibit. **Raw** pointers are the sanctioned escape hatch for breaking a cycle —
an unowned reference that holds no count (and carries no safety net: the
programmer ensures the referent outlives it).

`mem.raw-uaf` — Using a **raw borrow** (`*T`, `*[]T`) after the managed value it
borrows from has been released is a **use-after-free** — **user error** and
**undefined behavior** (Ch.21), not a compiler defect. An implementation **must
not** suppress a release to prevent such a use-after-free: doing so would trade a
detectable fault for a silent leak, which is worse. The discipline is to own with
a managed value (`@[]T`) anything whose lifetime must extend past the borrow,
rather than to keep a raw view alive (§18.1, `mem.managed-vs-raw`).

`mem.determinism` — Reference counting is **transparent and deterministic**:
cleanup happens at well-defined points (statement end, scope exit, last
reference), with no background collector and no non-deterministic finalization.
The remedy for an unwanted extra reference is a programmer **ownership** decision
(borrow vs own, move a temporary), not a compiler elision pass — cross-function
elision is excluded precisely because it would break dual-mode interop (§19).

> _Open._ Reference-count operations are **non-atomic**, and the language is
> single-threaded (§14.14); whether counts become atomic if shared-memory
> concurrency is added is an open question.
