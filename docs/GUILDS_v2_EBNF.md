# GUILDS v2 Language Specification - Complete EBNF Grammar

## Extended Backus-Naur Form (EBNF) Grammar

### Lexical Elements

```ebnf
(* Comments *)
LineComment     = "--" { ANY_CHAR } EOL ;
BlockComment    = "{-" { ANY_CHAR | BlockComment } "-}" ;

(* Identifiers *)
Identifier      = LETTER { LETTER | DIGIT | "_" } ;
LETTER          = "a".."z" | "A".."Z" ;
DIGIT           = "0".."9" ;

(* Literals *)
String          = '"' { STRING_CHAR | ESCAPE_SEQ } '"' ;
STRING_CHAR     = ANY_CHAR - '"' - "\\" ;
ESCAPE_SEQ      = "\\" ( "n" | "t" | "r" | '"' | "\\" ) ;

Number          = INTEGER | FLOAT ;
INTEGER         = DIGIT { DIGIT } ;
FLOAT           = INTEGER "." INTEGER ;

(* Sigils - Encoded as hex sequences *)
PhaseSigil      = "0x03C60x2080"  (* phi_0 orient *)
                | "0x03C60x2081"  (* phi_1 execute *)
                | "0x03C60x2082"  (* phi_2 verify *)
                | "0x03C60x2083"  (* phi_3 integrate *)
                | "0x03C60x1D63"  (* phi_r recover *)
                | "0x03C60x2205"  (* phi_empty idle *)
                ;

CertaintySigil  = "0x03C40x2713"  (* tau_certain *)
                | "0x03C4~"       (* tau_inferred *)
                | "0x03C4?"       (* tau_probable *)
                | "0x03C40x2205"  (* tau_unknown *)
                | "0x03C40x2694"  (* tau_contested *)
                | "0x03C40x231B"  (* tau_stale *)
                ;

FailureSigil    = "0x03A60x2193"  (* phi_degraded *)
                | "0x03A60x22A3"  (* phi_blocked *)
                | "0x03A60x2205"  (* phi_lost *)
                | "0x03A60x00BD"  (* phi_partial *)
                | "0x03A60x231B"  (* phi_stale *)
                | "0x03A60x27F3"  (* phi_recover *)
                | "0x03A60x2192"  (* phi_cascade *)
                | "0x03A6?"       (* phi_unknown *)
                | "0x03A60x2717"  (* phi_fatal *)
                | "0x03A60x2014"  (* phi_silent *)
                ;

DialogueSigil   = "0x03940x2192"  (* delta_assert *)
                | "0x0394?"       (* delta_query *)
                | "0x03940x2295"  (* delta_propose *)
                | "0x03940x26A0"  (* delta_warn *)
                | "0x03940x2713"  (* delta_ack *)
                | "0x03940x2205"  (* delta_silence *)
                | "0x03940x2190"  (* delta_correct *)
                | "0x03940x2191"  (* delta_escalate *)
                | "0x03940x2605"  (* delta_celebrate *)
                ;

CognitiveSigil  = "0x25C9"        (* focus *)
                | "0x25CB"        (* peripheral *)
                | "0x039B0x2193"  (* lambda_cost *)
                | "0x039B0x2191"  (* lambda_yield *)
                | "0x039B0x03A9"  (* lambda_omega *)
                | "0x2726"        (* salience *)
                | "0x2693"        (* anchor *)
                | "0x039B0x0303"  (* lambda_fade *)
                ;
```

### Program Structure

```ebnf
Program         = { Declaration } ;

Declaration     = LetDecl
                | ImportDecl       (* NEW *)
                | ClaimDecl
                | AffordDecl
                | VesselDecl
                | StageDecl
                | FlowDecl
                | BondDecl
                | SeamDecl
                | ContractDecl
                | ModalDecl        (* NEW *)
                | ToastDecl        (* NEW *)
                | NotificationDecl (* NEW *)
                | DialogDecl       (* NEW *)
                | MenuDecl         (* NEW *)
                | ComponentDecl    (* NEW *)
                ;
```

### Let Bindings

