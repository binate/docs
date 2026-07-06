# A. Grammar Summary
> **Status:** normative · **Maturity:** Stable (generated from `binate.ebnf`)  
> **Rule-ID prefix:** `grammar`

> _**Generated file — do not edit by hand.**_ This annex is produced from the canonical grammar [`binate.ebnf`](binate.ebnf) by [`scripts/gen-annex-a.py`](../scripts/gen-annex-a.py) (specification Decision D4). `binate.ebnf` is the single source of truth; to change the grammar, edit it and re-run the generator. The per-feature-chapter inlined productions present the same grammar in context.

The metalanguage is ISO/IEC-14977-flavored EBNF, defined normatively in **Ch.4 Notation**: `=` definition, `|` alternation, `{}` repetition (zero or more), `[]` optional, `()` grouping, `…` inclusive character range, `;` rule terminator, `(* … *)` comment, `"x"` literal terminal, juxtaposition = concatenation.

## A.1 Lexical elements

```ebnf
(* --- Characters --- *)

letter        = "a"…"z" | "A"…"Z" | "_" ;
digit         = "0"…"9" ;
hex_digit     = digit | "a"…"f" | "A"…"F" ;
octal_digit   = "0"…"7" ;
binary_digit  = "0" | "1" ;

(* --- Identifiers --- *)

identifier    = letter { letter | digit } ;

(* --- Reserved keywords --- *)
(*  break    case     const     continue  default   else      false
    for      func     if        impl      import    in        interface
    nil      package  readonly   return    Self      struct    switch
    true     type     var                                                *)

(* --- Keyword built-ins (operations with special call syntax; see BuiltinCall) --- *)
(*  make      make_slice  box       cast      bit_cast  len
    sizeof    alignof     present   same      unsafe_index
    unsafe_div  unsafe_rem  unsafe_shl  unsafe_shr  _func_handle  __c_call
    __c_global *)

(* --- Predeclared names (NOT reserved — may be shadowed) --- *)
(*  Types:     int  uint  int8  int16  int32  int64
               uint8  uint16  uint32  uint64  bool  byte  char  any
               float32  float64
    Constant:  iota   (significant only inside a grouped const block)
    Functions: print  println  panic                                     *)

(* --- Integer literals --- *)
(* A "0"-prefixed run of digits (e.g. 0123) is not a decimal literal; the
   scanner emits a single error token for it (use "0o…" for octal). *)

decimal_lit   = "1"…"9" { digit } | "0" ;
hex_lit       = "0" ( "x" | "X" ) hex_digit { hex_digit } ;
octal_lit     = "0" ( "o" | "O" ) octal_digit { octal_digit } ;
binary_lit    = "0" ( "b" | "B" ) binary_digit { binary_digit } ;
int_literal   = decimal_lit | hex_lit | octal_lit | binary_lit ;

(* --- Float literals --- *)

float_literal = digit { digit } "." { digit } [ exponent ]
              | digit { digit } exponent
              | "." digit { digit } [ exponent ] ;
exponent      = ( "e" | "E" ) [ "+" | "-" ] digit { digit } ;

(* --- String literals --- *)
(* A string literal is ONE double-quoted run.  There is no hidden null
   terminator; the value is exactly the characters written (after escape
   decoding).  Adjacent string literals are NOT joined by the lexer — that is a
   parse-time, expression-position operation (see PrimaryExpr; §13), so it does
   not apply in package/import context. *)

string_literal = '"' { string_char | escape_seq } '"' ;
string_char    = (* any character except '"', "\", or newline *) ;

(* --- Char literals --- *)

char_literal  = "'" ( char_char | escape_seq ) "'" ;
char_char     = (* any character except "'", "\", or newline *) ;

(* The valid escape set is shared by string and char literals (the lexer carries
   the raw text through; decoding and validation happen later).  "\uHHHH" is a
   Unicode code point: UTF-8-expanded in a string literal, restricted to a single
   byte (<= U+007F) in a char literal; surrogates are rejected.  There is no octal,
   no eight-digit "\U", and no \a \b \f \v escape (§5). *)
escape_seq    = "\" ( "n" | "r" | "t" | "\" | "'" | '"' | "0"
              | "x" hex_digit hex_digit
              | "u" hex_digit hex_digit hex_digit hex_digit ) ;

(* --- Operators and punctuation --- *)
(*  +    -    *    /    %    &    |    ^    ~    <<   >>
    ==   !=   <    >    <=   >=   &&   ||   !
    =    :=   +=   -=   *=   /=   %=   &=   |=   ^=   <<=  >>=
    ++   --
    .    ,    ;    :    @    #
    (    )    [    ]    {    }    ...                                     *)

(* --- Comments --- *)

line_comment  = "//" { (* any character except newline *) } ;
block_comment = "/*" { (* any character *) } "*/" ;

(* --- Automatic semicolon insertion (ASI) --- *)
(* A ";" is inserted after the final token of a line when that token is: an
   identifier or predeclared name; an int/float/char/string literal; "true",
   "false", or "nil"; "break", "continue", or "return"; "++" or "--"; or one of
   ")", "]", "}".  Consequently a multi-line argument, element, or parameter
   list requires a trailing comma after its last entry.  (Same rule as Go.) *)
```

