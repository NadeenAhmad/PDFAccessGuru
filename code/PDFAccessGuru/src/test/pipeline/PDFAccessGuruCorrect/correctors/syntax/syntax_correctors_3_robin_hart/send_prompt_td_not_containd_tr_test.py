import json

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart.utils import (
    run_generic_prompt_td_not_contained_tr_test,
)

# veraPDF_corpus/7.2-t09-fail-a.pdf — table structure from collector tests
#
# Tag tree (* = orphan, not inside TR):
#   Table(0)
#   +-- THead(1)
#   |   +-- TR(2)
#   |       +-- TH(3)  TH(4)
#   +-- TBody(5)
#   |   +-- TD(6)*  TD(7)*          <- same visual row, both orphan
#   +-- TBody(8)
#   |   +-- TR(9)
#   |       +-- TD(10)  TD(11)
#   +-- TFoot(12)
#       +-- TR(13)
#           +-- TD(14)  TD(15)
#
# Visual layout (from bboxes; left col ~x58, right col ~x307):
#   +--------+                    +--------+
#   | TH(3)  |                    | TH(4)  |
#   +--------+                    +--------+
#   | TD(6)* |                    | TD(7)* |
#   +--------+                    +--------+
#   | TD(10) |                    | TD(11) |
#   +--------+                    +--------+
#   | TD(14) |                    | TD(15) |
#   +--------+                    +--------+
_CORPUS_TABLE_JSON = {
    "ID": 0,
    "tag": "/Table",
    "children": [
        {
            "ID": 1,
            "tag": "/THead",
            "children": [
                {
                    "ID": 2,
                    "tag": "/TR",
                    "children": [
                        {"ID": 3, "tag": "/TH"},
                        {"ID": 4, "tag": "/TH"},
                    ],
                }
            ],
        },
        {
            "ID": 5,
            "tag": "/TBody",
            "children": [
                {"ID": 6, "tag": "/TD"},
                {"ID": 7, "tag": "/TD"},
            ],
        },
        {
            "ID": 8,
            "tag": "/TBody",
            "children": [
                {
                    "ID": 9,
                    "tag": "/TR",
                    "children": [
                        {"ID": 10, "tag": "/TD"},
                        {"ID": 11, "tag": "/TD"},
                    ],
                }
            ],
        },
        {
            "ID": 12,
            "tag": "/TFoot",
            "children": [
                {
                    "ID": 13,
                    "tag": "/TR",
                    "children": [
                        {"ID": 14, "tag": "/TD"},
                        {"ID": 15, "tag": "/TD"},
                    ],
                }
            ],
        },
    ],
}

# Bounding boxes extracted from veraPDF_corpus/7.2-t09-fail-a.pdf
_CORPUS_BBOX_JSON = (
    '{"3": {"x0": 142.8, "top": 59.992, "x1": 220.068, "bottom": 71.992}, '
    '"4": {"x0": 392.1, "top": 59.992, "x1": 469.368, "bottom": 71.992}, '
    '"6": {"x0": 58.2, "top": 76.592, "x1": 130.824, "bottom": 88.592}, '
    '"7": {"x0": 307.5, "top": 76.592, "x1": 380.124, "bottom": 88.592}, '
    '"10": {"x0": 58.2, "top": 93.292, "x1": 130.824, "bottom": 105.292}, '
    '"11": {"x0": 307.5, "top": 93.292, "x1": 380.124, "bottom": 105.292}, '
    '"14": {"x0": 58.2, "top": 109.892, "x1": 126.816, "bottom": 121.892}, '
    '"15": {"x0": 307.5, "top": 109.892, "x1": 376.116, "bottom": 121.892}}'
)

