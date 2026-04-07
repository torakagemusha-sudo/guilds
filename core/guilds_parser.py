"""
GUILDS v2 Parser
================
Lexer -> Token Stream -> Recursive Descent Parser -> AST -> Type Checker -> Violation Report

Sigil encoding: All GUILDS sigils are expressed as plain English words in source.
Examples:
  inferred          -> tau_inferred    (certainty: inferred)
  assert            -> dlg_assert      (dialogue: assert)
  fatal             -> phi_fatal       (failure: fatal)
  execute           -> phase_execute   (phase 1)
  focus             -> focus           (cognitive: focus point)
"""

from __future__ import annotations
import re
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional


# ---------------------------------------------------------------------------
# SECTION 1: TOKEN TYPES
# ---------------------------------------------------------------------------

class TT(Enum):
    # Literals
    IDENT    = auto()
    STRING   = auto()
    NUMBER   = auto()
    # Punctuation
    LBRACE   = auto()  # {
    RBRACE   = auto()  # }
    LBRACK   = auto()  # [
    RBRACK   = auto()  # ]
    LPAREN   = auto()  # (
    RPAREN   = auto()  # )
    COLON    = auto()  # :
    COMMA    = auto()  # ,
    PIPE     = auto()  # |
    ARROW    = auto()  # ->
    MINUS    = auto()  # -  (standalone, after -> already consumed)
    EQ       = auto()  # =
    SLASH    = auto()  # /
    DOT      = auto()  # .
    STAR     = auto()  # *
    # Keywords
    KW_VESSEL    = auto()
    KW_CLAIM     = auto()
    KW_AFFORD    = auto()
    KW_BOND      = auto()
    KW_SEAM      = auto()
    KW_STAGE     = auto()
    KW_FLOW      = auto()
    KW_CONTRACT  = auto()
    KW_STEP      = auto()
    KW_LET       = auto()
    KW_BETWEEN   = auto()
    KW_ANY       = auto()
    KW_NONE      = auto()
    KW_AUTO      = auto()
    KW_UNBOUNDED = auto()
    KW_SESSION   = auto()
    KW_COMPOSITE = auto()
    KW_SOURCE    = auto()
    KW_WITH      = auto()
    # Budget keywords
    KW_WHOLE   = auto()
    KW_FIXED   = auto()
    KW_CEILING = auto()
    KW_SHARED  = auto()
    # Arrangement keywords
    KW_SEQUENCE = auto()
    KW_EQUAL    = auto()
    KW_DOMINANT = auto()
    KW_GRID     = auto()
    KW_FREE     = auto()
    KW_STACK    = auto()
    KW_ADAPTIVE = auto()
    # Weight keywords
    KW_PRIMARY    = auto()
    KW_SECONDARY  = auto()
    KW_TERTIARY   = auto()
    KW_BACKGROUND = auto()
    KW_HIDDEN     = auto()
    # Stakes keywords
    KW_LOW      = auto()
    KW_MEDIUM   = auto()
    KW_HIGH     = auto()
    KW_CRITICAL = auto()
    # Phase sigils  (orient=idle, execute=active, verify=checking, integrate=merging, recover=repairing)
    PH_ORIENT    = auto()  # orient
    PH_EXECUTE   = auto()  # execute
    PH_VERIFY    = auto()  # verify
    PH_INTEGRATE = auto()  # integrate
    PH_RECOVER   = auto()  # recover
    PH_IDLE      = auto()  # idle
    # Certainty sigils  (tau = certainty grade)
    TAU_CERTAIN   = auto()  # certain
    TAU_INFERRED  = auto()  # inferred
    TAU_PROBABLE  = auto()  # probable
    TAU_UNKNOWN   = auto()  # uncertain
    TAU_CONTESTED = auto()  # contested
    TAU_STALE     = auto()  # outdated
    # Dialogue sigils  (Delta = speech act)
    DLG_ASSERT  = auto()  # assert
    DLG_QUERY   = auto()  # query
    DLG_PROPOSE = auto()  # propose
    DLG_WARN    = auto()  # warn
    DLG_ACK     = auto()  # ack
    DLG_SILENCE = auto()  # silence
    DLG_CORRECT = auto()  # correct
    DLG_ESCAL   = auto()  # escalate
    DLG_CELEB   = auto()  # celebrate
    # Failure sigils  (Phi = failure mode)
    PHI_DEGRADED  = auto()  # degraded
    PHI_BLOCKED   = auto()  # blocked
    PHI_LOST      = auto()  # lost
    PHI_PARTIAL   = auto()  # partial
    PHI_STALE     = auto()  # stale
    PHI_RECOVER   = auto()  # recovering
    PHI_CASCADE   = auto()  # cascade
    PHI_UNKNOWN   = auto()  # unknown
    PHI_FATAL     = auto()  # fatal
    PHI_SILENT    = auto()  # silent
    # Cognitive sigils
    COG_FOCUS     = auto()  # focus
    COG_PERIPH    = auto()  # peripheral
    COG_COST      = auto()  # cost
    COG_YIELD     = auto()  # yield
    COG_LOAD      = auto()  # load
    COG_SALIENCE  = auto()  # salience
    COG_ANCHOR    = auto()  # anchored
    COG_FADE      = auto()  # fade
    # Special
    EOF = auto()


KEYWORDS: dict[str, TT] = {
    "vessel": TT.KW_VESSEL, "claim": TT.KW_CLAIM, "afford": TT.KW_AFFORD,
    "bond": TT.KW_BOND, "seam": TT.KW_SEAM, "stage": TT.KW_STAGE,
    "flow": TT.KW_FLOW, "contract": TT.KW_CONTRACT, "step": TT.KW_STEP,
    "let": TT.KW_LET, "between": TT.KW_BETWEEN, "any": TT.KW_ANY,
    "none": TT.KW_NONE, "auto": TT.KW_AUTO, "unbounded": TT.KW_UNBOUNDED,
    "session": TT.KW_SESSION, "composite": TT.KW_COMPOSITE, "source": TT.KW_SOURCE,
    "with": TT.KW_WITH,
    "whole": TT.KW_WHOLE, "fixed": TT.KW_FIXED, "ceiling": TT.KW_CEILING,
    "shared": TT.KW_SHARED,
    "sequence": TT.KW_SEQUENCE, "equal": TT.KW_EQUAL, "dominant": TT.KW_DOMINANT,
    "grid": TT.KW_GRID, "free": TT.KW_FREE, "stack": TT.KW_STACK,
    "adaptive": TT.KW_ADAPTIVE,
    "primary": TT.KW_PRIMARY, "secondary": TT.KW_SECONDARY,
    "tertiary": TT.KW_TERTIARY, "background": TT.KW_BACKGROUND,
    "hidden": TT.KW_HIDDEN,
    "low": TT.KW_LOW, "medium": TT.KW_MEDIUM, "high": TT.KW_HIGH,
    "critical": TT.KW_CRITICAL,
}

# Sigil table: source text -> TT
# Each sigil is a plain English word as it appears in .guilds source files
SIGILS: dict[str, TT] = {
    # Phase sigils
    "orient":     TT.PH_ORIENT,
    "execute":    TT.PH_EXECUTE,
    "verify":     TT.PH_VERIFY,
    "integrate":  TT.PH_INTEGRATE,
    "recover":    TT.PH_RECOVER,
    "idle":       TT.PH_IDLE,
    # Certainty sigils
    "certain":    TT.TAU_CERTAIN,
    "inferred":   TT.TAU_INFERRED,
    "probable":   TT.TAU_PROBABLE,
    "uncertain":  TT.TAU_UNKNOWN,
    "contested":  TT.TAU_CONTESTED,
    "outdated":   TT.TAU_STALE,
    # Dialogue sigils
    "assert":     TT.DLG_ASSERT,
    "query":      TT.DLG_QUERY,
    "propose":    TT.DLG_PROPOSE,
    "warn":       TT.DLG_WARN,
    "ack":        TT.DLG_ACK,
    "silence":    TT.DLG_SILENCE,
    "correct":    TT.DLG_CORRECT,
    "escalate":   TT.DLG_ESCAL,
    "celebrate":  TT.DLG_CELEB,
    # Failure sigils
    "degraded":   TT.PHI_DEGRADED,
    "blocked":    TT.PHI_BLOCKED,
    "lost":       TT.PHI_LOST,
    "partial":    TT.PHI_PARTIAL,
    "stale":      TT.PHI_STALE,
    "recovering": TT.PHI_RECOVER,
    "cascade":    TT.PHI_CASCADE,
    "unknown":    TT.PHI_UNKNOWN,
    "fatal":      TT.PHI_FATAL,
    "silent":     TT.PHI_SILENT,
    # Cognitive sigils
    "focus":      TT.COG_FOCUS,
    "peripheral": TT.COG_PERIPH,
    "cost":       TT.COG_COST,
    "yield":      TT.COG_YIELD,
    "load":       TT.COG_LOAD,
    "salience":   TT.COG_SALIENCE,
    "anchored":   TT.COG_ANCHOR,
    "fade":       TT.COG_FADE,
}

