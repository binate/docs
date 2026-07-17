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
`pkg.acyclic`). Within a package, the package-level `var` initializers **also run
in dependency order**: each runs after the initializers of the package-level vars
its initializer **directly reads** — identifiers named in the initializer
expression, including inside an immediately-invoked function literal — regardless
of declaration position or which file each is in, so such a reference observes the
referenced global's initialized value, not a zero. A package var reached only
**indirectly** — through a call to a named function, or captured by a function
literal that is not immediately invoked — does **not** form an ordering dependency
and may be observed at its zero value. Vars with no ordering dependency between
them run in an unspecified but stable order.

`prog.init.var-cycle` _(Constraint)_ — A **cycle** in these initialization
dependencies (`prog.init.order`) — a var whose initializer depends on its own value
directly or transitively (e.g. `var a = a + 1`, or mutual `var a = b; var b = a`)
— is a **compile error**. Only the direct-read dependencies above form cycle edges;
a read reached only indirectly (through a called named function, or a
not-immediately-invoked function literal) forms no edge, so it is neither ordered
nor diagnosed.

`prog.init.vars` — Initialization runs each package-level `var x T = e` as the
assignment `x = e`, in the order above. A `var` declared without an initializer
is zero-initialized (§9.2) and does no work at init time. A **blank** (`_`) global
binds no storage, so no value is ever stored — but a blank *with* an initializer
(`var _ = e`) still **evaluates** `e` at init time (for its effects, and its reads
still order it after the vars it depends on). **Constants** are not part of
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

`prog.entry.sequence` — On entry, the runtime (1) runs every package's
initialization in dependency order (§17.2), then — for a program — (2) calls
`main`. This init-then-`main` sequence is the runtime's sole entry into Binate
code; all program-startup semantics live behind it. It is realized by the
compiler's entry glue (`prog.entry.glue`, §17.3.2); the build root is `main` for
a program but need not be for other artifacts such as a C library
(`prog.entry.pluggable`, §17.3.2).

### 17.3.1 Command-line arguments

`prog.argv` — Command-line arguments, where the host provides them, are reached
through a **library/runtime mechanism** (a tier-0/host package), not through the
core language or a `main` parameter, and not every target has them (a
freestanding target has no command line). The core language defines no `os.Args`
global; argument access is therefore **host-dependent** (Ch.2, hosted vs
freestanding conformance; the providing package, where present, is a tier-0
package, Ch.20).

> _Note (by design)._ Two facets, two phases. **(1) Shape of a present `main` —
> compile-time.** If the `main` package declares a `func main`, its **signature**
> (`func main()` with no parameters and no results) is checked when *that* package
> is compiled — the `main` package's own compilation sees its own `main`, so a
> wrong-shaped `func main(x int)` or `func main() int` is rejected at compile time.
> **(2) Existence of a `main` package — link-time.** Whether the *program* has a
> `main` package at all **cannot** be determined when a single package is compiled:
> the compiler processes **one package at a time**, and any package may be compiled
> or loaded independently and have its functions called across the
> compiled/interpreted boundary (the dual-mode interop model, Ch.19). So a
> **missing** `main` package (no entry) is a **link-time / program-assembly**
> failure, intrinsic to the separate-compilation model — not a per-package
> compile-time check.

> _Note (script mode — reference tooling; Draft, `proposal-shebang`)._ Where the
> host provides a command line, the reference **source-executing interpreter**
> (`bni` in this toolchain) runs a **single source file as a script** with `bni -x
> <file> [args…]`: `<file>` is taken as the program's **sole source**, and every
> argument **after** it becomes the program's **argv** — the script path as element
> `0`, the user arguments following — delivered through the host/runtime argument
> mechanism (`prog.argv`), rather than being taken as **additional source files** (the default
> multi-file / directory invocation). Combined with the `#!` shebang skip (§5.2
> `lex.shebang`), this makes a `chmod +x` Binate file directly executable; the
> intended shebang is `#!/usr/bin/env -S bni -x` (the `-S` splits the two words, so
> the kernel runs `bni -x <script> <user-args…>`). A bare `#!/usr/bin/env bni`
> (no `-x`) still **parses** — the line is skipped — but in the default mode treats
> trailing arguments as further source files, so an argument-taking script **should**
> use `-x`. This is **host-dependent tooling** (the command line is not part of the
> core language, Ch.2); another host or interpreter may provide a different
> mechanism. Not yet implemented.