## A.2 Source file structure

```ebnf
SourceFile    = [ Annotation ] PackageClause ";"
                { ImportDecl ";" }
                { TopLevelDecl ";" } ;

PackageClause = "package" string_literal ;

ImportDecl    = [ Annotation ] "import" ImportSpec
              | [ Annotation ] "import" "(" { ImportSpec ";" } ")" ;
ImportSpec    = [ identifier ] string_literal ;          (* optional alias *)

(* An annotation block ("#[ … ]") attaches to the declaration that follows; it
   is consumed once at the top-level declaration boundary, not within a
   declaration's own grammar. *)
TopLevelDecl  = [ Annotation ] ( TypeDecl
              | VarDecl
              | ConstDecl
              | FuncDecl
              | MethodDecl
              | InterfaceDecl
              | ImplDecl ) ;
```

## A.3 Declarations

```ebnf
(* --- Type declarations --- *)
(* `type X = U` is an alias; `type X U` is a distinct type; `type X` with no
   definition is an opaque (forward-declared) type.  A named struct is the
   distinct form whose definition is a struct type: `type Point struct { … }`.
   There is no `type X interface { … }` form — interfaces use the `interface`
   keyword (§4).  Function-local `type` declarations are rejected. *)

TypeDecl      = "type" TypeSpec
              | "type" "(" { TypeSpec ";" } ")" ;
TypeSpec      = identifier [ TypeParams ] TypeDef ;
TypeDef       = "=" Type            (* alias *)
              | Type                (* distinct type (incl. `struct { … }`) *)
              | (* empty *) ;       (* opaque / forward-declared *)

(* --- Variable declarations --- *)

VarDecl       = "var" VarSpec
              | "var" "(" { VarSpec ";" } ")" ;
VarSpec       = identifier Type [ "=" Expression ]
              | identifier "=" Expression ;              (* type inferred *)

(* --- Constant declarations (a grouped block predeclares iota) --- *)

ConstDecl     = "const" ConstSpec
              | "const" "(" { ConstSpec ";" } ")" ;
ConstSpec     = identifier [ Type ] "=" Expression
              | identifier ;        (* repeats the previous spec's type + expr *)

(* --- Short variable declaration (statement form) --- *)

ShortVarDecl  = IdentifierList ":=" ExpressionList ;
```

## A.4 Functions, methods, interfaces, impls