```ebnf
LetDecl         = "let" Identifier "=" Expression ;

Expression      = LiteralExpr
                | IdentifierExpr
                | CertaintySigil
                | BinaryExpr       (* NEW *)
                | UnaryExpr        (* NEW *)
                | ConditionalExpr  (* NEW *)
                | FunctionCall     (* NEW *)
                ;

BinaryExpr      = Expression BinaryOp Expression ;
BinaryOp        = "+" | "-" | "*" | "/" | "%" 
                | "==" | "!=" | "<" | ">" | "<=" | ">="
                | "&&" | "||"
                ;

UnaryExpr       = UnaryOp Expression ;
UnaryOp         = "!" | "-" ;

ConditionalExpr = "if" Expression "then" Expression "else" Expression ;

FunctionCall    = Identifier "(" [ ArgumentList ] ")" ;
ArgumentList    = Expression { "," Expression } ;
```

### Import System (NEW)

```ebnf
ImportDecl      = "import" ImportPath [ "as" Identifier ] [ ImportSpec ] ;
ImportPath      = String | RelativePath | PackagePath ;
RelativePath    = "./" Identifier { "/" Identifier } ;
PackagePath     = "@" Identifier "/" Identifier { "/" Identifier } ;

ImportSpec      = "{" ImportList "}"
                | "*"
                ;
ImportList      = ImportItem { "," ImportItem } ;
ImportItem      = Identifier [ "as" Identifier ] ;
```

### Claims

```ebnf
ClaimDecl       = "claim" Identifier "{" ClaimBody "}" ;

ClaimBody       = { ClaimField } ;

ClaimField      = "content" ":" ContentExpr
                | "certainty" ":" CertaintyExpr
                | "provenance" ":" ProvenanceExpr
                | "stakes" ":" StakesExpr
                | "freshness" ":" FreshnessExpr
                | "on_stale" ":" Identifier
                | "when" ":" Expression        (* NEW - conditional rendering *)
                | "compute" ":" ComputeExpr    (* NEW - computed values *)
                | "watch" ":" WatchExpr        (* NEW - reactive updates *)
                ;

ContentExpr     = FunctionCall | String | Expression ;

CertaintyExpr   = CertaintySigil
                | "composite" "(" "[" CertaintyExpr { "," CertaintyExpr } "]" ")"
                | Identifier
                ;

ProvenanceExpr  = "source" "." ProvenanceType "(" ArgumentList ")" ;
ProvenanceType  = "direct" | "derived" | "ai_generated" | "external" | "computed" ;

StakesExpr      = "low" | "medium" | "high" | "critical" | "context_dependent" | Expression ;

FreshnessExpr   = "live" | "cached" | "stale" | "event_driven" "(" EventSpec ")" ;

ComputeExpr     = "(" [ ParameterList ] ")" "=>" Expression ;  (* NEW *)
ParameterList   = Identifier { "," Identifier } ;

WatchExpr       = "[" Identifier { "," Identifier } "]" "=>" Expression ;  (* NEW *)
```

### Affordances

```ebnf
AffordDecl      = "afford" Identifier "{" AffordBody "}" ;

AffordBody      = { AffordField } ;

AffordField     = "perceivable" ":" PerceivableExpr
                | "offered" ":" OfferedExpr
                | "requires" ":" IdentifierList
                | "disables" ":" IdentifierList
                | "contracts" ":" ContractList
                | "on_unavail" ":" UnavailExpr
                | "when" ":" Expression         (* NEW *)
                | "disabled_when" ":" Expression (* NEW *)
                | "shortcut" ":" ShortcutExpr    (* NEW *)
                | "tooltip" ":" String           (* NEW *)
                ;

PerceivableExpr = "always_visible" 
                | "context_revealed" "(" Identifier ")"
                | "phase_coupled" "(" PhaseSigil ")"
                | Expression                     (* NEW *)
                ;

OfferedExpr     = "activate" | "toggle" | "hold" | "drag" | "swipe" | Expression ;

UnavailExpr     = "fade_locked" | "fade_locked" "(" String ")" 
                | "hidden" | "hidden" "(" String ")"
                ;

ShortcutExpr    = String  (* e.g., "Ctrl+S", "Cmd+K" *) ;
```

