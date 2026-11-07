from dataclasses import dataclass, field


@dataclass(frozen=True)
class TableGridCoordinate:
    """A single position in the logical table grid."""

    row: int
    column: int

    @property
    def as_slot_key(self) -> tuple[int, int]:
        return (self.row, self.column)


@dataclass(frozen=True)
class TableCellSpan:
    """Row and column span of a table cell in the logical grid."""

    row_span: int = 1
    col_span: int = 1


@dataclass(frozen=True)
class TableGridRow:
    """One /TR row within a table, with its zero-based grid row index."""

    index: int
    element_id: int


@dataclass(frozen=True)
class PlacedTableCell:
    """A /TD or /TH cell placed on the logical table grid."""

    element_id: int
    origin: TableGridCoordinate
    span: TableCellSpan
    parent_tr_id: int
    mcids: list[int] = field(default_factory=list)


@dataclass
class LogicalTableGrid:
    """Logical grid built from /RowSpan and /ColSpan while walking table rows."""

    rows: list[TableGridRow] = field(default_factory=list)
    cells: list[PlacedTableCell] = field(default_factory=list)
    slot_to_cell_id: dict[tuple[int, int], int] = field(default_factory=dict)


@dataclass(frozen=True)
class TableCellIntersection:
    """Overlap between the overlapped cell and another cell occupying its slots."""

    overlapped_cell_id: int
    other_cell_id: int
    conflicting_slots: list[TableGridCoordinate]


@dataclass(frozen=True)
class SpanAdjustment:
    """Span change to apply on a table cell."""

    cell_id: int
    new_row_span: int | None = None
    new_col_span: int | None = None


@dataclass(frozen=True)
class TableCellCorrectionPlan:
    """Correction for one table cell intersection."""

    intersection: TableCellIntersection
    cell_to_remove_id: int | None = None
    span_adjustment: SpanAdjustment | None = None
