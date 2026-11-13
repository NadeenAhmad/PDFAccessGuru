"""
Formulas (1.1): display equations (on their own line, in math fonts or with math signs, often
with an equation number such as "(3)" at the right margin) become Formula elements; math inside
a sentence stays part of the sentence.

layout.py calls find_formulas() for every page; builder.py gives each Formula its bounding box.
The description (/Alt) is written by the formula fix (rule 7.7-1): with an AI from a crop of
the page at that box, without an AI from formula_spoken_text() of the formula's own text.
"""

from __future__ import annotations

import re
import unicodedata

import pymupdf as fitz

_MATH_FONT = re.compile(r"cmmi|cmsy|cmex|cmbsy|cmmib|msam|msbm|eufm|eusm|rsfs|"
                        r"math|stix|symbol|mt ?extra|mtsy|mtmi|euclid|txsy|txex|txmi|rtxmi|rtxr|ntxmi|ntxsy|"
                        r"pxsy|pxex|pxmi|zplm|esint|wasy|stmary|lmmi|lmsy|lmex|xits|asana|cambria ?math",
                        re.IGNORECASE)
_MONOSPACE = re.compile(r"mono|courier|consol|cmtt|sftt|inconsolata|menlo|typewriter", re.IGNORECASE)
_MATH_SIGNS = set("=<>±∓×÷−∑∏∫∮√∂∇∞≤≥≠≈≡∼≃≅∝∈∉⊂⊆⊃⊇∪∩∀∃∄¬∧∨→←↔⇒⇐⇔↦∘⊗⊕⋅·∗′″‖∅ℝℕℤℚℂ")
_RELATIONS = set("=<>≤≥≠≈≡∼≃≅∝∈∉⊂⊆⊃⊇→⇒⇔↦")
_EQUATION_NUMBER = re.compile(r"^\(\s*([A-Za-z]?\d{1,3}(?:\.\d{1,3})*[a-z]?)\s*\)$")
_NUMBER_AT_LINE_END = re.compile(r"\s\(\s*[A-Za-z]?\d{1,3}(?:\.\d{1,3})*[a-z]?\s*\)$")
_FUNCTIONS = {"exp", "log", "sin", "cos", "tan", "max", "min", "lim", "sup", "inf", "det", "arg", "mod",
              "gcd", "deg", "dim", "ker", "var", "cov", "sgn", "sinh", "cosh", "tanh", "argmax", "argmin",
              "and", "for", "if", "or", "otherwise", "where", "with"}


# ------------------------------------------------------------------------------- spoken form

_GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "ϵ": "epsilon", "ζ": "zeta",
    "η": "eta", "θ": "theta", "ϑ": "theta", "ι": "iota", "κ": "kappa", "λ": "lambda", "μ": "mu", "µ": "mu",
    "ν": "nu", "ξ": "xi", "ο": "omicron", "π": "pi", "ϖ": "pi", "ρ": "rho", "ϱ": "rho", "σ": "sigma",
    "ς": "sigma", "τ": "tau", "υ": "upsilon", "φ": "phi", "ϕ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
    "Γ": "capital gamma", "Δ": "capital delta", "Θ": "capital theta", "Λ": "capital lambda",
    "Ξ": "capital xi", "Π": "capital pi", "Σ": "capital sigma", "Υ": "capital upsilon",
    "Φ": "capital phi", "Ψ": "capital psi", "Ω": "capital omega", "∆": "capital delta",
}
_SIGNS = {
    "∑": "sum of", "∏": "product of", "∫": "integral of", "∮": "contour integral of", "√": "square root of",
    "∂": "partial", "∇": "nabla", "∞": "infinity", "≤": "less than or equal to", "≥": "greater than or equal to",
    "⩽": "less than or equal to", "⩾": "greater than or equal to", "≠": "not equal to",
    "≈": "approximately equal to", "≃": "approximately equal to", "≅": "congruent to", "≡": "equivalent to",
    "∼": "similar to", "∝": "proportional to", "±": "plus or minus", "∓": "minus or plus", "×": "times",
    "·": "times", "⋅": "times", "∗": "star", "÷": "divided by", "−": "minus", "+": "plus", "=": "equals",
    "<": "less than", ">": "greater than", "≪": "much less than", "≫": "much greater than",
    "→": "goes to", "←": "from", "↦": "maps to", "⇒": "implies", "⇐": "is implied by",
    "⇔": "if and only if", "↔": "if and only if", "∈": "in", "∉": "not in", "⊂": "subset of",
    "⊆": "subset of or equal to", "⊃": "superset of", "⊇": "superset of or equal to", "∪": "union",
    "∩": "intersection", "∀": "for all", "∃": "there exists", "¬": "not", "∧": "and", "∨": "or",
    "∘": "composed with", "⊗": "tensor product", "⊕": "direct sum", "′": "prime", "″": "double prime",
    "‖": "norm", "∅": "empty set", "ℝ": "R", "ℕ": "N", "ℤ": "Z", "ℚ": "Q", "ℂ": "C", "°": "degrees",
    "…": "dots", "⋯": "dots", "⋮": "dots", "ˆ": "hat", "¯": "bar", "˜": "tilde", "/": "over",
}
_WORDS = {**_GREEK, **_SIGNS}
_ACCENTS = {"\u0302": " hat ", "\u0303": " tilde ", "\u0304": " bar ", "\u0305": " bar ", "\u0307": " dot "}
_POWER = re.compile(r"\^\s*(\{[^{}]*\}|\S)")
_INDEX = re.compile(r"_\s*(\{[^{}]*\}|\S)")
_NUMBER = re.compile(r"(?:^|(?<=[\s,.;:]))\(\s*([A-Za-z]?\d{1,3}(?:\.\d{1,3})*[a-z]?)\s*\)(?=\s|[.,;]|[^\W\d_]|$)")
_UNKNOWN_GLYPH = re.compile(r"\(cid:\d+\)")      # a sign without a known character (pdfplumber)
_MAX_SPOKEN = 300