```ebnf
(* In an interface file (.bni), a non-generic function or method declaration may
   omit its Block — the signature alone is given. *)
FuncDecl      = "func" identifier [ TypeParams ] Signature Block ;
MethodDecl    = "func" Receiver identifier Signature Block ;

Receiver      = "(" identifier ReceiverType ")" ;
(* A receiver type is one of T, *T, *readonly T, @T, @readonly T (an optional
   `*`/`@` and optional `readonly` over a named base), and must reduce to a named
   type declared in the same package (or, only in pkg/builtins/lang, a universe
   primitive).  If the base type is GENERIC, the receiver BINDS its type
   parameters as fresh names — `*Cursor[T]`, `(m HashMap[K, V])` — an identifier
   list (not type arguments).  A bracket name that resolves to a type (e.g.
   `Cursor[int]`) is instead a specific-instantiation receiver, NOT a binder — the
   distinction is SEMANTIC (predeclared names like `int` are ordinary identifiers,
   §5), resolved by the checker.  Constraints are inherited from the type's
   declaration and the count must match the type's arity; the method (or impl)
   introduces NO type parameters of its own (no method-level `[…]`; there is no
   `[TypeParams]` slot on MethodDecl).  Details: §12.1. *)
ReceiverType  = [ "*" | "@" ] [ "readonly" ] ReceiverBase ;
ReceiverBase  = QualifiedName [ "[" identifier { "," identifier } "]" ] ;

Signature     = "(" [ ParameterList ] ")" [ Result ] ;
(* An optional FINAL variadic parameter `name "..." T` (at most one, last only)
   collects the trailing call arguments; in the body it has type *[]T — a
   raw-slice borrow (§10.3).  D12. *)
ParameterList = ParameterDecl { "," ParameterDecl } [ "," VariadicParam ]
              | VariadicParam ;
ParameterDecl = identifier Type ;   (* name before type; each name carries its
                                       own type — grouped `a, b int` is rejected.
                                       Read-only parameters are expressed by a
                                       `readonly` type, not a parameter prefix. *)
VariadicParam = identifier "..." Type ;   (* final parameter only; body type *[]T *)
Result        = Type                 (* single result, unparenthesized *)
              | "(" TypeList ")" ;   (* parenthesized: one or more results; `(T)` ≡ T *)
TypeList      = Type { "," Type } ;

Block         = "{" { Statement ";" } "}" ;

(* An interface is declared at package scope.  There is no `type X interface`
   form and no anonymous interface type.  A method signature's parameter and
   result types may reference the interface being declared and may use `Self`. *)
InterfaceDecl = "interface" identifier [ TypeParams ]
                  [ ":" InterfaceList ] "{" { MethodSig ";" } "}"
              | "interface" identifier "=" TypeName ;   (* alias *)
MethodSig     = identifier Signature ;
InterfaceList = TypeName { "," TypeName } ;

(* An `impl` is a bodyless relational assertion that the receiver type satisfies
   each listed interface; its methods are declared separately (Go-style).  A
   PARAMETERIZED-receiver impl binds the generic type's parameters in the
   receiver, and the interface list may reference them: `impl *Cursor[T] :
   Iterator[T]` (§12.1). *)
ImplDecl      = "impl" ReceiverType ":" InterfaceList ;
```

## A.5 Types

```ebnf
(* The "*" and "@" prefixes are overloaded (see disambiguation D3):
     "*" "[" "]" T   → raw slice  *[]T          "@" "[" "]" T   → managed-slice @[]T
     "*" "func" …    → raw func value *func(…)   "@" "func" …    → managed @func(…)
     "*" T           → raw pointer *T            "@" T           → managed pointer @T
   For the pointer form the following type must not begin with "[" or "func";
   pointer-to-array and pointer-to-slice require parentheses — e.g. *([N]T),
   @(*[]T).  Leniency: `@[N]T` is accepted as `@([N]T)` though `*[N]T` requires
   the explicit parens (a known asymmetry, §7.8). *)

Type          = TypeName
              | "Self"
              | "(" Type ")"
              | "readonly" Type
              | "*" PointerTarget
              | "@" PointerTarget
              | ArrayType
              | StructType ;

PointerTarget = "[" "]" Type            (* slice sugar: *[]T / @[]T *)
              | "func" FuncTypeBody      (* function-value type: *func(…) / @func(…) *)
              | Type ;                   (* pointer (Type not starting "[" or "func") *)

(* A function-value type lists parameter TYPES only (no names).  A bare
   `func(…)` is not a usable type — it must be spelled `*func(…)` or `@func(…)`.
   A trailing `"..." T` marks a VARIADIC function-value type (`*func(...T)`);
   variadic-ness is part of the signature's type identity (§10.3).  D12. *)
FuncTypeBody   = "(" [ FuncTypeParams ] ")" [ Result ] ;
FuncTypeParams = Type { "," Type } [ "," "..." Type ]
               | "..." Type ;

TypeName      = QualifiedName [ "[" TypeArgList "]" ] ;   (* opt. generic instantiation *)
QualifiedName = identifier [ "." identifier ] ;           (* opt. package qualifier *)
TypeArgList   = Type { "," Type } ;

ArrayType     = "[" Expression "]" Type ;                 (* fixed-size array *)
StructType    = "struct" StructBody ;
StructBody    = "{" { StructField ";" } "}" ;
(* A field is `name Type` (named) or just `Type` / `QualifiedName` (an embedded
   field); see disambiguation D10.  Struct fields are not individually
   annotated. *)
StructField   = [ identifier ] Type ;
```

