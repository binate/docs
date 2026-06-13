# 17. Program Initialization and Execution

> **Status:** mixed · **Maturity:** Stable rules; entry/termination are host-dependent, and the closed panic set has flagged dual-mode gaps  
> **Rule-ID prefix:** `prog`

This chapter specifies how a program is validated, initialized, entered, and
terminated: the validation model (§17.1), package initialization (§17.2), the
program entry (§17.3), termination (§17.4), and the closed set of defined
non-recoverable runtime panics (§17.5). Ch.16 (`pkg.acyclic`) requires the package
import graph to be acyclic, which guarantees a well-defined dependency order; §17
specifies how that order is *used*. The annotation system that conditions program
structure is §16.7 (in `16b-build-constraints.md`). The dual-mode execution model
is Ch.19.

## 17.1 The validation model

`prog.validation` — A non-interactive program is **fully validated before any
execution begins**. The whole program (all loaded packages and the entry file)
is parsed and type-checked first; only if validation reports no error does
execution start, via an external call to the entry (§17.3). A program with any
validation error does not run.

`prog.no-forward-decl` — Because validation sees the whole program, **no forward
declarations or prototypes are required**: a declaration may refer to a name
declared later in its package (§9.8). Forward references resolve through the
deferred-validation model rather than ordering constraints.

`prog.modes` — The **same** type system and rules apply in compiled and
interpreted execution; only the *timing* of validation differs (Ch.19). This is
the **retained** model: a source file's declarations are retained and validated
as a whole. (The REPL additionally supports an **immediate** mode — statements
and expressions evaluated as entered, checking their dependencies on demand —
which is an interactive facility, not part of a compiled program; §19.)

## 17.2 Package initialization