def formula_spoken_text(text: str) -> str:
    """
    A short spoken form of a formula's text for screen readers, without an AI: Greek letters by
    name, signs as words (sum of, square root of, less than or equal to ...), "^2" as "to the
    power of 2", "x_i" as "x sub i", and the equation number first ("Equation 3: ..."). Fractions
    and the layout of large formulas cannot be recovered from the text, so the result is the
    formula read from left to right; an AI (or the author) can improve it. Returns "" if the
    text holds nothing to read.
    """
    text = _UNKNOWN_GLYPH.sub(" ", text or "")
    text = unicodedata.normalize("NFKC", text)              # mathematical italic letters -> plain letters
    text = "".join(_ACCENTS.get(char, char) for char in text
                   if (unicodedata.category(char)[0] != "C" or char in " \t\n") and not "\u239b" <= char <= "\u23b3")
    text = " ".join(text.split())
    prefix = ""
    numbers = _NUMBER.findall(text)
    if numbers and len(text) > 6:                       # "(3)" alone, or with the formula
        prefix = f"Equation {numbers[0]}: " if len(numbers) == 1 else \
            f"Equations {', '.join(numbers[:-1])} and {numbers[-1]}: "
        text = _NUMBER.sub(" ", text)
    text = text.strip(" ,.;")
    text = _POWER.sub(lambda match: " to the power of " + match.group(1).strip("{}") + " ", text)
    text = _INDEX.sub(lambda match: " sub " + match.group(1).strip("{}") + " ", text)
    spoken = []
    for index, char in enumerate(text):
        if char == "-" and 0 < index < len(text) - 1 and (text[index - 1] == " " or text[index + 1] == " "):
            spoken.append(" minus ")                    # a minus sign, not a hyphen in a word
        elif char in _WORDS:
            spoken.append(f" {_WORDS[char]} ")
        else:
            spoken.append(char)
    result = " ".join("".join(spoken).split())
    if not any(char.isalnum() for char in result):
        return ""
    if len(result) > _MAX_SPOKEN:
        result = result[:_MAX_SPOKEN].rsplit(" ", 1)[0] + " ..."
    return prefix + result


# ------------------------------------------------------------------------------- detection

class _LineInfo:
    """What a text line is made of: math signs and fonts, words of the sentence, an equation number."""

    def __init__(self, item, line, spans: list[dict]) -> None:
        self.item, self.line = item, line
        self.rect = line.rect
        chars = math = 0
        prose = 0
        monospace = 0
        self.relation = False
        for span in spans:
            text = span["text"]
            font = span.get("font", "")
            math_font = bool(_MATH_FONT.search(font))
            italic = bool(span.get("flags", 0) & 2) or "ital" in font.lower() or "oblique" in font.lower()
            for char in text:
                if char.isspace():
                    continue
                chars += 1
                if math_font or char in _MATH_SIGNS or char in _GREEK:
                    math += 1
                if char in _RELATIONS:
                    self.relation = True
                if _MONOSPACE.search(font):
                    monospace += 1
            # words of a sentence: in a text font, or long words in any font (some text fonts are
            # called "...Math"; variables in formulas are short)
            shortest = 3 if not math_font and not italic else 4
            prose += sum(1 for word in re.findall(r"[^\W\d_]{%d,}" % shortest, text)
                         if word.lower() not in _FUNCTIONS)
        self.chars, self.math, self.prose = chars, math, prose
        self.number = bool(_EQUATION_NUMBER.match(line.text.strip()))
        self.numbered = bool(_NUMBER_AT_LINE_END.search(line.text))   # "E = m c 2 (1)" on one line
        self.monospace = monospace > chars * 0.5

    @property
    def mathy(self) -> bool:
        """Mostly math: math signs or fonts and at most one word of a sentence."""
        return (not self.monospace and not self.number and self.math >= 1 and self.prose <= 1
                and (self.math >= self.chars * 0.25 or self.relation))

    @property
    def sentence(self) -> bool:
        """Words of a sentence: never part of a display equation."""
        return self.prose >= 2 or (self.prose == 1 and not self.mathy)

    @property
    def candidate(self) -> bool:
        """Can be part of a display equation: math, an equation number, or a piece without words."""
        return not self.monospace and (self.number or self.mathy or self.prose == 0)

    @property
    def weak(self) -> bool:
        """A short piece without words: the denominator of a fraction, an index, a big sum sign."""
        return not self.monospace and not self.number and self.chars <= 8 and self.prose == 0


