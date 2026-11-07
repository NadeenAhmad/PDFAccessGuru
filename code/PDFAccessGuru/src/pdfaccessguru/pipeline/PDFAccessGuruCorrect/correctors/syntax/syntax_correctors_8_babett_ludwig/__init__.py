import importlib

# 7.21.3.3
_module = importlib.import_module(".7_21_3_3_t01_non_standard_cmap_embedded", __name__)
correct_non_standard_cmap_embedded = _module.correct_non_standard_cmap_embedded

_module = importlib.import_module(".7_21_3_3_t02_wmode_embedded_cmap_not_identical", __name__)
correct_wmode_embedded_cmap_not_identical = _module.correct_wmode_embedded_cmap_not_identical

_module = importlib.import_module(".7_21_3_3_t03_cmap_references_another_non_standard_cmap", __name__)
correct_cmap_references_another_non_standard_cmap = _module.correct_cmap_references_another_non_standard_cmap

# 7.21.4.1
_module = importlib.import_module(".7_21_4_1_t01_font_program_embedded", __name__)
correct_font_program_embedded = _module.correct_font_program_embedded

_module = importlib.import_module(".7_21_4_1_t02_referenced_glyphs_missing", __name__)
correct_referenced_glyphs_missing = _module.correct_referenced_glyphs_missing

# 7.21.4.2
_module = importlib.import_module(".7_21_4_2_t01_charset_incorrectly_lists_glyphs", __name__)
correct_charset_incorrectly_lists_glyphs = _module.correct_charset_incorrectly_lists_glyphs

_module = importlib.import_module(".7_21_4_2_t02_cid_incorrectly_identifies_glpyhs", __name__)
correct_cid_incorrectly_identifies_glpyhs = _module.correct_cid_incorrectly_identifies_glpyhs

# 7.21.5
_module = importlib.import_module(".7_21_5_t01_glyph_width_inconsistent", __name__)
correct_glyph_width_inconsistent = _module.correct_glyph_width_inconsistent

# 7.21.6
_module = importlib.import_module(".7_21_6_t01_non_symbolic_cmap_missing", __name__)
correct_non_symbolic_cmap_missing = _module.correct_non_symbolic_cmap_missing

_module = importlib.import_module(".7_21_6_t02_invalid_non_symbolic_font_Adobe_mapping", __name__)
correct_invalid_non_symbolic_font_Adobe_mapping = _module.correct_invalid_non_symbolic_font_Adobe_mapping

_module = importlib.import_module(".7_21_6_t03_symbolic_true_type_font_contains_encoding", __name__)
correct_symbolic_true_type_font_contains_encoding = _module.correct_symbolic_true_type_font_contains_encoding

_module = importlib.import_module(".7_21_6_t04_embedded_font_program_multiple_cmap_subtables", __name__)
correct_embedded_font_program_multiple_cmap_subtables = _module.correct_embedded_font_program_multiple_cmap_subtables

# 7.21.7
_module = importlib.import_module(".7_21_7_t01_glyph_cannot_mapped_unicode", __name__)
correct_glyph_cannot_mapped_unicode = _module.correct_glyph_cannot_mapped_unicode

_module = importlib.import_module(".7_21_7_t02_glyph_invalid_unicode", __name__)
correct_glyph_invalid_unicode = _module.correct_glyph_invalid_unicode

# 7.21.8 (neu hinzugefügt)
_module = importlib.import_module(".7_21_8t01_document_reference_notdef_glyph", __name__)
correct_document_reference_notdef_glyph = _module.correct_document_reference_notdef_glyph

__all__ = [
    "correct_non_standard_cmap_embedded",
    "correct_wmode_embedded_cmap_not_identical",
    "correct_cmap_references_another_non_standard_cmap",
    "correct_font_program_embedded",
    "correct_referenced_glyphs_missing",
    "correct_charset_incorrectly_lists_glyphs",
    "correct_cid_incorrectly_identifies_glpyhs",
    "correct_glyph_width_inconsistent",
    "correct_non_symbolic_cmap_missing",
    "correct_invalid_non_symbolic_font_Adobe_mapping",
    "correct_symbolic_true_type_font_contains_encoding",
    "correct_embedded_font_program_multiple_cmap_subtables",
    "correct_glyph_cannot_mapped_unicode",
    "correct_glyph_invalid_unicode",
    "correct_document_reference_notdef_glyph",   
]

