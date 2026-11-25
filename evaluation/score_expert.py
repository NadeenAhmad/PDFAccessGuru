"""
Scores of the expert judgement: two judges (A, B) rated on the rating site (build_rating_netlify.py,
build_parts_23.py), each on their own and without knowing which tool made which version.

  - Part 1, picture descriptions: the 40 pictures of results/pictures/selection.csv, each described by PDFAccessGuru
    with AI, by PDFAccessGuru without AI (its simple rules) and by BLIP. "Describes the picture well" = rated 4 or 5
    for "How helpful is it for someone who cannot see the picture?" (1-5).
  - Part 2, structure: the 4 documents of results/pave/selection.csv in every tool's version, judged on PAVE 2.0's 13
    criteria (build_pave_sheet.CRITERIA). Per tool and criterion: correct / (correct + wrong or missing), summed over
    the documents; "pages" criteria count correct pages. As in PAVE 2.0's Table 1, the average is over the criteria
    that occur.
  - Part 3, links, titles and language: what a screen reader gets for each link, the title and language of each
    document, and passages PDFAccessGuru marked as another language.

    python evaluation/score_expert.py

Reads the judges' answers in results/expert-judgement/*.csv (anonymized; the tool of every version is given).
Writes results/expert-judgement/summary.md.
"""

from __future__ import annotations

import collections
import csv

from paths import RESULTS

FOLDER = RESULTS / "expert-judgement"
JUDGES = ["A", "B"]
WRITERS = {"pdfaccessguru-without-ai": "PDFAccessGuru without AI (simple rules)", "blip": "BLIP",
           "pdfaccessguru-with-ai": "PDFAccessGuru with AI"}
TOOLS = {"original": "Original", "acrobat": "Acrobat Pro", "opendataloader-pdf": "opendataloader-pdf",
         "pave-2.0": "PAVE 2.0", "pdfaccessguru": "PDFAccessGuru"}
CRITERIA = {"content": "All content tagged", "order": "Reading order", "headings": "Headings",
            "heading_levels": "Heading levels", "tables": "Tables", "table_structure": "Table structure",
            "lists": "Lists", "list_structure": "List structure", "figures": "Figures",
            "figure_alt": "Figure descriptions", "formulas": "Formulas", "formula_alt": "Formula descriptions",
            "captions": "Captions"}