# Sort sigils longest-first so the lexer matches greedily
SIGIL_LIST = sorted(SIGILS.keys(), key=len, reverse=True)

FAILURE_SIGILS = {
    TT.PHI_DEGRADED, TT.PHI_BLOCKED, TT.PHI_LOST, TT.PHI_PARTIAL,
    TT.PHI_STALE, TT.PHI_RECOVER, TT.PHI_CASCADE, TT.PHI_UNKNOWN,
    TT.PHI_FATAL, TT.PHI_SILENT,
}
CERTAINTY_SIGILS = {
    TT.TAU_CERTAIN, TT.TAU_INFERRED, TT.TAU_PROBABLE,
    TT.TAU_UNKNOWN, TT.TAU_CONTESTED, TT.TAU_STALE,
}
PHASE_SIGILS = {
    TT.PH_ORIENT, TT.PH_EXECUTE, TT.PH_VERIFY,
    TT.PH_INTEGRATE, TT.PH_RECOVER, TT.PH_IDLE,
}
DIALOGUE_SIGILS = {
    TT.DLG_ASSERT, TT.DLG_QUERY, TT.DLG_PROPOSE, TT.DLG_WARN,
    TT.DLG_ACK, TT.DLG_SILENCE, TT.DLG_CORRECT, TT.DLG_ESCAL, TT.DLG_CELEB,
}
# All sigil token types — used to allow sigil words as name tokens where needed
ALL_SIGIL_TYPES = (
    PHASE_SIGILS | CERTAINTY_SIGILS | FAILURE_SIGILS | DIALOGUE_SIGILS | {
        TT.COG_FOCUS, TT.COG_PERIPH, TT.COG_COST, TT.COG_YIELD,
        TT.COG_LOAD, TT.COG_SALIENCE, TT.COG_ANCHOR, TT.COG_FADE,
    }
)


@dataclass
class Token:
    typ: TT
    val: Any
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.typ.name}, {self.val!r}, {self.line}:{self.col})"


# ---------------------------------------------------------------------------
# SECTION 2: LEXER
# ---------------------------------------------------------------------------

class LexError(Exception):
    def __init__(self, msg, line, col):
        super().__init__(f"Lex error at {line}:{col} — {msg}")
        self.line = line
        self.col = col


class Lexer:
    def __init__(self, src: str):
        self.src = src
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []

    def error(self, msg):
        raise LexError(msg, self.line, self.col)

    def peek(self, n=0):
        p = self.pos + n
        return self.src[p] if p < len(self.src) else ""

    def advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def skip_line_comment(self):
        while self.pos < len(self.src) and self.src[self.pos] != "\n":
            self.pos += 1

    def skip_block_comment(self):
        # {- ... -}
        self.pos += 2  # skip {-
        depth = 1
        while self.pos < len(self.src) - 1:
            if self.src[self.pos] == "{" and self.src[self.pos+1] == "-":
                depth += 1
                self.pos += 2
            elif self.src[self.pos] == "-" and self.src[self.pos+1] == "}":
                depth -= 1
                self.pos += 2
                if depth == 0:
                    return
            else:
                if self.src[self.pos] == "\n":
                    self.line += 1
                    self.col = 1
                else:
                    self.col += 1
                self.pos += 1
        self.error("Unterminated block comment")

    def read_string(self):
        self.advance()  # consume opening "
        buf = []
        while self.pos < len(self.src):
            ch = self.src[self.pos]
            if ch == '"':
                self.advance()
                return "".join(buf)
            if ch == "\\":
                self.advance()
                esc = self.advance()
                buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc))
            else:
                buf.append(self.advance())
        self.error("Unterminated string")

    def read_number(self):
        start = self.pos
        while self.pos < len(self.src) and (self.src[self.pos].isdigit() or self.src[self.pos] == "."):
            self.pos += 1
            self.col += 1
        return float(self.src[start:self.pos]) if "." in self.src[start:self.pos] else int(self.src[start:self.pos])

    def try_sigil(self):
        """Try to match a sigil at current position. Return (sigil_str, TT) or None."""
        for s in SIGIL_LIST:
            if self.src[self.pos:self.pos+len(s)] == s:
                # Word-boundary check: if the sigil ends with a letter, the next
                # character must not be alphanumeric or '_' (prevents matching
                # 'execute' inside 'executed', or 'fade' inside 'fade_locked').
                end_pos = self.pos + len(s)
                if s[-1].isalpha() and end_pos < len(self.src):
                    next_ch = self.src[end_pos]
                    if next_ch.isalnum() or next_ch == '_':
                        continue
                return s, SIGILS[s]
        return None

    def tokenize(self) -> list[Token]:
        while self.pos < len(self.src):
            # Skip whitespace
            if self.src[self.pos] in " \t\r\n":
                self.advance()
                continue

            start_line, start_col = self.line, self.col

            # Line comment
            if self.src[self.pos:self.pos+2] == "--":
                self.skip_line_comment()
                continue

            # Block comment
            if self.src[self.pos:self.pos+2] == "{-":
                self.skip_block_comment()
                continue

            # Arrow ->
            if self.src[self.pos:self.pos+2] == "->":
                self.pos += 2; self.col += 2
                self.tokens.append(Token(TT.ARROW, "->", start_line, start_col))
                continue

            # Sigils (tried before identifier/keyword so they take priority)
            sigil_match = self.try_sigil()
            if sigil_match:
                s, tt = sigil_match
                self.pos += len(s)
                self.col += len(s)
                self.tokens.append(Token(tt, s, start_line, start_col))
                continue

            ch = self.src[self.pos]

            # String
            if ch == '"':
                val = self.read_string()
                self.tokens.append(Token(TT.STRING, val, start_line, start_col))
                continue

            # Number
            if ch.isdigit():
                val = self.read_number()
                self.tokens.append(Token(TT.NUMBER, val, start_line, start_col))
                continue

            # Identifier or keyword
            if ch.isalpha() or ch == "_":
                start = self.pos
                while self.pos < len(self.src) and (self.src[self.pos].isalnum() or self.src[self.pos] == "_"):
                    self.pos += 1
                    self.col += 1
                word = self.src[start:self.pos]
                tt = KEYWORDS.get(word, TT.IDENT)
                self.tokens.append(Token(tt, word, start_line, start_col))
                continue

            # Single-char punctuation
            punct = {
                "{": TT.LBRACE, "}": TT.RBRACE,
                "[": TT.LBRACK, "]": TT.RBRACK,
                "(": TT.LPAREN, ")": TT.RPAREN,
                ":": TT.COLON, ",": TT.COMMA,
                "|": TT.PIPE, "=": TT.EQ,
                "/": TT.SLASH, ".": TT.DOT,
                "*": TT.STAR, "-": TT.MINUS,
            }
            if ch in punct:
                self.pos += 1; self.col += 1
                self.tokens.append(Token(punct[ch], ch, start_line, start_col))
                continue

            self.error(f"Unexpected character: {ch!r}")

        self.tokens.append(Token(TT.EOF, None, self.line, self.col))
        return self.tokens


# ---------------------------------------------------------------------------
# SECTION 3: AST NODE TYPES
# ---------------------------------------------------------------------------

@dataclass
class Node:
    line: int = field(default=0, repr=False)
    col: int = field(default=0, repr=False)


@dataclass
class LetDecl:
    name: str
    value: Any


@dataclass
class BudgetNode:
    kind: str          # whole | fixed | auto | ceiling | shared
    args: list[Any]


@dataclass
class ArrangementNode:
    kind: str          # sequence | equal | dominant | grid | free | stack | adaptive
    args: list[Any]


@dataclass
class CertaintyNode:
    kind: str          # certain | inferred | probable | unknown | contested | stale | composite
    args: list[Any]    # for stale: [t0, elapsed]; for composite: [CertaintyNode, ...]


@dataclass
class StakesNode:
    level: str         # low | medium | high | critical


@dataclass
class PhaseSpec:
    phases: list[str]  # list of phase names or ["any"]


@dataclass
class AnchorSpec:
    elements: list[str]
    position: str


@dataclass
class PhaseConfig:
    arrangement: Optional[ArrangementNode]
    visible: list[str]
    faded: list[str]
    hidden: list[str]
    dominant: Optional[str]


@dataclass
class FailureSpec:
    trigger: str
    surfaces: TT       # failure sigil TT
    propagates: str    # no | yes | conditional


