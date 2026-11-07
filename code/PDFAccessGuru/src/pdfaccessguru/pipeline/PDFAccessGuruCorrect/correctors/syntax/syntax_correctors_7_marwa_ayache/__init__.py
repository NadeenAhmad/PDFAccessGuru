"""
Package that contains all correctors for syntax violations with following rule_ids:
 7.18.2-1 to 7.21.3.2-1.

"""

from .annotation_subtype_trapnet_exists import correct_annotation_subtype_trapnet_exists
from .alt_missing_media_clip_data import correct_alt_missing_media_clip_data
from .ct_missing_media_clip_data import correct_ct_missing_media_clip_data
from .document_reference_xobject import correct_document_reference_xobject
from .form_multiple_children import correct_form_multiple_children
from .form_xobject_mcids_multi_referenced import correct_form_xobject_mcids_multi_referenced
from .incompatible_CID_entries import correct_incompatible_CID_entries
from .invalid_type_2_cidfont import correct_invalid_type_2_cidfont
from .link_annotation_artifact_not_nested_tag_link import correct_link_annotation_artifact_not_nested_tag_link
from .link_annotation_missing_alternate_description_contents import correct_link_annotation_missing_alternate_description_contents
from .page_annotation_tabs_s import correct_page_annotation_tabs_s
from .printermark_annotation_logical_structure import correct_printermark_annotation_logical_structure
from .widget_annotation_artifact_nested_tag_form import correct_widget_annotation_artifact_nested_tag_form

#this provides all public correctors, so that when you import the package then you dont have to list each corrector.  
__all__ = [
    "correct_alt_missing_media_clip_data",
    "correct_annotation_subtype_trapnet_exists",
    "correct_ct_missing_media_clip_data",
    "correct_document_reference_xobject",
    "correct_form_multiple_children",
    "correct_form_xobject_mcids_multi_referenced",
    "correct_incompatible_CID_entries",
    "correct_invalid_type_2_cidfont",
    "correct_link_annotation_artifact_not_nested_tag_link",
    "correct_link_annotation_missing_alternate_description_contents",
    "correct_page_annotation_tabs_s",
    "correct_printermark_annotation_logical_structure",
    "correct_widget_annotation_artifact_nested_tag_form",
]