def _span_index(data: dict) -> dict[tuple, list[dict]]:
    index: dict[tuple, list[dict]] = {}
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            index[tuple(round(value, 1) for value in line["bbox"])] = line["spans"]
    return index


def find_formulas(page: fitz.Page, data: dict, items: list, body: float) -> list:
    """Display equations of a page become Formula items; their lines leave the paragraphs."""
    from pdfaccessguru.tagging.layout import Item

    spans = _span_index(data)
    infos = [_LineInfo(item, line, spans.get(tuple(round(value, 1) for value in line.rect), []))
             for item in items if item.kind in ("P", "LI") for line in item.lines]
    if not any(info.mathy and info.math >= 2 for info in infos):
        return items                                     # no math on this page
    prose = [info for info in infos if info.sentence]
    text_left = min((info.rect.x0 for info in infos), default=page.rect.x0)
    text_right = max((info.rect.x1 for info in infos), default=page.rect.x1)

    def column_of(rect: fitz.Rect) -> tuple[float, float]:
        """The column a line is in, from the nearest full paragraph lines above and below it."""
        near = [info.rect for info in prose if info.chars >= 25 and info.rect.x0 <= rect.x1
                and info.rect.x1 >= rect.x0 and abs(info.rect.y0 - rect.y0) < 250]
        narrow = [r for r in near if r.width < (text_right - text_left) * 0.6]      # lines of a column
        near = sorted(narrow or near, key=lambda r: abs(r.y0 - rect.y0))[:6]
        if not near:
            return text_left, text_right
        return min(r.x0 for r in near), max(r.x1 for r in near)

    used: set[int] = set()
    groups: list[list[_LineInfo]] = []
    seeds = [info for info in infos if (info.mathy and info.math >= 2) or info.number]
    for seed in sorted(seeds, key=lambda i: (not i.number, i.rect.y0)):         # numbered ones first
        if id(seed) in used:
            continue
        left, right = column_of(seed.rect)
        group = [seed]
        band = fitz.Rect(seed.rect)
        grown = True
        while grown:
            grown = False
            for info in infos:
                if id(info) in used or info in group or not info.candidate:
                    continue
                rect = info.rect
                if rect.x0 < left - 4 or rect.x1 > right + 4:
                    continue
                gap = max(band.y0 - rect.y1, rect.y0 - band.y1)
                if gap <= min(rect.height, band.height, body * 1.2) * 0.6:
                    group.append(info)
                    band |= rect
                    grown = True
        # a display equation has the band to itself: no sentence beside it in the same column
        if any(other.rect.x0 < right and other.rect.x1 > left
               and min(other.rect.y1, band.y1) - max(other.rect.y0, band.y0) > other.rect.height * 0.5
               for other in prose):
            continue
        numbers = [info for info in group if info.number or (info.numbered and info.mathy)]
        math_lines = [info for info in group if not info.number]
        math = sum(info.math for info in math_lines)
        chars = sum(info.chars for info in math_lines)
        if not math_lines or math < 2 or (numbers and any(info.rect.x1 < right - 30 for info in numbers)):
            continue                                     # an equation number sits at the right margin
        if not numbers and not (math >= 3 and math >= chars * 0.3 and sum(info.prose for info in group) == 0
                                and band.x0 >= left + 15 and band.x1 <= right - 15):
            continue                                     # without a number: clearly math, set apart
        groups.append(group)
        used.update(id(info) for info in group)

    if not groups:
        return items
    taken = {id(info.line) for group in groups for info in group}
    result = []
    for item in items:
        if item.kind not in ("P", "LI") or not any(id(line) in taken for line in item.lines):
            result.append(item)
            continue
        # the paragraph around an equation is split: the text before and the text after it
        part: list = []
        for line in item.lines:
            if id(line) in taken:
                if part:
                    result.append(_piece(item, part))
                    part = []
                continue
            part.append(line)
        if part:
            result.append(_piece(item, part))
    for group in groups:
        lines = sorted((info.line for info in group), key=lambda line: (round(line.rect.y0 + line.rect.y1), line.rect.x0))
        rect = fitz.Rect(lines[0].rect)
        for line in lines[1:]:
            rect |= line.rect
        result.append(Item("Formula", page.number, rect, lines, text=" ".join(line.text for line in lines)))
    return result


def _piece(item, lines: list):
    from pdfaccessguru.tagging.layout import Item

    rect = fitz.Rect(lines[0].rect)
    for line in lines[1:]:
        rect |= line.rect
    kind = item.kind if lines[0] is item.lines[0] else "P"   # only the first piece keeps a list marker
    return Item(kind, item.page, rect, lines, level=item.level)