@dataclass
class TriggerNode:
    kind: str
    args: list[Any]


@dataclass
class ObligationNode:
    kind: str          # acknowledge | display | navigate | execute | surface | escalate
    args: list[Any]


@dataclass
class DeadlineNode:
    kind: str          # ms | s | m | h | session | persistent | none
    value: Optional[float]


@dataclass
class ContractDecl:
    name: str
    trigger: TriggerNode
    obligation: ObligationNode
    deadline: DeadlineNode
    on_breach: Optional[TT]   # failure sigil or None


@dataclass
class ClaimDecl:
    name: str
    content: Any
    certainty: Optional[CertaintyNode]
    provenance: Optional[Any]
    stakes: Optional[StakesNode]
    freshness: Optional[str]
    on_stale: Optional[str]


@dataclass
class VesselDecl:
    name: str
    budget: Optional[BudgetNode]
    phase: Optional[PhaseSpec]
    arrangement: Optional[ArrangementNode]
    anchor: Optional[AnchorSpec]
    weight: Optional[str]
    contains: list[str]
    bonds: list[str]
    contracts: list[ContractDecl]
    failures: list[FailureSpec]
    on_handlers: list[Any]


@dataclass
class AffordDecl:
    name: str
    perceivable: Optional[str]
    offered: Optional[str]
    requires: list[str]
    disables: list[str]
    contracts: list[ContractDecl]
    on_unavail: Optional[str]


@dataclass
class BondDecl:
    name: str
    members: list[str]
    kind: str
    direction: Optional[str]
    strength: Optional[str]
    on_break: Optional[TT]


@dataclass
class SeamDecl:
    name: str
    members: list[str]
    kind: Optional[str]
    passage: list[str]
    filter_spec: Optional[str]
    failure_prop: Optional[dict]


@dataclass
class StageDecl:
    name: str
    budget: Optional[BudgetNode]
    anchor: Optional[AnchorSpec]
    phases: dict[str, PhaseConfig]    # phase name -> PhaseConfig
    default: Optional[PhaseConfig]
    transition: Optional[dict]


@dataclass
class StepDecl:
    name: str
    duration: Any    # DeadlineNode | "unbounded"
    state: str
    claim: Optional[Any]
    exit_cond: Optional[str]
    affordances: list[str]


@dataclass
class StallSpec:
    threshold: DeadlineNode
    surface: TT       # failure sigil
    recovery: list[str]


@dataclass
class FlowDecl:
    name: str
    trigger: TriggerNode
    steps: list[StepDecl]
    on_stall: Optional[StallSpec]
    terminal: list[str]


@dataclass
class Program:
    declarations: list[Any]   # LetDecl | VesselDecl | ClaimDecl | AffordDecl |
                               # BondDecl | SeamDecl | StageDecl | FlowDecl | ContractDecl


# ---------------------------------------------------------------------------
# SECTION 4: PARSER
# ---------------------------------------------------------------------------

