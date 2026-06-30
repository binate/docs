# 19. Execution Model: the Abstract Machine and Dual-Mode Interop

> **Status:** mixed · **Maturity:** the dual-mode contract is Stable; full in-process embedding is a GOAL, not realized (D2)  
> **Rule-ID prefix:** `exec`

Binate's defining feature is **dual-mode execution**: every program runs either
**compiled** to native code or **interpreted** by a bytecode virtual machine, and
the two modes are designed to **interoperate**. This chapter defines the abstract
machine (§19.1), the two execution modes (§19.2), the dual-mode contract (§19.3),
the function-value interop seam (§19.4), the enumerated cross-mode divergences
(§19.5), and the status of in-process embedding (§19.6).

For the dual-mode dispatch semantics, prose is supplemented by an **operational**
description over an abstract machine; where both are given, **the prose is
authoritative** (§4.6).

## 19.1 The abstract machine

`exec.machine` — A program's behavior is defined over an **abstract machine**:
a single **shared heap** of managed allocations carrying reference-count metadata
(§18), a store of local and global variables, and a **call primitive** that both
execution modes implement identically. The machine is **single-threaded** (§14.14).
A program's meaning is defined over this machine **independently of execution
mode** — the two modes are two realizations of the same machine, not two
languages.

`exec.same-ir` — The two modes share a single front end: a source program is
parsed and type-checked once into one typed intermediate representation, and that
IR is then either lowered to native code (compiled) or lowered to bytecode and
executed (interpreted). The modes differ **only in how an IR operation is
realized**, never in what the program means.

## 19.2 The two execution modes

`exec.modes` — A conforming implementation provides one or both of:

- **Compiled** — the program is translated to a native binary (through a
  general-purpose code generator and/or a direct native backend) and executed by
  the host.
- **Interpreted** — the program is executed by a **bytecode virtual machine**: the
  shared IR is lowered to a flat bytecode and run by a dispatch loop.

Both modes **validate the whole program before a non-interactive run** (§17.1; an
interactive interpreter may defer per input) and run the
same initialization-then-`main` entry sequence (§17.3). Each mode that an
implementation provides independently produces the program's defined behavior.

`exec.vm.runtime-floor` — Even under the interpreter, the **runtime and
foreign-function floor is native**: the runtime package (`pkg/builtins/rt`, whose
manifest is the subject of §20.2 — e.g. reference counting, allocation, process
exit) and any function reached through the C boundary (`__c_call`, §16.9, which
includes the host I/O primitives) execute as native code, reached from the
bytecode through the same function-value mechanism as any other call (§19.4).
The interpreter interprets everything **above** that floor.

## 19.3 The dual-mode contract

`exec.contract` — Where a target supports **both** modes, they **agree exactly**
on the observable layout and behavior of every program — the **cross-mode
agreement** invariant (the master ABI invariant of Ch.2 and Ch.21). The two
engines are **co-equal implementations**. This agreement rests on three
prerequisites:

`exec.contract.types` — Both modes use the **same type system and the same static
rules**; only the **timing** of validation differs (the compiler checks up front;
an interactive interpreter may defer, §17.1). A program is accepted or rejected
identically in both modes.

`exec.contract.layout` — Both modes use the **same heap, the same reference
counting (§18), and the same memory layout for every type** — structs, arrays,
raw slices and managed-slices, managed-pointer headers, interface values, and function
values — with **no marshalling** at the boundary. Memory layout is therefore a
**language-level contract** (§7.13), identical across **every** compiler backend
**and** the interpreter; any layout divergence is **silent data corruption**.
This is the keystone that makes the two modes share one heap.

> _Note._ "Same layout" pins field **positions and sizes**; a field's *value* may
> still differ per mode where the value is **self-describing**. The one sanctioned
> case is a `@[]readonly char` literal's `backing` word, whose form realizes the
> literal's environment-lifetime — immortal (null backing) when compiled, an owned
> VM-interned allocation when interpreted — an accepted mode-specific realization,
> not a layout divergence (`type.layout.slice-managed.backing`, §7.13).

`exec.contract.errors` — Errors are **values**, not exceptions (§14.14): there is
**no stack unwinding** to bridge across the mode boundary, so a call that crosses
modes is an ordinary call returning ordinary values.

`exec.contract.scope` — The agreement binds the **result** of every defined
operation. Two things are **outside** it: an **undefined** operation (Ch.21) is
unconstrained and may behave differently in each mode; and a **defined abort**
whose observable *form* is target/mode-dependent (e.g. nil-interface dispatch,
§19.5) guarantees the *abort*, not its precise form. The implementation-defined
choices the two modes must nonetheless **agree on** for a target (notably word
size) are catalogued in Ch.21.

## 19.4 Function-value interop

