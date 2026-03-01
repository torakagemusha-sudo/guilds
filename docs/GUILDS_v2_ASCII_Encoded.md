# GUILDS
## GUI Language: Invariant Domain Semantics
### Version 2.0 0x2014 Complete Standalone Language

```
Author   : Claude (Anthropic)
Version  : 2.0
Status   : Language Specification (pre-parser)
Paradigm : Contract-typed, attention-budgeted, certainty-graded, phase-coupled

This document specifies GUILDS as a complete, standalone language for
describing graphical user interfaces. It requires no companion specification.
It covers structure, layout, content, interaction, motion, information display,
failure, and the full grammar of system-human dialogue.

Core ontological commitment:
  A GUI is not a layout.
  A GUI is a conversation between a system and a human
  conducted within a finite budget of cognitive resources.
  Every design decision is a resource allocation decision.
  Every display is an assertion with a certainty grade.
  Every change is a commitment with a deadline.
  Every failure is a structured state, never an absence.
```

---

## PART I 0x2014 FOUNDATIONS

### 1.1 The Five Domains

GUILDS is built from five irreducible primitive domains.
All higher constructs decompose to these.

```
0x039B 0x2014 COGNITIVE DOMAIN     (attention, load, salience, focus)
0x0399 0x2014 INTENT DOMAIN        (task, phase, horizon, abandon)
0x03C4 0x2014 CERTAINTY DOMAIN     (grade, provenance, stakes, decay)
0x0394 0x2014 DIALOGUE DOMAIN      (turn type, obligation, grammar)
0x03A6 0x2014 FAILURE DOMAIN       (kind, scope, cause, recovery, propagation)
```

### 1.2 The Six Axioms

These are not guidelines. Violation of an axiom is a type error.

```
AXIOM 0x039B 0x2014 CONSERVATION
  A human has exactly one focus at any moment.
  Total cognitive load has a hard ceiling of 7 0x00B1 2 independent elements.
  No interface may demand more. This is not a style choice.
  Attention not spent costs nothing. Attention demanded and wasted
  costs error. There is no neutral element. Decoration taxes.

AXIOM 0x0399 0x2014 COUPLING
  What is visible must be a function of what the human is trying to do.
  A surface that renders identically across all task phases
  is wasting the cognitive budget of the phases it is not serving.
  Surface = f(intent). This is not personalization. It is honesty.

AXIOM 0x03C4 0x2014 DISCLOSURE
  Every system-generated assertion carries a certainty grade.
  Hiding a certainty grade does not mean certain.
  It means the system has chosen to lie by omission.
  There are no ungradable assertions. Grade or do not assert.

AXIOM 0x0394 0x2014 GRAMMAR
  The system speaks. This is not optional in any interactive interface.
  Every form of system speech has a type, and each type
  has obligations that cannot be discharged by other types.
  A warning cannot be replaced by an assertion.
  An escalation cannot be replaced by silence.
  Grammar is not aesthetic. It is ethical.

AXIOM 0x03A6 0x2014 STRUCTURE
  Every failure is a state with properties, not an absence of success.
  Properties: kind, scope, cause, recovery path, propagation map.
  "Something went wrong" states none of these.
  Silent failure 0x2014 failure that does not surface 0x2014 is always a violation.
  No exceptions. No extenuating circumstances.

AXIOM E 0x2014 ECONOMY
  Every element earns its presence or it must not render.
  Earning presence requires: attention yield > attention cost.
  An element that consumes attention without returning value
  is extracting cognitive labor from the human without consent.
```

### 1.3 Type Hierarchy

```
-- GUILDS is typed. Every expression has a type.
-- Types are either primitive or composed.

-- Primitive types (lowercase)
attention  : 0x039B-type
intent     : 0x0399-type
certainty  : 0x03C4-type
dialogue   : 0x0394-type
failure    : 0x03A6-type

-- Composed types (Capitalized)
Vessel     : the fundamental renderable unit
Claim      : a system assertion with certainty
Contract   : a system commitment with deadline
Bond       : a declared relationship between Vessels
Seam       : an interface between Vessels (where failures often propagate)
Flow       : a temporal behavior (state change over time)
Affordance : an offered interaction with obligation
Stage      : a Vessel that transforms based on intent phase
Budget     : an attention allocation with hard ceiling
Arrangement: how a Vessel partitions its Budget among children
```

---

## PART II 0x2014 PRIMITIVE TABLES

### 2.1 0x039B 0x2014 Cognitive Primitives

```
Symbol  Name         Type      Definition                        Invariant
0x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x2500
0x25C9       focus        attention  Single locus of conscious         Exactly one 0x25C9 per human;
                                processing at any moment          cannot be split

0x25CB       peripheral   attention  In visual field; not actively     0x25CB change may migrate 0x25C9;
                                processed; background awareness   cost is low but nonzero

0x039B0x2193      cost         scalar     Attention demanded by element     0x2200 element: 0x039B0x2193 > 0;
                     [0,1]      when rendered                     no element is free

0x039B0x2191      yield        scalar     Cognitive value returned          Element earns presence
                     [0,1]      to human by attending             iff 0x039B0x2191 > 0x039B0x2193

0x039B0x03A9      load         scalar     Total cognitive weight of         0x039B0x03A9 0x2264 7 0x00B1 2 independent
                     [0,0x221E)      all visible elements combined     elements; ceiling is hard

0x2726       salience     attention  Degree to which element draws     0x2726 must be proportional
                                0x25C9 migration toward it             to 0x039B0x2191, not 0x039B0x2193

0x2693       anchor       attention  Stable spatial reference that     0x2693 position is invariant;
                                spatial memory depends on         it cannot move across
                                                                  state transitions

0x039B0x0303       fade         attention  Element becoming less prominent   Applied to elements whose
                                as task phase diverges            phase coupling is inactive;
                                                                  fade, never abrupt removal

0x039B0x03A8      chunk        attention  Set of elements processed as      Nesting depth 0x2264 3 before
                                single cognitive unit             chunk penalty activates;
                                                                  deep nesting = load spike
```

**Cognitive Laws**

```
YIELD LAW:     0x2200 element e: 0x039B0x2191(e) / 0x039B0x2193(e) > 1.0  0x2228  e must not render
LOAD LAW:      0x039B0x03A9(surface) 0x2264 7 0x00B1 2 at all times; enforced by Budget type
ANCHOR LAW:    0x2693 is invariant across all phase transitions 0x0399.0x03C6
SALIENCE LAW:  0x2726(e) 0x221D 0x039B0x2191(e), not 0x039B0x2193(e) or cost-to-produce(e)
FADE LAW:      When 0x0399.0x03C6 changes, elements not relevant to new phase must 0x039B0x0303 (fade)
               not disappear; abrupt removal violates spatial memory
ECONOMY LAW:   Decorative elements with 0x039B0x2191 = 0 are violations of Axiom E
```

---

### 2.2 0x0399 0x2014 Intent Primitives

```
Symbol  Name         Type      Definition                        Invariant
0x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x2500
0x2295       task         intent    The declared or inferred goal     Exactly one 0x2295 active;
                               the human is pursuing             system should reflect it

0x03C6       phase        intent    Current stage of task execution   Phases are ordered and
                               within the task 0x2295                 transition has cost

0x03C60x2080      orient       phase     Human building mental model;      High information density;
                               understanding context             low action density; low 0x039B0x03A9
                               before acting                     pressure on execute tools

0x03C60x2081      execute      phase     Human performing the primary      Low noise; maximum tool
                               task action                       access; 0x039B0x03A9 minimized;
                                                                 irrelevant elements 0x039B0x0303

0x03C60x2082      verify       phase     Human confirming result is        Prior state visible;
                               correct before committing         comparison surfaces active;
                                                                 provenance 0x03C40x2190 accessible

0x03C60x2083      integrate    phase     Human incorporating result        Transition out; persistence
                               into broader context              layer writes; task closes;
                                                                 celebration 0x03940x2605 if earned

0x03C60x1D63      recover      phase     Human and system restoring        Prior state visible;
                               function after failure            recovery options explicit;
                                                                 nothing hidden

0x03C60x2205      idle         phase     No active task; resting state     Minimal surface; 0x039B0x03A9 0x2192 0;
                               or between tasks                  readiness signaled not imposed

0x2194       horizon      intent    Temporal scope of current         Immediate / Session /
                               intent                            Project / Persistent

0x2298       abandon      intent    Human exits task without          0x2298 is valid; system must
                               completing it                     not penalize or guilt-prompt
                                                                 May offer restore once.
```

