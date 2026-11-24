"""
Parts 2 and 3 of the rating site: same Netlify site and participant code as Part 1 (the picture rating).

Part 2, structure (the PAVE-style check): the 4 documents of results/pave/selection.csv in every tool's version,
  judged on PAVE 2.0's 13 criteria (build_pave_sheet.CRITERIA). Pages and screen-reader views come from
  build_pave_sheet (cache in evaluation/work/pave/cache).
Part 3, links, titles and language:
  - 30 links from files of the Acrobat batch (15 external, 15 internal, at most 2 per file, fixed seed),
    plus every link of the 4 PAVE documents. For each: what a screen reader gets in the original, Acrobat,
    opendataloader-pdf and PDFAccessGuru 1.1 (and PAVE 2.0 on the PAVE documents);
  - title and language of each of these documents, in the same versions;
  - 20 of the passages PDFAccessGuru 1.1 marked as another language (fixed seed, at most 2 per file).
The items of the site the judges rated are published with their ratings.
Versions are blind: letters in a random order per item. The keys go to evaluation/work/rating/
(key-structure.json, key-links.json), never into the site.

    RENDER_PYTHON=evaluation/work/venv/bin/python \
      evaluation/work/venv/bin/python evaluation/build_parts_23.py OUTPUT_FOLDER

Run it with a Python that has PDFAccessGuru (pikepdf, PyMuPDF, pdfplumber). OUTPUT_FOLDER is the Netlify folder of
Part 1; structure.html, links.html, their pictures and their save/load functions are added; Part 1 is not touched.
The pictures show third-party pages: deploy the folder, never commit it, and take the site down after the rating.
"""

from __future__ import annotations

import base64
import csv
import json
import random
import sys
from pathlib import Path

import pikepdf
import pymupdf

import build_pave_sheet
from paths import ODL_RUNS, RESULTS, RUNS, WORK

SEED = 20261113
RUNS_110 = RUNS
ACROBAT, PAVE = WORK / "acrobat", WORK / "pave"
LANGUAGES = {"en": "English", "de": "German", "fr": "French", "es": "Spanish", "it": "Italian", "nl": "Dutch",
             "pt": "Portuguese", "no": "Norwegian", "nb": "Norwegian", "da": "Danish", "sv": "Swedish", "fi": "Finnish",
             "pl": "Polish", "cs": "Czech", "ru": "Russian", "tr": "Turkish", "el": "Greek", "la": "Latin",
             "ja": "Japanese", "zh": "Chinese", "ko": "Korean", "ar": "Arabic", "ca": "Catalan", "ro": "Romanian",
             "hu": "Hungarian", "id": "Indonesian", "ms": "Malay", "af": "Afrikaans", "et": "Estonian", "sk": "Slovak",
             "sl": "Slovenian", "hr": "Croatian", "lt": "Lithuanian", "lv": "Latvian", "eo": "Esperanto", "cy": "Welsh"}


def clean_text(text: str) -> str:
    """Text as a reader sees it: no private-use symbols (font-specific glyphs) or control characters."""
    return " ".join("".join(ch for ch in str(text or "") if not ("\ue000" <= ch <= "\uf8ff") and (ch.isprintable() or ch == " ")).split())


def language_name(code: str) -> str:
    code = (code or "").strip()
    return f"{LANGUAGES.get(code.lower()[:2], code)} ({code})" if code else "none"


# ---------------------------------------------------------------- versions of a file

def versions(run_id: str) -> dict[str, Path]:
    """original + every tool's output of one test file (only those that exist)."""
    found: dict[str, Path] = {}
    if run_id.startswith("pave-"):
        found["original"] = PAVE / "input" / f"{run_id}.pdf"
        for tool, folder in (("acrobat", "acrobat"), ("odl", "odl"), ("pdfaccessguru-1.1.0", "pdfaccessguru-1.1.0"),
                             ("pave", "pave")):
            found[tool] = PAVE / "outputs" / folder / f"{run_id}.pdf"
    else:
        test_set = run_id.split("-")[0]
        found["original"] = ACROBAT / "input" / f"{run_id}.pdf"
        found["acrobat"] = ACROBAT / "output" / f"{run_id}AdobeFix.pdf"
        odl = sorted((ODL_RUNS / test_set / "odl" / run_id).glob("*.pdf"))
        if odl:
            found["odl"] = odl[0]
        found["pdfaccessguru-1.1.0"] = RUNS_110 / test_set / "gemma" / run_id / "fixed.pdf"
    return {tool: path for tool, path in found.items() if path.exists()}