`exec.interop.funcval` — A **function value** (§10.8) is the seam between modes.
The caller is **oblivious** to whether the callee is compiled or interpreted: it
calls **through** the value, and the only cost of crossing modes is **one
indirection**, paid only at the boundary. The bridge translates **calling
conventions**, never types or layout (which already agree, `exec.contract.layout`).

`exec.interop.call` _(operational)_ — In the abstract machine a function value is
a callable carrying the information needed to invoke its target and to destroy it:

```
call(fv, args):
    if fv targets compiled code:   invoke its native entry with args
    if fv targets interpreted code: invoke a trampoline that re-enters
                                    the interpreter on its body with args
```

A managed function value's (and any managed object's) **destructor** is reached
through a **type-independent handle**, so an object created in one mode is
destroyed correctly when its last reference is released in the **other** mode —
the cross-function reference-count operations are never elided (§18.7), which is
what keeps the shared heap consistent across modes.

`exec.interop.self-describing` — Every managed object carries its own management
information: the allocation header `{refcount, free_fn}` (§18.2) deallocates it,
and its destructor is reached mode-independently — for an ordinary `@T`/`@[]T`
through a static, type-determined destructor handle, and for an interface or
function value through the embedded dispatch table's destructor slot (§7.13). So
**neither mode needs special knowledge of the other's objects**: an object frees
itself, dispatches its methods, and reports its presence the same way regardless
of which mode created or holds it. The set of runtime functions a generated
program may call (the **runtime function manifest**) is the runtime contract whose
home is §20.2 (not yet authored).

## 19.5 Cross-mode divergences

`exec.divergence` — The contract (§19.3) is the target. Three kinds of cross-mode
difference are distinguished:

- **Mode-dependent form of a defined abort** (accepted). Some **defined**
  non-recoverable panics (§17.5) have an observable **form** that is target- or
  mode-dependent, even though the *fact* of the abort is guaranteed. Dispatching
  through a **nil interface value** (`iface.dispatch.nil`, §11.11) is the example:
  it faults silently in compiled native code but reports a diagnostic and exits
  under the bytecode VM (and, on a target with no memory protection, may not fault
  at all) — so the two forms are pinned by **separate** conformance tests per mode.
- **Undefined behavior** (accepted, undefined regardless). The raw-pointer /
  `unsafe_*` / `bit_cast` escape hatches and a use-after-free of a raw borrow
  (§18.7) are **undefined** (Ch.21); their behavior is not constrained and may
  differ across modes (and within a mode).
- **Permanent carve-out** (intentional). The bytecode VM performs **no
  foreign-function calls**: `__c_call` (§16.9) is a **compiled-mode-only** facility
  and will not be interpreted. Interpreted code that needs functionality otherwise
  obtained from C is supplied a Binate implementation instead. This is a
  deliberate, permanent boundary, not a pending feature.
- **Tracked defects** (to be fixed). Where the two modes currently disagree on
  **defined** behavior, that is a non-conformance to be fixed, not sanctioned
  latitude. (`panic(msg)` previously diverged — a **no-op** in the bytecode VM,
  and a message-discarding abort when compiled — but now **aborts with its
  message in both modes** (`builtin.panic.vm-noop`, §15.7, §17.5).) The remaining
  cases are bounded realization limits of the interpreter — its **reflection
  accessor** for non-built-in packages, and a cap on the **argument count** of a
  cross-mode function-value call (the general cross-mode dispatch mechanism
  itself is in place).

## 19.6 In-process embedding (a goal)

`exec.embedding.contract-vs-goal` — Two things must be kept distinct:

- **The dual-mode contract is design-of-record and Stable** (§19.3): the
  function-value unification mechanism and the identical-layout prerequisite are
  fixed, and each execution mode an implementation provides passes the conformance
  suite **individually** (the same programs produce the same observable output
  whether compiled or interpreted).
- **Full seamless in-process embedding is a GOAL, not yet realized.** A single
  running binary in which compiled and interpreted functions call each other
  **live** over one shared heap — with mixed-mode dispatch tables and runtime
  hot-swapping/redefinition — is the long-term aim; the current interpreter binary
  is a **partial** step toward it. The spec describes the execution model and the
  dual-mode contract; it does **not** assert a shipping in-process embedded
  interpreter.

`exec.embedding.api` — The concrete **interpreter embedding API** — how a host
program instantiates the interpreter as a library, registers compiled symbols, and
drives evaluation — is a **separate specification**, out of scope here (Ch.1).

`exec.hosted` — The bytecode VM and the interactive REPL are **hosted** facilities.
A **freestanding** (bare-metal) target may be a conforming **compiled-only**
implementation with no interpreter and no REPL (the hosted-vs-freestanding split,
Ch.2); the dual-mode contract (§19.3) governs wherever both modes coexist.