## A.6 Annotations and build constraints

```ebnf
(* An annotation attaches to the immediately following element.  Multiple
   entries are comma-separated within one "#[ … ]"; separate blocks do not
   stack. *)

Annotation      = "#" "[" [ AnnotationEntry { "," AnnotationEntry } ] "]" ;
AnnotationEntry = AnnotationName [ "(" [ ExpressionList ] ")" ] ;
AnnotationName  = identifier { "." identifier } ;

(* A build-constraint annotation's argument is syntactically an ordinary
   Expression (§8); it is RESTRICTED — and validated after parsing — to the
   shape below, where `is` is an ordinary identifier (not a reserved keyword)
   and "&&"/"||"/"!" are the ordinary logical operators.  This is a semantic
   restriction on Expression, not a separate parser production. *)
(*   build-constraint  ::=  is( <predicate-name> , <string-literal> )
                        |    ! build-constraint
                        |    build-constraint && build-constraint
                        |    build-constraint || build-constraint
                        |    ( build-constraint )                          *)
```

## A.7 Statements

```ebnf
(* Only var/const declarations may appear in a block; `type` is package-level. *)

Statement     = BlockDecl
              | SimpleStmt
              | ReturnStmt
              | BreakStmt
              | ContinueStmt
              | Block
              | IfStmt
              | ForStmt
              | SwitchStmt ;

BlockDecl     = VarDecl | ConstDecl ;

SimpleStmt    = EmptyStmt
              | ExpressionStmt
              | Assignment
              | ShortVarDecl
              | IncDecStmt ;

EmptyStmt     = (* empty *) ;
ExpressionStmt = Expression ;

(* A simple assignment allows a list on each side (multi-value, e.g.
   x, err = foo()).  A compound assignment takes exactly one expression a
   side. *)
Assignment    = ExpressionList "=" ExpressionList
              | Expression compound_assign_op Expression ;
compound_assign_op = "+=" | "-=" | "*=" | "/=" | "%="
              | "&=" | "|=" | "^=" | "<<=" | ">>=" ;

IncDecStmt    = Expression ( "++" | "--" ) ;

ReturnStmt    = "return" [ ExpressionList ] ;
BreakStmt     = "break" ;
ContinueStmt  = "continue" ;

(* In the condition of if/for/switch a bare composite literal must be
   parenthesized (D4). *)
IfStmt        = "if" Expression Block [ "else" ( IfStmt | Block ) ] ;

ForStmt       = "for" ForClause Block ;
ForClause     = (* empty *)                (* infinite:    for { … } *)
              | Expression                 (* while-style: for cond { … } *)
              | ForCClause                 (* C-style:     for init; cond; post { … } *)
              | ForInClause ;              (* range:       for x in coll { … } *)
ForCClause    = SimpleStmt ";" [ Expression ] ";" SimpleStmt ;
ForInClause   = identifier [ "," identifier ] "in" Expression ;   (* value, or index + value *)

(* A tagless switch (`switch { … }`) is the condition-less form; there is no
   fallthrough.  The second form is a TYPE SWITCH: the head `x.(type)` (optionally
   bound as `v := x.(type)`) dispatches on the DYNAMIC type of an interface value,
   and each case lists ASSERT TARGETS — a `*`/`@`/value recovery kind plus a NAMED
   type — not expressions (§11.12, §14.10).  D13. *)
SwitchStmt    = "switch" [ Expression ] "{" { CaseClause } "}"
              | "switch" [ identifier ":=" ] PostfixExpr "." "(" "type" ")"
                  "{" { TypeCaseClause } "}" ;
CaseClause    = ( "case" ExpressionList | "default" ) ":" { Statement ";" } ;
TypeCaseClause = ( "case" AssertTargetList | "default" ) ":" { Statement ";" } ;
(* A type-assertion / type-switch target is a mandatory recovery kind (raw "*",
   managed "@", or value = neither) plus an optional `readonly` and a NAMED type
   (TypeName — a concrete type, an interface, or `any`).  It deliberately EXCLUDES
   slice / func / array / struct / `Self` targets and pointer-to-composite: only a
   nameable type may be asserted (§11.12).  The leading "*"/"@" is ALWAYS the
   recovery kind here, never a pointer/slice type constructor (D13). *)
AssertTarget  = [ "*" | "@" ] [ "readonly" ] TypeName ;
AssertTargetList = AssertTarget { "," AssertTarget } ;
```