class ParseError(Exception):
    def __init__(self, msg, tok: Token):
        super().__init__(f"Parse error at {tok.line}:{tok.col} — {msg} (got {tok.typ.name} {tok.val!r})")
        self.token = tok


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def peek_type(self) -> TT:
        return self.tokens[self.pos].typ

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.typ != TT.EOF:
            self.pos += 1
        return tok

    def expect(self, tt: TT) -> Token:
        tok = self.advance()
        if tok.typ != tt:
            raise ParseError(f"Expected {tt.name}", tok)
        return tok

    def expect_name(self) -> str:
        """Consume an IDENT token or any sigil token as a bare name string.

        Sigil words (e.g. 'execute', 'degraded') are valid identifier-like
        names in trigger/obligation/function-call positions even though the
        lexer classifies them as sigil tokens.
        """
        tok = self.peek()
        if tok.typ == TT.IDENT or tok.typ in ALL_SIGIL_TYPES:
            self.advance()
            return tok.val
        self.error("Expected identifier")

    def match(self, *types: TT) -> Optional[Token]:
        if self.peek_type() in types:
            return self.advance()
        return None

    def check(self, *types: TT) -> bool:
        return self.peek_type() in types

    def error(self, msg: str):
        raise ParseError(msg, self.peek())

    # -- Program -----------------------------------------------------------

    def parse(self) -> Program:
        decls = []
        while not self.check(TT.EOF):
            decls.append(self.parse_declaration())
        return Program(declarations=decls)

    def parse_declaration(self):
        tok = self.peek()
        if tok.typ == TT.KW_LET:       return self.parse_let()
        if tok.typ == TT.KW_VESSEL:    return self.parse_vessel()
        if tok.typ == TT.KW_CLAIM:     return self.parse_claim()
        if tok.typ == TT.KW_AFFORD:    return self.parse_afford()
        if tok.typ == TT.KW_BOND:      return self.parse_bond()
        if tok.typ == TT.KW_SEAM:      return self.parse_seam()
        if tok.typ == TT.KW_STAGE:     return self.parse_stage()
        if tok.typ == TT.KW_FLOW:      return self.parse_flow()
        if tok.typ == TT.KW_CONTRACT:  return self.parse_contract_top()
        self.error("Expected declaration keyword (vessel, claim, afford, bond, seam, stage, flow, contract, let)")

    # -- Let ---------------------------------------------------------------

    def parse_let(self) -> LetDecl:
        tok = self.expect(TT.KW_LET)
        name = self.expect(TT.IDENT).val
        self.expect(TT.EQ)
        value = self.parse_value_expr()
        return LetDecl(name=name, value=value)

    # -- Vessel ------------------------------------------------------------

    def parse_vessel(self) -> VesselDecl:
        tok = self.expect(TT.KW_VESSEL)
        name = self.expect(TT.IDENT).val
        self.expect(TT.LBRACE)

        budget = None; phase = None; arrangement = None; anchor = None
        weight = None; contains = []; bonds = []; contracts = []
        failures = []; on_handlers = []

        while not self.check(TT.RBRACE, TT.EOF):
            field_tok = self.peek()
            field_name = field_tok.val if field_tok.typ == TT.IDENT else None

            if field_name == "budget":
                self.advance(); self.expect(TT.COLON)
                budget = self.parse_budget()
            elif field_name == "phase":
                self.advance(); self.expect(TT.COLON)
                phase = self.parse_phase_spec()
            elif field_name == "arrangement":
                self.advance(); self.expect(TT.COLON)
                arrangement = self.parse_arrangement()
            elif field_name == "anchor":
                self.advance(); self.expect(TT.COLON)
                anchor = self.parse_anchor_spec()
            elif field_name == "weight":
                self.advance(); self.expect(TT.COLON)
                weight = self.parse_weight()
            elif field_name == "contains":
                self.advance(); self.expect(TT.COLON)
                contains = self.parse_ident_list()
            elif field_name == "bonds":
                self.advance(); self.expect(TT.COLON)
                bonds = self.parse_ident_list()
            elif field_name == "contracts":
                self.advance(); self.expect(TT.COLON)
                contracts = self.parse_contract_list()
            elif field_name == "failures":
                self.advance(); self.expect(TT.COLON)
                failures = self.parse_failure_spec_list()
            elif field_name == "on":
                self.advance(); self.expect(TT.COLON)
                on_handlers = self.parse_event_handler_list()
            else:
                self.error(f"Unknown vessel field: {field_tok.val!r}")

        self.expect(TT.RBRACE)
        return VesselDecl(name=name, budget=budget, phase=phase,
                          arrangement=arrangement, anchor=anchor, weight=weight,
                          contains=contains, bonds=bonds, contracts=contracts,
                          failures=failures, on_handlers=on_handlers)

    # -- Claim -------------------------------------------------------------

    def parse_claim(self) -> ClaimDecl:
        tok = self.expect(TT.KW_CLAIM)
        name = self.expect(TT.IDENT).val
        self.expect(TT.LBRACE)

        content = None; certainty = None; provenance = None
        stakes = None; freshness = None; on_stale = None

        while not self.check(TT.RBRACE, TT.EOF):
            field_tok = self.peek()
            field_name = field_tok.val if field_tok.typ == TT.IDENT else None

            if field_name == "content":
                self.advance(); self.expect(TT.COLON)
                content = self.parse_content_expr()
            elif field_name == "certainty":
                self.advance(); self.expect(TT.COLON)
                certainty = self.parse_certainty()
            elif field_name == "provenance":
                self.advance(); self.expect(TT.COLON)
                provenance = self.parse_provenance()
            elif field_name == "stakes":
                self.advance(); self.expect(TT.COLON)
                stakes = self.parse_stakes()
            elif field_name == "freshness":
                self.advance(); self.expect(TT.COLON)
                freshness = self.parse_freshness()
            elif field_name == "on_stale":
                self.advance(); self.expect(TT.COLON)
                on_stale = self.expect(TT.IDENT).val
            else:
                self.error(f"Unknown claim field: {field_tok.val!r}")

        self.expect(TT.RBRACE)
        return ClaimDecl(name=name, content=content, certainty=certainty,
                         provenance=provenance, stakes=stakes, freshness=freshness,
                         on_stale=on_stale)

    # -- Afford ------------------------------------------------------------

    def parse_afford(self) -> AffordDecl:
        tok = self.expect(TT.KW_AFFORD)
        name = self.expect(TT.IDENT).val
        self.expect(TT.LBRACE)

        perceivable = None; offered = None; requires = []
        disables = []; contracts = []; on_unavail = None

        while not self.check(TT.RBRACE, TT.EOF):
            field_tok = self.peek()
            field_name = field_tok.val if field_tok.typ == TT.IDENT else None

            if field_name == "perceivable":
                self.advance(); self.expect(TT.COLON)
                perceivable = self.parse_raw_expr()
            elif field_name == "offered":
                self.advance(); self.expect(TT.COLON)
                offered = self.parse_raw_expr()
            elif field_name == "requires":
                self.advance(); self.expect(TT.COLON)
                requires = self.parse_ident_list()
            elif field_name == "disables":
                self.advance(); self.expect(TT.COLON)
                disables = self.parse_ident_list()
            elif field_name == "contracts":
                self.advance(); self.expect(TT.COLON)
                contracts = self.parse_contract_list()
            elif field_name == "on_unavail":
                self.advance(); self.expect(TT.COLON)
                on_unavail = self.parse_raw_expr()
            else:
                self.error(f"Unknown afford field: {field_tok.val!r}")

        self.expect(TT.RBRACE)
        return AffordDecl(name=name, perceivable=perceivable, offered=offered,
                          requires=requires, disables=disables, contracts=contracts,
                          on_unavail=on_unavail)

    # -- Bond --------------------------------------------------------------

    def parse_bond(self) -> BondDecl:
        tok = self.expect(TT.KW_BOND)
        name = self.expect(TT.IDENT).val
        self.expect(TT.KW_BETWEEN)
        self.expect(TT.LPAREN)
        members = self.parse_ident_list_raw()
        self.expect(TT.RPAREN)
        self.expect(TT.LBRACE)

        kind = None; direction = None; strength = None; on_break = None

        while not self.check(TT.RBRACE, TT.EOF):
            field_name = self.peek().val if self.peek().typ == TT.IDENT else None
            if field_name == "kind":
                self.advance(); self.expect(TT.COLON)
                kind = self.parse_raw_expr()
            elif field_name == "direction":
                self.advance(); self.expect(TT.COLON)
                direction = self.parse_raw_expr()
            elif field_name == "strength":
                self.advance(); self.expect(TT.COLON)
                strength = self.expect(TT.IDENT).val
            elif field_name == "on_break":
                self.advance(); self.expect(TT.COLON)
                on_break = self.parse_failure_sigil()
            else:
                self.error(f"Unknown bond field: {self.peek().val!r}")

        self.expect(TT.RBRACE)
        return BondDecl(name=name, members=members, kind=kind,
                        direction=direction, strength=strength, on_break=on_break)

    # -- Seam --------------------------------------------------------------

    def parse_seam(self) -> SeamDecl:
        tok = self.expect(TT.KW_SEAM)
        name = self.expect(TT.IDENT).val
        self.expect(TT.KW_BETWEEN)
        self.expect(TT.LPAREN)
        members = self.parse_ident_list_raw()
        self.expect(TT.RPAREN)
        self.expect(TT.LBRACE)

        kind = None; passage = []; filter_spec = None; failure_prop = None

        while not self.check(TT.RBRACE, TT.EOF):
            field_name = self.peek().val if self.peek().typ == TT.IDENT else None
            if field_name == "kind":
                self.advance(); self.expect(TT.COLON)
                kind = self.expect(TT.IDENT).val
            elif field_name == "passage":
                self.advance(); self.expect(TT.COLON)
                passage = self.parse_ident_list()
            elif field_name == "filter":
                self.advance(); self.expect(TT.COLON)
                filter_spec = self.parse_raw_expr()
            elif field_name == "failure":
                self.advance(); self.expect(TT.COLON)
                failure_prop = self.parse_failure_prop()
            else:
                self.error(f"Unknown seam field: {self.peek().val!r}")

        self.expect(TT.RBRACE)
        return SeamDecl(name=name, members=members, kind=kind,
                        passage=passage, filter_spec=filter_spec,
                        failure_prop=failure_prop)

    # -- Stage -------------------------------------------------------------

    def parse_stage(self) -> StageDecl:
        tok = self.expect(TT.KW_STAGE)
        name = self.expect(TT.IDENT).val
        self.expect(TT.LBRACE)

        budget = None; anchor = None; phases = {}; default = None; transition = None

        while not self.check(TT.RBRACE, TT.EOF):
            field_name = self.peek().val if self.peek().typ == TT.IDENT else None
            if field_name == "budget":
                self.advance(); self.expect(TT.COLON)
                budget = self.parse_budget()
            elif field_name == "anchor":
                self.advance(); self.expect(TT.COLON)
                anchor = self.parse_anchor_spec()
            elif field_name == "phases":
                self.advance(); self.expect(TT.COLON)
                phases = self.parse_phases_block()
            elif field_name == "default":
                self.advance(); self.expect(TT.COLON)
                default = self.parse_phase_config()
            elif field_name == "transition":
                self.advance(); self.expect(TT.COLON)
                transition = self.parse_transition_block()
            else:
                self.error(f"Unknown stage field: {self.peek().val!r}")

        self.expect(TT.RBRACE)
        return StageDecl(name=name, budget=budget, anchor=anchor,
                         phases=phases, default=default, transition=transition)

    def parse_phases_block(self) -> dict[str, PhaseConfig]:
        self.expect(TT.LBRACE)
        phases = {}
        while not self.check(TT.RBRACE, TT.EOF):
            phase_tok = self.peek()
            if phase_tok.typ not in PHASE_SIGILS:
                self.error("Expected phase sigil in phases block")
            phase_name = self.advance().val
            self.expect(TT.COLON)
            phases[phase_name] = self.parse_phase_config()
            self.match(TT.COMMA)
        self.expect(TT.RBRACE)
        return phases

    def parse_phase_config(self) -> PhaseConfig:
        tok = self.peek()
        self.expect(TT.LBRACE)
        arrangement = None; visible = []; faded = []; hidden = []; dominant = None

        FIELD_LIKE = {TT.IDENT, TT.KW_HIDDEN, TT.KW_BACKGROUND, TT.KW_PRIMARY,
                      TT.KW_SECONDARY, TT.KW_AUTO, TT.KW_FREE, TT.KW_STACK,
                      TT.KW_SEQUENCE, TT.KW_EQUAL, TT.KW_GRID, TT.KW_DOMINANT,
                      TT.KW_ADAPTIVE, TT.KW_FIXED, TT.KW_SHARED, TT.KW_WHOLE,
                      TT.KW_CEILING}
        while not self.check(TT.RBRACE, TT.EOF):
            field_name = self.peek().val if self.peek().typ in FIELD_LIKE else None
            if field_name == "arrangement":
                self.advance(); self.expect(TT.COLON)
                arrangement = self.parse_arrangement()
            elif field_name == "visible":
                self.advance(); self.expect(TT.COLON)
                visible = self.parse_ident_list()
            elif field_name == "faded":
                self.advance(); self.expect(TT.COLON)
                faded = self.parse_ident_list()
            elif field_name == "hidden":
                self.advance(); self.expect(TT.COLON)
                hidden = self.parse_ident_list()
            elif field_name == "dominant":
                self.advance(); self.expect(TT.COLON)
                dominant = self.expect(TT.IDENT).val
            else:
                self.error(f"Unknown phase config field: {self.peek().val!r}")

        self.expect(TT.RBRACE)
        return PhaseConfig(arrangement=arrangement, visible=visible, faded=faded,
                           hidden=hidden, dominant=dominant)

    def parse_transition_block(self) -> dict:
        self.expect(TT.LBRACE)
        result = {}
        while not self.check(TT.RBRACE, TT.EOF):
            # Accept any token as a key — keywords like 'sequence', 'curve' etc.
            key_tok = self.advance()
            key = key_tok.val if key_tok.val is not None else key_tok.typ.name.lower()
            self.expect(TT.COLON)
            result[key] = self.parse_raw_expr()
            self.match(TT.COMMA)
        self.expect(TT.RBRACE)
        return result

    # -- Flow --------------------------------------------------------------

    def parse_flow(self) -> FlowDecl:
        tok = self.expect(TT.KW_FLOW)
        name = self.expect(TT.IDENT).val
        self.expect(TT.LBRACE)

        trigger = None; steps = []; on_stall = None; terminal = []

        while not self.check(TT.RBRACE, TT.EOF):
            field_name = self.peek().val if self.peek().typ == TT.IDENT else None
            if field_name == "trigger":
                self.advance(); self.expect(TT.COLON)
                trigger = self.parse_trigger()
            elif field_name == "steps":
                self.advance(); self.expect(TT.COLON)
                steps = self.parse_step_list()
            elif field_name == "on_stall":
                self.advance(); self.expect(TT.COLON)
                on_stall = self.parse_stall_spec()
            elif field_name == "terminal":
                self.advance(); self.expect(TT.COLON)
                terminal = self.parse_terminal()
            else:
                self.error(f"Unknown flow field: {self.peek().val!r}")

        self.expect(TT.RBRACE)
        return FlowDecl(name=name, trigger=trigger, steps=steps,
                        on_stall=on_stall, terminal=terminal)

    def parse_step_list(self) -> list[StepDecl]:
        self.expect(TT.LBRACK)
        steps = []
        while not self.check(TT.RBRACK, TT.EOF):
            steps.append(self.parse_step())
        self.expect(TT.RBRACK)
        return steps

    def parse_step(self) -> StepDecl:
        tok = self.expect(TT.KW_STEP)
        name = self.expect(TT.IDENT).val
        self.expect(TT.LBRACE)

        duration = None; state_str = None; claim = None
        exit_cond = None; affordances = []

        while not self.check(TT.RBRACE, TT.EOF):
            field_name = self.peek().val if self.peek().typ == TT.IDENT else None
            if field_name == "duration":
                self.advance(); self.expect(TT.COLON)
                if self.check(TT.KW_UNBOUNDED):
                    self.advance(); duration = "unbounded"
                else:
                    duration = self.parse_deadline()
            elif field_name == "state":
                self.advance(); self.expect(TT.COLON)
                state_str = self.parse_raw_expr()
            elif field_name == "claim":
                self.advance(); self.expect(TT.COLON)
                claim = self.parse_raw_expr()
            elif field_name == "exit":
                self.advance(); self.expect(TT.COLON)
                exit_cond = self.parse_raw_expr()
            elif field_name == "affordances":
                self.advance(); self.expect(TT.COLON)
                affordances = self.parse_ident_list()
            else:
                self.error(f"Unknown step field: {self.peek().val!r}")

        self.expect(TT.RBRACE)
        return StepDecl(name=name, duration=duration, state=state_str,
                        claim=claim, exit_cond=exit_cond, affordances=affordances)

    def parse_stall_spec(self) -> StallSpec:
        tok = self.peek()
        self.expect(TT.LBRACE)
        threshold = None; surface = None; recovery = []

        while not self.check(TT.RBRACE, TT.EOF):
            field_name = self.peek().val if self.peek().typ == TT.IDENT else None
            if field_name == "threshold":
                self.advance(); self.expect(TT.COLON)
                threshold = self.parse_deadline()
            elif field_name == "surface":
                self.advance(); self.expect(TT.COLON)
                surface = self.parse_failure_sigil()
            elif field_name == "recovery":
                self.advance(); self.expect(TT.COLON)
                recovery = self.parse_ident_list()
            else:
                self.error(f"Unknown stall spec field: {self.peek().val!r}")

        self.expect(TT.RBRACE)
        return StallSpec(threshold=threshold, surface=surface, recovery=recovery)

    def parse_terminal(self) -> list[str]:
        """Parse terminal: success | failure(...) | partial(...) | abandoned(...)"""
        items = []
        item = self.parse_raw_expr()
        items.append(item)
        while self.match(TT.PIPE):
            items.append(self.parse_raw_expr())
        return items

    # -- Contract (top-level declaration) ----------------------------------

    def parse_contract_top(self) -> ContractDecl:
        return self.parse_contract_inner()

    def parse_contract_inner(self) -> ContractDecl:
        tok = self.expect(TT.KW_CONTRACT)
        name = self.expect(TT.IDENT).val
        self.expect(TT.LBRACE)

        trigger = None; obligation = None; deadline = None; on_breach = None

        while not self.check(TT.RBRACE, TT.EOF):
            field_name = self.peek().val if self.peek().typ == TT.IDENT else None
            if field_name == "trigger":
                self.advance(); self.expect(TT.COLON)
                trigger = self.parse_trigger()
            elif field_name == "obligation":
                self.advance(); self.expect(TT.COLON)
                obligation = self.parse_obligation()
            elif field_name == "deadline":
                self.advance(); self.expect(TT.COLON)
                deadline = self.parse_deadline()
            elif field_name == "on_breach":
                self.advance(); self.expect(TT.COLON)
                on_breach = self.parse_failure_sigil()
            else:
                self.error(f"Unknown contract field: {self.peek().val!r}")

        self.expect(TT.RBRACE)
        return ContractDecl(name=name, trigger=trigger, obligation=obligation,
                            deadline=deadline, on_breach=on_breach)

    # -- Sub-parsers -------------------------------------------------------

    def parse_budget(self) -> BudgetNode:
        tok = self.peek()
        if self.match(TT.KW_AUTO):
            return BudgetNode(kind="auto", args=[])
        if self.match(TT.KW_WHOLE):
            self.expect(TT.LPAREN); n = self.expect(TT.NUMBER).val; self.expect(TT.RPAREN)
            return BudgetNode(kind="whole", args=[n])
        if self.match(TT.KW_FIXED):
            self.expect(TT.LPAREN); n = self.expect(TT.NUMBER).val; self.expect(TT.RPAREN)
            return BudgetNode(kind="fixed", args=[n])
        if self.match(TT.KW_CEILING):
            self.expect(TT.LPAREN)
            n = self.expect(TT.NUMBER).val; self.expect(TT.COMMA)
            base = self.parse_budget()
            self.expect(TT.RPAREN)
            return BudgetNode(kind="ceiling", args=[n, base])
        if self.match(TT.KW_SHARED):
            self.expect(TT.LPAREN)
            n = self.expect(TT.NUMBER).val; self.expect(TT.COMMA)
            k = self.expect(TT.IDENT).val  # may be an identifier like n_seats
            self.expect(TT.RPAREN)
            return BudgetNode(kind="shared", args=[n, k])
        self.error("Expected budget expression (whole, fixed, auto, ceiling, shared)")

    def parse_arrangement(self) -> ArrangementNode:
        tok = self.peek()
        kw_to_kind = {
            TT.KW_SEQUENCE: "sequence", TT.KW_EQUAL: "equal",
            TT.KW_DOMINANT: "dominant", TT.KW_GRID: "grid",
            TT.KW_FREE: "free", TT.KW_STACK: "stack",
            TT.KW_ADAPTIVE: "adaptive",
        }
        if self.peek_type() in kw_to_kind:
            kind = kw_to_kind[self.advance().typ]
            # Parse args as raw expression list in parens
            args = []
            if self.match(TT.LPAREN):
                args = self.parse_raw_arg_list()
                self.expect(TT.RPAREN)
            return ArrangementNode(kind=kind, args=args)
        self.error("Expected arrangement keyword")

    def parse_certainty(self) -> CertaintyNode:
        tok = self.peek()
        if tok.typ == TT.KW_COMPOSITE:
            self.advance()
            self.expect(TT.LPAREN)
            self.expect(TT.LBRACK)
            items = []
            while not self.check(TT.RBRACK, TT.EOF):
                items.append(self.parse_certainty())
                self.match(TT.COMMA)
            self.expect(TT.RBRACK)
            self.expect(TT.RPAREN)
            return CertaintyNode(kind="composite", args=items)

        sigil_to_kind = {
            TT.TAU_CERTAIN:   "certain",
            TT.TAU_INFERRED:  "inferred",
            TT.TAU_PROBABLE:  "probable",
            TT.TAU_UNKNOWN:   "unknown",
            TT.TAU_CONTESTED: "contested",
        }
        if tok.typ == TT.TAU_STALE:
            self.advance()
            args = []
            if self.match(TT.LPAREN):
                t0 = self.parse_raw_expr(); self.expect(TT.COMMA)
                elapsed = self.parse_deadline(); self.expect(TT.RPAREN)
                args = [t0, elapsed]
            return CertaintyNode(kind="stale", args=args)

        if tok.typ in sigil_to_kind:
            kind = sigil_to_kind[self.advance().typ]
            return CertaintyNode(kind=kind, args=[])

        # Also accept identifier references (from let bindings)
        if tok.typ == TT.IDENT:
            name = self.advance().val
            return CertaintyNode(kind="ref", args=[name])

        self.error("Expected certainty sigil (tau_certain, tau_inferred, etc.) or composite")

    def parse_stakes(self) -> StakesNode:
        tok = self.peek()
        levels = {TT.KW_LOW: "low", TT.KW_MEDIUM: "medium",
                  TT.KW_HIGH: "high", TT.KW_CRITICAL: "critical"}
        if tok.typ in levels:
            return StakesNode(level=levels[self.advance().typ])
        if tok.typ == TT.IDENT:  # e.g. context_dependent
            return StakesNode(level=self.advance().val)
        self.error("Expected stakes level (low, medium, high, critical)")

    def parse_phase_spec(self) -> PhaseSpec:
        tok = self.peek()
        if self.match(TT.KW_ANY):
            return PhaseSpec(phases=["any"])
        if self.check(TT.LBRACK):
            self.advance()
            phases = []
            while not self.check(TT.RBRACK, TT.EOF):
                pt = self.peek()
                if pt.typ in PHASE_SIGILS:
                    phases.append(self.advance().val)
                else:
                    self.error("Expected phase sigil in phase list")
                self.match(TT.COMMA)
            self.expect(TT.RBRACK)
            return PhaseSpec(phases=phases)
        if self.peek_type() in PHASE_SIGILS:
            return PhaseSpec(phases=[self.advance().val])
        self.error("Expected phase specification")

    def parse_anchor_spec(self) -> AnchorSpec:
        tok = self.peek()
        self.expect(TT.LBRACE)
        elements = []; position = "top"
        while not self.check(TT.RBRACE, TT.EOF):
            key = self.expect(TT.IDENT).val
            self.expect(TT.COLON)
            if key == "elements":
                elements = self.parse_ident_list()
            elif key == "position":
                position = self.expect(TT.IDENT).val
            else:
                self.parse_raw_expr()  # consume unknown field
        self.expect(TT.RBRACE)
        return AnchorSpec(elements=elements, position=position)

    def parse_weight(self) -> str:
        tok = self.peek()
        weights = {
            TT.KW_PRIMARY: "primary", TT.KW_SECONDARY: "secondary",
            TT.KW_TERTIARY: "tertiary", TT.KW_BACKGROUND: "background",
            TT.KW_HIDDEN: "hidden",
        }
        if tok.typ in weights:
            return weights[self.advance().typ]
        if tok.typ == TT.IDENT:
            return self.advance().val
        self.error("Expected weight (primary, secondary, tertiary, background, hidden)")

    def parse_trigger(self) -> TriggerNode:
        tok = self.peek()
        kind = self.expect_name()
        args = []
        if self.match(TT.LPAREN):
            args = self.parse_raw_arg_list()
            self.expect(TT.RPAREN)
        return TriggerNode(kind=kind, args=args)

    def parse_obligation(self) -> ObligationNode:
        tok = self.peek()
        kind = self.expect_name()
        args = []
        if self.match(TT.LPAREN):
            args = self.parse_raw_arg_list()
            self.expect(TT.RPAREN)
        return ObligationNode(kind=kind, args=args)

    def parse_deadline(self) -> DeadlineNode:
        tok = self.peek()
        if self.match(TT.KW_NONE):
            return DeadlineNode(kind="none", value=None)
        if self.match(TT.KW_SESSION):
            return DeadlineNode(kind="session", value=None)
        if self.peek_type() == TT.KW_UNBOUNDED:
            self.advance()
            return DeadlineNode(kind="unbounded", value=None)
        # ms(n), s(n), m(n), h(n)
        unit_kws = {"ms": "ms", "s": "s", "m": "m", "h": "h"}
        if self.peek_type() == TT.IDENT and self.peek().val in unit_kws:
            unit = self.advance().val
            self.expect(TT.LPAREN)
            n = self.expect(TT.NUMBER).val
            self.expect(TT.RPAREN)
            return DeadlineNode(kind=unit, value=n)
        # Fallback: bare number (treat as ms)
        if self.peek_type() == TT.NUMBER:
            n = self.advance().val
            return DeadlineNode(kind="ms", value=n)
        self.error("Expected deadline (none, session, ms(n), s(n), m(n), h(n))")

    def parse_failure_sigil(self) -> TT:
        tok = self.peek()
        if tok.typ in FAILURE_SIGILS:
            self.advance()
            return tok.typ
        self.error(f"Expected failure sigil (PHI_*)")

    def parse_provenance(self) -> Any:
        return self.parse_raw_expr()

    def parse_content_expr(self) -> Any:
        return self.parse_raw_expr()

    def parse_freshness(self) -> str:
        return self.parse_raw_expr()

    def parse_failure_prop(self) -> dict:
        self.expect(TT.LBRACE)
        result = {}
        while not self.check(TT.RBRACE, TT.EOF):
            key = self.expect(TT.IDENT).val
            self.expect(TT.COLON)
            result[key] = self.parse_raw_expr()
            self.match(TT.COMMA)
        self.expect(TT.RBRACE)
        return result

    def parse_contract_list(self) -> list[ContractDecl]:
        self.expect(TT.LBRACK)
        contracts = []
        while not self.check(TT.RBRACK, TT.EOF):
            contracts.append(self.parse_contract_inner())
            self.match(TT.COMMA)
        self.expect(TT.RBRACK)
        return contracts

    def parse_failure_spec_list(self) -> list[FailureSpec]:
        self.expect(TT.LBRACK)
        specs = []
        while not self.check(TT.RBRACK, TT.EOF):
            tok = self.peek()
            self.expect(TT.IDENT)  # FailureSpec
            self.expect(TT.LBRACE)
            trigger_str = ""; surfaces = TT.PHI_UNKNOWN; propagates = "no"
            while not self.check(TT.RBRACE, TT.EOF):
                key = self.expect(TT.IDENT).val
                self.expect(TT.COLON)
                if key == "trigger":
                    trigger_str = self.parse_raw_expr()
                elif key == "surfaces":
                    surfaces = self.parse_failure_sigil()
                elif key == "propagates":
                    propagates = self.parse_raw_expr()
                else:
                    self.parse_raw_expr()
            self.expect(TT.RBRACE)
            specs.append(FailureSpec(trigger=trigger_str, surfaces=surfaces,
                                     propagates=propagates))
            self.match(TT.COMMA)
        self.expect(TT.RBRACK)
        return specs

    def parse_event_handler_list(self) -> list[Any]:
        self.expect(TT.LBRACK)
        handlers = []
        while not self.check(TT.RBRACK, TT.EOF):
            handlers.append(self.parse_raw_expr())
            self.match(TT.COMMA)
        self.expect(TT.RBRACK)
        return handlers

    def parse_ident_list(self) -> list[str]:
        self.expect(TT.LBRACK)
        items = self.parse_ident_list_raw()
        self.expect(TT.RBRACK)
        return items

    def parse_ident_list_raw(self) -> list[str]:
        items = []
        while True:
            tt = self.peek_type()
            if tt != TT.IDENT and tt not in ALL_SIGIL_TYPES:
                break
            items.append(self.advance().val)
            self.match(TT.COMMA)
        return items

    def parse_value_expr(self) -> Any:
        """Parse a simple value: sigil, number, string, or ident"""
        tok = self.peek()
        if tok.typ in CERTAINTY_SIGILS:
            return self.parse_certainty()
        if tok.typ == TT.NUMBER:
            return self.advance().val
        if tok.typ == TT.STRING:
            return self.advance().val
        if tok.typ == TT.IDENT:
            return self.advance().val
        self.error("Expected value expression")

    def parse_raw_arg_list(self) -> list[Any]:
        """Parse comma-separated raw expressions until matching RPAREN."""
        args = []
        while not self.check(TT.RPAREN, TT.EOF):
            args.append(self.parse_raw_expr())
            if not self.match(TT.COMMA):
                break
        return args

    def parse_raw_expr(self) -> str:
        """
        Consume an expression as a raw string for fields we don't fully parse.
        Stops at comma, RBRACE, RBRACK, RPAREN, or a field-name pattern (ident ':').
        Handles nested parens/brackets/braces.
        """
        parts = []
        depth_paren = 0
        depth_brace = 0
        depth_brack = 0

        while True:
            tok = self.peek()
            if tok.typ == TT.EOF:
                break
            if depth_paren == 0 and depth_brace == 0 and depth_brack == 0:
                if tok.typ in (TT.COMMA, TT.RBRACE, TT.RBRACK, TT.RPAREN):
                    break
                if tok.typ == TT.PIPE:
                    break
                # field terminator: ident OR keyword followed by colon = new field
                next_is_colon = (self.pos + 1 < len(self.tokens) and
                                 self.tokens[self.pos + 1].typ == TT.COLON)
                if tok.typ == TT.IDENT and next_is_colon:
                    break
                # Also stop on keywords followed by colon (e.g. sequence:, curve:)
                if tok.typ in KEYWORDS.values() and next_is_colon:
                    break

            if tok.typ == TT.LPAREN:   depth_paren += 1
            elif tok.typ == TT.RPAREN: depth_paren -= 1
            elif tok.typ == TT.LBRACE: depth_brace += 1
            elif tok.typ == TT.RBRACE: depth_brace -= 1
            elif tok.typ == TT.LBRACK: depth_brack += 1
            elif tok.typ == TT.RBRACK: depth_brack -= 1

            parts.append(str(tok.val) if tok.val is not None else tok.typ.name)
            self.advance()

        return " ".join(parts)