**Intent Laws**

```
PHASE ORDER:    0x03C60x2080 0x2192 0x03C60x2081 0x2192 0x03C60x2082 0x2192 0x03C60x2083 is the canonical path;
                shortcuts permitted; skipping 0x03C60x2082 incurs risk, not error
COUPLING LAW:   Surface(0x03C60x2099) 0x2260 Surface(0x03C60x2098) for n 0x2260 m (unless trivially simple task)
                Same surface across all phases = intent-blindness violation
ABANDON LAW:    0x2298 must be honored without penalty, guilt, or unsolicited prompt
                System may offer resume path exactly once, not repeatedly
IDLE LAW:       0x03C60x2205 surface must not impose 0x039B0x03A9 on a human not currently working
```

---

### 2.3 0x03C4 0x2014 Certainty Primitives

```
Symbol  Name         Type       Definition                       Invariant
0x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x2500
0x03C40x2713      certain      certainty  Known with high confidence;      No visual qualification
                                verified or directly observed    required; but absence of 0x03C4
                                                                 grade 0x2260 0x03C40x2713. Must be explicit.

0x03C4~      inferred     certainty  Derived from evidence;           Visually distinguishable
                                not directly observed            from 0x03C40x2713; stakes determine
                                                                 visual prominence

0x03C4?      probable     certainty  May be correct; credible         Primary alternative must
                                alternatives exist               be surfaced alongside 0x03C4?

0x03C40x2205      unknown      certainty  Information not available        Must be explicit; blank
                                                                 space 0x2260 0x03C40x2205; never elided

0x03C40x2694      contested    certainty  Conflicting evidence;            Both sides must be shown;
                                no consensus                     resolution cannot be forced
                                                                 by UI choice

0x03C40x231B      stale        certainty  Valid at time t0x2080; may have       t0x2080 and elapsed 0x0394t must
                     (t0x2080, 0x0394t)   changed since then              be visible; at threshold,
                                                                 degrades to 0x03C4?

0x03C4!      stakes       certainty  Consequence magnitude if         0x03C4! 0x2265 high amplifies visual
                     {lo,med,   certainty is wrong               weight of 0x03C4? 0x03C4~ 0x03C40x2205;
                      hi,crit}                                   0x03C4! = crit requires explicit
                                                                 acknowledgment before action

0x03C40x2190      provenance   certainty  Origin and derivation path       Reachable within 0x2264 2
                                of an assertion                  interactions from any
                                                                 displayed claim

0x03C40x2229      composite    certainty  Certainty of a display           0x03C4(A 0x2218 B) = min(0x03C4(A), 0x03C4(B));
                                built from parts                 certainty degrades, never
                                                                 compounds
```

**Certainty Laws**

```
DISCLOSURE LAW: 0x2200 system assertion a: 0x03C4(a) must be visible
                Hiding 0x03C4 implies 0x03C40x2713 by omission. That is a lie.
COMPOSITION:    0x03C4(A 0x2218 B) = min(0x03C4(A), 0x03C4(B))  0x2014 certainty is minimum of parts
UNKNOWN LAW:    0x03C40x2205 renders as explicit marker; it is not the absence of a marker
CONTEST LAW:    0x03C40x2694 must show both evidence streams; suppressing one = violation
STAKES AMP:     When 0x03C4! 0x2265 high: 0x03C4? and 0x03C4~ render at increased visual weight
PROVENANCE:     0x03C40x2190 reachable in 0x2264 2 interactions from any displayed claim
STALE DECAY:    0x03C40x231B visual prominence increases with elapsed 0x0394t;
                at system-defined threshold, 0x03C40x231B degrades automatically to 0x03C4?
```

---

### 2.4 0x0394 0x2014 Dialogue Primitives

```
Symbol  Name           Type      Definition                       Invariant
0x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x2500
0x03940x2192      assert         dialogue  System declares a fact,          Must carry 0x03C4 grade;
                                 result, or status                0x03940x2192 without 0x03C4 = VIOL-01

0x0394?      query          dialogue  System requests information      Must justify its 0x039B0x2193 cost;
                                 or decision from human           only one 0x0394? per turn unless
                                                                  0x03C6 transition occurs

0x03940x2295      propose        dialogue  System suggests action for       Must be binary: accept/reject;
                                 explicit human approval          silent acceptance prohibited;
                                                                  0x03940x26A0 must precede if risk

0x03940x26A0      warn           dialogue  System signals risk before       Must fire before the 0x03940x2295 or
                                 action occurs                    action it qualifies;
                                                                  post-hoc warning = violation

0x03940x2713      acknowledge    dialogue  System confirms receipt          Within deadline (default 200ms);
                                 of human input                   absence creates uncertainty
                                                                  that costs 0x039B0x2193

0x03940x2205      silence        dialogue  System has no output             0x03940x2205 is valid; must be
                                 (intentional, declared)          distinguishable from 0x03A60x27F3
                                                                  and 0x03A60x22A3; silence 0x2260 failure

0x03940x2190      correct        dialogue  System revises prior 0x03940x2192          Prior 0x03940x2192 remains visible
                                                                  during 0x03940x2190; correction is
                                                                  additive, not erasure

0x03940x2191      escalate       dialogue  System transfers decision        Must include: reason, 0x22652
                                 requiring human judgment         options, consequence of each,
                                                                  declared safe default

0x03940x2605      celebrate      dialogue  System marks significant         Proportional to significance;
                                 positive outcome                 asymmetric (errors always
                                                                  shown; celebration earned)
```

**Dialogue Laws**

```
ORDER LAW:      0x03940x26A0 precedes 0x03940x2295 precedes 0x03940x2192
                Reversing this order is a disclosure violation; no exceptions
QUERY COST:     One 0x0394? per system turn unless 0x03C6 transition occurs between them
CORRECTION:     0x03940x2190 must not delete prior 0x03940x2192; prior remains visible; revision is additive
SILENCE VALID:  0x03940x2205 is a first-class dialogue type; system may legitimately be silent
ACK DEADLINE:   0x03940x2713 must fire within system-declared deadline (default: 200ms)
ESCALATE FULL:  0x03940x2191 without {reason, options, consequences, default} = VIOL-06
CELEBRATE LAW:  0x03940x2605 is earned, not performed; it is asymmetric with failure surfacing
```

---

### 2.5 0x03A6 0x2014 Failure Primitives

```
Symbol  Name         Type     Definition                        Invariant
0x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x25000x2500
0x03A60x2193      degraded     failure  Component operating at            Capability loss must be
                               reduced capacity                  specified; 0x03A60x2193 0x2260 0x03A60x2717

0x03A60x22A3      blocked      failure  Cannot proceed; awaiting          Blocker must be named;
                               external input or event           indefinite spin without
                                                                 cause = VIOL-10

0x03A60x2205      lost         failure  State or data unrecoverable       Acknowledge immediately;
                                                                 surface any partial recovery

0x03A60x00BD      partial      failure  Result delivered but              Completeness ratio visible;
                               incomplete                        0x03A60x00BD 0x2260 0x03A60x2717; partial is honoured

0x03A60x231B      stale        failure  Component operating on            Same as 0x03C40x231B but for system
                               outdated state                    state, not display content

0x03A60x27F3      recovering   failure  System actively restoring         Progress must be visible;
                               function                          0x03A60x27F3 without progress = 0x03A60x2014
                                                                 (spinning lie = silent failure)

0x03A60x2192      cascade      failure  Failure propagating to            Full dependency chain visible
                               dependents                        before user acts; not after

0x03A6?      unknown      failure  Cause cannot be determined        0x03A6? is valid; must be
                                                                 distinguished from other kinds;
                                                                 "something went wrong" 0x2260 0x03A6?

0x03A60x2717      fatal        failure  Complete failure of component     Recovery path required, OR
                                                                 explicit acknowledgment of
                                                                 impossibility

0x03A60x2014      silent       failure  Failure with no surface           Always a violation;
                               (notification                     no exceptions; no edge cases;
                               suppressed)                       no extenuating circumstances
```