def read(name: str) -> list[dict]:
    with (FOLDER / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def pct(part: int, whole: int) -> str:
    return "–" if not whole else f"{100 * part / whole:.0f}%"


def mean(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def kappa(pairs: list[tuple], quadratic: bool = False) -> float:
    """Cohen's kappa of two judges; quadratic weights for ordered scores."""
    categories = sorted({value for pair in pairs for value in pair})
    index = {value: i for i, value in enumerate(categories)}
    size = len(categories)
    weight = [[((i - j) / (size - 1)) ** 2 if quadratic else float(i != j) for j in range(size)] for i in range(size)]
    observed = sum(weight[index[a]][index[b]] for a, b in pairs) / len(pairs)
    first, second = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    expected = sum(weight[index[a]][index[b]] * first[a] * second[b] for a in categories for b in categories) / len(pairs) ** 2
    return 1 - observed / expected


def same(pairs: list[tuple]) -> str:
    return pct(sum(a == b for a, b in pairs), len(pairs))


def paired(rows: list[dict], item: tuple, value: str) -> list[tuple]:
    by_judge = {judge: {tuple(row[f] for f in item): row[value] for row in rows if row["judge"] == judge} for judge in JUDGES}
    return [(by_judge["A"][key], by_judge["B"][key]) for key in by_judge["A"] if key in by_judge["B"]]


def part1() -> list[str]:
    rows = read("pictures.csv")
    lines = ["## Part 1: picture descriptions (40 pictures)", "",
             "*Describes the picture well*: rated 4 or 5 for \"How helpful is it for someone who cannot see the "
             "picture?\" (1 = not at all, 5 = very).", "",
             "| Written by | Describes the picture well: judge A | judge B | both judges | Helpfulness, mean (1–5): "
             "judge A | judge B | both |", "|---|---|---|---|---|---|---|"]
    for writer, label in WRITERS.items():
        mine = [row for row in rows if writer in row["written_by"].split("+")]
        score = {judge: {row["picture"]: int(row["helpfulness"]) for row in mine if row["judge"] == judge} for judge in JUDGES}
        pictures = sorted(score["A"])
        good = {judge: sum(score[judge][p] >= 4 for p in pictures) for judge in JUDGES}
        both = sum(score["A"][p] >= 4 and score["B"][p] >= 4 for p in pictures)
        means = [mean(list(score[judge].values())) for judge in JUDGES]
        lines.append(f"| {label} | {pct(good['A'], len(pictures))} | {pct(good['B'], len(pictures))} "
                     f"| **{pct(both, len(pictures))}** | {means[0]:.2f} | {means[1]:.2f} | **{mean(means):.2f}** |")
    scores = [(int(a), int(b)) for a, b in paired(rows, ("picture", "description"), "helpfulness")]
    well = [(a >= 4, b >= 4) for a, b in scores]
    lines += ["", f"Agreement of the judges ({len(scores)} descriptions): *describes the picture well* same answer "
              f"{same(well)}, kappa {kappa(well):.2f}; helpfulness within one point "
              f"{pct(sum(abs(a - b) <= 1 for a, b in scores), len(scores))}, weighted kappa {kappa(scores, True):.2f}.",
              ""]
    return lines


def part2() -> list[str]:
    rows = read("structure.csv")
    tools = [t for t in TOOLS if any(row["tool"] == t for row in rows)]
    totals = collections.defaultdict(lambda: [0, 0])
    for row in rows:
        if row["none_on_pages"] != "yes":
            totals[(row["judge"], row["tool"], row["criterion"])][0] += int(row["correct"] or 0)
            totals[(row["judge"], row["tool"], row["criterion"])][1] += int(row["wrong_or_missing"] or 0)

    def score(judge, tool, criterion):
        correct, wrong = totals.get((judge, tool, criterion), (0, 0))
        return None if correct + wrong == 0 else 100 * correct / (correct + wrong)

    lines = ["## Part 2: structure of the 4 PAVE documents (PAVE 2.0's 13 criteria)", "",
             "Per cent correct: correct / (correct + wrong or missing), summed over the 4 documents; the first two "
             "criteria count correct pages. Mean of the two judges; – = no such content in the documents.", "",
             "| Criterion | " + " | ".join(TOOLS[t] for t in tools) + " |", "|---|" + "---|" * len(tools)]
    averages = {(judge, tool): [] for judge in JUDGES + ["both"] for tool in tools}
    for criterion, name in CRITERIA.items():
        cells = []
        for tool in tools:
            per_judge = [score(judge, tool, criterion) for judge in JUDGES]
            for judge, value in zip(JUDGES, per_judge):
                if value is not None:
                    averages[(judge, tool)].append(value)
            both = mean(per_judge)
            if both is not None:
                averages[("both", tool)].append(both)
            cells.append("–" if both is None else f"{both:.0f}")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    for judge in JUDGES:
        lines.append(f"| Average, judge {judge} | " + " | ".join(f"{mean(averages[(judge, t)]):.0f}" for t in tools) + " |")
    lines.append("| **Average, both judges** | " + " | ".join(f"**{mean(averages[('both', t)]):.0f}**" for t in tools) + " |")
    none = paired(rows, ("document", "tool", "criterion"), "none_on_pages")
    lines += ["", f"Agreement of the judges: on whether a kind of content occurs at all, same answer "
              f"{same([p for p in none if '' not in p])}.", ""]
    return lines


def part3() -> list[str]:
    links, titles, passages = read("links.csv"), read("titles.csv"), read("passages.csv")
    lines = ["## Part 3: links, titles and language", "",
             "| Version | Links | Link says where it goes: yes / partly / no (both judges) | judge A | judge B "
             "| Documents | Title describes the document (both) | Language right (both) |",
             "|---|---|---|---|---|---|---|---|"]
    for tool in [t for t in TOOLS if any(row["tool"] == t for row in links)]:
        mine = [row["tells_where_it_goes"] for row in links if row["tool"] == tool]
        per = {judge: [row["tells_where_it_goes"] for row in links if row["tool"] == tool and row["judge"] == judge]
               for judge in JUDGES}
        mine_t = [row for row in titles if row["tool"] == tool]

        def split(values):
            return " / ".join(pct(values.count(answer), len(values)) for answer in ("yes", "partly", "no"))

        lines.append(f"| {TOOLS[tool]} | {len(per['A'])} | {split(mine)} | {split(per['A'])} | {split(per['B'])} "
                     f"| {len(mine_t) // len(JUDGES)} "
                     f"| {pct(sum(row['title_describes_document'] == 'yes' for row in mine_t), len(mine_t))} "
                     f"| {pct(sum(row['language_right'] == 'yes' for row in mine_t), len(mine_t))} |")
    counts = {judge: collections.Counter(row["written_in_marked_language"] for row in passages if row["judge"] == judge)
              for judge in JUDGES}
    total = len(passages) // len(JUDGES)
    link_pairs = paired(links, ("link", "tool"), "tells_where_it_goes")
    title_pairs = paired(titles, ("document", "tool"), "title_describes_document")
    lines += ["", "PAVE 2.0 was run only on the 4 PAVE documents, so it has few links and one title here.", "",
              f"**Passages marked as another language by PDFAccessGuru** ({total}): is the passage written in the "
              "marked language? " + "; ".join(f"judge {j}: yes {counts[j]['yes']}, no {counts[j]['no']}, "
                                               f"can't tell {counts[j]['unsure']}" for j in JUDGES) + ".", "",
              f"Agreement of the judges: links same answer {same(link_pairs)} (kappa {kappa(link_pairs):.2f}, "
              f"{len(link_pairs)} link versions); titles same answer {same(title_pairs)} (kappa "
              f"{kappa(title_pairs):.2f}, {len(title_pairs)} document versions).", ""]
    return lines


def main() -> int:
    lines = ["# Expert judgement", "",
             "Two judges (A, B) rated every item on their own, without knowing which tool made which version. Built by "
             "`evaluation/score_expert.py` from the answers in this folder.", ""]
    lines += part1() + part2() + part3()
    target = FOLDER / "summary.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(target.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