# ---------------------------------------------------------------- reading a PDF

def _role(element, roles) -> str:
    tag = element.get("/S")
    seen = 0
    while roles is not None and tag is not None and tag in roles and seen < 10:
        tag, seen = roles[tag], seen + 1
    return str(tag or "").lstrip("/")


def link_facts(path: Path) -> dict:
    """Per page: the link annotations with their rectangle (PDF units), and how a screen reader can reach them."""
    facts = {"pages": {}, "title": "", "display_title": False, "lang": ""}
    with pikepdf.open(path) as pdf:
        root = pdf.Root
        facts["lang"] = str(root.get("/Lang", "") or "")
        try:
            facts["title"] = str(pdf.open_metadata().get("dc:title") or "")
        except Exception:
            facts["title"] = ""
        if not facts["title"].strip():
            facts["title"] = str(pdf.docinfo.get("/Title", "") or "")
        prefs = root.get("/ViewerPreferences")
        facts["display_title"] = bool(prefs is not None and prefs.get("/DisplayDocTitle") is True)
        owners: dict = {}
        tree = root.get("/StructTreeRoot")
        if tree is not None:
            roles = tree.get("/RoleMap")
            stack, seen = [(tree, "")], set()
            while stack:
                node, role = stack.pop()
                if isinstance(node, pikepdf.Array):
                    stack.extend((child, role) for child in node)
                    continue
                if not isinstance(node, pikepdf.Dictionary):
                    continue
                if node.is_indirect:
                    if node.objgen in seen:
                        continue
                    seen.add(node.objgen)
                if node.get("/Type") == "/OBJR":
                    target = node.get("/Obj")
                    if target is not None and target.is_indirect:
                        owners[target.objgen] = role
                    continue
                if node.get("/S") is not None:
                    role = _role(node, roles)
                    if role == "Link" and node.get("/Alt") is not None:
                        role = "Link|" + str(node.get("/Alt"))
                kids = node.get("/K")
                if kids is not None:
                    stack.append((kids, role))
        for number, page in enumerate(pdf.pages):
            items = []
            for annotation in page.obj.get("/Annots") or []:
                if not isinstance(annotation, pikepdf.Dictionary) or annotation.get("/Subtype") != "/Link":
                    continue
                try:
                    rect = [float(v) for v in annotation.get("/Rect")]
                except Exception:
                    continue
                owner = owners.get(annotation.objgen, "") if annotation.is_indirect else ""
                alt = owner.split("|", 1)[1] if owner.startswith("Link|") else ""
                items.append({"rect": [min(rect[0], rect[2]), min(rect[1], rect[3]), max(rect[0], rect[2]), max(rect[1], rect[3])],
                              "tagged": owner.split("|", 1)[0] == "Link", "contents": str(annotation.get("/Contents", "") or ""),
                              "alt": alt})
            facts["pages"][number] = items
    return facts


def _overlap(a, b) -> float:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    area = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / area if area > 0 else 0.0


def announced(facts: dict, page: int, rect) -> dict:
    """What a screen reader gets for the link at this place in one version."""
    best, score = None, 0.3
    for item in facts["pages"].get(page, []):
        value = _overlap(item["rect"], rect)
        if value > score:
            best, score = item, value
    if best is None:
        return {"found": False, "tagged": False, "description": ""}
    return {"found": True, "tagged": best["tagged"], "description": clean_text(best["alt"] or best["contents"])}


def png(pixmap) -> str:
    return base64.b64encode(pixmap.tobytes("png")).decode("ascii")


# ---------------------------------------------------------------- Part 2

