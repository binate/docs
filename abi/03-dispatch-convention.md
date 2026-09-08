# 3. Dispatch convention (function values, interfaces, cross-mode)

> **Status:** normative · **Maturity:** Provisional  
> **Rule-ID prefix:** `abi` (area `dispatch`)

Every **indirect** call — through a function value, through an interface
method, or across the compiled/interpreted seam — uses one uniform
convention, distinct from the direct-call convention of Ch.2. It is shared
bit-for-bit by the LLVM backend, all three native backends, and the bytecode
VM; it realizes the language spec's mode-transparent calling seam
(§19.4 `exec.interop.funcval`: the bridge "translates calling conventions,
never types or layout").

## 3.1 The seam

`abi.dispatch.seam` — An indirect call never targets a function's code address
directly. The caller holds a function value `{vtable, data}`
(§7.13.9 `type.layout.func-value`), loads `vtable.call` (slot 1; slot 0 is a
destructor **handle**), and calls it under this chapter's convention. What
`vtable.call` points at — a compiled function's marshalling shim (§3.4) or a
VM trampoline (§3.5) — is invisible to the caller; crossing modes costs
exactly this one indirection.

## 3.2 Shim signatures

`abi.dispatch.shape` — Every `vtable.call` target has one of exactly two
signatures:

- **scalar/void result:** `result(data, slot0, slot1, …)`
- **aggregate result:** `void(retbuf, data, slot0, slot1, …)`

where `data` is the function value's data word passed through verbatim, and
the slots encode the user arguments (§3.3). The aggregate shape is used for
**any** multi-return (regardless of size), for any ABI-named struct or array
result (§2.2, register-coercible ones included), and for any single
aggregate-kind result wider than one word — except that a **zero-size**
result uses the scalar/void shape (no retbuf; §2.2's skip rule extends to
shape selection). The **caller allocates** `retbuf` with at least the result
type's natural size and at least its `AlignOf` alignment; the callee writes
**exactly the natural size** through it and returns nothing in registers.
Space beyond the natural size, if any, belongs to the caller and is not
writable (VM-side callers over-allocate to a whole number of 8-byte words;
other callers allocate the natural size). Multi-return results always use
the retbuf — there is no field-per-register form on this seam.

An interface-method call inserts the receiver as one extra leading slot after
`data`: `result(data, receiver, slots…)` / `void(retbuf, data, receiver,
slots…)`, with `receiver` the interface value's data pointer.

## 3.3 Slot encoding

`abi.dispatch.slots` — The dispatch convention is **all-integer and
positional**: slot *g* occupies the target's *g*-th GP argument register, then
the stack, per Ch.2's GP rules. Per argument type:

- an **aggregate** of any size travels as **one pointer slot** — the address
  of the argument value; the shim loads it and re-marshals to the underlying
  function's direct-call convention. (This includes ≤16-byte aggregates that
  a direct call would pass by value in registers.)
- a **float scalar** travels as its bit image in an integer slot
  (`float32` → 32-bit image, `float64` → 64-bit image); no float register is
  used on this seam. A float scalar **result** of the scalar shape returns in
  the GP return register as its bit image.
- on ILP32, a **64-bit scalar argument** splits into two consecutive 32-bit
  slots (low word, then high word); a bare 64-bit scalar **result** is
  returned as a register pair via the dedicated 64-bit scalar shape (§3.5).
- a narrow scalar rides one slot with **only its low bits guaranteed**: the
  canonical-form discipline of §2.3 does not extend to this seam (a producer
  may pass a bare narrow value), and a consumer shall not rely on a narrow
  slot's high bits.

## 3.4 The static triple: shim, vtable, handle

`abi.dispatch.triple` — For every compiled function that can be reached
indirectly, its **defining** translation unit emits a **weak**,
link-coalescible triple: the per-function marshalling **shim** (the
`vtable.call` target, which re-marshals slots to the underlying function's
Ch.2 convention and calls or tail-calls it), a static two-word **vtable**
`{dtor, call}`, and a static two-word **handle** `{&vtable, data = null}`. A
*referencing* translation unit may additionally emit its own weak copy where
it can synthesize the signature (the LLVM backend does; the native backends
instead resolve cross-unit references against the defining unit's emission —
per-referencing-unit emission of every symbol kind is not safe under Mach-O
strict-symbol semantics). The handle's symbol,
`__handle.<mangled>` (§5.5), is the **cross-producer contract name** — every
backend emits the identical symbol so references coalesce to one definition.
The shim and vtable symbols are backend-internal and deliberately not
harmonized across backends.