### Vessels

```ebnf
VesselDecl      = "vessel" Identifier "{" VesselBody "}" ;

VesselBody      = { VesselField } ;

VesselField     = "budget" ":" BudgetExpr
                | "phase" ":" PhaseSpec
                | "arrangement" ":" ArrangementExpr
                | "anchor" ":" AnchorSpec
                | "weight" ":" WeightExpr
                | "contains" ":" IdentifierList
                | "bonds" ":" IdentifierList
                | "contracts" ":" ContractList
                | "failures" ":" FailureSpecList
                | "on" ":" EventHandlerList
                | "responsive" ":" ResponsiveSpec  (* NEW *)
                | "animation" ":" AnimationSpec    (* NEW *)
                | "when" ":" Expression            (* NEW *)
                ;

BudgetExpr      = "whole" "(" Number ")"
                | "fixed" "(" Number ")"
                | "auto"
                | "ceiling" "(" Number "," BudgetExpr ")"
                | "shared" "(" Number "," ( Number | Identifier ) ")"
                | "responsive" "(" ResponsiveBudget ")"  (* NEW *)
                ;

ResponsiveBudget = "{" BreakpointBudget { "," BreakpointBudget } "}" ;  (* NEW *)
BreakpointBudget = Breakpoint ":" BudgetExpr ;
Breakpoint      = "mobile" | "tablet" | "desktop" | "wide" | String ;

PhaseSpec       = "any"
                | PhaseSigil
                | "[" PhaseSigil { "," PhaseSigil } "]"
                ;

ArrangementExpr = ArrangementKind [ "(" ArgumentList ")" ] ;

ArrangementKind = "sequence" | "equal" | "dominant" | "grid" 
                | "free" | "stack" | "adaptive" 
                | "flexbox"    (* NEW *)
                | "masonry"    (* NEW *)
                | "carousel"   (* NEW *)
                ;

WeightExpr      = "primary" | "secondary" | "tertiary" | "background" | "hidden" ;

AnchorSpec      = "{" AnchorField { "," AnchorField } "}" ;
AnchorField     = "elements" ":" IdentifierList
                | "position" ":" ( "top" | "bottom" | "left" | "right" | "center" )
                | "sticky" ":" Boolean         (* NEW *)
                ;

ResponsiveSpec  = "{" ResponsiveRule { "," ResponsiveRule } "}" ;  (* NEW *)
ResponsiveRule  = Breakpoint ":" "{" VesselField { "," VesselField } "}" ;

AnimationSpec   = "{" AnimationProp { "," AnimationProp } "}" ;  (* NEW *)
AnimationProp   = "type" ":" AnimationType
                | "duration" ":" DeadlineExpr
                | "easing" ":" EasingFunction
                | "trigger" ":" AnimationTrigger
                ;

AnimationType   = "fade" | "slide" | "scale" | "rotate" | "bounce" | String ;
EasingFunction  = "linear" | "ease" | "ease-in" | "ease-out" | "ease-in-out" | String ;
AnimationTrigger = "enter" | "exit" | "hover" | "click" | "scroll" | Expression ;
```

### Stages

```ebnf
StageDecl       = "stage" Identifier "{" StageBody "}" ;

StageBody       = { StageField } ;

StageField      = "budget" ":" BudgetExpr
                | "anchor" ":" AnchorSpec
                | "phases" ":" PhasesBlock
                | "default" ":" PhaseConfig
                | "transition" ":" TransitionBlock
                ;

PhasesBlock     = "{" PhaseEntry { "," PhaseEntry } "}" ;

PhaseEntry      = PhaseSigil ":" PhaseConfig ;

PhaseConfig     = "{" PhaseConfigField { "," PhaseConfigField } "}" ;

PhaseConfigField = "arrangement" ":" ArrangementExpr
                 | "visible" ":" IdentifierList
                 | "faded" ":" IdentifierList
                 | "hidden" ":" IdentifierList
                 | "dominant" ":" Identifier
                 ;

TransitionBlock = "{" TransitionField { "," TransitionField } "}" ;

TransitionField = "duration" ":" DeadlineExpr
                | "curve" ":" EasingFunction
                | "sequence" ":" SequenceKind
                | "stagger" ":" DeadlineExpr      (* NEW *)
                ;

SequenceKind    = "simultaneous" | "anchor_first" | "content_first" 
                | "staggered" [ "(" Number ")" ]
                | "orchestrated" [ "(" String ")" ]  (* NEW *)
                ;
```

