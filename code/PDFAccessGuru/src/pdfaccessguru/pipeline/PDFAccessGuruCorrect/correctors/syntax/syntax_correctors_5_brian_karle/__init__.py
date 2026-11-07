"""
Brian Karle: Rules 7.2-36 to 7.2-43, 7.3-1, 7.4-2-1, and 7.4-4-1 to 7.4-4-3.
"""

import importlib

_PACKAGE = __name__

_MODULE_NAMES = [
    "7_2_t36_thead_invalid_elements",
    "7_2_t37_tbody_invalid_elements",
    "7_2_t38_tfoot_invalid_elements",
    "7_2_t39_table_several_captions",
    "7_2_t40_l_caption_child_not_first",
    "7_2_t41_table_columns_different_number_rows",
    "7_2_t42_table_rows_span_different_number_columns",
    "7_2_t43_table_rows_span_different_number_columns_02",
    "7_3_t01_figure_structure_alternate_description_missing",
    "7_4_2_t01_heading_level_skipped",
    "7_4_4_t01_node_more_one_h_tag",
    "7_4_4_t02_document_uses_h_h_sharp_tags",
    "7_4_4_t03_document_uses_hn_h_tags",
]

for _module_name in _MODULE_NAMES:
    importlib.import_module(f".{_module_name}", _PACKAGE)

correct_thead_invalid_elements = importlib.import_module(
    ".7_2_t36_thead_invalid_elements", _PACKAGE
).correct_thead_invalid_elements
correct_tbody_invalid_elements = importlib.import_module(
    ".7_2_t37_tbody_invalid_elements", _PACKAGE
).correct_tbody_invalid_elements
correct_tfoot_invalid_elements = importlib.import_module(
    ".7_2_t38_tfoot_invalid_elements", _PACKAGE
).correct_tfoot_invalid_elements
correct_table_several_captions = importlib.import_module(
    ".7_2_t39_table_several_captions", _PACKAGE
).correct_table_several_captions
correct_l_caption_child_not_first = importlib.import_module(
    ".7_2_t40_l_caption_child_not_first", _PACKAGE
).correct_l_caption_child_not_first
correct_table_columns_different_number_rows = importlib.import_module(
    ".7_2_t41_table_columns_different_number_rows", _PACKAGE
).correct_table_columns_different_number_rows
correct_table_rows_span_different_number_columns = importlib.import_module(
    ".7_2_t42_table_rows_span_different_number_columns", _PACKAGE
).correct_table_rows_span_different_number_columns
correct_table_rows_span_different_number_columns_02 = importlib.import_module(
    ".7_2_t43_table_rows_span_different_number_columns_02", _PACKAGE
).correct_table_rows_span_different_number_columns_02
correct_figure_structure_alternate_description_missing = importlib.import_module(
    ".7_3_t01_figure_structure_alternate_description_missing", _PACKAGE
).correct_figure_structure_alternate_description_missing
correct_heading_level_skipped = importlib.import_module(
    ".7_4_2_t01_heading_level_skipped", _PACKAGE
).correct_heading_level_skipped
correct_node_more_one_h_tag = importlib.import_module(
    ".7_4_4_t01_node_more_one_h_tag", _PACKAGE
).correct_node_more_one_h_tag
correct_document_uses_h_h_sharp_tags = importlib.import_module(
    ".7_4_4_t02_document_uses_h_h_sharp_tags", _PACKAGE
).correct_document_uses_h_h_sharp_tags
correct_document_uses_hn_h_tags = importlib.import_module(
    ".7_4_4_t03_document_uses_hn_h_tags", _PACKAGE
).correct_document_uses_hn_h_tags

__all__ = [
    "correct_document_uses_h_h_sharp_tags",
    "correct_document_uses_hn_h_tags",
    "correct_figure_structure_alternate_description_missing",
    "correct_heading_level_skipped",
    "correct_l_caption_child_not_first",
    "correct_node_more_one_h_tag",
    "correct_table_columns_different_number_rows",
    "correct_table_rows_span_different_number_columns",
    "correct_table_rows_span_different_number_columns_02",
    "correct_table_several_captions",
    "correct_tbody_invalid_elements",
    "correct_tfoot_invalid_elements",
    "correct_thead_invalid_elements",
]