# PDFAccessGuru_corpus/7.2-t09-fail-a_one_corrected.pdf — TD 7 already wrapped in TR 6
#
# Tag tree (* = orphan):
#   Table(0)
#   +-- THead(1)
#   |   +-- TR(2)
#   |       +-- TH(3)  TH(4)
#   +-- TBody(5)
#   |   +-- TR(6)
#   |   |   +-- TD(7)
#   |   +-- TD(8)*                   <- orphan; same visual row as TR(6)
#   +-- TBody(9)
#   |   +-- TR(10)
#   |       +-- TD(11)  TD(12)
#   +-- TFoot(13)
#       +-- TR(14)
#           +-- TD(15)  TD(16)
#
# Visual layout (from bboxes; left col ~x58, right col ~x307):
#   +--------+                    +--------+
#   | TH(3)  |                    | TH(4)  |
#   +--------+                    +--------+
#   | TD(7)  | TR(6)              | TD(8)* |
#   +--------+                    +--------+
#   | TD(11) | TR(10)             | TD(12) |
#   +--------+                    +--------+
#   | TD(15) | TR(14)             | TD(16) |
#   +--------+                    +--------+
_ONE_CORRECTED_TABLE_JSON = {
    "ID": 0,
    "tag": "/Table",
    "children": [
        {
            "ID": 1,
            "tag": "/THead",
            "children": [
                {
                    "ID": 2,
                    "tag": "/TR",
                    "children": [
                        {"ID": 3, "tag": "/TH"},
                        {"ID": 4, "tag": "/TH"},
                    ],
                }
            ],
        },
        {
            "ID": 5,
            "tag": "/TBody",
            "children": [
                {
                    "ID": 6,
                    "tag": "/TR",
                    "children": [
                        {"ID": 7, "tag": "/TD"},
                    ],
                },
                {"ID": 8, "tag": "/TD"},
            ],
        },
        {
            "ID": 9,
            "tag": "/TBody",
            "children": [
                {
                    "ID": 10,
                    "tag": "/TR",
                    "children": [
                        {"ID": 11, "tag": "/TD"},
                        {"ID": 12, "tag": "/TD"},
                    ],
                }
            ],
        },
        {
            "ID": 13,
            "tag": "/TFoot",
            "children": [
                {
                    "ID": 14,
                    "tag": "/TR",
                    "children": [
                        {"ID": 15, "tag": "/TD"},
                        {"ID": 16, "tag": "/TD"},
                    ],
                }
            ],
        },
    ],
}

_ONE_CORRECTED_BBOX_JSON = (
    '{"3": {"x0": 142.8, "top": 59.992, "x1": 220.068, "bottom": 71.992}, '
    '"4": {"x0": 392.1, "top": 59.992, "x1": 469.368, "bottom": 71.992}, '
    '"7": {"x0": 58.2, "top": 76.592, "x1": 130.824, "bottom": 88.592}, '
    '"8": {"x0": 307.5, "top": 76.592, "x1": 380.124, "bottom": 88.592}, '
    '"11": {"x0": 58.2, "top": 93.292, "x1": 130.824, "bottom": 105.292}, '
    '"12": {"x0": 307.5, "top": 93.292, "x1": 380.124, "bottom": 105.292}, '
    '"15": {"x0": 58.2, "top": 109.892, "x1": 126.816, "bottom": 121.892}, '
    '"16": {"x0": 307.5, "top": 109.892, "x1": 376.116, "bottom": 121.892}}'
)

# Minimal table: one orphan TD in TBody
#
# Tag tree:
#   Table(0)
#   +-- TBody(1)
#       +-- TD(2)*
#
# Visual layout (from bboxes):
#   +--------+
#   | TD(2)* |
#   +--------+
_MINIMAL_SINGLE_ORPHAN_TD_TABLE_JSON = {
    "ID": 0,
    "tag": "/Table",
    "children": [
        {
            "ID": 1,
            "tag": "/TBody",
            "children": [{"ID": 2, "tag": "/TD"}],
        }
    ],
}

_MINIMAL_SINGLE_ORPHAN_TD_BBOX_JSON = (
    '{"2": {"x0": 10.0, "top": 20.0, "x1": 50.0, "bottom": 40.0}}'
)

# Orphan TD on the left of a row whose right cell is already wrapped in a TR
#
# Tag tree:
#   Table(0)
#   +-- TBody(1)
#       +-- TR(2)
#       |   +-- TD(3)
#       +-- TD(4)*                   <- orphan; left of TD(3) on same row
#
# Visual layout (from bboxes; TD(4) ~x10 left, TD(3) ~x200 right):
#   +--------+                    +--------+
#   | TD(4)* |                    | TD(3)  | TR(2)
#   +--------+                    +--------+
_TWO_COLUMN_ROW_PARTIAL_TR_TABLE_JSON = {
    "ID": 0,
    "tag": "/Table",
    "children": [
        {
            "ID": 1,
            "tag": "/TBody",
            "children": [
                {
                    "ID": 2,
                    "tag": "/TR",
                    "children": [
                        {"ID": 3, "tag": "/TD"},
                    ],
                },
                {"ID": 4, "tag": "/TD"},
            ],
        }
    ],
}

_TWO_COLUMN_ROW_PARTIAL_TR_BBOX_JSON = (
    '{"3": {"x0": 200.0, "top": 50.0, "x1": 280.0, "bottom": 70.0}, '
    '"4": {"x0": 10.0, "top": 50.0, "x1": 90.0, "bottom": 70.0}}'
)