### Flows

```ebnf
FlowDecl        = "flow" Identifier "{" FlowBody "}" ;

FlowBody        = { FlowField } ;

FlowField       = "trigger" ":" TriggerExpr
                | "steps" ":" StepList
                | "on_stall" ":" StallSpec
                | "terminal" ":" TerminalExpr
                | "cancel" ":" CancelSpec        (* NEW *)
                | "retry" ":" RetrySpec          (* NEW *)
                ;

StepList        = "[" StepDecl { "," StepDecl } "]" ;

StepDecl        = "step" Identifier "{" StepBody "}" ;

StepBody        = { StepField } ;

StepField       = "duration" ":" ( DeadlineExpr | "unbounded" )
                | "state" ":" StateKind
                | "claim" ":" ClaimRef
                | "exit" ":" ExitCondition
                | "affordances" ":" IdentifierList
                | "parallel" ":" ParallelSteps   (* NEW *)
                | "branch" ":" BranchSpec        (* NEW *)
                ;

StateKind       = "acquiring" | "streaming" | "processing" | "completing" | "settled" | Identifier ;

ExitCondition   = "on_event" "(" Identifier ")"
                | "on_complete"
                | "on_timeout"
                | "when" "(" Expression ")"      (* NEW *)
                ;

StallSpec       = "{" StallField { "," StallField } "}" ;

StallField      = "threshold" ":" DeadlineExpr
                | "surface" ":" FailureSigil
                | "recovery" ":" IdentifierList
                ;

TerminalExpr    = "success" | FailureSpec { "|" FailureSpec } ;

ParallelSteps   = "[" StepDecl { "," StepDecl } "]" ;  (* NEW *)

BranchSpec      = "{" BranchCase { "," BranchCase } "}" ;  (* NEW *)
BranchCase      = Expression ":" StepDecl ;

CancelSpec      = "{" "graceful" ":" Boolean "," "cleanup" ":" Identifier "}" ;  (* NEW *)
RetrySpec       = "{" "max_attempts" ":" Number "," "backoff" ":" BackoffStrategy "}" ;  (* NEW *)
BackoffStrategy = "linear" | "exponential" | "fibonacci" | Expression ;
```

### Bonds and Seams

```ebnf
BondDecl        = "bond" Identifier "between" "(" IdentifierList ")" "{" BondBody "}" ;

BondBody        = { BondField } ;

BondField       = "kind" ":" BondKind
                | "direction" ":" Direction
                | "strength" ":" Strength
                | "on_break" ":" FailureSigil
                | "bidirectional" ":" Boolean     (* NEW *)
                ;

BondKind        = Identifier | String ;
Direction       = Identifier | String ;
Strength        = "weak" | "strong" | "required" | Number ;

SeamDecl        = "seam" Identifier "between" "(" IdentifierList ")" "{" SeamBody "}" ;

SeamBody        = { SeamField } ;

SeamField       = "kind" ":" SeamKind
                | "passage" ":" IdentifierList
                | "filter" ":" FilterExpr
                | "failure" ":" FailurePropagation
                | "transform" ":" TransformSpec   (* NEW *)
                ;

SeamKind        = "hard" | "soft" | "elastic" | "selective" | Identifier ;

FilterExpr      = Expression ;

FailurePropagation = "{" PropagationField { "," PropagationField } "}" ;

PropagationField = "blocks" ":" FailureSigilList
                 | "passes" ":" FailureSigilList
                 | "transforms" ":" TransformMap
                 | "all_pass" ":" Boolean
                 | "all_block" ":" Boolean
                 ;

TransformSpec   = "{" TransformRule { "," TransformRule } "}" ;  (* NEW *)
TransformRule   = Expression "=>" Expression ;
```

