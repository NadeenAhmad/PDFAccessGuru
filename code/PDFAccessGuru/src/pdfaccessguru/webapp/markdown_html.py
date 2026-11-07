"""
Turns the Markdown of PDFAccessGuru's own reports into accessible HTML (Phase 7a): real
headings, lists, and tables whose header cells are marked as column headers, so screen readers
can move through them. Every text is escaped; only the few Markdown forms the reports use are
supported (headings, paragraphs, lists, tables, images, links).
"""

from __future__ import annotations

import html
import re

_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)\)$")


def _inline(text: str, image_url) -> str:
    escaped = html.escape(text, quote=False)
    return _LINK.sub(lambda m: f'<a href="{html.escape(image_url(m.group(2)))}">{m.group(1)}</a>', escaped)


def markdown_to_html(markdown: str, image_url=lambda path: path, heading_offset: int = 0) -> str:
    """HTML for the report body. image_url(path) turns a relative image path into a URL."""
    out: list[str] = []
    lines = markdown.splitlines()
    index = 0
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            out.append("<p>" + "<br>".join(_inline(line, image_url) for line in paragraph) + "</p>")
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            level = min(6, len(heading.group(1)) + heading_offset)
            out.append(f"<h{level}>{_inline(heading.group(2), image_url)}</h{level}>")
            index += 1
            continue
        image = _IMAGE.match(stripped)
        if image:
            flush_paragraph()
            out.append(f'<p><img src="{html.escape(image_url(image.group(2)))}" alt="{html.escape(image.group(1))}" '
                       f'style="max-width:100%;height:auto"></p>')
            index += 1
            continue
        if stripped.startswith("|"):
            flush_paragraph()
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(lines[index].strip())
                index += 1
            cells = [[cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", row)[1:-1]] for row in rows]
            header, body = cells[0], [row for row in cells[2:]]
            out.append("<table><thead><tr>" + "".join(f'<th scope="col">{_inline(c, image_url)}</th>' for c in header)
                       + "</tr></thead><tbody>")
            for row in body:
                out.append("<tr>" + "".join(
                    (f'<th scope="row">{_inline(c, image_url)}</th>' if i == 0 else f"<td>{_inline(c, image_url)}</td>")
                    for i, c in enumerate(row)) + "</tr>")
            out.append("</tbody></table>")
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            out.append("<ul>")
            while index < len(lines) and lines[index].strip().startswith("- "):
                item = _inline(lines[index].strip()[2:], image_url)
                index += 1
                sub = []
                while index < len(lines) and lines[index].startswith("  - "):
                    sub.append(f"<li>{_inline(lines[index].strip()[2:], image_url)}</li>")
                    index += 1
                out.append(f"<li>{item}" + (f"<ul>{''.join(sub)}</ul>" if sub else "") + "</li>")
                while index < len(lines) and not lines[index].strip() and index + 1 < len(lines) \
                        and lines[index + 1].strip().startswith("- "):
                    index += 1                                   # blank lines between items
            out.append("</ul>")
            continue
        paragraph.append(stripped)
        index += 1
    flush_paragraph()
    return "\n".join(out)