# Orphan TH in THead that belongs in an existing header row
#
# Tag tree:
#   Table(0)
#   +-- THead(1)
#       +-- TR(2)
#       |   +-- TH(3)
#       +-- TH(4)*                   <- orphan; right of TH(3) on same row
#
# Visual layout (from bboxes; TH(3) ~x10 left, TH(4) ~x200 right):
#   +--------+                    +--------+
#   | TH(3)  | TR(2)              | TH(4)* |
#   +--------+                    +--------+
_ORPHAN_TH_IN_THEAD_TABLE_JSON = {
    "ID": 0,
    "tag": "/Table",
    "children": [
        {
            "ID": 1,
            "tag": "/THead",
            "children": [
                {
                    "ID": 2,
                    "tag": "/TR",
                    "children": [
                        {"ID": 3, "tag": "/TH"},
                    ],
                },
                {"ID": 4, "tag": "/TH"},
            ],
        }
    ],
}

_ORPHAN_TH_IN_THEAD_BBOX_JSON = (
    '{"3": {"x0": 10.0, "top": 20.0, "x1": 90.0, "bottom": 40.0}, '
    '"4": {"x0": 200.0, "top": 20.0, "x1": 280.0, "bottom": 40.0}}'
)


def test_prompt_td_not_contained_tr_corpus_first_orphan_td_creates_new_tr():
    """
    Prompt test: first orphan TD in corpus table should create a new TR.
    """
    run_generic_prompt_td_not_contained_tr_test(
        {
            "table_json": json.dumps(_CORPUS_TABLE_JSON),
            "id_to_bounding_box_mapping_json": _CORPUS_BBOX_JSON,
            "affected_element_id": 6,
        },
        {"create_new_tr": "true"},
    )


def test_prompt_td_not_contained_tr_corpus_second_orphan_td_creates_new_tr():
    """
    Prompt test: second orphan TD in corpus table should create a new TR.
    """
    run_generic_prompt_td_not_contained_tr_test(
        {
            "table_json": json.dumps(_CORPUS_TABLE_JSON),
            "id_to_bounding_box_mapping_json": _CORPUS_BBOX_JSON,
            "affected_element_id": 7,
        },
        {"create_new_tr": "true"},
    )


def test_prompt_td_not_contained_tr_partially_corrected_orphan_td_joins_existing_tr():
    """
    Prompt test: orphan TD should join an existing TR when one sibling is already wrapped.
    """
    run_generic_prompt_td_not_contained_tr_test(
        {
            "table_json": json.dumps(_ONE_CORRECTED_TABLE_JSON),
            "id_to_bounding_box_mapping_json": _ONE_CORRECTED_BBOX_JSON,
            "affected_element_id": 8,
        },
        {
            "create_new_tr": "false",
            "id_of_tr_element": 6,
            "index_tr_elements_children": 1,
        },
    )


def test_prompt_td_not_contained_tr_minimal_single_orphan_td_creates_new_tr():
    """
    Prompt test: single orphan TD in a minimal table should create a new TR.
    """
    run_generic_prompt_td_not_contained_tr_test(
        {
            "table_json": json.dumps(_MINIMAL_SINGLE_ORPHAN_TD_TABLE_JSON),
            "id_to_bounding_box_mapping_json": _MINIMAL_SINGLE_ORPHAN_TD_BBOX_JSON,
            "affected_element_id": 2,
        },
        {"create_new_tr": "true"},
    )


def test_prompt_td_not_contained_tr_orphan_td_joins_existing_tr_at_left_column():
    """
    Prompt test: orphan TD on the left of a visual row should join the existing TR at index 0.
    """
    run_generic_prompt_td_not_contained_tr_test(
        {
            "table_json": json.dumps(_TWO_COLUMN_ROW_PARTIAL_TR_TABLE_JSON),
            "id_to_bounding_box_mapping_json": _TWO_COLUMN_ROW_PARTIAL_TR_BBOX_JSON,
            "affected_element_id": 4,
        },
        {
            "create_new_tr": "false",
            "id_of_tr_element": 2,
            "index_tr_elements_children": 0,
        },
    )


def test_prompt_td_not_contained_tr_orphan_th_joins_existing_header_tr():
    """
    Prompt test: orphan TH in THead on the same visual row should join the existing header TR.
    """
    run_generic_prompt_td_not_contained_tr_test(
        {
            "table_json": json.dumps(_ORPHAN_TH_IN_THEAD_TABLE_JSON),
            "id_to_bounding_box_mapping_json": _ORPHAN_TH_IN_THEAD_BBOX_JSON,
            "affected_element_id": 4,
        },
        {
            "create_new_tr": "false",
            "id_of_tr_element": 2,
            "index_tr_elements_children": 1,
        },
    )
