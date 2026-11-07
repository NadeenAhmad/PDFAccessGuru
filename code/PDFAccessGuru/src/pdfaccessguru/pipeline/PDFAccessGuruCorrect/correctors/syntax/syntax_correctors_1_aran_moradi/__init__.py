"""

Aran Moradi: Rule 5-1 to 7.1-6



WARNING: this package is AI generated and not verified. Defined functions

may not be correct/meaning-full. Please verify by yourself!

"""



import importlib



_PACKAGE = __name__



_MODULE_NAMES = [

    "5_1_id_scheme_missing",

    "5_2_invalid_part_property",

    "5_3_invalid_part_namespace_prefix",

    "5_4_invalid_amd_property",

    "5_5_invalid_corr_property",

    "6_1_1_invalid_pdf_version",

    "6_2_1_markinfo_dictionary_missing",

    "7_1_1_artifact_present_inside_tagged_content",

    "7_1_2_tagged_content_inside_artifact",

    "7_1_3_content_neither_artifact_nor_tagged_content",

    "7_1_4_suspects_entry_true",

    "7_1_5_not_mapped_to_standard_type",

    "7_1_6_circular_mapping_exists",

]



for _module_name in _MODULE_NAMES:

    importlib.import_module(f".{_module_name}", _PACKAGE)



correct_id_schema_missing = importlib.import_module(

    ".5_1_id_scheme_missing", _PACKAGE

).correct_id_schema_missing

correct_invalid_part_property = importlib.import_module(

    ".5_2_invalid_part_property", _PACKAGE

).correct_invalid_part_property

correct_invalid_part_namespace_prefix = importlib.import_module(

    ".5_3_invalid_part_namespace_prefix", _PACKAGE

).correct_invalid_part_namespace_prefix

correct_invalid_amd_property = importlib.import_module(

    ".5_4_invalid_amd_property", _PACKAGE

).correct_invalid_amd_property

correct_invalid_corr_property = importlib.import_module(

    ".5_5_invalid_corr_property", _PACKAGE

).correct_invalid_corr_property

correct_invalid_pdf_version = importlib.import_module(

    ".6_1_1_invalid_pdf_version", _PACKAGE

).correct_invalid_pdf_version

correct_markinfo_dictionary_missing = importlib.import_module(

    ".6_2_1_markinfo_dictionary_missing", _PACKAGE

).correct_markinfo_dictionary_missing

correct_artifact_present_inside_tagged_content = importlib.import_module(

    ".7_1_1_artifact_present_inside_tagged_content", _PACKAGE

).correct_artifact_present_inside_tagged_content

correct_tagged_content_inside_artifact = importlib.import_module(

    ".7_1_2_tagged_content_inside_artifact", _PACKAGE

).correct_tagged_content_inside_artifact

correct_content_neither_artifact_nor_tagged_content = importlib.import_module(

    ".7_1_3_content_neither_artifact_nor_tagged_content", _PACKAGE

).correct_content_neither_artifact_nor_tagged_content

correct_suspects_entry_true = importlib.import_module(

    ".7_1_4_suspects_entry_true", _PACKAGE

).correct_suspects_entry_true

correct_not_mapped_to_standard_type = importlib.import_module(

    ".7_1_5_not_mapped_to_standard_type", _PACKAGE

).correct_not_mapped_to_standard_type

correct_circular_mapping_exists = importlib.import_module(

    ".7_1_6_circular_mapping_exists", _PACKAGE

).correct_circular_mapping_exists

__all__ = [

    "correct_artifact_present_inside_tagged_content",

    "correct_circular_mapping_exists",

    "correct_content_neither_artifact_nor_tagged_content",

    "correct_id_schema_missing",

    "correct_invalid_amd_property",

    "correct_invalid_corr_property",

    "correct_invalid_pdf_version",

    "correct_invalid_part_namespace_prefix",

    "correct_invalid_part_property",

    "correct_markinfo_dictionary_missing",

    "correct_not_mapped_to_standard_type",

    "correct_suspects_entry_true",

    "correct_tagged_content_inside_artifact",

]