def part2(public: Path) -> tuple[list, dict]:
    build_pave_sheet.main()                                   # refreshes the cache and pave/key.json
    key = json.loads((PAVE / "key.json").read_text(encoding="utf-8"))
    documents = list(csv.DictReader((RESULTS / "pave" / "selection.csv").open(encoding="utf-8")))
    folder = public / "p2"
    folder.mkdir(parents=True, exist_ok=True)
    data = []
    for number, document in enumerate(documents, start=1):
        pages = []
        with pymupdf.open(PAVE / "input" / f"{document['doc']}.pdf") as doc:
            for index, page in enumerate(doc, start=1):
                name = f"doc{number}-page{index}.png"
                (folder / name).write_bytes(page.get_pixmap(dpi=110).tobytes("png"))
                pages.append(f"p2/{name}")
        entries = []
        for code in sorted(c for c, v in key.items() if v["doc"] == document["doc"]):
            cached = json.loads((PAVE / "cache" / f"{key[code]['tool']}__{document['doc']}.json").read_text(encoding="utf-8"))
            entries.append({"code": code, "letter": code[-1], "preview": cached["preview"], "summary": cached["summary"]})
        data.append({"number": number, "pages": pages, "versions": entries})
    criteria = [{"key": k, "name": n, "explain": e, "kind": kind} for k, n, e, kind in build_pave_sheet.CRITERIA]
    types = {}
    for document in data:
        for version in document["versions"]:
            for criterion in criteria:
                types[f"{version['code']}-{criterion['key']}"] = criterion["kind"]
            types[f"{version['code']}-comment"] = "comment"
    (WORK / "rating" / "key-structure.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    return [{"documents": data, "criteria": criteria}], types


# ---------------------------------------------------------------- Part 3

def _acrobat_batch() -> list[str]:
    return sorted(p.stem for p in (ACROBAT / "input").glob("*.pdf") if not p.stem.startswith("pave"))


def _candidate_links(run_id: str, path: Path) -> list[dict]:
    found = []
    with pymupdf.open(path) as doc:
        for number, page in enumerate(doc):
            for link in page.get_links():
                raw = doc.xref_get_key(link["xref"], "Rect") if link.get("xref") else ("null", "")
                try:
                    pdf_rect = [float(v) for v in raw[1].strip("[] ").split()]            # PDF units, as in the file
                except ValueError:
                    continue
                if len(pdf_rect) != 4:
                    continue
                pdf_rect = [min(pdf_rect[0], pdf_rect[2]), min(pdf_rect[1], pdf_rect[3]),
                            max(pdf_rect[0], pdf_rect[2]), max(pdf_rect[1], pdf_rect[3])]
                if pdf_rect[2] - pdf_rect[0] < 2 or pdf_rect[3] - pdf_rect[1] < 2:
                    continue
                if link["kind"] == pymupdf.LINK_URI and str(link.get("uri", "")).strip():
                    found.append({"run_id": run_id, "page": number, "rect": pdf_rect, "kind": "external",
                                  "uri": str(link["uri"]).strip()})
                elif link["kind"] in (pymupdf.LINK_GOTO, pymupdf.LINK_NAMED) and link.get("page") is not None \
                        and 0 <= int(link.get("page", -1)) < len(doc):
                    to = link.get("to")
                    found.append({"run_id": run_id, "page": number, "rect": pdf_rect, "kind": "internal",
                                  "target_page": int(link["page"]), "target_y": float(to.y) if to is not None else 0.0})
    return found


def _on_page(page, pdf_rect):
    """A rectangle in PDF units as a PyMuPDF page rectangle (handles crop boxes and rotation)."""
    return (pymupdf.Rect(pdf_rect) * page.transformation_matrix).normalize()


def _crop(path: Path, page_number: int, pdf_rect, outline: bool) -> str:
    with pymupdf.open(path) as doc:
        page = doc[page_number]
        rect = _on_page(page, pdf_rect)
        if outline:
            page.draw_rect(rect + (-2, -2, 2, 2), color=(0.8, 0.05, 0.05), width=2)
        clip = pymupdf.Rect(rect.x0 - 160, rect.y0 - 70, rect.x1 + 160, rect.y1 + 70) & page.rect
        return png(page.get_pixmap(clip=clip, dpi=130))


def _target_crop(path: Path, page_number: int, y: float) -> str:
    with pymupdf.open(path) as doc:
        page = doc[page_number]
        top = max(0.0, min(y, page.rect.height - 40) - 20)
        clip = pymupdf.Rect(0, top, page.rect.width, min(page.rect.height, top + 200))
        return png(page.get_pixmap(clip=clip, dpi=110))


def _visible_text(path: Path, page_number: int, pdf_rect) -> str:
    with pymupdf.open(path) as doc:
        page = doc[page_number]
        rect = _on_page(page, pdf_rect)
        return clean_text(page.get_textbox(rect + (-1, -1, 1, 1)))


def _passages(rng: random.Random, batch: set[str]) -> list[dict]:
    """Passages PDFAccessGuru 1.1 marked with another language than the document, with their text."""
    import pdfplumber

    pool = []
    for test_set in ("kumar", "safedocs"):
        for fixed in sorted((RUNS_110 / test_set / "gemma").glob("*/fixed.pdf")):
            run_id = fixed.parent.name
            try:
                with pikepdf.open(fixed) as pdf:
                    doc_lang = str(pdf.Root.get("/Lang", "") or "")
                    page_of = {page.obj.objgen: i for i, page in enumerate(pdf.pages)}
                    tree = pdf.Root.get("/StructTreeRoot")
                    if tree is None:
                        continue
                    marked = []
                    stack, seen = [(tree.get("/K"), None)], set()
                    while stack:
                        node, page = stack.pop()
                        if isinstance(node, pikepdf.Array):
                            stack.extend((child, page) for child in node)
                            continue
                        if not isinstance(node, pikepdf.Dictionary) or node.get("/S") is None:
                            continue
                        if node.is_indirect:
                            if node.objgen in seen:
                                continue
                            seen.add(node.objgen)
                        pg = node.get("/Pg")
                        page = page_of.get(pg.objgen, page) if pg is not None else page
                        lang = node.get("/Lang")
                        if lang is not None and str(lang).lower()[:2] != doc_lang.lower()[:2]:
                            mcids = []
                            inner = [(node.get("/K"), page)]
                            while inner:
                                k, p = inner.pop()
                                if isinstance(k, pikepdf.Array):
                                    inner.extend((x, p) for x in k)
                                elif isinstance(k, int) and not isinstance(k, bool):
                                    mcids.append((p, int(k)))
                                elif isinstance(k, pikepdf.Dictionary):
                                    kp = k.get("/Pg")
                                    kp = page_of.get(kp.objgen, p) if kp is not None else p
                                    if k.get("/MCID") is not None:
                                        mcids.append((kp, int(k.get("/MCID"))))
                                    elif k.get("/S") is not None:
                                        inner.append((k.get("/K"), kp))
                            marked.append({"lang": str(lang), "mcids": mcids})
                            continue
                        stack.append((node.get("/K"), page))
                if not marked:
                    continue
                with pdfplumber.open(fixed) as plumb:
                    texts = {}
                    for item in marked:
                        parts = []
                        for page, mcid in item["mcids"]:
                            if page is None or page >= len(plumb.pages):
                                continue
                            if page not in texts:
                                chars = {}
                                for ch in plumb.pages[page].chars:
                                    if ch.get("mcid") is not None:
                                        chars.setdefault(ch["mcid"], []).append(ch["text"])
                                texts[page] = {k: "".join(v) for k, v in chars.items()}
                            parts.append(texts[page].get(mcid, ""))
                        text = clean_text(" ".join(parts))
                        if len(text) >= 3:
                            pool.append({"run_id": run_id, "doc_lang": doc_lang, "lang": item["lang"], "text": text[:600]})
            except Exception as error:                    # one unreadable file must not stop the build
                print("  passages: skipped", run_id, type(error).__name__)
    rng.shuffle(pool)
    chosen, per_file = [], {}
    for item in pool:
        if per_file.get(item["run_id"], 0) >= 2:
            continue
        per_file[item["run_id"]] = per_file.get(item["run_id"], 0) + 1
        chosen.append(item)
        if len(chosen) == 20:
            break
    print(f"  passages marked as another language: {len(pool)}; sampled {len(chosen)}")
    return chosen


def part3(public: Path) -> tuple[list, dict]:
    rng = random.Random(SEED)
    batch = _acrobat_batch()
    pool = []
    for run_id in batch:
        pool += _candidate_links(run_id, ACROBAT / "input" / f"{run_id}.pdf")
    rng.shuffle(pool)
    chosen, per_file, per_kind = [], {}, {"external": 0, "internal": 0}
    for link in pool:
        if per_kind[link["kind"]] >= 15 or per_file.get(link["run_id"], 0) >= 2:
            continue
        if any(link["run_id"] == c["run_id"] and link["page"] == c["page"] and _overlap(link["rect"], c["rect"]) > 0.3 for c in chosen):
            continue
        per_file[link["run_id"]] = per_file.get(link["run_id"], 0) + 1
        per_kind[link["kind"]] += 1
        chosen.append(link)
    for number in range(1, 5):                                 # every link of the PAVE documents
        chosen += _candidate_links(f"pave-{number}", PAVE / "input" / f"pave-{number}.pdf")
    print(f"  links: {per_kind['external']} external + {per_kind['internal']} internal sampled, "
          f"{len(chosen) - sum(per_kind.values())} from the PAVE documents")

    key, types, facts_cache = {}, {}, {}

    def facts(path: Path) -> dict:
        if path not in facts_cache:
            facts_cache[path] = link_facts(path)
        return facts_cache[path]

    links = []
    for number, link in enumerate(chosen, start=1):
        code = f"L{number:02d}"
        found = versions(link["run_id"])
        original = found["original"]
        item = {"code": code, "picture": _crop(original, link["page"], link["rect"], True),
                "text": _visible_text(original, link["page"], link["rect"]), "kind": link["kind"]}
        if link["kind"] == "external":
            item["target"] = link["uri"]
        else:
            item["target_page"] = link["target_page"] + 1
            item["target_picture"] = _target_crop(original, link["target_page"], link["target_y"])
        tools = list(found)
        rng.shuffle(tools)
        item["versions"] = []
        for letter, tool in zip("ABCDEF", tools):
            got = announced(facts(found[tool]), link["page"], link["rect"])
            item["versions"].append({"letter": letter, **got})
            key[f"{code}-{letter}"] = {"run_id": link["run_id"], "tool": tool, "kind": link["kind"]}
            types[f"{code}-{letter}"] = "link"
        types[f"{code}-c"] = "comment"
        links.append(item)

    titles = []
    for number, run_id in enumerate(dict.fromkeys(link["run_id"] for link in chosen), start=1):
        code = f"T{number:02d}"
        found = versions(run_id)
        with pymupdf.open(found["original"]) as doc:
            first = png(doc[0].get_pixmap(dpi=60))
        tools = list(found)
        rng.shuffle(tools)
        item = {"code": code, "picture": first, "versions": []}
        for letter, tool in zip("ABCDEF", tools):
            f = facts(found[tool])
            item["versions"].append({"letter": letter, "title": clean_text(f["title"]), "display_title": f["display_title"],
                                     "lang": language_name(f["lang"])})
            key[f"{code}-{letter}"] = {"run_id": run_id, "tool": tool}
            types[f"{code}-{letter}"] = "title"
        types[f"{code}-c"] = "comment"
        titles.append(item)

    passages = []
    for number, passage in enumerate(_passages(rng, set(batch)), start=1):
        code = f"P{number:02d}"
        passages.append({"code": code, "text": passage["text"], "lang": language_name(passage["lang"]),
                         "doc_lang": language_name(passage["doc_lang"])})
        key[code] = {"run_id": passage["run_id"], "lang": passage["lang"], "doc_lang": passage["doc_lang"]}
        types[code] = "passage"
        types[f"{code}-c"] = "comment"

    (WORK / "rating" / "key-links.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    return [{"links": links, "titles": titles, "passages": passages}], types


# ---------------------------------------------------------------- site

SAVE = r'''import { getStore } from "@netlify/blobs";

const STORE = "__STORE__";
const TYPES = __TYPES__;
const ONE_OF = { link: ["yes", "partly", "no", ""], passage: ["yes", "no", "unsure", ""] };

function clean(type, a) {
  if (type === "comment") return typeof a === "string" ? a.slice(0, 500) : "";
  if (type in ONE_OF) return ONE_OF[type].includes(a) ? a : "";
  const v = a && typeof a === "object" ? a : {};
  const n = (x) => (Number.isInteger(x) && x >= 0 && x <= 999 ? x : null);
  if (type === "count") return { c: n(v.c), w: n(v.w), none: v.none === true };
  if (type === "pages") return { pages: Array.isArray(v.pages) ? v.pages.slice(0, 10).map((x) => (x === true || x === false ? x : null)) : [] };
  if (type === "title") return { t: ["yes", "partly", "no", ""].includes(v.t) ? v.t : "", l: ["yes", "no", ""].includes(v.l) ? v.l : "" };
  return null;
}

export default async (req) => {
  if (req.method !== "POST") return new Response("Use POST", { status: 405 });
  let body;
  try { body = await req.json(); } catch { return new Response("Not JSON", { status: 400 }); }
  const participant = String(body.participant || "");
  if (!/^[A-Z2-9]{16}$/.test(participant)) return new Response("Unknown participant code", { status: 400 });
  const store = getStore({ name: STORE, consistency: "strong" });
  const record = (await store.get(participant, { type: "json" })) || { participant, created_at: Date.now(), name: "", answers: {} };
  if (typeof body.name === "string" && body.name.trim()) record.name = body.name.trim().slice(0, 60);
  for (const [code, answer] of Object.entries(body.answers || {})) {
    if (Object.prototype.hasOwnProperty.call(TYPES, code)) record.answers[code] = clean(TYPES[code], answer);
  }
  record.updated_at = Date.now();
  await store.setJSON(participant, record);
  return Response.json({ ok: true });
};

export const config = { path: "/api/save-__NAME__" };
'''

LOAD = r'''import { getStore } from "@netlify/blobs";

export default async (req) => {
  const participant = new URL(req.url).searchParams.get("p") || "";
  if (!/^[A-Z2-9]{16}$/.test(participant)) return new Response("Unknown participant code", { status: 400 });
  const record = await getStore({ name: "__STORE__", consistency: "strong" }).get(participant, { type: "json" });
  if (!record) return new Response("Not found", { status: 404 });
  return Response.json({ name: record.name, answers: record.answers });
};

export const config = { path: "/api/load-__NAME__" };
'''


def write_part(out: Path, name: str, store: str, template: str, data: list, types: dict) -> None:
    page = (Path(__file__).parent / template).read_text(encoding="utf-8")
    common = (Path(__file__).parent / "rating_parts_common.html").read_text(encoding="utf-8")
    css = common.split("<!--CSS-->")[1].split("<!--/CSS-->")[0]
    js = common.split("<!--JS-->")[1].split("<!--/JS-->")[0]
    page = page.replace("/*COMMON-CSS*/", css).replace("/*COMMON-JS*/", js)
    page = page.replace("/*DATA*/null", json.dumps(data[0], ensure_ascii=False).replace("</", "<\\/"))
    (out / "public" / f"{name}.html").write_text(page, encoding="utf-8")
    functions = out / "netlify" / "functions"
    functions.mkdir(parents=True, exist_ok=True)
    (functions / f"save-{name}.mjs").write_text(
        SAVE.replace("__STORE__", store).replace("__NAME__", name).replace("__TYPES__", json.dumps(types)), encoding="utf-8")
    (functions / f"load-{name}.mjs").write_text(LOAD.replace("__STORE__", store).replace("__NAME__", name), encoding="utf-8")


def main(out: Path) -> int:
    public = out / "public"
    if not (public / "index.html").exists():
        print("OUTPUT_FOLDER must be the Netlify folder of Part 1 (public/index.html missing)")
        return 1
    print("Part 2 (structure) ...")
    data2, types2 = part2(public)
    write_part(out, "structure", "structure-11", "rating_structure_template.html", data2, types2)
    print(f"  {sum(len(d['versions']) for d in data2[0]['documents'])} versions of {len(data2[0]['documents'])} documents")
    print("Part 3 (links, titles, language) ...")
    data3, types3 = part3(public)
    write_part(out, "links", "links-11", "rating_links_template.html", data3, types3)
    print(f"  {len(data3[0]['links'])} links, {len(data3[0]['titles'])} documents (titles), {len(data3[0]['passages'])} passages")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))
