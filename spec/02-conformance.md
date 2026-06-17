# 2. Conformance

> **Status:** normative · **Maturity:** Stable (the cross-mode contract; full in-process embedding is a goal — §2.4, Ch.19)  
> **Rule-ID prefix:** `conf`

This chapter defines what it means to **conform** to this specification: what a
conforming program is (§2.1), what a conforming implementation is (§2.2), the
**co-equality** of the two execution modes (§2.3), the **cross-mode agreement**
invariant that binds them (§2.4), the **hosted/freestanding** split (§2.5), and
the distinction between an implementation's **conformance** and the language's
**design stability** (§2.6).

## 2.1 Conforming program

`conf.program` — A **conforming program** is **well-formed** — it satisfies every
static rule this specification marks diagnosable (the **Constraints** of each
chapter) — and its observable behavior depends only on behavior this
specification **defines**. A program whose result depends on **undefined**
behavior (Ch.21) is **not** conforming. A program whose result depends on
**unspecified** or **implementation-defined** behavior (Ch.21) is conforming but
**not portable**: its behavior may differ between conforming implementations (or
targets), even though any one conforming implementation accepts and runs it.

`conf.program.diagnostics` — A conforming program contains **no** Constraint
violation. Whether a particular implementation happens to accept a
Constraint-violating program does not make that program conforming.

## 2.2 Conforming implementation

`conf.implementation` — A **conforming implementation** accepts every conforming
program and realizes the behavior this specification defines for it, and issues a
**diagnostic** for every Constraint violation the specification requires to be
diagnosed. Binate implementations emit **errors only** — there are no warnings
(advisory analysis is the province of separate tooling, not the
compiler/interpreter; Ch.15).

`conf.implementation.conformant` — An implementation is **conformant with respect
to a rule** when its observable behavior on that rule matches the specification. A
**defect** — a miscompile, a missing required diagnostic, or a divergence on a
defined operation — makes the implementation **non-conformant** for that rule; it
does not alter the rule itself (§2.6).

`conf.implementation.timing` — The **timing** of validation may differ by mode: a
batch compiler validates a whole translation unit before it runs; an interactive
interpreter may validate incrementally, per input (§17.1). The set of programs
accepted and the diagnostics required are the **same** across modes — only *when*
they are reported differs.

## 2.3 The two execution modes are co-equal

`conf.modes` — Binate is **one** language with **two** realizations: a
**compiled** mode (native code, through a general-purpose code generator and/or a
direct native backend) and an **interpreted** mode (a bytecode virtual machine).
They are **co-equal conforming implementations of the same semantics** (Ch.19) —
neither is the reference against which the other is measured; each independently
produces the program's defined behavior. An implementation **may** provide one
mode or both; where it provides both, §2.4 binds them.

## 2.4 Cross-mode agreement (the master ABI invariant)

`conf.cross-mode` _(normative)_ — Where an implementation provides **both** modes
for a target, the two **shall agree exactly** on the **observable layout and
behavior** of every program on that target. This is the language's **master ABI
invariant**: the two modes share one heap, one set of type layouts (§7.13), one
reference-counting discipline (Ch.18), and one function-value calling seam
(§19.4), so a value created in one mode is used and destroyed correctly in the
other. Every **implementation-defined** choice (Ch.21) — notably the **word
size**, and the byte layout of every type — **shall be identical** in both modes
for a target; any divergence is **silent data corruption**, not latitude.

`conf.cross-mode.scope` — The agreement binds the **result** of every **defined**
operation. Two things lie outside it: an **undefined** operation (Ch.21) is
unconstrained and may differ between modes; and a **defined abort** whose
observable *form* is mode- or target-dependent (for example nil-interface
dispatch, §19.5) guarantees the *abort*, not its precise form. The full
enumeration of what the modes must agree on, and what they need not, is §21.3.

> _Note._ Full **in-process embedding** — a single running binary in which
> compiled and interpreted functions call one another live over one shared heap —
> is a long-term **goal**, not a claim about the current implementation (§19.6).
> The cross-mode contract above is design-of-record and Stable, and each mode an
> implementation provides passes the conformance suite **individually**.

## 2.5 Hosted and freestanding conformance

`conf.hosted` — A **hosted** implementation (Ch.3 `term.hosted`) targets an
environment that provides host facilities — a process model, a command line, and
I/O. It may provide both execution modes, the interactive REPL, and the
host-facing tier-0 surface (the hosted portion of `pkg/builtins/rt`, §20.2).

`conf.freestanding` — A **freestanding** (bare-metal) implementation (Ch.3
`term.freestanding`) targets an environment with **no** console, filesystem,
process model, or threads. It is a **conforming** implementation even though it
is **compiled-only** — the bytecode VM and the REPL are hosted facilities (§19.6)
— and provides only the freestanding tier-0 surface. The **core language** (this
specification, including the tier-0 packages of Ch.20) is defined so that it
remains implementable on a freestanding target; the **standard library** (a
separate specification, §1.4) layers host-dependent facilities selectively per
target.

`conf.host-dependent` — Behavior a freestanding target cannot provide —
command-line arguments (§17.3.1), host I/O — is **host-dependent**: it is not part
of the core language, and a conforming implementation need not provide it. A
program that uses only the core language and the freestanding tier-0 surface is
portable to both kinds of target.

## 2.6 Conformance versus language stability

`conf.status` — Two **orthogonal** axes describe the state of any feature (Ch.3,
[`conventions.md`](conventions.md)): its **language-design stability** (Stable /
Provisional / Draft / Reserved — is the *rule* fixed?) and its
**implementation-conformance** (does the current toolchain *realize* the rule?).
The axes are independent: a Stable rule may have an open implementation defect,
and an implemented feature may still be Provisional in design.

`conf.defect` — A known **defect** makes the **implementation** non-conformant for
the affected rule; it does **not** make the language rule unstable, unspecified,
or undefined. The specification states each rule **normatively** in its home
chapter, and **Annex C** (the status ledger, cross-referenced to the project
defect tracker) records the non-conformances. A reader writing portable Binate
relies on the **rule**; a reader targeting a particular toolchain version
consults Annex C for where that version falls short.