# ---------------------------------------------------------------------------
# SECTION 5: TYPE CHECKER + VIOLATION REPORTER
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    code: str
    severity: str   # "error" | "warning"
    message: str
    node_name: str
    line: int = 0
    col: int = 0

    def __str__(self):
        sev = "ERROR  " if self.severity == "error" else "WARNING"
        return f"  [{self.code}] {sev} in '{self.node_name}' ({self.line}:{self.col})\n         {self.message}"


class TypeChecker:
    def __init__(self, program: Program, lets: dict[str, Any] = None):
        self.program = program
        self.lets: dict[str, Any] = lets or {}
        self.violations: list[Violation] = []
        self.vessels: dict[str, VesselDecl] = {}
        self.claims: dict[str, ClaimDecl] = {}
        self.affords: dict[str, AffordDecl] = {}
        self.stages: dict[str, StageDecl] = {}
        self.flows: dict[str, FlowDecl] = {}

    def v(self, code, severity, msg, name, node: Node):
        line = getattr(node, "line", 0); col = getattr(node, "col", 0)
        self.violations.append(Violation(code, severity, msg, name, line, col))

    def resolve_certainty_kind(self, c: CertaintyNode) -> str:
        if c.kind == "ref":
            ref_name = c.args[0]
            resolved = self.lets.get(ref_name)
            if isinstance(resolved, CertaintyNode):
                return self.resolve_certainty_kind(resolved)
            return "unknown"
        return c.kind

    def certainty_rank(self, kind: str) -> int:
        return {"certain": 5, "inferred": 4, "probable": 3,
                "stale": 2, "unknown": 1, "contested": 0, "ref": 3}.get(kind, 3)

    def composite_min(self, c: CertaintyNode) -> str:
        if c.kind != "composite":
            return self.resolve_certainty_kind(c)
        kinds = [self.composite_min(sub) for sub in c.args]
        return min(kinds, key=lambda k: self.certainty_rank(k), default="unknown")

    def check(self) -> list[Violation]:
        # Build lookup tables
        for decl in self.program.declarations:
            if isinstance(decl, LetDecl):
                self.lets[decl.name] = decl.value
            elif isinstance(decl, VesselDecl):
                self.vessels[decl.name] = decl
            elif isinstance(decl, ClaimDecl):
                self.claims[decl.name] = decl
            elif isinstance(decl, AffordDecl):
                self.affords[decl.name] = decl
            elif isinstance(decl, StageDecl):
                self.stages[decl.name] = decl
            elif isinstance(decl, FlowDecl):
                self.flows[decl.name] = decl

        for decl in self.program.declarations:
            if isinstance(decl, ClaimDecl):
                self.check_claim(decl)
            elif isinstance(decl, VesselDecl):
                self.check_vessel(decl)
            elif isinstance(decl, AffordDecl):
                self.check_afford(decl)
            elif isinstance(decl, StageDecl):
                self.check_stage(decl)
            elif isinstance(decl, FlowDecl):
                self.check_flow(decl)
            elif isinstance(decl, ContractDecl):
                self.check_contract(decl, context_name="<top-level>")
            elif isinstance(decl, BondDecl):
                self.check_bond(decl)

        return self.violations

    # TC-3: Certainty disclosure
    def check_claim(self, c: ClaimDecl):
        if c.certainty is None:
            self.v("VIOL-01", "error",
                   "Claim has no certainty declaration. "
                   "Grade or do not assert. Minimum: tau_inferred for AI-generated content.",
                   c.name, c)
            return

        cert_kind = self.composite_min(c.certainty) if c.certainty.kind == "composite" \
                    else self.resolve_certainty_kind(c.certainty)

        # AI-generated provenance cannot be certain
        if c.provenance and "ai_generated" in str(c.provenance):
            if cert_kind == "certain":
                self.v("VIOL-01", "error",
                       "AI-generated claim cannot have certainty = tau_certain. "
                       "Maximum for ai_generated provenance is tau_inferred.",
                       c.name, c)

        # Redacted content without reason
        if c.content and "redacted" in str(c.content) and c.content.count('"') < 2:
            self.v("VIOL-08", "error",
                   "Redacted content must declare a reason string. "
                   "Silent redaction transfers cognitive work to the human without contract.",
                   c.name, c)

    # TC-1, TC-2: Budget and load
    def check_vessel(self, v: VesselDecl):
        # TC-2: Load ceiling
        child_count = len(v.contains)
        if child_count > 9:
            self.v("VIOL-03", "error",
                   f"Load ceiling exceeded: {child_count} children in contains "
                   f"(max 9 = 7+2). Chunk or phase-gate related elements.",
                   v.name, v)

        # TC-1: All contained claims should have certainty
        for name in v.contains:
            if name in self.claims:
                claim = self.claims[name]
                if claim.certainty is None:
                    self.v("VIOL-01", "error",
                           f"Claim '{name}' in vessel has no certainty declaration.",
                           v.name, v)

        # Check contracts
        for c in v.contracts:
            self.check_contract(c, context_name=v.name)

        # TC-6: Anchor stability - if anchor declared, check it's in contained set
        if v.anchor:
            for elem in v.anchor.elements:
                if elem not in v.contains and elem not in self.vessels:
                    self.v("VIOL-11", "warning",
                           f"Anchor element '{elem}' not found in vessel's contains list.",
                           v.name, v)

        # TC-7: Failure coverage
        # Any contract with obligation = execute should have a breach handler
        for c in v.contracts:
            if c.obligation and c.obligation.kind == "execute" and c.on_breach is None:
                self.v("VIOL-12", "error",
                       f"Contract '{c.name}' executes an operation but has no on_breach handler. "
                       f"If the operation fails, the failure is silent (VIOL-08).",
                       v.name, c)

    def check_contract(self, c: ContractDecl, context_name: str):
        # TC-5: Acknowledge deadline
        if c.obligation and c.obligation.kind == "acknowledge":
            if c.deadline:
                if c.deadline.kind == "ms":
                    if c.deadline.value and c.deadline.value > 200:
                        self.v("VIOL-01", "warning",
                               f"Acknowledge contract '{c.name}' has deadline {c.deadline.value}ms > 200ms default. "
                               f"Delays above 200ms create user uncertainty.",
                               context_name, c)
                elif c.deadline.kind == "none":
                    self.v("VIOL-15", "warning",
                           f"Contract '{c.name}' has deadline = none. "
                           f"Infinite commitments may never be fulfilled.",
                           context_name, c)
            # no deadline declared: also warn
        elif c.deadline and c.deadline.kind == "none":
            self.v("VIOL-15", "warning",
                   f"Contract '{c.name}' has deadline = none. "
                   f"Infinite commitments may never be fulfilled.",
                   context_name, c)

        # TC-8: Escalation completeness
        if c.obligation and c.obligation.kind == "escalate":
            args_str = " ".join(str(a) for a in c.obligation.args)
            missing = []
            for required in ["reason", "options", "consequence", "default"]:
                if required not in args_str:
                    missing.append(required)
            if missing:
                self.v("VIOL-06", "error",
                       f"Escalation obligation in contract '{c.name}' is missing: {', '.join(missing)}. "
                       f"Escalation without full disclosure transfers confusion to the human.",
                       context_name, c)

    def check_afford(self, a: AffordDecl):
        # TC-?: on_unavail = hidden requires justification
        if a.on_unavail and "hidden" in str(a.on_unavail):
            has_justification = any(kw in str(a.on_unavail) for kw in ['"', "reason", "because"])
            if not has_justification:
                self.v("VIOL-14", "warning",
                       f"Affordance '{a.name}' uses on_unavail = hidden without a stated reason. "
                       f"Hidden affordances are undiscoverable. Prefer fade_locked(reason).",
                       a.name, a)

        # Affordance with contracts should have breach handlers
        for c in a.contracts:
            if c.obligation and c.obligation.kind == "execute" and c.on_breach is None:
                self.v("VIOL-12", "error",
                       f"Contract '{c.name}' in afford '{a.name}' has no on_breach. "
                       f"If execution fails, failure is silent.",
                       a.name, c)

    # TC-6, TC-12: Phase completeness and anchor stability in stages
    def check_stage(self, s: StageDecl):
        if not s.phases and s.default is None:
            self.v("VIOL-04", "error",
                   f"Stage '{s.name}' has no phases and no default. "
                   f"A stage must configure at least one phase or declare a default.",
                   s.name, s)
            return

        # TC-12: Phase completeness
        declared = set(s.phases.keys())
        all_phases = {"orient", "execute", "verify",
                      "integrate", "recover", "idle"}
        if s.default is None and declared != all_phases:
            missing_phases = all_phases - declared
            self.v("VIOL-04", "warning",
                   f"Stage '{s.name}' does not cover all phases and has no default. "
                   f"Uncovered phases: {', '.join(sorted(missing_phases))}.",
                   s.name, s)

        # TC-6: Anchor elements must never be in hidden list of any PhaseConfig
        anchor_elements = set(s.anchor.elements) if s.anchor else set()
        for phase_sig, config in s.phases.items():
            for elem in anchor_elements:
                if elem in config.hidden:
                    self.v("VIOL-11", "error",
                           f"Anchor element '{elem}' is in hidden list for phase {phase_sig}. "
                           f"Anchors must remain visible (or faded) in all phases. "
                           f"Hiding an anchor violates spatial memory.",
                           s.name, config)

        # VIOL-04: Intent blindness — all PhaseConfigs identical
        if len(s.phases) > 1:
            configs = list(s.phases.values())
            first = (sorted(configs[0].visible), sorted(configs[0].hidden))
            all_same = all((sorted(c.visible), sorted(c.hidden)) == first for c in configs[1:])
            if all_same:
                self.v("VIOL-04", "warning",
                       f"Stage '{s.name}' has identical phase configurations across all phases. "
                       f"This is intent-blindness: the surface does not adapt to the human's task phase.",
                       s.name, s)

    # TC-10: Stall coverage in flows
    def check_flow(self, f: FlowDecl):
        has_unbounded = any(
            (s.duration == "unbounded" or
             (isinstance(s.duration, DeadlineNode) and s.duration.kind == "unbounded"))
            for s in f.steps
        )

        if has_unbounded:
            if f.on_stall is None:
                self.v("VIOL-10", "error",
                       f"Flow '{f.name}' has unbounded steps but no on_stall declaration. "
                       f"Without stall coverage, a hung step surfaces nothing. "
                       f"This is Phi_silent in disguise.",
                       f.name, f)
            else:
                # Stall surface must not be PHI_SILENT
                if f.on_stall.surface == TT.PHI_SILENT:
                    self.v("VIOL-10", "error",
                           f"Flow '{f.name}' on_stall.surface = Phi_silent. "
                           f"Phi_silent is always a violation. A stall must surface visibly.",
                           f.name, f.on_stall)

        if not f.terminal:
            self.v("VIOL-10", "error",
                   f"Flow '{f.name}' has no terminal declaration. "
                   f"Open-ended flows are a violation: every flow must declare its possible endings.",
                   f.name, f)

    def check_bond(self, b: BondDecl):
        # Bonds of kind 'excludes' should note that symmetry is implied
        if b.kind and "excludes" in str(b.kind):
            if b.on_break is None:
                self.v("VIOL-12", "warning",
                       f"Bond '{b.name}' (excludes kind) has no on_break handler. "
                       f"If the exclusion constraint is violated, the failure is silent.",
                       b.name, b)