**Failure Laws**

```
SCOPE LAW:     0x03A6 scope = minimum necessary; 0x03A60x2192 must be explicit, not assumed
NAMING LAW:    Every 0x03A6 must declare: kind, scope, cause (or 0x03A6?), recovery, propagation
SPIN LAW:      0x03A60x27F3 without measurable progress = 0x03A60x2014 (spinning lie is silent failure)
PARTIAL LAW:   0x03A60x00BD is honored as a result type, not collapsed to error; ratio required
SILENCE:       0x03A60x2014 is always a violation; there are no exceptions in this domain
RECOVERY:      Every 0x03A6 with a recovery path must show that path
               Every 0x03A6 with no recovery must acknowledge impossibility explicitly
UNKNOWN:       0x03A6? renders explicitly with "cause undetermined"; vague text 0x2260 0x03A6?
CASCADE:       0x03A60x2192 dependency map must be visible before user takes recovery action
```

---

## PART III 0x2014 COMPOSED TYPES

### 3.1 Budget

```
Budget is the fundamental resource unit of GUILDS.
It is the attention allocation for a Vessel and its contents.

Budget ::= 
    whole(n)          -- n 0x2208 [0, 1]: fraction of parent budget
  | fixed(n)          -- n independent of parent (use sparingly)
  | auto              -- computed from content; enforces YIELD LAW internally
  | ceiling(n, base)  -- base allocation with hard cap at n
  | shared(n, k)      -- n divided equally among k siblings

Budget laws:
  sum(child budgets) 0x2264 parent budget   (conservation)
  0x2200 budget b: b.ceiling 0x2264 7 0x00B1 2 independent elements (LOAD LAW)
  fixed() must declare justification   (it overrides the hierarchy)
```

### 3.2 Arrangement

```
Arrangement is how a Vessel partitions its Budget among children.
It replaces the concept of "layout" 0x2014 arrangement is a budget allocation
strategy, not a geometric prescription.

Arrangement ::=
    sequence(axis, weights)
      -- Children placed along axis; weights are proportional budget shares
      -- axis 0x2208 {primary, cross, depth}
      -- weights 0x2208 [Ratio] where sum(weights) = 1.0

  | equal(axis)
      -- Children share budget equally along axis

  | dominant(n, rest)
      -- Child n receives majority; rest share remainder
      -- Common pattern: dominant(0, tail) = main content + sidebar

  | grid(rows, cols, gap)
      -- Regular subdivision; each cell receives 1/(rows 0x00D7 cols) of budget
      -- gap reduces each cell by gap/budget

  | free(coordinate_system)
      -- Children declare their own position within parent's extent
      -- coordinate_system 0x2208 {cartesian, polar, radial}
      -- Highest load risk; requires explicit Budget ceiling

  | stack(axis, clip)
      -- Children occupy same position; z-ordered by declaration sequence
      -- clip: whether parent clips children that exceed its extent
      -- Used for overlays, popovers, modals

  | adaptive(intent_map)
      -- Arrangement changes based on 0x0399.0x03C6
      -- intent_map: Map<Phase, Arrangement>
      -- Implements COUPLING LAW mechanically

Arrangement laws:
  sum of child budgets within arrangement 0x2264 parent budget
  free() requires explicit ceiling declaration to prevent 0x039B0x03A9 violation
  adaptive() must declare arrangement for every phase in scope
```

### 3.3 Vessel

```
Vessel is the fundamental renderable unit in GUILDS.
It has a cognitive budget, a phase coupling, claims it makes,
contracts it holds, and children it contains.

Vessel ::= vessel <Name> {
    budget:      Budget
    phase:       Phase | any | [Phase, ...]
    arrangement: Arrangement
    anchor:      AnchorSpec?          -- stable reference points
    weight:      Weight               -- visual prominence, 0x221D budget
    contains:    [Vessel | Claim | Affordance]
    bonds:       [Bond]
    contracts:   [Contract]
    failures:    [FailureSpec]
    on:          [EventHandler]
}

-- AnchorSpec: declares which elements within this Vessel are 0x2693 anchors
-- Anchors must remain positionally stable across all phase transitions

-- Weight: how visually prominent this Vessel is relative to siblings
Weight ::= primary | secondary | tertiary | background | hidden

-- hidden is distinct from not-rendered:
-- hidden maintains its budget claim but contributes 0 to 0x039B0x03A9
-- It may become visible without layout recalculation
```

### 3.4 Claim

```
Claim is a system assertion with explicit certainty grading.
All information displayed by the system is a Claim.

Claim ::= claim <Name> {
    content:    ContentType
    certainty:  CertaintyType
    provenance: Source
    stakes:     StakesLevel
    freshness:  FreshnessSpec
    on_stale:   StaleAction
}

ContentType ::=
    text(value, typography)        -- textual assertion
  | numeric(value, unit, format)   -- quantified assertion
  | status(value, scale)           -- state within enumerated scale
  | comparison(a, b, basis)        -- relational assertion
  | aggregate(items, function)     -- collection-derived assertion
  | empty(reason)                  -- explicit 0x03C40x2205 declaration
  | redacted(reason)               -- information withheld; must state why

CertaintyType ::= 0x03C40x2713 | 0x03C4~ | 0x03C4? | 0x03C40x2205 | 0x03C40x2694 | 0x03C40x231B(t0x2080, elapsed) | composite(min_0x03C4)

Source ::=
    direct(system_component)       -- 0x03C40x2190 one hop
  | derived(source, method)        -- 0x03C40x2190 two hops; method visible
  | external(origin, fetch_time)   -- 0x03C40x2190 plus 0x03C40x231B; freshness mandatory
  | ai_generated(model, context)   -- 0x03C4~  minimum; never 0x03C40x2713
  | user_provided(session)         -- 0x03C40x2713 from user's perspective; verify context

FreshnessSpec ::=
    live                           -- refreshes continuously
  | polled(interval)               -- refreshes every interval
  | event_driven(trigger)          -- refreshes on event
  | static                         -- does not refresh; static content
  | snapshot(captured_at)          -- was live, now frozen; 0x03C40x231B applies

StaleAction ::=
    degrade_to(0x03C4?)                 -- when threshold elapsed, change grade
  | mark_stale                     -- keep content, add 0x03C40x231B indicator
  | remove                         -- remove from surface; leave 0x03C40x2205 marker
  | warn(0x03940x26A0)                      -- fire warning; await refresh

Claim laws:
  certainty(ai_generated) 0x2265 0x03C4~    (AI output is never 0x03C40x2713 by default)
  provenance always reachable in 0x2264 2 interactions
  content = empty(reason) MUST render 0x03C40x2205 marker, not blank space
  content = redacted(reason) MUST state reason; silent redaction = VIOL-08
```

### 3.5 Contract

```
Contract is a system commitment 0x2014 something the system promises to do.
Breaking a Contract is a Failure that must be surfaced.

Contract ::= contract <Name> {
    trigger:    Trigger
    obligation: Obligation
    deadline:   Duration | none
    on_breach:  FailureSpec
}

Trigger ::=
    user_action(affordance)        -- human takes action
  | system_event(source)           -- system detects event
  | phase_enter(0x03C6)                 -- task enters phase
  | phase_exit(0x03C6)
  | time(duration)                 -- elapsed time
  | condition(expression)          -- logical condition met

Obligation ::=
    acknowledge(within: Duration)  -- 0x03940x2713 fires within deadline
  | display(claim)                 -- Claim becomes visible
  | navigate(target_vessel)        -- surface transitions to target
  | execute(operation)             -- system performs operation
  | surface(failure)               -- if operation fails, 0x03A6 surfaces
  | escalate(0x03940x2191)                   -- decision transferred to human

Duration ::= ms(n) | s(n) | m(n) | h(n) | session | persistent | none

Contract laws:
  Every Contract breach must surface as 0x03A6 (Failure)
  A Contract with deadline = none is an infinite commitment (dangerous; flag)
  acknowledge obligations default deadline = 200ms
  Contracts are ordered: earlier Contracts may block later ones (document this)
```

