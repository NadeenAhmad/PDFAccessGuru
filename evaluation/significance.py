"""
Significance of the differences in the README tables: paired tests, PDFAccessGuru against the original files and the
other tools, on the same files and items.

  - Numbers per file or item (problems left, share of text a screen reader reaches, helpfulness, answers coded
    yes = 2, partly = 1, no = 0): Wilcoxon signed-rank test, zero differences left out, exact for up to 60 non-zero
    pairs, normal approximation with tie correction above.
  - Yes/no per file or item (passes, describes the picture well, language right): exact McNemar test.
  - Judges: the mean of the two judges per item (for yes/no: both judges).
  - All p-values are corrected for the number of tests with Holm's method.

Only the Python standard library.

    python evaluation/significance.py

Reads results/acrobat/files.csv, results/runs/, results/opendataloader/, results/expert-judgement/. Writes
results/significance/tests.csv and results/significance/summary.md.
"""

from __future__ import annotations

import collections
import csv
import math
import statistics

from paths import RESULTS

OUT = RESULTS / "significance"
SCORE = {"yes": 2, "partly": 1, "no": 0}
PAG = {"rules": "PDFAccessGuru without AI", "gemma": "PDFAccessGuru with AI"}


# ------------------------------------------------------------------ tests

def wilcoxon(a: list[float], b: list[float]) -> float:
    """Two-sided p of the Wilcoxon signed-rank test for paired values."""
    diffs = [x - y for x, y in zip(a, b) if x != y]
    n = len(diffs)
    if n == 0:
        return 1.0
    order = sorted(range(n), key=lambda i: abs(diffs[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(diffs[order[j + 1]]) == abs(diffs[order[i]]):
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j + 2) / 2
        i = j + 1
    w_plus = sum(r for r, d in zip(ranks, diffs) if d > 0)
    if n <= 60:                                               # exact: every sign pattern of the (doubled) ranks
        doubled = [int(round(2 * r)) for r in ranks]
        counts = collections.Counter({0: 1})
        for r in doubled:
            step = collections.Counter(counts)
            for total, ways in counts.items():
                step[total + r] += ways
            counts = step
        observed, mean = round(2 * w_plus), sum(doubled) / 2
        tail = sum(ways for total, ways in counts.items() if abs(total - mean) >= abs(observed - mean) - 1e-9)
        return min(1.0, tail / 2 ** n)
    ties = collections.Counter(abs(d) for d in diffs)
    variance = n * (n + 1) * (2 * n + 1) / 24 - sum(t ** 3 - t for t in ties.values()) / 48
    z = (abs(w_plus - n * (n + 1) / 4) - 0.5) / math.sqrt(variance)
    return min(1.0, math.erfc(z / math.sqrt(2)))


def mcnemar(a: list[bool], b: list[bool]) -> float:
    """Two-sided p of the exact McNemar test for paired yes/no values."""
    only_a = sum(x and not y for x, y in zip(a, b))
    only_b = sum(y and not x for x, y in zip(a, b))
    n = only_a + only_b
    if n == 0:
        return 1.0
    k = min(only_a, only_b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def holm(pvalues: list[float]) -> list[float]:
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    adjusted, running = [0.0] * len(pvalues), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvalues) - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


# ------------------------------------------------------------------ data

def read(path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def automatic(tests: list[dict]) -> None:
    files = collections.defaultdict(dict)                   # run_id -> tool -> row
    for row in read(RESULTS / "acrobat" / "files.csv"):
        if row["ok"] == "True":
            files[row["run_id"]][row["tool"]] = row
    pag = {"rules": "pdfaccessguru-1.1.0 rules", "gemma": "pdfaccessguru-1.1.0 gemma"}
    for setting, label in PAG.items():
        for other, other_label in (("acrobat", "Acrobat Pro"), ("opendataloader-pdf", "opendataloader-pdf")):
            pairs = [(tools[pag[setting]], tools[other]) for tools in files.values() if pag[setting] in tools and other in tools]
            group = "4. Other tools: 156 untagged files"
            ours = [float(p["problems"]) for p, _ in pairs]
            theirs = [float(o["problems"]) for _, o in pairs]
            tests.append(test(group, f"{label} vs {other_label}", "problems left (median)", len(pairs),
                              statistics.median(ours), statistics.median(theirs), wilcoxon(ours, theirs)))
            passes = ([p["passes"] == "True" for p, _ in pairs], [o["passes"] == "True" for _, o in pairs])
            tests.append(test(group, f"{label} vs {other_label}", "files passing", len(pairs),
                              sum(passes[0]), sum(passes[1]), mcnemar(*passes)))
            shared = [(float(p["tagged_share"]), float(o["tagged_share"])) for p, o in pairs
                      if p["tagged_share"] and o["tagged_share"]]
            tests.append(test(group, f"{label} vs {other_label}", "text a screen reader reaches (median)", len(shared),
                              statistics.median(s for s, _ in shared), statistics.median(t for _, t in shared),
                              wilcoxon([s for s, _ in shared], [t for _, t in shared]), percent=True))

    for setting, label in PAG.items():
        before, after, odl = [], [], []
        for set_name in ("kumar", "safedocs", "reference"):
            ours = {r["run_id"]: r for r in read(RESULTS / "runs" / f"{set_name}__{setting}.csv") if r["ok"] == "True"}
            theirs = {r["run_id"]: r for r in read(RESULTS / "opendataloader" / f"{set_name}__odl.csv") if r["ok"] == "True"}
            before += [ours[k] for k in ours]
            after += [(ours[k], theirs[k]) for k in ours if k in theirs]
        group = "1. Before and after fixing: all 316 files"
        problems_before = [float(r["problems_before"]) for r in before]
        problems_after = [float(r["problems_after"]) for r in before]
        tests.append(test(group, f"{label}: after vs before", "problems (median)", len(before),
                          statistics.median(problems_after), statistics.median(problems_before),
                          wilcoxon(problems_after, problems_before)))
        tests.append(test(group, f"{label}: after vs before", "files passing", len(before),
                          sum(r["passes"] == "True" for r in before), sum(float(r["problems_before"]) == 0 for r in before),
                          mcnemar([r["passes"] == "True" for r in before], [float(r["problems_before"]) == 0 for r in before])))
        group = "4. Other tools: all files opendataloader-pdf processed"
        ours = [float(p["problems_after"]) for p, _ in after]
        theirs = [float(o["problems"]) for _, o in after]
        tests.append(test(group, f"{label} vs opendataloader-pdf", "problems left (median)", len(after),
                          statistics.median(ours), statistics.median(theirs), wilcoxon(ours, theirs)))
        passes = ([p["passes"] == "True" for p, _ in after], [o["passes"] == "True" for _, o in after])
        tests.append(test(group, f"{label} vs opendataloader-pdf", "files passing", len(after),
                          sum(passes[0]), sum(passes[1]), mcnemar(*passes)))


def judges(tests: list[dict]) -> None:
    folder = RESULTS / "expert-judgement"
    # Part 1: per picture, mean helpfulness of the two judges; "describes well" = both judges rated 4 or 5
    help_, good = collections.defaultdict(dict), collections.defaultdict(dict)
    by = collections.defaultdict(list)
    for row in read(folder / "pictures.csv"):
        by[(row["picture"], row["written_by"])].append(int(row["helpfulness"]))
    for (picture, writer), scores in by.items():
        help_[writer][picture] = sum(scores) / len(scores)
        good[writer][picture] = all(s >= 4 for s in scores)
    group = "7. Expert judgement: picture descriptions (40 pictures)"
    ours = "pdfaccessguru-with-ai"
    for other, label in (("pdfaccessguru-without-ai", "PDFAccessGuru without AI"), ("blip", "BLIP")):
        pictures = sorted(help_[ours])
        a, b = [help_[ours][p] for p in pictures], [help_[other][p] for p in pictures]
        tests.append(test(group, f"PDFAccessGuru with AI vs {label}", "helpfulness (mean, 1–5)", len(pictures),
                          statistics.mean(a), statistics.mean(b), wilcoxon(a, b), decimals=2))
        a, b = [good[ours][p] for p in pictures], [good[other][p] for p in pictures]
        tests.append(test(group, f"PDFAccessGuru with AI vs {label}", "describes the picture well (both judges)",
                          len(pictures), sum(a), sum(b), mcnemar(a, b)))

    # Part 2: per criterion, share correct (mean of the judges), as in the README table
    totals = collections.defaultdict(lambda: [0, 0])
    for row in read(folder / "structure.csv"):
        if row["none_on_pages"] != "yes":
            totals[(row["judge"], row["tool"], row["criterion"])][0] += int(row["correct"] or 0)
            totals[(row["judge"], row["tool"], row["criterion"])][1] += int(row["wrong_or_missing"] or 0)
    score = {}
    for (judge, tool, criterion), (ok, bad) in totals.items():
        if ok + bad:
            score.setdefault((tool, criterion), []).append(100 * ok / (ok + bad))
    criteria = sorted({c for _, c in score})
    group = "7. Expert judgement: structure (13 criteria, 4 documents)"
    for other, label in (("acrobat", "Acrobat Pro"), ("opendataloader-pdf", "opendataloader-pdf"), ("pave-2.0", "PAVE 2.0")):
        both = [c for c in criteria if ("pdfaccessguru", c) in score and (other, c) in score]
        a = [statistics.mean(score[("pdfaccessguru", c)]) for c in both]
        b = [statistics.mean(score[(other, c)]) for c in both]
        tests.append(test(group, f"PDFAccessGuru vs {label}", "per cent correct, per criterion (mean)", len(both),
                          statistics.mean(a), statistics.mean(b), wilcoxon(a, b), decimals=0))

    # Part 3: per link or document, mean of the two judges (yes = 2, partly = 1, no = 0); language: both judges "yes"
    links = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in read(folder / "links.csv"):
        links[row["tool"]][row["link"]].append(SCORE[row["tells_where_it_goes"]])
    titles = collections.defaultdict(lambda: collections.defaultdict(list))
    language = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in read(folder / "titles.csv"):
        titles[row["tool"]][row["document"]].append(SCORE[row["title_describes_document"]])
        language[row["tool"]][row["document"]].append(row["language_right"] == "yes")
    group = "7. Expert judgement: links, titles and language"
    for other, label in (("original", "original"), ("acrobat", "Acrobat Pro"), ("opendataloader-pdf", "opendataloader-pdf")):
        items = sorted(set(links["pdfaccessguru"]) & set(links[other]))
        a = [statistics.mean(links["pdfaccessguru"][i]) for i in items]
        b = [statistics.mean(links[other][i]) for i in items]
        tests.append(test(group, f"PDFAccessGuru vs {label}", "link says where it goes (0–2, mean)", len(items),
                          statistics.mean(a), statistics.mean(b), wilcoxon(a, b), decimals=2))
        items = sorted(set(titles["pdfaccessguru"]) & set(titles[other]))
        a = [statistics.mean(titles["pdfaccessguru"][i]) for i in items]
        b = [statistics.mean(titles[other][i]) for i in items]
        tests.append(test(group, f"PDFAccessGuru vs {label}", "title describes the document (0–2, mean)", len(items),
                          statistics.mean(a), statistics.mean(b), wilcoxon(a, b), decimals=2))
        a = [all(language["pdfaccessguru"][i]) for i in items]
        b = [all(language[other][i]) for i in items]
        tests.append(test(group, f"PDFAccessGuru vs {label}", "language right (both judges)", len(items),
                          sum(a), sum(b), mcnemar(a, b)))


def test(group, comparison, measure, n, ours, theirs, p, percent=False, decimals=None) -> dict:
    def show(value):
        if percent:
            return f"{value:.0%}"
        if decimals is not None:
            return f"{value:.{decimals}f}"
        return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"
    return {"group": group, "comparison": comparison, "measure": measure, "n": n, "pdfaccessguru": show(ours),
            "other": show(theirs), "p": p}


def fmt(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def main() -> int:
    tests: list[dict] = []
    automatic(tests)
    judges(tests)
    for row, adjusted in zip(tests, holm([t["p"] for t in tests])):
        row["p_holm"] = adjusted
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "tests.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(tests[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows({**t, "p": f"{t['p']:.3g}", "p_holm": f"{t['p_holm']:.3g}"} for t in tests)
    lines = ["# How sure are the differences?", "",
             "Paired tests on the same files and items: Wilcoxon signed-rank test for numbers, exact McNemar test for "
             "yes/no. For the judges, the mean of the two judges per item (yes/no: both judges). p is corrected for "
             f"all {len(tests)} tests together (Holm). Built by `evaluation/significance.py`.", ""]
    for group in sorted(dict.fromkeys(t["group"] for t in tests), key=lambda g: int(g.split(".")[0])):
        lines += [f"## {group}", "", "| Comparison | Measure | n | PDFAccessGuru | Other | p (Holm) |",
                  "|---|---|---|---|---|---|"]
        for t in (t for t in tests if t["group"] == group):
            lines.append(f"| {t['comparison']} | {t['measure']} | {t['n']} | {t['pdfaccessguru']} | {t['other']} "
                         f"| {fmt(t['p_holm'])} |")
        lines.append("")
    (OUT / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
