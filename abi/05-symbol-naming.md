# 5. Symbol naming

> **Status:** normative · **Maturity:** Provisional  
> **Rule-ID prefix:** `abi` (area `sym`)

The language spec classifies symbol decoration as implementation-defined with
a documented scheme (§21.4; `pkg.identity` ties symbol identity to the full
package path). This chapter **is** that documentation. Stability follows
§1.4: the scheme is fixed for the current toolchain, not declared permanent.

## 5.1 The symbol namespace

`abi.sym.namespace` — Every linker symbol a Binate translation unit defines is
one of:

1. a **mangled** symbol `bn_…` (§5.2) — functions, globals, type-identity
   cores;
2. a **decorated** symbol — a fixed prefix ending in `.` applied to a mangled
   core (§5.5);
3. one of the two **reserved glue literals** `bn_entry` / `bn_init`
   (language spec `prog.entry.glue`) — produced only as sentinels for the
   reserved source names `main.__entry` / `<facade>.__bninit`, never by the
   mangling grammar;
4. a **C-facing verbatim name** — `#[c_export]` export names, and the symbols
   named by `__c_call`/`__c_global` (references only). This is the **only**
   unmangled path (language spec `pkg.ccall`);
5. a translation-unit-local artifact (string blobs, labels) — not part of the
   cross-object contract.

## 5.2 The mangling grammar

`abi.sym.grammar` — Mangled symbols use an injective length-prefix scheme over
the output alphabet `[A-Za-z0-9_]`; counts are decimal with no leading zero;
demangling is an exact inverse. The alphabet guarantee presupposes that
identifiers and package-path segments themselves use only those characters —
identifiers do by the language grammar; package paths are currently
**unvalidated** (an out-of-set byte, or a `.`, would leak into symbols and
break the decorated-name discriminator, §5.5) — a recorded enforcement
gap.

```
Symbol   = "bn_" Kind Body
Kind     = "F" | "G" | "S" | "I" | "T" | "V" | "W"
Ident    = count "_" bytes            (* count = byte length *)
PkgPath  = segcount "_" Ident*        (* the "/"-split package path *)
ArgList  = argcount "_" TypeArg*
```

| Kind | Meaning | Body |
|------|---------|------|
| `F` | function / method / synthesized helper | `PkgPath` membercount `"_"` `Ident`* |
| `G` | global variable | as `F` |
| `S` | struct type identity | as `F` |
| `I` | generic function instantiation | `PkgPath Ident ArgList` |
| `T` | generic struct instantiation | `PkgPath Ident ArgList` |
| `V` | interface-impl vtable core | `PkgPath Ident PkgPath Ident` (type, then interface) |
| `W` | impl shim-vtable core | as `V` |

Examples: `pkg/binate/parser.parseExpr` →
`bn_F3_3_pkg6_binate6_parser1_9_parseExpr`; `main.main` →
`bn_F1_4_main1_4_main`; the instantiation `pair[int, bool]` in `pkg/aa/gen` →
`bn_I3_3_pkg2_aa3_gen4_pair2_N0_3_intN0_4_bool`.

## 5.3 The type-argument sub-language

`abi.sym.typeargs` — `TypeArg` encodes a type compositionally:

| Form | Type |
|------|------|
| `p T` / `m T` | `*T` / `@T` |
| `s T` / `M T` | raw slice `*[]T` / managed-slice `@[]T` |
| `r T` | `readonly T` |
| `i T` / `j T` | `*Iface` / `@Iface` |
| `a` count `"_"` T | `[count]T` |
| `f Sig` / `F Sig` / `g Sig` | func type / `*func` value / `@func` value, `Sig = "p"pc"_"TypeArg* "r"rc"_"TypeArg*` |
| `N PkgPath Ident` | named type or primitive leaf (the only name-introducing form; `int` is `N0_3_int`) |
| `S` fieldcount `"_"` (`Ident TypeArg`)* | anonymous struct, structural identity |

## 5.4 Reserved names

`abi.sym.reserved` — In source, identifiers beginning `__` and identifiers
containing `__bn_inst__` are rejected in user declarations; every
compiler-synthesized source-level name lives in the `__` namespace (`__init`,
`__entry`, `__funclit_<n>`, `__dtor_…`, `__copy_…`, `__Package`, the
per-package descriptor globals `__pkgname` / `__pkg_info` / `__pkg_funcs` /
`__pkg_globals` / `__pkg_vtables` / `__pkg_satentries` / `__pkg_satfrag`, …). A
"."-member containing the infix `__bn_inst__` marks a monomorphized generic
instantiation, with the verbatim `ArgList` following the marker. Single-
underscore identifiers (`_foo`, `_pkg…`) are a normal user convention and are
NOT reserved — they cannot collide with a synthesized name, which always carries
the `__` prefix.

## 5.5 Decorated symbol families

`abi.sym.decorated` — Decorations prefix a mangled core (these symbols
contain a `.`). The coalescing families — `__ivt.`, `__ivtshim.`,
`__typeinfo.`, `__ifaceid.`, `__satentry.`, `__handle.`, `__centry.` — are
weak, link-coalesced definitions (§6.1); the blob families (`*_name.`,
`*fields.`, `*fieldnames.`, `*_typesym.`, `*_ifacesym.`) are
translation-unit-local:

| Symbol | Contents |
|--------|----------|
| `__ivt.` + `bn_V` core | interface-impl vtable (method slots hold handles, §3.4) |
| `__ivtshim.` + `bn_W` core | parallel shim vtable (VM-consumed; content-identical to `__ivt.`) |
| `__typeinfo.` + type core | the TypeInfo record (§7.13.14); its **address** is the type-identity token |
| `__typeinfo_name.` / `__typefields.` / `__typefieldnames.` + type core | TU-local RTTI blobs |
| `__ifaceid.` + interface core | per-interface identity token |
| `__satentry.` (+`_typesym.`/`_ifacesym.`) + `bn_V` core | interface-satisfaction registry entry (+ VM-key blobs) |
| `__handle.` + mangled function | the function's static handle — the **cross-producer contract name** (§3.4) |
| `__centry.` + mangled function | native `__c_entry` normalization thunk (§4.5) |

The per-function shim and vtable symbols backing a handle are
backend-internal: the LLVM and native backends deliberately spell them
differently, and only the handle name is contract.

## 5.6 Object-format prefix

`abi.sym.prefix` — Mach-O symbols carry a leading `_`; ELF symbols are bare.
The prefix applies uniformly to mangled, decorated, reserved, and C-facing
names, and is outside the mangling scheme (demangling operates on the bare
name).