### 3.6 Affordance

```
Affordance is an offered interaction with a binding Contract.
Every Affordance that a human can perceive and act on
must have a Contract specifying what the system will do.

Affordance ::= afford <Name> {
    perceivable:  PerceivabilitySpec
    offered:      InteractionType
    requires:     [Condition]         -- constraints on when available
    disables:     [Vessel]            -- what becomes unavailable during
    contracts:    [Contract]          -- what system commits to on activation
    on_unavail:   UnavailableSpec     -- how disabled state communicates
}

PerceivabilitySpec ::=
    always_visible               -- affordance permanently perceivable
  | context_revealed(trigger)   -- appears when context makes it relevant
  | mode_revealed(phase)        -- appears in specific phase only
  | progressive(threshold)      -- becomes more perceivable as relevance increases

-- PerceivabilitySpec law:
-- context_revealed and mode_revealed affordances
-- must still be discoverable; pure invisibility is VIOL-04

InteractionType ::=
    activate                     -- single action (click/tap/key)
  | toggle(states)               -- binary or multi-state switch
  | select(cardinality)          -- choose from set; cardinality 0x2208 {one, many, zero+}
  | input(type, constraints)     -- freeform entry
  | gesture(kind, axis)          -- directional or complex gesture
  | drag(source, target_spec)    -- positional transfer
  | navigate(target)             -- context transition

UnavailableSpec ::=
    fade_locked                  -- visually present but non-responsive; reason shown
  | hidden                       -- removed from surface; budget maintained
  | replaced(explanation)        -- replaced by explanation of why unavailable
  -- Note: fade_locked is preferred; hidden must justify why hiding is better

Affordance laws:
  0x2200 affordance a: perceivable(a) 0x2194 0x2203 contract(a)  (perceivable 0x27F9 contractually bound)
  on_unavail must communicate reason; silent locking = VIOL-07 (anonymous assertion)
  disables list must be complete; undeclared disabling is a Contract breach
  Affordances with requires conditions must keep conditions queryable by human
```

### 3.7 Bond

```
Bond is a declared relationship between two or more Vessels.
Bonds are first-class because relationships drive layout and behavior.
Declaring a Bond is declaring an invariant about how Vessels relate.

Bond ::= bond <Name> between (<Vessel>, <Vessel>, ...) {
    kind:       BondKind
    direction:  Direction?        -- for asymmetric bonds
    strength:   BondStrength      -- how tightly coupled
    on_break:   BreakResponse     -- what happens if bond is violated
}

BondKind ::=
    contains(depth)               -- first contains second; depth = recursion limit
  | adjacent(gap)                 -- share boundary; gap is spacing as budget fraction
  | corresponds(mapping)          -- change in first implies change in second
  | groups(by)                    -- siblings; grouped by shared attribute
  | excludes                      -- mutual exclusion; activating one deactivates other
  | sequences(ordering)           -- temporal or logical order declared
  | parallels                     -- simultaneous existence; no causal link
  | mirrors(transform)            -- one reflects the other with optional transform

BondStrength ::=
    rigid                         -- bond cannot be broken by system or user
  | flexible(range)               -- bond can flex within declared range
  | soft                          -- bond is a default; user may break

Direction ::= unidirectional(from, to) | bidirectional

BreakResponse ::=
    fail_hard(0x03A6)                  -- surface failure; refuse to proceed
  | degrade(0x03A60x2193)                   -- continue with degraded capability
  | adapt(fallback_bond)          -- substitute a weaker bond
  | notify(0x03940x26A0)                    -- warn but permit

Bond laws:
  contains bonds are transitive: if A contains B, and B contains C, then A contains C
  excludes bonds are symmetric: if A excludes B, then B excludes A
  rigid bonds that are broken are always 0x03A60x2717 (fatal failure of the bond)
  corresponds bonds must declare the mapping function; vague "related to" = violation
```

### 3.8 Seam

```
Seam is the interface between two Vessels 0x2014 where they meet.
Most UI failures propagate across Seams, not within Vessels.
Declaring Seams explicitly makes propagation paths visible.

Seam ::= seam <Name> between (<Vessel>, <Vessel>) {
    kind:       SeamKind
    passage:    [PassageType]     -- what can cross this seam
    filter:     FilterSpec?       -- what is blocked or transformed
    failure:    FailurePropagation
}

SeamKind ::=
    hard                          -- distinct boundary; neither leaks into other
  | soft                          -- permeable; visual blending permitted
  | shared_edge                   -- Vessels share a border that belongs to both
  | z_transition                  -- depth-based; one overlaps other on z-axis

PassageType ::=
    data(type)                    -- data values cross the seam
  | focus                         -- 0x25C9 can migrate across this seam
  | events(kind)                  -- events propagate across
  | failure(0x03A6)                    -- failure type propagates across
  | none                          -- sealed; nothing crosses

FailurePropagation ::=
    blocks(0x03A6_kinds)               -- named failure types stop at this seam
  | passes(0x03A6_kinds)               -- named failure types cross freely
  | transforms(0x03A6_from, 0x03A6_to)      -- failure transforms as it crosses
  | all_pass                      -- no filtering (high cascade risk; flag)
  | all_block                     -- fully isolated (may hide cascade; document)

Seam laws:
  all_pass seams require explicit documentation of cascade risk
  all_block seams require documentation of what happens when blocked failure accumulates
  0x25C9 can only migrate across seams declared as focus-passable
```

### 3.9 Stage

```
Stage is a Vessel that transforms its Arrangement and child visibility
based on current 0x0399.0x03C6. It mechanically implements the COUPLING LAW.

Stage ::= stage <Name> {
    budget:    Budget              -- consistent across all phases
    anchor:    AnchorSpec?         -- anchors must be phase-invariant
    phases:    {
        0x03C60x2080: PhaseConfig,
        0x03C60x2081: PhaseConfig,
        0x03C60x2082: PhaseConfig,
        0x03C60x2083: PhaseConfig,
        0x03C60x1D63: PhaseConfig,
        0x03C60x2205: PhaseConfig
    }
    default:   PhaseConfig         -- when phase is unknown or not listed
    transition: TransitionSpec     -- how surface changes between phases
}

PhaseConfig ::= {
    arrangement: Arrangement
    visible:     [Vessel | Claim | Affordance]
    faded:       [Vessel | Claim | Affordance]   -- present at reduced prominence
    hidden:      [Vessel | Claim | Affordance]   -- budget maintained; not rendered
    dominant:    Vessel?                          -- which vessel receives 0x25C9 bias
}

TransitionSpec ::= {
    duration:   Duration
    curve:      EasingCurve        -- linear | ease-in | ease-out | spring(params)
    sequence:   TransitionSequence
}

TransitionSequence ::=
    simultaneous           -- all elements change at once
  | anchor_first           -- anchors settle first; then content follows
  | content_first          -- content changes first; then layout settles
  | staggered(n)           -- elements change sequentially with n ms offset

Stage laws:
  anchor elements must appear in visible or faded in every PhaseConfig (never hidden)
  budget is constant across all phases (surface changes; budget does not)
  transition.duration must be 0x2265 threshold of perceptible change (0x2248 100ms)
  transition.duration must be 0x2264 threshold of frustration (0x2248 400ms for phase transitions)
```

### 3.10 Flow

