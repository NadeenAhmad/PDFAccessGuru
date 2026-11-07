"""
Riard Qupevaj: Rule 7.2-22 to 7.2-34.
"""

import importlib

_PACKAGE = __name__

_MODULE_NAMES = [
    "7_2_t22_natural_language_alt_attribute_undefined",
    "7_2_t23_natural_language_e_attribute_undefined",
    "7_2_t24_natural_language_annotations_undefined",
    "7_2_t25_natural_language_tu_form_fields_undefined",
    "7_2_t26_toci_missing_from_toc",
    "7_2_t27_toc_contains_invalid_element",
    "7_2_t28_toc_caption_child",
    "7_2_t29_invalid_lang_entry",
    "7_2_t30_natural_language_actualtext_span_undetermined",
    "7_2_t31_natural_language_alt_attribute_span_undetermined",
    "7_2_t32_natural_language_e_attribute_span_undetermined",
    "7_2_t33_natural_language_metadata_undetermined",
    "7_2_t34_natural_language_text_page_undetermined",
]

for _module_name in _MODULE_NAMES:
    importlib.import_module(f".{_module_name}", _PACKAGE)

correct_natural_language_alt_attribute_undefined = importlib.import_module(
    ".7_2_t22_natural_language_alt_attribute_undefined", _PACKAGE
).correct_natural_language_alt_attribute_undefined
correct_natural_language_e_attribute_undefined = importlib.import_module(
    ".7_2_t23_natural_language_e_attribute_undefined", _PACKAGE
).correct_natural_language_e_attribute_undefined
correct_natural_language_annotations_undefined = importlib.import_module(
    ".7_2_t24_natural_language_annotations_undefined", _PACKAGE
).correct_natural_language_annotations_undefined
correct_natural_language_tu_form_fields_undefined = importlib.import_module(
    ".7_2_t25_natural_language_tu_form_fields_undefined", _PACKAGE
).correct_natural_language_tu_form_fields_undefined
correct_toci_missing_from_toc = importlib.import_module(
    ".7_2_t26_toci_missing_from_toc", _PACKAGE
).correct_toci_missing_from_toc
correct_toc_contains_invalid_element = importlib.import_module(
    ".7_2_t27_toc_contains_invalid_element", _PACKAGE
).correct_toc_contains_invalid_element
correct_toc_caption_child = importlib.import_module(
    ".7_2_t28_toc_caption_child", _PACKAGE
).correct_toc_caption_child
correct_invalid_lang_entry = importlib.import_module(
    ".7_2_t29_invalid_lang_entry", _PACKAGE
).correct_invalid_lang_entry
correct_natural_language_ActualText_span_undetermined = importlib.import_module(
    ".7_2_t30_natural_language_actualtext_span_undetermined", _PACKAGE
).correct_natural_language_ActualText_span_undetermined
correct_natural_language_alt_attribute_span_undetermined = importlib.import_module(
    ".7_2_t31_natural_language_alt_attribute_span_undetermined", _PACKAGE
).correct_natural_language_alt_attribute_span_undetermined
correct_natural_language_e_attribute_span_undetermined = importlib.import_module(
    ".7_2_t32_natural_language_e_attribute_span_undetermined", _PACKAGE
).correct_natural_language_e_attribute_span_undetermined
correct_natural_language_metadata_undetermined = importlib.import_module(
    ".7_2_t33_natural_language_metadata_undetermined", _PACKAGE
).correct_natural_language_metadata_undetermined
correct_natural_language_text_page_undetermined = importlib.import_module(
    ".7_2_t34_natural_language_text_page_undetermined", _PACKAGE
).correct_natural_language_text_page_undetermined

__all__ = [
    "correct_invalid_lang_entry",
    "correct_natural_language_ActualText_span_undetermined",
    "correct_natural_language_alt_attribute_span_undetermined",
    "correct_natural_language_alt_attribute_undefined",
    "correct_natural_language_annotations_undefined",
    "correct_natural_language_e_attribute_span_undetermined",
    "correct_natural_language_e_attribute_undefined",
    "correct_natural_language_metadata_undetermined",
    "correct_natural_language_text_page_undetermined",
    "correct_natural_language_tu_form_fields_undefined",
    "correct_toc_caption_child",
    "correct_toc_contains_invalid_element",
    "correct_toci_missing_from_toc",
]
