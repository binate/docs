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
    unsafe_div  unsafe_rem  unsafe_shl  unsafe_shr  _func_handle  __c_call *)

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
(* A receiver type is one of T, *T, *readonly T, @T, @readonly T, and must
   reduce to a named type declared in the same package (or, only in
   pkg/builtins/lang, a universe primitive). *)
ReceiverType  = Type ;

Signature     = "(" [ ParameterList ] ")" [ Result ] ;
ParameterList = ParameterDecl { "," ParameterDecl } ;
ParameterDecl = identifier Type ;   (* name before type; each name carries its
                                       own type — grouped `a, b int` is rejected.
                                       Read-only parameters are expressed by a
                                       `readonly` type, not a parameter prefix. *)
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
   each listed interface; its methods are declared separately (Go-style). *)
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
   `func(…)` is not a usable type — it must be spelled `*func(…)` or `@func(…)`. *)
FuncTypeBody  = "(" [ TypeList ] ")" [ Result ] ;

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
   fallthrough. *)
SwitchStmt    = "switch" [ Expression ] "{" { CaseClause } "}" ;
CaseClause    = ( "case" ExpressionList | "default" ) ":" { Statement ";" } ;
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
              | "[" Expression "]"                         (* index *)
              | "[" [ Expression ] ":" [ Expression ] "]"  (* slice *)
              | "[" TypeArgList "]"                         (* generic instantiation (D5) *)
              | CallArgs ;                                  (* call *)
CallArgs      = "(" [ ExpressionList ] ")" ;

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
              | "__c_call" "(" string_literal "," CCallRet { "," CCallArg } ")" ;
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
*)
```