```
Flow describes temporal behavior that is not covered by phase transitions.
This includes loading, streaming, animation, polling, and decay.

Flow ::= flow <Name> {
    trigger:    Trigger
    steps:      [Step]
    terminal:   TerminalState
    on_stall:   StallSpec
}

Step ::= step <Name> {
    duration:   Duration | unbounded
    state:      FlowState
    claim:      Claim?             -- what is asserted during this step
    affordances: [Affordance]      -- what is available during this step
    exit:       ExitCondition
}

FlowState ::=
    acquiring                      -- system fetching or computing
  | streaming(progress)            -- partial result arriving incrementally
  | processing                     -- computation in progress; no output yet
  | completing                     -- final steps; near-done
  | settled                        -- stable; flow ended

StallSpec ::= {
    threshold:  Duration           -- how long before stall is declared
    surface:    0x03A60x27F3 | 0x03A60x22A3 | 0x03A6?      -- how stall surfaces (never 0x03A60x2014)
    recovery:   [Affordance]       -- what human can do when stalled
}

ExitCondition ::=
    on_complete                    -- step exits when operation finishes
  | on_event(trigger)              -- step exits on specific event
  | on_timeout(duration, next)     -- step exits at timeout; next declares fallback
  | on_user(affordance)            -- step exits when user takes action

TerminalState ::= success | failure(0x03A6) | partial(0x03A60x00BD) | abandoned(0x2298)

Flow laws:
  Every Flow must declare terminal states; open-ended Flow is a violation
  Stall threshold must be declared; system must not spin silently past threshold
  streaming steps must show progress indicator (count, proportion, or activity)
  acquiring steps must distinguish from stall after StallSpec.threshold elapsed
```

---

## PART IV 0x2014 SYNTAX

### 4.1 Lexical Grammar

```
-- GUILDS uses UTF-8 encoding
-- Comments begin with -- and extend to end of line
-- Block comments: {- ... -}

-- Identifiers
<ident>    ::= [a-zA-Z_][a-zA-Z0-9_]*

-- Literals
<string>   ::= '"' <char>* '"'
<number>   ::= [0-9]+ ('.' [0-9]+)?
<duration> ::= <number> ('ms' | 's' | 'm' | 'h')
<fraction> ::= <number>    -- understood as [0,1]
<ratio>    ::= <number> ':' <number>

-- Reserved words
vessel     budget      phase      arrangement  anchor     weight
contains   bonds       contracts  failures     on         claim
content    certainty   provenance stakes       freshness  on_stale
afford     perceivable offered    requires     disables   on_unavail
bond       between     kind       direction    strength   on_break
seam       passage     filter     failure      propagation
stage      phases      default    transition   flow       steps
step       duration    state      exit         terminal   on_stall
contract   trigger     obligation deadline     on_breach

-- Certainty sigils (these are lexical tokens)
0x03C40x2713  0x03C4~  0x03C4?  0x03C40x2205  0x03C40x2694  0x03C40x231B

-- Dialogue sigils
0x03940x2192  0x0394?  0x03940x2295  0x03940x26A0  0x03940x2713  0x03940x2205  0x03940x2190  0x03940x2191  0x03940x2605

-- Failure sigils
0x03A60x2193  0x03A60x22A3  0x03A60x2205  0x03A60x00BD  0x03A60x231B  0x03A60x27F3  0x03A60x2192  0x03A6?  0x03A60x2717  0x03A60x2014

-- Cognitive sigils
0x25C9  0x25CB  0x039B0x2193  0x039B0x2191  0x039B0x03A9  0x2726  0x2693  0x039B0x0303

-- Phase sigils
0x03C60x2080  0x03C60x2081  0x03C60x2082  0x03C60x2083  0x03C60x1D63  0x03C60x2205
```

### 4.2 Expression Grammar

```
<program>       ::= <declaration>*

<declaration>   ::=
    <vessel_decl>
  | <claim_decl>
  | <afford_decl>
  | <bond_decl>
  | <seam_decl>
  | <stage_decl>
  | <flow_decl>
  | <contract_decl>
  | <let_decl>

-- Let bindings for reuse
<let_decl>      ::= 'let' <ident> '=' <expression>

-- Vessel
<vessel_decl>   ::= 'vessel' <ident> '{' <vessel_field>* '}'

<vessel_field>  ::=
    'budget'      ':' <budget_expr>
  | 'phase'       ':' <phase_expr>
  | 'arrangement' ':' <arrangement_expr>
  | 'anchor'      ':' <anchor_spec>
  | 'weight'      ':' <weight_expr>
  | 'contains'    ':' '[' <containee>* ']'
  | 'bonds'       ':' '[' <bond_ref>* ']'
  | 'contracts'   ':' '[' <contract_ref>* ']'
  | 'failures'    ':' '[' <failure_spec>* ']'
  | 'on'          ':' '[' <event_handler>* ']'

<containee>     ::= <ident> | <inline_vessel> | <inline_claim> | <inline_afford>

-- Claim
<claim_decl>    ::= 'claim' <ident> '{' <claim_field>* '}'

<claim_field>   ::=
    'content'    ':' <content_expr>
  | 'certainty'  ':' <certainty_expr>
  | 'provenance' ':' <source_expr>
  | 'stakes'     ':' <stakes_expr>
  | 'freshness'  ':' <freshness_expr>
  | 'on_stale'   ':' <stale_action>

-- Budget expressions
<budget_expr>   ::=
    'whole' '(' <fraction> ')'
  | 'fixed' '(' <number> ')'
  | 'auto'
  | 'ceiling' '(' <fraction> ',' <budget_expr> ')'
  | 'shared' '(' <fraction> ',' <number> ')'

-- Phase expressions
<phase_expr>    ::=
    'any'
  | <phase_sigil>
  | '[' <phase_sigil> (',' <phase_sigil>)* ']'

-- Arrangement expressions
<arrangement_expr> ::=
    'sequence' '(' <axis> ',' '[' <fraction>* ']' ')'
  | 'equal' '(' <axis> ')'
  | 'dominant' '(' <number> ',' <arrangement_expr> ')'
  | 'grid' '(' <number> ',' <number> ',' <fraction> ')'
  | 'free' '(' <coord_system> ')'
  | 'stack' '(' <axis> ',' <bool> ')'
  | 'adaptive' '(' '{' <phase_sigil> ':' <arrangement_expr> (',' <phase_sigil> ':' <arrangement_expr>)* '}' ')'

-- Event handlers
<event_handler> ::= 'on' <trigger_expr> '->' <response_expr>
<trigger_expr>  ::= <trigger_kind> '(' <trigger_args> ')'
<response_expr> ::= <response_kind> '(' <response_args> ')'

-- Certainty expressions
<certainty_expr> ::=
    0x03C40x2713 | 0x03C4~ | 0x03C4? | 0x03C40x2205 | 0x03C40x2694
  | '0x03C40x231B' '(' <timestamp> ',' <duration> ')'
  | 'composite' '(' '[' <certainty_expr>* ']' ')'

-- Stakes expressions
<stakes_expr>   ::= 'low' | 'medium' | 'high' | 'critical'
```

### 4.3 Type Checking Rules

```
-- The type checker enforces GUILDS laws at specification time.
-- Violations are type errors, not runtime warnings.

RULE TC-1 (Yield):
  0x2200 vessel v in surface: 0x039B0x2191(v) / 0x039B0x2193(v) > 1.0
  OR v.weight = background  (backgrounds have different yield calculus)
  OR v is declared decoration_only  (explicit opt-out, flagged for review)

RULE TC-2 (Load):
  0x2200 vessel v: count_independent_elements(v.contains) 0x2264 7 0x00B1 2
  Where count_independent_elements counts non-chunked, non-grouped elements

RULE TC-3 (Certainty):
  0x2200 claim c: c.certainty is explicitly declared
  If c.provenance.kind = ai_generated: c.certainty 0x2208 {0x03C4~, 0x03C4?, 0x03C40x2205, 0x03C40x2694}
    -- ai_generated claims cannot be 0x03C40x2713 without explicit override + justification

RULE TC-4 (Dialogue Order):
  0x2200 dialogue sequence in contract:
    0x03940x26A0 before 0x03940x2295 before 0x03940x2192
    (evaluated in execution order of contracts)

RULE TC-5 (Acknowledge Deadline):
  0x2200 contract c where c.obligation = acknowledge:
    c.deadline 0x2264 200ms  (unless explicitly overridden with justification)

RULE TC-6 (Anchor Stability):
  0x2200 element e where e declared as 0x2693:
    e appears in PhaseConfig.visible for every phase in scope (never hidden)

RULE TC-7 (Failure Surface):
  0x2200 operation o with possible failure:
    0x2203 contract c where c.trigger = operation_fail(o)
    AND c.obligation = surface(0x03A6)
    -- Every possible failure must have a surfacing contract

RULE TC-8 (Escalation Completeness):
  0x2200 dialogue d where d.type = 0x03940x2191:
    d declares {reason, options (0x2265 2), consequences (per option), default}
    If any field missing: type error

RULE TC-9 (Bond Symmetry):
  0x2200 bond b where b.kind = excludes:
    bond exists in both directions  (symmetric bonds must be declared once
    but type checker validates symmetry)

RULE TC-10 (Stall Coverage):
  0x2200 flow f where any step has duration = unbounded:
    f.on_stall is declared
    f.on_stall.surface 0x2260 0x03A60x2014  (stall cannot be silent)

RULE TC-11 (Seam Passage):
  0x2200 data d crossing seam s:
    d.type 0x2208 s.passage  (type checker validates passage declarations match usage)

RULE TC-12 (Phase Completeness in Stage):
  0x2200 stage s:
    s.phases covers every 0x03C6 in scope  OR  s.default is declared
    anchor elements appear in visible or faded in every PhaseConfig
```