`prog.init.order` — Packages are initialized in **dependency order**: a package's
imports are fully initialized before it (the dependency graph is acyclic,
`pkg.acyclic`). Within a package, the package-level `var` initializers run in
**source-declaration order** (across the package's merged files), so a later
global may read an earlier one's initialized value.

`prog.init.vars` — Initialization runs each package-level `var x T = e` as the
assignment `x = e`, in the order above. A `var` declared without an initializer
is zero-initialized (§9.2) and does no work at init time. A **blank** (`_`)
global is not initialized (it binds no storage). **Constants** are not part of
initialization: a `const` has no storage and each use is replaced by its value
at compile time (§9.1), so it is never runtime-initialized.

`prog.no-init-func` — There is **no `init()` function** (unlike Go): a package
has no implicit initializer hook beyond the initialization of its package-level
variables. Setup logic that must run before `main` is called explicitly from
`main` (or a function it calls).

> _Note._ A package-level managed (`@T`/`@[]T`) global is a program-lifetime
> value: its initializer (e.g. `make`, `make_slice`) runs once during package
> init, and the global holds an owning reference for the rest of the program
> (§18). Allocating initializers in an imported package run before `main`
> observes the global.

## 17.3 The program entry

`prog.main.package` — Program execution begins in the **`main` package** (the
package given to the compiler as the program). The `main` package requires a
function **`main`** and needs no `.bni`.

`prog.main.signature` — The entry function is **`func main()`** — **no
parameters and no results**. Command-line arguments are not delivered as `main`
parameters, and a return value from `main` is not consumed; argument access and
the process exit code are host-dependent (§17.3.1, §17.4).

`prog.entry.sequence` — On entry, the runtime calls a single synthesized entry
point that (1) runs every package's initialization in dependency order (§17.2),
then (2) calls `main`. This entry point is the runtime's sole entry into Binate
code; all program-startup semantics live behind it.

### 17.3.1 Command-line arguments

`prog.argv` — Command-line arguments, where the host provides them, are reached
through a **library/runtime mechanism** (a tier-0/host package), not through the
core language or a `main` parameter, and not every target has them (a
freestanding target has no command line). The core language defines no `os.Args`
global; argument access is therefore **host-dependent** (Ch.2, hosted vs
freestanding conformance; the providing package, where present, is a tier-0
package, Ch.20).

> _Implementation note._ Neither the existence of `main` in the `main` package
> nor its `func main()` signature is currently enforced by a compiler diagnostic
> — a missing or wrong-shaped `main` fails at link time rather than with a clean
> error (`prog.main.unchecked`, `claude-todo.md`).

## 17.4 Program termination

`prog.terminate` — A program terminates when `main` returns (normal termination)
or when the program calls a runtime **exit** primitive, or when a defined
non-recoverable panic fires (§17.5). The **exit code** and any panic **message**
are **implementation-defined** (Ch.21): a conforming implementation fixes them
for a target, and the compiled and interpreted modes must agree on a target, but
the core spec does not pin their exact values.

> _Implementation note._ In the current implementation, normal termination
> (`main` returns) yields exit code **0** unconditionally — `main` cannot set a
> nonzero code by returning a value (a value-returning `main` is not yet wired);
> a nonzero exit requires the explicit runtime exit primitive. A panic or runtime
> trap exits with code **1** and writes its diagnostic to standard output
> (§17.5).

## 17.5 Defined non-recoverable runtime panics

`prog.panic` — Binate has **no exceptions and no `panic`/`recover`** (§14.14):
recoverable conditions are returned as error *values* (Ch.8/Ch.11). A small,
**closed set** of conditions are **defined, non-recoverable runtime panics** —
they are not undefined behavior, and they cannot be caught; the program
terminates. The set is:

| Panic | Where defined | Diagnostic (current impl) |
|-------|---------------|---------------------------|
| Index / slice out of bounds | §13.9 | `runtime error: index out of bounds: <i> (len <n>)` |
| Integer divide-by-zero | §13.4 | `runtime error: integer divide by zero` |
| Signed `MIN / -1` overflow | §13.4 | `runtime error: integer overflow (MIN / -1)` |
| `make_slice` negative length | §15.2 | `runtime error: make_slice with negative length` |
| Nil-interface-value dispatch | §11.11 (`iface.dispatch.nil`) | (see below — mode-dependent) |
| `panic(msg)` | §15.7 | (see below — currently incomplete) |

`prog.panic.defined` — Each panic in the set is a **defined** abort: the
condition is detected (or deterministically faults) and the program stops; it is
not undefined behavior. The diagnostic text and exit code are
implementation-defined (§17.4). By contrast, **integer overflow wraps** (it is
not a panic, §13.3), and the **unchecked escape hatches** — `unsafe_index`,
`unsafe_div`, `unsafe_rem`, and raw-pointer/`bit_cast` misuse — are **undefined
behavior**, not defined panics (Ch.21). A panic-triggering value that is a
**compile-time constant** is rejected at compile time instead (e.g. a constant
zero divisor is a compile error, §13.4), so the runtime panic applies only to
non-constant operands.

`prog.panic.no-recover` — There is no `recover`; a panic is the program's last
action. A `panic(msg)` expression statement is also a control-flow terminator for
the missing-return analysis (§14.13).

> _Open (dual-mode gaps in `panic`/dispatch)._ Two members of the set are
> realized inconsistently across the execution modes — flagged so the dual-mode
> contract (§19) is not read as already met:
> - **`panic(msg)`** aborts (exit 1) in compiled mode but currently **discards
>   its message**, and is a **no-op in the bytecode VM** (it neither aborts nor
>   prints, and control falls through) — a MAJOR dual-mode gap
>   (`builtin.panic.vm-noop`, `claude-todo.md`). The intended behavior is to
>   abort with the message in both modes.
> - **Nil-interface-value dispatch** aborts with a message in the bytecode VM
>   (`vm: call through nil interface value`) but is a **silent deterministic
>   fault** (a null-vtable dereference) in compiled mode; on a target with **no
>   MMU**, a null dereference does not fault at all, so the guarantee there is
>   effectively a hardware-dependent edge. The *fact* of a non-recoverable abort
>   on nil-interface dispatch is the rule; its observable form is currently
>   target-dependent.
