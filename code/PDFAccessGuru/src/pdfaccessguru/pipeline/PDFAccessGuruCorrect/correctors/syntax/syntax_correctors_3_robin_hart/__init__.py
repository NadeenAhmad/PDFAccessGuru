"""

Robin Hart: Rule 7.2-9 to 7.2-21



WARNING: this package is AI generated and not verified. Defined functions

may not be correct/meaning-full. Please verify by yourself!

"""



import importlib



_PACKAGE = __name__



_MODULE_NAMES = [

    "7_2_t09_td_not_contained_tr",

    "7_2_t10_th_td_missing",

    "7_2_t11_table_more_one_thead_kid",

    "7_2_t12_table_more_one_tfoot_kid",

    "7_2_t13_table_tfoot_kid_not_tbody_kids",

    "7_2_t14_table_thead_kid_not_tbody_kids",

    "7_2_t15_table_cell_intersection_other_cells",

    "7_2_t16_table_caption_child",

    "7_2_t17_li_not_contained_l",

    "7_2_t18_lbody_not_contained_li",

    "7_2_t19_invalid_elements_l",

    "7_2_t20_invalid_elements_li",

    "7_2_t21_natural_language_actual_text_attribute_undefined",

]



for _module_name in _MODULE_NAMES:

    importlib.import_module(f".{_module_name}", _PACKAGE)



correct_td_not_contained_tr = importlib.import_module(

    ".7_2_t09_td_not_contained_tr", _PACKAGE

).correct_td_not_contained_tr

correct_th_td_missing = importlib.import_module(

    ".7_2_t10_th_td_missing", _PACKAGE

).correct_th_td_missing

correct_table_more_one_thead_kid = importlib.import_module(

    ".7_2_t11_table_more_one_thead_kid", _PACKAGE

).correct_table_more_one_thead_kid

correct_table_more_one_tfoot_kid = importlib.import_module(

    ".7_2_t12_table_more_one_tfoot_kid", _PACKAGE

).correct_table_more_one_tfoot_kid

correct_table_tfoot_kid_not_tbody_kids = importlib.import_module(

    ".7_2_t13_table_tfoot_kid_not_tbody_kids", _PACKAGE

).correct_table_tfoot_kid_not_tbody_kids

correct_table_thead_kid_not_tbody_kids = importlib.import_module(

    ".7_2_t14_table_thead_kid_not_tbody_kids", _PACKAGE

).correct_table_thead_kid_not_tbody_kids

correct_table_cell_intersection_other_cells = importlib.import_module(

    ".7_2_t15_table_cell_intersection_other_cells", _PACKAGE

).correct_table_cell_intersection_other_cells

correct_table_caption_child = importlib.import_module(

    ".7_2_t16_table_caption_child", _PACKAGE

).correct_table_caption_child

correct_li_not_contained_l = importlib.import_module(

    ".7_2_t17_li_not_contained_l", _PACKAGE

).correct_li_not_contained_l

correct_lbody_not_contained_li = importlib.import_module(

    ".7_2_t18_lbody_not_contained_li", _PACKAGE

).correct_lbody_not_contained_li

correct_invalid_elements_l = importlib.import_module(

    ".7_2_t19_invalid_elements_l", _PACKAGE

).correct_invalid_elements_l

correct_invalid_elements_li = importlib.import_module(

    ".7_2_t20_invalid_elements_li", _PACKAGE

).correct_invalid_elements_li

correct_natural_language_actual_text_attribute_undefined = importlib.import_module(

    ".7_2_t21_natural_language_actual_text_attribute_undefined", _PACKAGE

).correct_natural_language_actual_text_attribute_undefined

prompt_determine_lang_tag = importlib.import_module(

    ".7_2_t21_natural_language_actual_text_attribute_undefined", _PACKAGE

).prompt_determine_lang_tag

__all__ = [

    "correct_invalid_elements_l",

    "correct_invalid_elements_li",

    "correct_lbody_not_contained_li",

    "correct_li_not_contained_l",

    "correct_natural_language_actual_text_attribute_undefined",

    "correct_table_caption_child",

    "correct_table_cell_intersection_other_cells",

    "correct_table_more_one_tfoot_kid",

    "correct_table_more_one_thead_kid",

    "correct_table_tfoot_kid_not_tbody_kids",

    "correct_table_thead_kid_not_tbody_kids",

    "correct_td_not_contained_tr",

    "correct_th_td_missing",

]