# ---------------------------------------------------------------------------
# SECTION 6: REPORT FORMATTING
# ---------------------------------------------------------------------------

def format_report(program: Program, violations: list[Violation], source_name: str) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append(f"GUILDS v2 — Validation Report")
    lines.append(f"Source : {source_name}")
    lines.append("=" * 70)

    # Summary counts
    decl_counts: dict[str, int] = {}
    for d in program.declarations:
        key = type(d).__name__
        decl_counts[key] = decl_counts.get(key, 0) + 1

    lines.append("\nDeclarations parsed:")
    for k, v in sorted(decl_counts.items()):
        lines.append(f"  {k:<20} {v}")

    errors   = [v for v in violations if v.severity == "error"]
    warnings = [v for v in violations if v.severity == "warning"]

    lines.append(f"\nViolations found:  {len(violations)}")
    lines.append(f"  Errors   : {len(errors)}")
    lines.append(f"  Warnings : {len(warnings)}")

    if violations:
        lines.append("\n" + "-" * 70)
        lines.append("ERRORS" if errors else "")
        for v in errors:
            lines.append(str(v))
        if warnings:
            lines.append("\n" + "-" * 70)
            lines.append("WARNINGS")
            for v in warnings:
                lines.append(str(v))
    else:
        lines.append("\n  PASS — specification is GUILDS-valid.")
        lines.append("  All claims graded. All contracts covered. All failures surfaced.")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SECTION 7: PUBLIC API + CLI