---

## PART V 0x2014 EVALUATION RULES

### 5.1 Budget Evaluation

```
-- Budget is evaluated bottom-up, then validated top-down.

eval_budget(vessel v, parent_budget p):
  match v.budget with
  | whole(n)          -> n 0x00D7 p
  | fixed(n)          -> n
  | auto              -> sum(eval_budget(child, auto_share) for child in v.contains)
                         where auto_share = p / count(v.contains)
  | ceiling(n, base)  -> min(n 0x00D7 p, eval_budget(vessel with budget=base, p))
  | shared(n, k)      -> (n 0x00D7 p) / k

validate_budget(vessel v, parent_budget p):
  allocated = eval_budget(v, p)
  children_sum = sum(eval_budget(c, allocated) for c in v.contains)
  if children_sum > allocated:
    FAIL "Budget overflow in vessel " + v.name
  load = count_independent_elements(v)
  if load > 9:  -- 7 + 2 ceiling
    FAIL "Load ceiling exceeded in vessel " + v.name + ": " + load + " elements"
```

### 5.2 Certainty Evaluation

```
-- Certainty grades form an ordered lattice.
-- 0x03C40x2713 > 0x03C4~ > 0x03C4? > 0x03C40x231B > 0x03C40x2205  (ordering by confidence)
-- 0x03C40x2694 is orthogonal (contested, not gradable on confidence axis)

certainty_order = { 0x03C40x2713: 5, 0x03C4~: 4, 0x03C4?: 3, 0x03C40x231B: 2, 0x03C40x2205: 1 }

eval_certainty(composite([c0x2081, c0x2082, ..., c0x2099])):
  return min_by(certainty_order, [c0x2081, c0x2082, ..., c0x2099])

-- Stale decay
eval_stale(0x03C40x231B(t0x2080, elapsed), threshold):
  if elapsed > threshold:
    return 0x03C4?   -- certainty has degraded
  else:
    return 0x03C40x231B(t0x2080, elapsed)  -- with visual decay proportional to elapsed/threshold

-- Stakes amplification
eval_display_weight(claim c):
  base = certainty_order[c.certainty]
  stakes_multiplier = { low: 1.0, medium: 1.2, high: 1.5, critical: 2.0 }[c.stakes]
  when c.certainty 0x2208 {0x03C4?, 0x03C4~, 0x03C40x2205}:
    return base 0x00D7 stakes_multiplier  -- uncertain + high-stakes = high visual weight
  else:
    return base
```

### 5.3 Phase Evaluation

```
-- Phase evaluation determines what is visible at any moment.

eval_phase(stage s, current_phase 0x03C6):
  config = s.phases[0x03C6]  OR  s.default
  return {
    render:  config.visible,
    fade:    config.faded,
    hide:    config.hidden,
    focus:   config.dominant
  }

-- Phase transition evaluation
eval_transition(stage s, from_0x03C6, to_0x03C6):
  leaving  = s.phases[from_0x03C6].visible - s.phases[to_0x03C6].visible
  arriving = s.phases[to_0x03C6].visible  - s.phases[from_0x03C6].visible
  stable   = s.phases[from_0x03C6].visible 0x2229 s.phases[to_0x03C6].visible
  anchors  = filter(is_anchor, stable)

  match s.transition.sequence with
  | simultaneous  -> all change at once
  | anchor_first  -> anchors settle first, then leaving 0x039B0x0303, then arriving appear
  | content_first -> content changes, then layout settles
  | staggered(n)  -> elements change with n ms offset between each

  validate: anchors must appear in arriving (never in leaving)
            if anchor in leaving: FAIL "Anchor violation in transition " + from_0x03C6 + "->" + to_0x03C6
```

### 5.4 Dialogue Evaluation

```
-- Dialogue sequence validation
-- Given a sequence of dialogue acts, validate ordering constraints

eval_dialogue_sequence([d0x2081, d0x2082, ..., d0x2099]):
  for each d0x1D62:
    if d0x1D62.type = 0x03940x2295:
      preceding = [d0x2081 .. d0x1D620x208B0x2081]
      if 0x03940x26A0 not in [d.type for d in preceding]:
        if d0x1D62.stakes 0x2265 medium:
          WARN "0x03940x2295 without preceding 0x03940x26A0 for stakes 0x2265 medium"
        if d0x1D62.stakes = critical:
          FAIL "0x03940x2295 without preceding 0x03940x26A0 for critical stakes"
    if d0x1D62.type = 0x03940x2191:
      validate_escalation(d0x1D62)  -- TC-8

validate_escalation(d):
  if d.reason = null:    FAIL "0x03940x2191 missing reason"
  if len(d.options) < 2: FAIL "0x03940x2191 requires 0x2265 2 options"
  for opt in d.options:
    if opt.consequence = null: FAIL "0x03940x2191 option missing consequence"
  if d.default = null:   FAIL "0x03940x2191 missing declared default"
```

### 5.5 Failure Evaluation

```
-- Failure coverage validation
-- Every operation must have a failure contract

eval_failure_coverage(vessel v):
  operations = [c for c in v.contracts if c.obligation.kind = execute]
  for op in operations:
    failure_contracts = [c for c in v.contracts if c.trigger = operation_fail(op)]
    if len(failure_contracts) = 0:
      FAIL "Operation " + op + " in vessel " + v.name + " has no failure contract"
    for fc in failure_contracts:
      if fc.obligation.failure.kind = 0x03A60x2014:
        FAIL "Silent failure contract detected in " + v.name  -- 0x03A60x2014 is always FAIL

-- Cascade validation
eval_cascade(failure 0x03A6, seam s):
  match s.failure with
  | blocks(kinds)            -> if 0x03A6.kind 0x2208 kinds: stop; return contained 0x03A6
  | passes(kinds)            -> if 0x03A6.kind 0x2208 kinds: propagate to seam's other vessel
  | transforms(from, to)     -> if 0x03A6.kind = from: replace with to; propagate
  | all_pass                 -> propagate; LOG "Unconstrained cascade across " + s.name
  | all_block                -> stop; LOG "Cascade blocked at " + s.name
```

---

## PART VI 0x2014 VIOLATION TAXONOMY

