"""
Builds the public rating site for Netlify (free plan): the same 40 pictures and blind descriptions as the
claude.ai version, one shared link, the participant's name or initials on the start page, every answer saved
automatically by a small Netlify Function into Netlify Blobs (one record per participant). The key
(code -> setups) never goes into the site.

    python evaluation/build_rating_netlify.py OUTPUT_FOLDER

OUTPUT_FOLDER gets public/ (page + pictures), netlify/functions/ (save, load), netlify.toml, package.json.
The pictures are third-party figures: deploy the folder, never commit it.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from build_rating_site import items_v11
from paths import WORK

SAVE = r'''import { getStore } from "@netlify/blobs";

const STORE = "ratings-11";            // the final design (rules, BLIP, PDFAccessGuru 1.1); older answers stay apart
const CODES = new Set(__CODES__);
const PICTURES = new Set(__PICTURES__);
const TRUE = new Set(["yes", "mostly", "no", ""]);
const PROBLEMS = new Set(["omission", "invented", "wrong", "length", "looks", "abbreviation", "unclear"]);

function clean(answer) {
  const a = answer && typeof answer === "object" ? answer : {};
  return {
    t: TRUE.has(a.t) ? a.t : "",
    h: Number.isInteger(a.h) && a.h >= 0 && a.h <= 5 ? a.h : 0,
    p: Array.isArray(a.p) ? [...new Set(a.p.filter((x) => PROBLEMS.has(x)))] : [],
    c: typeof a.c === "string" ? a.c.slice(0, 500) : "",
    at: Number.isFinite(a.at) ? a.at : Date.now(),
  };
}

export default async (req) => {
  if (req.method !== "POST") return new Response("Use POST", { status: 405 });
  let body;
  try { body = await req.json(); } catch { return new Response("Not JSON", { status: 400 }); }
  const participant = String(body.participant || "");
  if (!/^[A-Z2-9]{16}$/.test(participant)) return new Response("Unknown participant code", { status: 400 });
  const store = getStore({ name: STORE, consistency: "strong" });
  const record = (await store.get(participant, { type: "json" })) ||
    { participant, created_at: Date.now(), name: "", answers: {}, seconds: {} };
  if (typeof body.name === "string" && body.name.trim()) record.name = body.name.trim().slice(0, 60);
  for (const [code, answer] of Object.entries(body.answers || {})) if (CODES.has(code)) record.answers[code] = clean(answer);
  for (const [picture, value] of Object.entries(body.seconds || {})) {
    if (PICTURES.has(picture) && Number.isFinite(value) && value >= 0) record.seconds[picture] = Math.min(Math.round(value), 1000000);
  }
  record.updated_at = Date.now();
  await store.setJSON(participant, record);
  return Response.json({ ok: true, rated: Object.values(record.answers).filter((a) => a.t && a.h).length });
};

export const config = { path: "/api/save" };
'''

LOAD = r'''import { getStore } from "@netlify/blobs";

const STORE = "ratings-11";

export default async (req) => {
  const participant = new URL(req.url).searchParams.get("p") || "";
  if (!/^[A-Z2-9]{16}$/.test(participant)) return new Response("Unknown participant code", { status: 400 });
  const record = await getStore({ name: STORE, consistency: "strong" }).get(participant, { type: "json" });
  if (!record) return new Response("Not found", { status: 404 });
  return Response.json({ name: record.name, answers: record.answers, seconds: record.seconds });
};

export const config = { path: "/api/load" };
'''

TOML = '''[build]
  publish = "public"
  functions = "netlify/functions"

[[headers]]
  for = "/*"
  [headers.values]
    X-Robots-Tag = "noindex, nofollow"
    Referrer-Policy = "no-referrer"
'''


def main(out: Path) -> int:
    data = items_v11()
    key = {d["code"]: d["setups"] for item in data for d in item["descriptions"]}
    (WORK / "rating" / "key-11.json").write_text(json.dumps(key, indent=1), encoding="utf-8")   # never in the site
    (out / "public" / "pictures").mkdir(parents=True, exist_ok=True)
    (out / "netlify" / "functions").mkdir(parents=True, exist_ok=True)
    page_items = []
    for item in data:
        shutil.copy2(item["png"], out / "public" / "pictures" / f"{item['id']}.png")
        page_items.append({"id": item["id"], "img": f"pictures/{item['id']}.png", "context": item["context"],
                           "descriptions": [{"code": d["code"], "text": d["text"]} for d in item["descriptions"]]})
    template = (Path(__file__).parent / "rating_netlify_template.html").read_text(encoding="utf-8")
    page = template.replace("/*DATA*/null", json.dumps(page_items, ensure_ascii=False).replace("�", "\\ufffd"))
    (out / "public" / "index.html").write_text(page, encoding="utf-8")
    (out / "public" / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    codes = [d["code"] for item in data for d in item["descriptions"]]
    pictures = [item["id"] for item in data]
    (out / "netlify" / "functions" / "save.mjs").write_text(
        SAVE.replace("__CODES__", json.dumps(codes)).replace("__PICTURES__", json.dumps(pictures)), encoding="utf-8")
    (out / "netlify" / "functions" / "load.mjs").write_text(LOAD, encoding="utf-8")
    (out / "netlify.toml").write_text(TOML, encoding="utf-8")
    (out / "package.json").write_text(json.dumps({"name": "picture-description-rating", "private": True, "type": "module",
                                                  "dependencies": {"@netlify/blobs": "8.1.0"}}, indent=1), encoding="utf-8")
    print(f"{len(data)} pictures, {len(codes)} descriptions -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))