## A.8 Expressions

```ebnf
(* Precedence, lowest (loosest) to highest (tightest):
     1   ||
     2   &&
     3   ==  !=  <  >  <=  >=        (non-chaining: a < b < c is an error)
     4   |
     5   ^
     6   &
     7   <<  >>
     8   +  -
     9   *  /  %
    10   unary prefix:  !  ~  -  *  &
    11   postfix:       .  []  ()
   All binary operators are left-associative; unary prefixes are
   right-associative.  Assignment and ++/-- are statements, not expressions. *)

Expression    = OrExpr ;
OrExpr        = AndExpr { "||" AndExpr } ;
AndExpr       = CompareExpr { "&&" CompareExpr } ;
CompareExpr   = BitOrExpr [ compare_op BitOrExpr ] ;      (* no chaining *)
compare_op    = "==" | "!=" | "<" | ">" | "<=" | ">=" ;
BitOrExpr     = BitXorExpr { "|" BitXorExpr } ;
BitXorExpr    = BitAndExpr { "^" BitAndExpr } ;
BitAndExpr    = ShiftExpr { "&" ShiftExpr } ;
ShiftExpr     = AddExpr { ( "<<" | ">>" ) AddExpr } ;
AddExpr       = MulExpr { ( "+" | "-" ) MulExpr } ;
MulExpr       = UnaryExpr { ( "*" | "/" | "%" ) UnaryExpr } ;

UnaryExpr     = PostfixExpr
              | "!" UnaryExpr
              | "~" UnaryExpr
              | "-" UnaryExpr
              | "*" UnaryExpr          (* dereference *)
              | "&" UnaryExpr          (* address-of *)
              | RawSliceLiteral ;      (* *[]T{…} — distinguished from deref by the "[" (D3) *)

PostfixExpr   = PrimaryExpr { PostfixOp } ;
PostfixOp     = "." identifier                            (* field / method / pkg member *)
              | "." "(" AssertTarget ")"                   (* type assertion x.(K T) — D13, §11.12 *)
              | "[" Expression "]"                         (* index *)
              | "[" [ Expression ] ":" [ Expression ] "]"  (* slice *)
              | "[" TypeArgList "]"                         (* generic instantiation (D5) *)
              | CallArgs ;                                  (* call *)
(* A trailing `"..."` on the final argument is a SPREAD: it expands a slice into
   the variadic parameter (§10.3).  The spread is exclusive — it supplies the
   entire variadic argument and may not be mixed with individual variadic args
   (only fixed args may precede it).  D12. *)
CallArgs      = "(" [ ArgumentList ] ")" ;
ArgumentList  = Expression { "," Expression } [ "..." ] ;

PrimaryExpr   = BuiltinCall
              | CompositeLiteral
              | FuncLiteral
              | identifier
              | int_literal
              | float_literal
              | string_literal { string_literal }   (* adjacent literals concatenate, §13 *)
              | char_literal
              | "true" | "false" | "nil"
              | "(" Expression ")" ;

(* A function literal binds parameter NAMES (unlike a function-value type).  A
   literal that references an enclosing local is a closure; capture is by
   value. *)
FuncLiteral   = "func" Signature Block ;

(* A composite literal builds a struct/named value, an array, or a slice.  The
   literal head is a TypeName — optionally a generic instantiation, e.g.
   `List[int]{…}` or `pkg.Pair[int, S]{…}` (D5/D9).  Element keys are parsed as
   expressions; semantic analysis resolves a bare-identifier key as a field name
   or an index (D6).
   (Implementation gap: the parser does not yet build the generic-instantiated
   head — it consumes `[…]` as instantiation/index and never enters the
   composite-literal path; `claude-todo.md`, §13.10.) *)
CompositeLiteral = TypeName "{" [ ElementList [ "," ] ] "}"
              | ArrayLiteral
              | ManagedSliceLiteral ;
ArrayLiteral  = "[" ArrayLen "]" Type "{" [ ElementList [ "," ] ] "}" ;
ManagedSliceLiteral = "@" "[" "]" Type "{" [ ElementList [ "," ] ] "}" ;
RawSliceLiteral     = "*" "[" "]" Type "{" [ ElementList [ "," ] ] "}" ;
ArrayLen      = Expression | "..." ;
ElementList   = Element { "," Element } ;
Element       = [ Expression ":" ] Expression ;

(* Built-ins are keywords with fixed call shapes, distinct from ordinary calls.
   `make(T)` zero-initializes a value; `make_slice(T, n)` allocates a
   runtime-sized slice.  `panic`, `print`, and `println` are predeclared
   FUNCTIONS, not built-ins — they are ordinary calls on an identifier. *)
BuiltinCall   = "make" "(" Type ")"
              | "make_slice" "(" Type "," Expression ")"
              | "box" "(" Expression ")"
              | "cast" "(" Type "," Expression ")"
              | "bit_cast" "(" Type "," Expression ")"
              | "len" "(" Expression ")"
              | "sizeof" "(" Type ")"
              | "alignof" "(" Type ")"
              | "present" "(" Expression ")"
              | "same" "(" Expression "," Expression ")"
              | "unsafe_index" "(" Expression "," Expression ")"
              | "unsafe_div" "(" Expression "," Expression ")"
              | "unsafe_rem" "(" Expression "," Expression ")"
              | "unsafe_shl" "(" Expression "," Expression ")"
              | "unsafe_shr" "(" Expression "," Expression ")"
              | "_func_handle" "(" Expression ")"
              | "__c_call" "(" string_literal "," CCallRet { "," CCallArg } ")"
              | "__c_global" "(" string_literal "," Type ")" ;  (* address of a C global as *T — §16.9 *)
CCallRet      = Type | string_literal ; (* the C return type, OR the string literal "void" for a void-returning C function *)
CCallArg      = Expression | "..." ;    (* "..." marks the C varargs boundary *)

ExpressionList = Expression { "," Expression } ;
IdentifierList = identifier { "," identifier } ;

(* Note: where a list (arguments, parameters, type arguments/parameters, or
   composite-literal elements) spans multiple lines, a trailing comma after the
   last entry is permitted — and required when the closing delimiter starts the
   next line (ASI).  The productions omit it for brevity. *)
```