```
Every violation has: a code, a description, a type (error | warning),
a detection rule, and a mechanical fix.

VIOL-01  UNGRADABLE ASSERTION (Error)
  Pattern:  claim without certainty declaration
  Rule:     TC-3 failure
  Effect:   User cannot calibrate trust in displayed information
  Fix:      Add certainty: 0x03C4[grade] to claim; minimum 0x03C4~ for ai_generated

VIOL-02  BUDGET OVERFLOW (Error)
  Pattern:  Child budgets sum to more than parent budget
  Rule:     Budget evaluation overflow
  Effect:   Load ceiling violation; 0x039B0x03A9 > 7 0x00B1 2 possible
  Fix:      Recalculate child proportions; use ceiling() to enforce

VIOL-03  LOAD CEILING EXCEEDED (Error)
  Pattern:  More than 9 independent elements in a vessel
  Rule:     TC-2 failure
  Effect:   Working memory exceeded; user error rate increases
  Fix:      Chunk related elements; reduce visible elements per phase

VIOL-04  INTENT BLINDNESS (Warning)
  Pattern:  Stage with identical PhaseConfig across all phases
  Rule:     All PhaseConfigs in stage are structurally identical
  Effect:   Surface wastes attention budget across irrelevant phases
  Fix:      Differentiate PhaseConfig per phase; apply faded list

VIOL-05  CORRECTION ERASURE (Error)
  Pattern:  0x03940x2190 that deletes prior 0x03940x2192 from surface
  Rule:     Correction evaluated as replacement, not addition
  Effect:   User cannot detect system self-revision; provenance lost
  Fix:      0x03940x2190 adds revision marker to prior 0x03940x2192; both remain visible

VIOL-06  INCOMPLETE ESCALATION (Error)
  Pattern:  0x03940x2191 missing reason, options, consequences, or default
  Rule:     TC-8 failure
  Effect:   Human makes decision without adequate information
  Fix:      Complete 0x03940x2191 declaration; all four fields required

VIOL-07  ANONYMOUS ASSERTION (Warning 0x2192 Error at 0x03C4! 0x2265 high)
  Pattern:  Claim with provenance = null or provenance unreachable > 2 hops
  Rule:     TC-3 provenance check
  Effect:   User cannot audit assertion; trust is blind
  Fix:      Declare provenance; minimum 0x03C4~ certainty without it

VIOL-08  SILENT REDACTION (Error)
  Pattern:  content = redacted without reason
  Rule:     Claim evaluation: redacted(reason) requires reason
  Effect:   User cannot understand why information is absent
  Fix:      redacted("reason text"); reason must be human-readable

VIOL-09  SALIENCE INFLATION (Warning)
  Pattern:  0x2726 applied to elements based on production cost, not 0x039B0x2191
  Rule:     Salience 0x221D 0x039B0x2191 check
  Effect:   Notification fatigue; important signals lost in noise
  Fix:      Audit 0x2726 assignments; apply only where 0x039B0x2191 justifies 0x25C9 migration

VIOL-10  SPINNING LIE (Error)
  Pattern:  0x03A60x27F3 without progress indicator OR stall without StallSpec
  Rule:     TC-10 failure; Flow stall validation
  Effect:   User cannot distinguish working from hung
  Fix:      Add progress to 0x03A60x27F3; declare on_stall with threshold and surface

VIOL-11  ANCHOR DRIFT (Error)
  Pattern:  Element declared 0x2693 appears in PhaseConfig.hidden for any phase
  Rule:     TC-6 failure; transition anchor validation
  Effect:   Spatial memory violated; user loses orientation after phase change
  Fix:      Move anchor from hidden to faded; anchors always visible

VIOL-12  UNCOVERED FAILURE (Error)
  Pattern:  Operation with no failure contract
  Rule:     TC-7 failure
  Effect:   System fails silently when operation fails; 0x03A60x2014
  Fix:      Add contract with trigger = operation_fail and obligation = surface(0x03A6)

VIOL-13  GUILT ABANDON (Error)
  Pattern:  0x2298 triggers unsolicited prompt, discouragement, or repeated restore offer
  Rule:     Abandon evaluation; 0x2298 must clear silently
  Effect:   Human autonomy violated; trust eroded
  Fix:      0x2298 clears task; one silent restore path available; no prompts

VIOL-14  LOCKED WITHOUT REASON (Warning)
  Pattern:  Affordance.on_unavail = hidden without justification
  Rule:     Perceivability check; hidden requires justification
  Effect:   Human cannot discover that affordance exists; silent lock
  Fix:      Use fade_locked with reason, or replaced(explanation)

VIOL-15  INFINITE CONTRACT (Warning)
  Pattern:  Contract with deadline = none
  Rule:     Contract evaluation; open-ended commitments flagged
  Effect:   System has made a commitment it may never fulfill
  Fix:      Assign deadline; if truly indefinite, document with justification
```

---

## PART VII 0x2014 SURFACE ARCHETYPES

```
Surface Archetypes are reusable GUILDS patterns for recurring UI situations.
Each is a partial specification that can be instantiated and extended.

ARCHETYPE: OracleView
  -- For displaying AI-generated output with honest certainty
  stage OracleView {
    budget:  ceiling(0.5, auto)
    phases: {
      0x03C60x2081: {
        arrangement: sequence(primary, [1.0])
        visible:     [OutputClaim, ProvLabel, CertaintyBadge]
        dominant:    OutputClaim
      }
      0x03C60x2082: {
        visible:     [OutputClaim, ProvLabel, CertaintyBadge, AlternativesClaim]
        dominant:    OutputClaim
      }
    }
  }
  claim OutputClaim {
    certainty:   0x03C4~                  -- minimum for AI output
    provenance:  source.ai_generated(model, context)
    stakes:      context_dependent
    on_stale:    mark_stale
  }

ARCHETYPE: DecisionGate
  -- For moments requiring explicit human approval before consequential action
  vessel DecisionGate {
    budget: whole(0.4)
    phase:  [0x03C60x2081, 0x03C60x2082]
    contracts: [
      contract WarningFirst {
        trigger:     phase_enter(0x03C60x2081)
        obligation:  display(RiskClaim)
        deadline:    none            -- warning persists until dismissed
        on_breach:   0x03A60x2717
      }
      contract RequireExplicit {
        trigger:     user_action(ConfirmAfford)
        obligation:  execute(action)
        deadline:    session
        on_breach:   0x03A60x22A3
      }
    ]
  }
  -- ConfirmAfford must be visible; silent acceptance is type error

ARCHETYPE: MonitorWidget
  -- Peripheral awareness vessel; does not consume 0x25C9
  vessel MonitorWidget {
    budget:  whole(0.08)             -- small fraction; peripheral
    weight:  background
    phase:   any
    contains: [StatusClaim]
    contracts: [
      contract NotifyOnChange {
        trigger:    condition(status_changed)
        obligation: display(ChangeClaim) with 0x2726(proportional to change_magnitude)
        deadline:   s(1)
        on_breach:  0x03A60x2193              -- degraded, not fatal
      }
    ]
  }

ARCHETYPE: RecoveryView
  -- Post-failure surface; nothing is hidden
  stage RecoveryView {
    budget:  ceiling(0.6, auto)
    phases: {
      0x03C60x1D63: {
        visible:  [PriorStateClaim, FailureClaim, RecoveryOptions]
        dominant: FailureClaim
      }
    }
  }
  claim PriorStateClaim {
    content:   snapshot(prior_state)
    certainty: 0x03C40x2713                   -- prior state is known
    stakes:    high
  }
  claim FailureClaim {
    content:   status(failure, FailureScale)
    certainty: 0x03C40x2713                   -- failure itself is known
    stakes:    high
  }

ARCHETYPE: StreamView
  -- For streaming output (tokens, data, events arriving incrementally)
  flow StreamFlow {
    trigger:  system_event(stream_start)
    steps: [
      step Acquiring {
        duration:  ms(200)
        state:     acquiring
        claim:     LoadingClaim { certainty: 0x03C40x2205, content: empty("Waiting for first token") }
        exit:      on_event(first_token)
      }
      step Streaming {
        duration:  unbounded
        state:     streaming(progress = token_count)
        claim:     PartialClaim { certainty: 0x03C4~, freshness: live }
        exit:      on_event(stream_complete)
      }
      step Settling {
        duration:  ms(150)
        state:     completing
        exit:      on_complete
      }
    ]
    on_stall: {
      threshold:  s(5)
      surface:    0x03A60x27F3
      recovery:   [RetryAfford, AbortAfford]
    }
    terminal: success | failure(0x03A6?) | partial(0x03A60x00BD) | abandoned(0x2298)
  }
```

---

## PART VIII 0x2014 EXAMPLE: COMPLETE VESSEL SPECIFICATION