### Contracts

```ebnf
ContractDecl    = "contract" Identifier "{" ContractBody "}" ;

ContractBody    = { ContractField } ;

ContractField   = "trigger" ":" TriggerExpr
                | "obligation" ":" ObligationExpr
                | "deadline" ":" DeadlineExpr
                | "on_breach" ":" FailureSigil
                | "compensation" ":" CompensationSpec  (* NEW *)
                ;

TriggerExpr     = Identifier "(" [ ArgumentList ] ")" ;

ObligationExpr  = Identifier "(" [ ArgumentList ] ")" ;

DeadlineExpr    = "ms" "(" Number ")"
                | "s" "(" Number ")"
                | "m" "(" Number ")"
                | "h" "(" Number ")"
                | "session"
                | "persistent"
                | "none"
                | "unbounded"
                ;

CompensationSpec = "{" CompensationAction { "," CompensationAction } "}" ;  (* NEW *)
CompensationAction = "rollback" | "retry" | "notify" | FunctionCall ;
```

### NEW Declarations - Enhanced Primitives

```ebnf
(* Modal Declaration *)
ModalDecl       = "modal" Identifier "{" ModalBody "}" ;

ModalBody       = { ModalField } ;

ModalField      = "title" ":" String
                | "content" ":" ContentRef
                | "size" ":" ModalSize
                | "closable" ":" Boolean
                | "backdrop" ":" BackdropSpec
                | "trigger" ":" TriggerExpr
                | "actions" ":" IdentifierList
                | "animation" ":" AnimationSpec
                | "z_index" ":" Number
                ;

ModalSize       = "small" | "medium" | "large" | "fullscreen" | Expression ;

BackdropSpec    = "{" "blur" ":" Boolean "," "dismiss_on_click" ":" Boolean "}" ;

ContentRef      = Identifier | InlineContent ;
InlineContent   = "{" { Declaration } "}" ;

(* Toast/Notification Declaration *)
ToastDecl       = "toast" Identifier "{" ToastBody "}" ;

ToastBody       = { ToastField } ;

ToastField      = "message" ":" String
                | "type" ":" ToastType
                | "duration" ":" DeadlineExpr
                | "position" ":" Position
                | "dismissable" ":" Boolean
                | "action" ":" Identifier
                | "icon" ":" String
                ;

ToastType       = "info" | "success" | "warning" | "error" | String ;

Position        = "top-left" | "top-center" | "top-right" 
                | "bottom-left" | "bottom-center" | "bottom-right"
                | "center" | Expression
                ;

NotificationDecl = "notification" Identifier "{" NotificationBody "}" ;

NotificationBody = { NotificationField } ;

NotificationField = "title" ":" String
                  | "body" ":" String
                  | "icon" ":" String
                  | "priority" ":" Priority
                  | "persistent" ":" Boolean
                  | "actions" ":" IdentifierList
                  | "timestamp" ":" Expression
                  | "read" ":" Boolean
                  ;

Priority        = "low" | "normal" | "high" | "urgent" | Number ;

(* Dialog Declaration *)
DialogDecl      = "dialog" Identifier "{" DialogBody "}" ;

DialogBody      = { DialogField } ;

DialogField     = "type" ":" DialogType
                | "title" ":" String
                | "message" ":" String
                | "buttons" ":" ButtonList
                | "default_button" ":" Identifier
                | "icon" ":" String
                | "timeout" ":" DeadlineExpr
                ;

DialogType      = "alert" | "confirm" | "prompt" | "custom" ;

ButtonList      = "[" ButtonSpec { "," ButtonSpec } "]" ;

ButtonSpec      = "{" "label" ":" String "," "value" ":" Expression 
                [ "," "style" ":" ButtonStyle ] "}" ;

ButtonStyle     = "primary" | "secondary" | "destructive" | "ghost" | String ;

(* Menu Declaration *)
MenuDecl        = "menu" Identifier "{" MenuBody "}" ;

MenuBody        = { MenuField } ;

MenuField       = "items" ":" MenuItemList
                | "type" ":" MenuType
                | "trigger" ":" Identifier
                | "position" ":" MenuPosition
                | "nested" ":" Boolean
                | "icons" ":" Boolean
                | "shortcuts" ":" Boolean
                ;

MenuType        = "dropdown" | "context" | "popup" | "mega" | "sidebar" ;

MenuPosition    = Position | "auto" ;

MenuItemList    = "[" MenuItem { "," MenuItem } "]" ;

MenuItem        = "{" MenuItemField { "," MenuItemField } "}" 
                | "---"  (* separator *)
                ;

MenuItemField   = "label" ":" String
                | "action" ":" Identifier
                | "shortcut" ":" String
                | "icon" ":" String
                | "disabled" ":" Expression
                | "submenu" ":" MenuItemList
                | "badge" ":" String
                ;

(* Component Declaration - for reusable components *)
ComponentDecl   = "component" Identifier [ "(" ParameterList ")" ] "{" ComponentBody "}" ;

ComponentBody   = { Declaration } ;
```