## A.9 Generics

```ebnf
TypeParams    = "[" TypeParamDecl { "," TypeParamDecl } "]" ;
TypeParamDecl = identifier Type ;   (* type-parameter name + interface constraint *)
```

## A.10 Disambiguation summary

```ebnf
(* The parser is single-pass recursive descent; these rules collect the
   lookahead decisions referenced above.

   D1. ShortVarDecl vs Assignment:
       Parse the LHS as an ExpressionList, then inspect the operator.  ":=" →
       verify the LHS is all identifiers and reinterpret as ShortVarDecl; "=" or
       a compound operator → Assignment.

   D2. For-clause variants:
       "for" "{" → infinite loop.  "for" identifier ["," identifier] "in" →
       range (lookahead for "in").  "for" … ";" → C-style (lookahead for ";"
       after the first SimpleStmt).  Otherwise "for" Expression "{" →
       while-style.

   D3. "*[" / "@[" slice sugar / slice literal vs pointer / func value:
       "*"/"@" then "[" "]" begins a slice — a slice TYPE in type context, or a
       slice LITERAL (RawSliceLiteral / ManagedSliceLiteral) when a "{" follows
       the element type; then "func" → function-value type; then "(" → a
       parenthesized inner type; otherwise → pointer.  A bare "*[" or "@[" not
       immediately followed by "]" is an error: pointer-to-array and
       pointer-to-slice require parentheses.

   D4. Composite literals in control-flow conditions:
       In an if/for/switch condition a bare composite literal (a QualifiedName or
       slice/array head followed by "{") is disallowed (its "{" is ambiguous with
       the block body); parenthesize it as (Point{…}).  (The parenthesized
       escape is the intended rule but is currently defective; §13.11.)

   D5. Generic instantiation vs indexing/slicing (expression context):
       "[" … ":" … "]" → slice (the colon is unambiguous).  "[" Type "," … "]" →
       generic instantiation (commas cannot occur in a single index).  "["
       single-contents "]" then "(" → try generic instantiation, falling back to
       index.  "[" single-contents "]" otherwise → index.  In type context
       (make, cast, declarations) "[" TypeArgList "]" is always instantiation.

   D6. Composite-literal element keys:
       Keys are parsed as expressions.  For a struct target a bare-identifier
       key is a field name; for an array target keys are index expressions.
       Semantic analysis resolves which from the target type.

   D7. ConstSpec bare identifier:
       In a grouped const block a bare identifier (no type, no "=") repeats the
       previous spec; the trailing ";" (ASI) separates it from the next spec.

   D8. Unary "*" vs binary "*":
       Resolved by precedence: unary "*" (dereference) is in UnaryExpr; binary
       "*" (multiplication) is in MulExpr.  Unary binds tighter: *p * x is
       (*p) * x.

   D9. PrimaryExpr ordering:
       Built-in keywords are tried first (the lexer distinguishes them from
       identifiers).  A TypeName followed by "{" — a QualifiedName, or a generic
       instantiation `Ident "[" TypeArgList "]"` — is a composite literal;
       otherwise a bare identifier.

   D10. StructField — named field vs embedded:
        When a field begins with an identifier, one-token lookahead decides:
        followed by another identifier, "Self", "*", "@", "[", "(", "struct", or
        "readonly" → a named field (the identifier is the name, the rest begins
        the type); followed by ";" or "}" → an embedded field (the identifier is
        a TypeName); followed by "." → an embedded field with a qualified name.

   D11. TypeDef — TypeParams vs ArrayType when "[" follows:
        Both start with "[".  Two-token lookahead: "[" literal → ArrayType
        expression; "[" identifier identifier → TypeParams (name + constraint);
        "[" identifier "]" → ArrayType (expression = a single variable); "["
        identifier "," → TypeParams; "[" identifier operator → ArrayType
        expression.

   D12. "..." — three roles, disambiguated purely by adjacency (never a token
        clash; "..." is always one token):
        - STANDALONE: `[...]T{…}` inferred array length (ArrayLen), and the
          fixed/variadic boundary marker inside `__c_call` (CCallArg).  The
          "..." stands alone (no adjacent Type or Expression).
        - PREFIX on a Type: `name "..." T` in a parameter (VariadicParam) — a
          variadic parameter, whose in-body type is *[]T; or `"..." T` in a
          function-value type (FuncTypeParams) — a variadic function-value type
          (no body, binds no name).  Either way §10.3.  In ParameterList,
          ParameterDecl and VariadicParam both begin with `identifier`, so a
          one-token peek AFTER the name resolves them: a following "..." selects
          VariadicParam, otherwise a Type follows (ParameterDecl).  The "..."
          immediately precedes a Type.
        - SUFFIX on an Expression: `expr "..."` as the FINAL call argument
          (ArgumentList) — a slice spread (§10.3).  The "..." immediately
          follows an Expression and is the last token before the closing ")".

   D13. ".(" — selector vs. type assertion vs. type-switch head.  A "." is
        resolved by the token that follows it:
        - "." identifier → selector (field / method / package member).
        - "." "(" AssertTarget ")" → a type-ASSERTION expression (PostfixOp;
          §11.12).  Inside the parens a leading "*"/"@" is ALWAYS the recovery
          kind (never a pointer/slice type constructor), and the remainder is an
          optional `readonly` plus a NAMED type (TypeName): `x.(@C)`, `x.(*S)`,
          `x.(readonly C)`, `x.(pkg.T)`.  A non-nameable target (`*[]T`, `*func`,
          an array/struct literal, `Self`) does not match AssertTarget and is
          rejected.  A qualified `pkg.T` inside the parens is consumed wholly by
          TypeName, so its inner "." is not a selector.
        - "." "(" "type" ")" → the head of a TYPE SWITCH statement — the keyword
          `type`, not a type — valid only in switch-statement position, with an
          optional `v :=` binder (§11.12, §14.10).  `type` is reserved (§5), so
          `.(type)` can never be an AssertTarget; it terminates the postfix loop.
        The two `switch` alternatives are also chosen up front: `switch`
        `identifier` ":=" begins a type switch; otherwise the parser reads the
        scrutinee/tag (under the same composite-literal suppression as an
        expression-switch tag, D4) and a trailing `.(type)` marks the type switch.
*)
```