```guilds
-- ToraFirma Station: KnightsPanel specified in GUILDS

-- The certainty anchor: all seat outputs are AI-generated, therefore 0x03C4~
let seatCertainty = 0x03C4~

-- The deliberation flow for a single round
flow RoundFlow {
  trigger:  system_event(round_start)
  steps: [
    step SeatsInferring {
      duration:   unbounded
      state:      streaming(progress = seats_complete / seats_total)
      exit:       on_event(all_seats_complete)
    }
    step SupervisorSynthesizing {
      duration:   unbounded
      state:      processing
      exit:       on_event(synthesis_complete)
    }
  ]
  on_stall: {
    threshold:  s(30)
    surface:    0x03A60x27F3    -- "Inference stalled 0x2014 seat N has not responded"
    recovery:   [AbortSeatAfford, AbortRoundAfford]
  }
  terminal: success | failure(0x03A6?) | abandoned(0x2298)
}

-- Individual seat vessel
vessel SeatCard {
  budget:      shared(0.8, n_seats)   -- n_seats is runtime parameter
  phase:       0x03C60x2081                     -- active during execution
  weight:      secondary
  arrangement: sequence(primary, [0.1, 0.8, 0.1])

  contains: [SeatHeader, SeatOutputClaim, SeatFooter]

  failures: [
    FailureSpec {
      trigger:   seat_inference_stall
      surfaces:  0x03A60x27F3           -- spinning indicator with elapsed time
      propagates: no           -- seat stall does not cascade to other seats
    }
    FailureSpec {
      trigger:   seat_inference_fail
      surfaces:  0x03A6?            -- seat output not available; cause may be unknown
      propagates: conditional  -- if all seats fail, propagate 0x03A60x2717 to KnightsPanel
    }
  ]

  contracts: [
    contract SeatAcknowledge {
      trigger:     phase_enter(0x03C60x2081)
      obligation:  acknowledge
      deadline:    ms(200)
      on_breach:   0x03A60x2193           -- visible degraded state, not silent
    }
  ]
}

claim SeatOutputClaim {
  content:     text(seat.output, typography.mono)
  certainty:   seatCertainty              -- 0x03C4~
  provenance:  source.ai_generated(model = station.model, context = seat.role_prompt)
  stakes:      context_dependent          -- evaluated at render time from task
  freshness:   live                       -- streaming; updates per token
  on_stale:    mark_stale                 -- if stream stalls, mark stale
}

claim SynthesisClaim {
  content:     text(supervisor.synthesis, typography.body)
  certainty:   composite([seatCertainty, seatCertainty, seatCertainty, seatCertainty])
  -- composite certainty = min(0x03C4~, 0x03C4~, ...) = 0x03C4~
  -- synthesis derived from multiple 0x03C4~ sources = 0x03C4~ at best
  provenance:  source.derived(seats_all, method = "supervisor_synthesis_prompt")
  stakes:      context_dependent
  freshness:   event_driven(round_complete)
  on_stale:    degrade_to(0x03C4?)
}

-- The synthesis requires explicit approval (it is a proposal, not a fact)
afford AcceptSynthesisAfford {
  perceivable:  context_revealed(round_complete)
  offered:      activate
  requires:     [round.state = complete, synthesis.visible = true]
  contracts: [
    contract AcceptContract {
      trigger:     user_action(AcceptSynthesisAfford)
      obligation:  execute(commit_synthesis_to_session)
      deadline:    session
      on_breach:   0x03A60x00BD    -- partial if session commit fails; not fatal
    }
    contract WarnFirst {
      trigger:     phase_enter(0x03C60x2082)
      obligation:  display(StakesClaim)    -- show stakes before accept is offered
      deadline:    none
      on_breach:   0x03A60x2717    -- if warning cannot display, do not show accept button
    }
  ]
  on_unavail:  fade_locked   -- visible but non-responsive before round complete
}

-- The stage that wraps the Knights panel and phase-couples it
stage KnightsPanel {
  budget:  whole(1.0)         -- within its parent's allocation
  anchor:  { elements: [RoundHeader], position: top }

  phases: {
    0x03C60x2205: {
      arrangement: sequence(primary, [1.0])
      visible:     [IdleMessage]
      faded:       []
      hidden:      [SeatGrid, RoundHeader, SynthesisArea, ControlBar]
      dominant:    IdleMessage
    }
    0x03C60x2081: {
      arrangement: sequence(primary, [0.08, 0.72, 0.2])
      visible:     [RoundHeader, SeatGrid, ControlBar]
      faded:       [SynthesisArea]     -- present but not yet active
      hidden:      [IdleMessage]
      dominant:    SeatGrid
    }
    0x03C60x2082: {
      arrangement: sequence(primary, [0.08, 0.5, 0.42])
      visible:     [RoundHeader, SeatGrid, SynthesisArea]
      faded:       [ControlBar]
      hidden:      [IdleMessage]
      dominant:    SynthesisArea      -- verification phase: synthesis is dominant
    }
  }

  transition: {
    duration:   ms(200)
    curve:      ease-out
    sequence:   anchor_first    -- RoundHeader settles, then content follows
  }
}

-- Bond between seats: they are parallel (simultaneous, non-causal)
bond SeatParallelism between (SeatCard 0x00D7 n_seats) {
  kind:      parallels
  strength:  rigid
  on_break:  0x03A60x2192   -- if parallelism breaks (one seat blocks others), cascade
}

-- Bond between synthesis and seats: synthesis corresponds to seat outputs
bond SynthesisCorrespondence between (SynthesisClaim, SeatGrid) {
  kind:      corresponds(mapping = "supervisor_prompt(seat_outputs)")
  direction: unidirectional(from = SeatGrid, to = SynthesisClaim)
  strength:  rigid
  on_break:  0x03A60x2717   -- synthesis without seat outputs is fatal
}

-- Seam between KnightsPanel and its parent
seam KnightsPanelSeam between (KnightsPanel, ParentWorkspace) {
  kind:    hard
  passage: [
    data(SynthesisText),       -- accepted synthesis crosses into session
    focus,                     -- 0x25C9 can migrate freely
    events(round_complete)     -- parent needs to know round completed
  ]
  filter:  none
  failure: {
    blocks: [0x03A60x22A3]              -- blocked failures stay within KnightsPanel
    passes: [0x03A60x2717]              -- fatal failures propagate to parent
    transforms: [(0x03A60x2193, 0x03A60x2192)]    -- degraded failures become cascade warnings in parent
  }
}
```

---

## CLOSING

```
GUILDS defines a GUI not as a layout, but as a system of obligations.

Every Vessel is an attention claim. It must earn its place.
Every Claim is an assertion with a grade. Hiding the grade is dishonest.
Every Contract is a commitment with a deadline. Breaking it is a failure.
Every Failure is a state with structure. Hiding it is silent failure.
Every Dialogue act has a type and a grammar. Violating the grammar is unethical.
Every Phase transition reshapes the surface. Ignoring the phase is intent-blindness.

The language has types, laws, evaluation rules, and violations.
Violations are not style critiques. They are type errors.
A GUILDS-valid specification is not just describable 0x2014 it is auditable.

The parser receives: a GUILDS specification.
The parser outputs: either a valid surface model, or a list of violations.
There is no third option.

A GUI that passes GUILDS validation:
  0x2014 Makes no ungradable claims
  0x2014 Wastes no attention budget
  0x2014 Breaks no commitment silently
  0x2014 Lies about no failure
  0x2014 Ignores no human intent
  0x2014 Punishes no human autonomy

That is the minimum standard for honesty in interface design.
```

---

```
GUILDS v2.0 0x2014 Language Specification Complete

Domains    : 5  (0x039B 0x0399 0x03C4 0x0394 0x03A6)
Primitives : 52
Axioms     : 6
Type rules : 12
Eval rules : 9  (budget, certainty, phase, transition, dialogue, failure, cascade)
Violations : 15
Archetypes : 5  (Oracle, Decision, Monitor, Recovery, Stream)
Composed   : 9  (Vessel, Claim, Contract, Bond, Seam, Stage, Flow, Affordance, Budget)

Next: GUILDS Parser (tokenizer 0x2192 AST 0x2192 type checker 0x2192 violation reporter)
```