### Common Sub-Expressions

```ebnf
IdentifierList  = "[" [ Identifier { "," Identifier } ] "]" ;

ContractList    = "[" [ ContractDecl { "," ContractDecl } ] "]" ;

FailureSpecList = "[" [ FailureSpec { "," FailureSpec } ] "]" ;

FailureSpec     = "{" FailureField { "," FailureField } "}" ;

FailureField    = "trigger" ":" Expression
                | "surfaces" ":" FailureSigil
                | "propagates" ":" PropagationBehavior
                ;

PropagationBehavior = "no" | "yes" | "conditional" ;

EventHandlerList = "[" [ EventHandler { "," EventHandler } ] "]" ;

EventHandler    = "{" "event" ":" EventType "," "handler" ":" Identifier "}" ;

EventType       = "click" | "hover" | "focus" | "blur" | "change" | "input" 
                | "submit" | "keydown" | "keyup" | "scroll" | "resize"
                | String
                ;

FailureSigilList = "[" [ FailureSigil { "," FailureSigil } ] "]" ;

TransformMap    = "{" [ TransformEntry { "," TransformEntry } ] "}" ;

TransformEntry  = FailureSigil "->" FailureSigil ;

Boolean         = "true" | "false" ;
```

### Type System (NEW - for future type checking)

```ebnf
TypeAnnotation  = ":" Type ;

Type            = PrimitiveType
                | CollectionType
                | FunctionType
                | UnionType
                | CustomType
                ;

PrimitiveType   = "string" | "number" | "boolean" | "void" | "any" ;

CollectionType  = "array" "<" Type ">"
                | "map" "<" Type "," Type ">"
                | "set" "<" Type ">"
                ;

FunctionType    = "(" [ TypeList ] ")" "=>" Type ;

TypeList        = Type { "," Type } ;

UnionType       = Type "|" Type { "|" Type } ;

CustomType      = Identifier [ "<" TypeList ">" ] ;
```

## Semantic Rules

### 1. Name Resolution
- All identifiers must be declared before use
- No duplicate names within the same scope
- Imports are resolved before local declarations

### 2. Type Constraints
- Certainty sigils only valid in certainty contexts
- Phase sigils only valid in phase contexts
- Failure sigils only valid in failure contexts

### 3. Budget Conservation
- Sum of child budgets ≤ parent budget (within tolerance)
- `whole(n)` where n ∈ (0, 1] for fractional allocation
- `fixed(n)` must not exceed parent allocation

### 4. Load Ceiling (λΩ)
- Maximum 9 independently visible elements per vessel (7+2 rule)
- Faded elements count as 0.5 load
- Hidden elements contribute 0 load

### 5. Phase Coupling
- Vessels must be in-scope for current phase
- Stage phase configs must cover all reachable phases or provide default
- Anchor elements cannot be in hidden set

### 6. Certainty Grades
- Composite certainty = minimum of constituent certainties
- AI-generated content cannot be τ✓ (certain)
- Stale decay reduces certainty over time

### 7. Failure Propagation
- Failures propagate through seams unless blocked
- Seam filters determine pass/block/transform behavior
- Cascade paths must be acyclic

