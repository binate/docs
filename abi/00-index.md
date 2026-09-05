# Binate ABI Specification — index

The **application binary interface (ABI) specification** for the Binate
toolchain: the per-target binary contract *beneath* the
[language specification](../spec/00-index.md) — calling conventions, symbol
naming and linkage, object-file conventions, the C-interop boundary, and the
function-value dispatch seam that compiled code, the bytecode VM, and C code
all meet on.

The two specs divide the subject deliberately:

- The **language spec** owns everything a Binate *program* can observe:
  type **layout** (§7.13 — "the cross-mode ABI contract"), the refcount
  ownership contract at call boundaries (Ch.18), the cross-mode master
  invariant (§2.4 `conf.cross-mode`), variadic erasure
  (§10 `func.variadic.identity`), and the `bn_entry`/`bn_init` glue-symbol
  contract (§17 `prog.entry.glue`). This spec **cites** those rules and never
  restates them.
- The language spec deliberately refuses to own this layer: §7.13's latitude
  taxonomy classifies calling-convention register choices and binary formats
  as **backend-private**, and §21.4 classifies symbol decoration as
  **implementation-defined** with a documented scheme. That refused space is exactly **this spec's subject**: it pins the
  implementation's concrete choices so that backends, the VM, C callers, and
  external tools can interoperate against a written contract instead of
  against one another's source code.

## Documents

| Ch | Document | Contents |
|----|----------|----------|
| 1 | [Scope and model](01-scope-and-model.md) | What this spec governs; the three convention layers; targets; stability |
| 2 | [Calling convention](02-calling-convention.md) | The internal direct-call convention: argument/return passing per target |
| 3 | [Dispatch convention](03-dispatch-convention.md) | The function-value / interface / cross-mode shim seam |
| 4 | [C boundary](04-c-boundary.md) | `__c_call` / `#[c_export]` / `__c_entry` / `__c_global` at the binary level |
| 5 | [Symbol naming](05-symbol-naming.md) | The `bn_` mangling scheme, decorated families, reserved names |
| 6 | [Linkage and object format](06-linkage-and-object-format.md) | Bindings, sections, relocations, linker resolution, startup |
| 7 | [The runtime at the ABI level](07-runtime-abi.md) | How compiled code reaches `pkg/builtins/rt`; what is linkable and what is not |

## Status

> **Status:** normative for the current toolchain · **Maturity:** Provisional
> (documented and implemented, **not declared stable** — see §1.4
> `abi.scope.stability`) · **Rule-ID prefix:** `abi`

Rule-IDs follow the language spec's declaration grammar (`conventions.md`)
under the single prefix `abi` (`abi.<area>.<name>`), chosen so the two specs'
ID namespaces cannot collide. They are **not yet** listed in the language
spec's §4.5 prefix table nor extracted into `rule-ids.txt`; wiring the ABI
spec into that apparatus is a tracked follow-up decision.

## Relationship to conformance

Everything here binds **per target**: a rule holds for the named target(s) and
both execution modes on that target, per the master invariant
(§2.4 `conf.cross-mode`). Where the current implementation is known to deviate
from a rule, the rule carries a `> _Status._` note naming the deviation — the
rule states the contract; the note tracks the implementation.