### 17.3.2 Entry glue and pluggable platform startup

> _Status (Draft / pending)._ `prog.entry.glue`, `prog.entry.pluggable`, and
> `prog.init.idempotent` are **specified but not yet implemented** — the FFI-export
> feature (§16.9). They generalize `prog.entry.sequence`: the entry becomes pluggable
> package code so the program's startup glue can be written in Binate and a *set* of
> Binate packages can be exposed as a C library. Design: `explorations/design-ffi-export.md`.
> Symbol names (`bn_init`, `bn_entry`) are provisional but the linkage contract is decided.

`prog.entry.glue` — The compiler emits two hardcoded, well-known glue symbols,
**referenceable by literal name** (a linkage-ABI contract, the `bn_` family):
**`bn_init`** runs every package's initialization (`prog.init.order`) over the **build
root's** transitive dependency closure — the build root is `main` for a program and the
facade package for a C library (§16.9), generalizing a `main`-rooted dispatcher — and
**`bn_entry`** = `bn_init()` then `main.main()`.

`prog.entry.pluggable` — The platform entry — a hosted C `main` (capturing `argc`/`argv`),
a freestanding `_start` (placed via a linker-placement annotation, §16.9
`pkg.link-placement`), or a C library's `_init` — is **build-conditional** (§16.8) **package
code** in a tier-0 package (`pkg/builtins/platform_init`, §20 `pkg0.platform-init`), **not
compiler-hardcoded**. Each entry function is an ordinary function (typically `#[c_export]`'d)
that calls `bn_init`/`bn_entry`. The **set of wired-up entry symbols is the build "mode"**:
a `#[c_export("main")]` entry → a hosted program, a `_init` → a C library, a placed `_start`
→ a freestanding image — no separate mode flag. Argument capture (`bn_argc`/`bn_argv`) is that
package's hosted-only, build-conditional code, consistent with `prog.argv`.

`prog.init.idempotent` — `bn_init` (`prog.entry.glue`) is **idempotent**: a run-once guard
makes a second call a no-op, so a host may call more than one C-library `_init` (each
forwarding to the one shared `bn_init`), or re-enter, without double-initializing shared
package globals. The guard mechanism and its storage are implementation-defined.

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
| Negative shift count (runtime) | §13.5 | `runtime error: negative shift count` |
| `make_slice` negative length | §15.2 | `runtime error: make_slice with negative length` |
| Nil-interface-value dispatch | §11.11 (`iface.dispatch.nil`) | (see below — mode-dependent) |
| `panic(msg)` | §15.7 | `panic: <msg>` |
| Failed type assertion, expression form | §11.12 (`iface.assert`) | `runtime error: type assertion failed: <dyn> is not <T>` |

> _Note._ Only the **expression** form of a failed type assertion panics; the
> **comma-ok** form (`v, ok := x.(K T)`) does **not** panic — it yields
> `{recovered, false}`. `<dyn>` is the value's dynamic-type name (or `<unset>` for
> a typed-nil / null-vtable value) and `<T>` the asserted type's name.

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

> _Open (dual-mode gap in dispatch)._ One member of the set is realized
> inconsistently across the execution modes — flagged so the dual-mode contract
> (§19) is not read as already met. (`panic(msg)` previously diverged — a no-op in
> the bytecode VM — but now aborts with its message in both modes.)
> - **Nil-interface-value dispatch** aborts with a message in the bytecode VM
>   (`vm: call through nil interface value`) but is a **silent deterministic
>   fault** (a null-vtable dereference) in compiled mode; on a target with **no
>   MMU**, a null dereference does not fault at all, so the guarantee there is
>   effectively a hardware-dependent edge. The *fact* of a non-recoverable abort
>   on nil-interface dispatch is the rule; its observable form is currently
>   target-dependent.