# ---------------------------------------------------------------------------

def parse_source(src: str, source_name: str = "<input>") -> tuple[Program, list[Violation]]:
    """
    Full pipeline: source -> tokens -> AST -> type-checked violations.
    Returns (program, violations).
    """
    lexer = Lexer(src)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    program = parser.parse()
    checker = TypeChecker(program)
    violations = checker.check()
    return program, violations


def main():
    if len(sys.argv) < 2:
        print("Usage: guilds_parser.py <file.guilds>")
        print("       guilds_parser.py --example")
        sys.exit(1)

    if sys.argv[1] == "--example":
        src = EXAMPLE_SOURCE
        source_name = "<built-in example>"
    else:
        with open(sys.argv[1], "r") as f:
            src = f.read()
        source_name = sys.argv[1]

    try:
        program, violations = parse_source(src, source_name)
    except (LexError, ParseError) as e:
        print(f"\nFATAL: {e}")
        sys.exit(2)

    report = format_report(program, violations, source_name)
    print(report)

    has_errors = any(v.severity == "error" for v in violations)
    sys.exit(1 if has_errors else 0)


# ---------------------------------------------------------------------------
# SECTION 8: BUILT-IN EXAMPLES
# Two examples: one valid, one deliberately invalid.
# ---------------------------------------------------------------------------