### 8. Contract Obligations
- Execute obligations require breach handlers
- Deadlines must be positive
- Acknowledge contracts default to 200ms deadline

### 9. Flow Steps
- Steps must form valid state machine
- Unbounded steps require stall detection
- Terminal states must be reachable

### 10. Expression Evaluation (NEW)
- Conditional expressions must have boolean condition
- Binary operators require compatible types
- Function calls must reference defined functions

### 11. Module System (NEW)
- Import paths must be resolvable
- Circular imports are forbidden
- Component parameters must match usage

### 12. Responsive Design (NEW)
- Breakpoints must be ordered (mobile < tablet < desktop)
- Responsive budgets must maintain conservation law
- Animation triggers must reference valid events

## Reserved Keywords

```
claim, afford, vessel, stage, flow, bond, seam, contract, let, step,
between, any, none, auto, unbounded, session, composite, source, with,
whole, fixed, ceiling, shared, sequence, equal, dominant, grid, free,
stack, adaptive, primary, secondary, tertiary, background, hidden,
low, medium, high, critical, import, as, from, component, modal, toast,
notification, dialog, menu, when, unless, compute, watch, if, then, else,
responsive, animation, parallel, branch, retry, cancel, transform
```

## File Extension

`.guilds` - GUILDS specification file

## MIME Type

`application/x-guilds` or `text/x-guilds`

## Grammar Version

GUILDS v2.1 - Extended with expressions, modules, and enhanced primitives

---

## Examples

### Basic Claim with Computed Value
```guilds
claim UserScore {
    content:     text(score_display)
    certainty:   0x03C40x2713
    compute:     (base_score, multiplier) => base_score * multiplier
    watch:       [base_score, multiplier] => recalculate()
    when:        user_authenticated == true
}
```

### Modal with Animation
```guilds
modal ConfirmationDialog {
    title:       "Confirm Action"
    content:     ConfirmContent
    size:        medium
    closable:    true
    backdrop:    { blur: true, dismiss_on_click: false }
    actions:     [ConfirmButton, CancelButton]
    animation:   {
        type: "fade",
        duration: ms(300),
        easing: "ease-out",
        trigger: "enter"
    }
}
```

### Responsive Vessel
```guilds
vessel MainPanel {
    budget:      responsive({
        mobile:  whole(1.0),
        tablet:  whole(0.8),
        desktop: whole(0.6)
    })
    arrangement: responsive({
        mobile:  stack(vertical),
        desktop: grid(3, 2)
    })
    contains:    [Header, Content, Footer]
}
```

### Flow with Branches
```guilds
flow PaymentProcess {
    trigger:     user_action(CheckoutButton)
    steps: [
        step ValidateCart {
            duration: s(2)
            state:    processing
            branch:   {
                cart_valid:   next_step,
                cart_invalid: error_step
            }
        },
        step ProcessPayment {
            duration: s(5)
            state:    processing
            parallel: [VerifyCard, CalculateTax]
        }
    ]
    retry:       { max_attempts: 3, backoff: "exponential" }
    terminal:    success | failure(payment_failed)
}
```

### Import and Component Reuse
```guilds
import "./components/buttons.guilds" as Buttons
import "@guilds/ui-kit" { Card, Badge, Icon }

component CustomPanel(title, items) {
    vessel Panel {
        contains: [
            Card { title: title },
            ItemList { items: items }
        ]
    }
}
```

---

## Change Log

### v2.1 (Current)
- Added expression evaluation system
- Added module/import system  
- Added new primitives (modal, toast, notification, dialog, menu)
- Added conditional rendering (when, unless)
- Added computed properties and watchers
- Added responsive design support
- Added animation specifications
- Added flow branches and parallel steps
- Added component declarations
- Added type annotations (preparation for type checker)

### v2.0
- Initial EBNF specification
- Core primitives (claim, afford, vessel, stage, flow, bond, seam)
- Sigil-based encoding for phases, certainty, failures
- Budget system and load ceiling
- Phase coupling and transitions
- Failure propagation through seams
- Contract obligations

---

End of GUILDS v2.1 EBNF Specification
