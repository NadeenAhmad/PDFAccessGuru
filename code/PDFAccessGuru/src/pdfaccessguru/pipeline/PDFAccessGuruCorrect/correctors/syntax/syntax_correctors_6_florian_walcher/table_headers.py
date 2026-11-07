"""
Helpers for table header correctors (rules 7.5-1 and 7.5-2).

The scope of a header cell is derived from its position in the table:
- a TH in the first row of the table (or inside THead) labels its column  -> /Scope /Column
- a TH that is the first cell of a later row labels its row               -> /Scope /Row
- any other TH is ambiguous and is left unchanged (reported to the caller)
Existing /Scope values are never overwritten. Row and column spans are not taken into
account; tables with spanning header cells may keep ambiguous headers.
"""

from __future__ import annotations

import pikepdf
from pikepdf import Name

_SECTION_TYPES = ("/THead", "/TBody", "/TFoot")
_CELL_TYPES = ("/TH", "/TD")


def _struct_type(element: object) -> str:
    if isinstance(element, pikepdf.Dictionary):
        return str(element.get("/S", ""))
    return ""


def _kids(element: pikepdf.Dictionary) -> list[pikepdf.Dictionary]:
    kids = element.get("/K")
    if isinstance(kids, pikepdf.Dictionary):
        return [kids]
    if isinstance(kids, pikepdf.Array):
        return [kid for kid in kids if isinstance(kid, pikepdf.Dictionary)]
    return []


def find_table(element: pikepdf.Object) -> pikepdf.Dictionary | None:
    """Climb the /P chain from a cell, row or section to the enclosing /Table."""
    current = element
    for _ in range(10):
        if not isinstance(current, pikepdf.Dictionary):
            return None
        if _struct_type(current) == "/Table":
            return current
        current = current.get("/P")
    return None


def table_rows(table: pikepdf.Dictionary) -> list[tuple[pikepdf.Dictionary, bool]]:
    """Rows of the table in reading order, each with a flag telling whether it is in THead."""
    rows: list[tuple[pikepdf.Dictionary, bool]] = []
    for kid in _kids(table):
        kind = _struct_type(kid)
        if kind == "/TR":
            rows.append((kid, False))
        elif kind in _SECTION_TYPES:
            rows.extend((row, kind == "/THead") for row in _kids(kid) if _struct_type(row) == "/TR")
    return rows


def _table_attribute(cell: pikepdf.Dictionary) -> pikepdf.Dictionary:
    """Return the cell's /Table attribute dictionary, creating it if needed."""
    attributes = cell.get("/A")
    if isinstance(attributes, pikepdf.Dictionary):
        if attributes.get("/O") == Name("/Table"):
            return attributes
        cell["/A"] = pikepdf.Array([attributes, pikepdf.Dictionary(O=Name("/Table"))])
        return cell["/A"][1]
    if isinstance(attributes, pikepdf.Array):
        for item in attributes:
            if isinstance(item, pikepdf.Dictionary) and item.get("/O") == Name("/Table"):
                return item
        attributes.append(pikepdf.Dictionary(O=Name("/Table")))
        return attributes[len(attributes) - 1]
    cell["/A"] = pikepdf.Dictionary(O=Name("/Table"))
    return cell["/A"]


def assign_header_scopes(table: pikepdf.Dictionary) -> tuple[int, int, int]:
    """
    Set /Scope on header cells that have none, based on their position.

    Returns (header_cells, scopes_set, ambiguous_cells).
    """
    header_cells = scopes_set = ambiguous = 0
    for row_index, (row, in_thead) in enumerate(table_rows(table)):
        cells = [cell for cell in _kids(row) if _struct_type(cell) in _CELL_TYPES]
        for column_index, cell in enumerate(cells):
            if _struct_type(cell) != "/TH":
                continue
            header_cells += 1
            attribute = _table_attribute(cell)
            if "/Scope" in attribute:
                continue
            if in_thead or row_index == 0:
                attribute["/Scope"] = Name("/Column")
            elif column_index == 0:
                attribute["/Scope"] = Name("/Row")
            else:
                ambiguous += 1
                continue
            scopes_set += 1
    return header_cells, scopes_set, ambiguous


def header_ids(table: pikepdf.Dictionary) -> set[bytes]:
    """IDs of all header cells of the table."""
    ids: set[bytes] = set()
    for row, _ in table_rows(table):
        for cell in _kids(row):
            if _struct_type(cell) == "/TH" and "/ID" in cell:
                ids.add(bytes(cell["/ID"]))
    return ids