EXAMPLE_SOURCE = """\
-- GUILDS v2 Example Suite
-- Example A: Valid stream panel specification

let seatCert = 0x03C4~

claim StreamOutput {
    content:    text(output_buffer)
    certainty:  0x03C4~
    provenance: source.ai_generated(model, context)
    stakes:     medium
    freshness:  live
    on_stale:   mark_stale
}

claim LoadingIndicator {
    content:    empty("Awaiting first token")
    certainty:  0x03C40x2205
    provenance: source.direct(stream_subsystem)
    stakes:     low
    freshness:  event_driven(stream_start)
    on_stale:   mark_stale
}

flow StreamFlow {
    trigger: system_event(stream_start)
    steps: [
        step Acquiring {
            duration:  ms(200)
            state:     acquiring
            exit:      on_event(first_token)
        }
        step Streaming {
            duration:  unbounded
            state:     streaming(progress = token_count)
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

vessel StreamPanel {
    budget:      whole(0.6)
    phase:       [0x03C60x2081, 0x03C60x2082]
    arrangement: sequence(primary, [0.1, 0.8, 0.1])
    weight:      primary
    contains:    [StreamOutput, LoadingIndicator]
    contracts: [
        contract AckStart {
            trigger:     system_event(stream_start)
            obligation:  acknowledge
            deadline:    ms(200)
            on_breach:   0x03A60x2193
        }
        contract SurfaceStall {
            trigger:     system_event(stream_stall)
            obligation:  surface(0x03A60x27F3)
            deadline:    s(5)
            on_breach:   0x03A60x2014
        }
    ]
}

-- Example B: Invalid specification (deliberate violations for demonstration)

claim BadClaim {
    content:    text(inferred_data)
    certainty:  0x03C40x2713
    provenance: source.ai_generated(llm, context)
    stakes:     high
    freshness:  live
    on_stale:   mark_stale
}

vessel OverloadedVessel {
    budget:  whole(0.9)
    phase:   any
    weight:  primary
    contains: [A, B, C, D, E, F, G, H, I, J]
}

flow OpenFlow {
    trigger: system_event(start)
    steps: [
        step Forever {
            duration:  unbounded
            state:     processing
            exit:      on_event(never)
        }
    ]
    terminal: success
}

stage IdenticalStage {
    budget: whole(1.0)
    phases: {
        0x03C60x2080: {
            arrangement: sequence(primary, [1.0])
            visible:     [MainPanel]
            faded:       []
            hidden:      []
            dominant:    MainPanel
        }
        0x03C60x2081: {
            arrangement: sequence(primary, [1.0])
            visible:     [MainPanel]
            faded:       []
            hidden:      []
            dominant:    MainPanel
        }
    }
}
"""

if __name__ == "__main__":
    main()