An interface vtable's method slots hold exactly these **handles** — a method
slot is a pointer to a `{vtable, data}` block, never a raw code address — so
interface dispatch is: load slot → treat as function value → call
`handle.vtable.call(handle.data, receiver, …)` under §3.2. Vtable slots are
one word wide; slot 0 of an impl vtable holds the receiver-type destructor
handle, and the interface-value `any` block carries the concrete type's
TypeInfo pointer (language spec §7.13.8, §7.13.14).

## 3.5 Crossing into the interpreter, and out

`abi.dispatch.cross-mode` — A VM (interpreted) function's function value has
the same `{vtable, data}` shape; its `vtable.call` slot holds one of exactly
**three universal trampolines** — `TrampolineScalar` (one-word scalar/void
result), `TrampolineScalar64` (bare 64-bit scalar result on ILP32),
`TrampolineAggregate` (retbuf result) — and its data word points at a
**tagged** VM closure record (first word: a data-kind tag). The trampolines
are the only functions whose vtable call slot is the function itself rather
than a shim (their data parameter *is* the closure record); their identities
are load-bearing, shared by all producers.

In the other direction, bytecode reaches compiled code exclusively through
three fixed-shape primitives declared in `pkg/builtins/rt` and lowered by the
compiler to plain indirect calls — `_call_shim_scalar`, `_call_shim_scalar64`,
`_call_shim_aggregate` — each carrying the shim address, the data (and retbuf)
words, and a fixed bank of **seven** integer argument slots. There is no
dynamic call-frame construction (no libffi, no runtime code generation);
consequently a cross-mode indirect call is limited to seven argument slots,
enforced loudly. The language spec records this as a bounded realization
limit of the interpreter (§19.5), not a language rule.

> _Note._ Trampolines read only the first *NumParams* of the seven slot
> registers; trailing registers are uninitialized but unread (the same
> soundness argument as C variadics). Before dispatching outward the VM
> substitutes any interface-argument vtable word that is a VM index with the
> impl's native handle vtable, and `TrampolineAggregate` performs the same
> substitution on the result copy, so compiled code never sees a VM index.

> _Note._ Like the seven-slot argument bank, the cross-mode **result** copy
> is bounded: the VM's aggregate trampoline rejects (loudly) a result image
> wider than 64 bytes.

## 3.6 Closure environments

`abi.dispatch.closures` — A capturing function literal is lifted to a
top-level function taking its captures as prepended parameters; the
environment is a per-literal struct with one field per capture, and the
function value's data word points at it (stack storage for `*func`, a managed
allocation for `@func`). The per-closure shim loads each capture from `data`
and calls the lifted function with `(captures…, user args…)`. For a managed
closure whose environment contains anything needing destruction (managed
captures), the vtable's dtor slot holds the environment struct's destructor
handle — null otherwise — so releasing the function value releases the
captures in either mode.

> _Status._ A **native** capturing closure's environment struct is untagged
> (no data-kind word), so such a function value is not currently dispatchable
> **by the interpreter** (the VM's tag check rejects it, and an unlucky first
> capture word could misdispatch instead). Raised for an owner decision:
> designed fail-loud boundary, or gap to fix. VM-created closure records are
> always tagged.

## 3.7 Sub-word results on this seam

`abi.dispatch.subword` — Shims do not widen sub-word results; the platform
guarantee (correct low bits) is all this seam promises for a narrow scalar
result. Consumers therefore defend: shims re-extend register-passed narrow
slot arguments before invoking the underlying function, compiled seam
callers re-canonicalize a narrow scalar result after the call, and the VM
re-narrows after every potentially-cross-mode call.

> _Status._ Moving the widening into every producer's shim (and dropping the
> VM-side narrow) is a recorded, deferred cleanup; until it lands the VM-side
> narrow is the intended mechanism.

## 3.8 Raw indirect calls are toolchain-internal

`abi.dispatch.raw` — A call through a **raw code address** with no
`data`/`retbuf` prefix exists only inside the toolchain (the `_call_shim_*`
lowerings above, destructor dispatch through handles, and the runtime's
internal trampoline plumbing). It is not a user-reachable convention: user
indirect calls always go through §3.2, and `__c_entry` pointers are for **C**
callers under Ch.4, not for Binate indirect calls.
