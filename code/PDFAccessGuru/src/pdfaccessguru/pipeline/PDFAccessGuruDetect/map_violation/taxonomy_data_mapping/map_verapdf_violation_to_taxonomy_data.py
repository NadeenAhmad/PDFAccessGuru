

    
from pdfaccessguru.model.map_violation.taxonomy_data import TaxonomyData
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation


def map_verapdf_violation_to_taxonomy_data(veraPdf_violation: VeraPdfViolation) -> TaxonomyData:
    """
    Maps a single {@link VeraPdfViolation} to the corresponding {@link TaxonomyData} object.

    Parameters:
        - veraPdf_violation: The VeraPdfViolation to be mapped.
    Returns: 
        - The corresponding TaxonomyData object.
    """
    return TaxonomyData(
        name = map_rule_id_to_syntax_violation_name(veraPdf_violation.rule_id),
        description=veraPdf_violation.message,
        guidelines=[], # TODO: implement mapping of guidelines
        rank=map_rule_id_to_syntax_violation_rank(veraPdf_violation.rule_id)
    )


def map_rule_id_to_syntax_violation_rank(rule_id: str) -> float:
    """
    Maps a veraPDF rule ID to its corresponding syntax violation rank 
    based on the taxonomy configuration.
    A lower rank means that the violation will be executed earlier.
    """
    rule_id_to_rank_mapping = {
        "5-1": 100.0,
        "5-2": 100.0,
        "5-3": 100.0,
        "5-4": 100.0,
        "5-5": 100.0,
        "6.1-1": 100.0,
        "6.2-1": 100.0,
        "7.1-1": 100.0,
        "7.1-2": 100.0,
        "7.1-3": 100.0,
        "7.1-4": 100.0,
        "7.1-5": 100.0,
        "7.1-6": 100.0,
        "7.1-7": 100.0,
        "7.1-8": 100.0,
        "7.1-9": 100.0,
        "7.1-10": 100.0,
        "7.1-11": 1.0,
        "7.1-12": 2.0,
        "7.2-2": 100.0,
        "7.2-3": 100.0,
        "7.2-4": 100.0,
        "7.2-5": 100.0,
        "7.2-6": 3.0,
        "7.2-7": 100.0,
        "7.2-8": 100.0,
        "7.2-9": 100.0,
        "7.2-10": 100.0,
        "7.2-11": 100.0,
        "7.2-12": 100.0,
        "7.2-13": 100.0,
        "7.2-14": 100.0,
        "7.2-15": 100.0,
        "7.2-16": 100.0,
        "7.2-17": 100.0,
        "7.2-18": 100.0,
        "7.2-19": 100.0,
        "7.2-20": 100.0,
        "7.2-21": 100.0,
        "7.2-22": 100.0,
        "7.2-23": 100.0,
        "7.2-24": 100.0,
        "7.2-25": 100.0,
        "7.2-26": 100.0,
        "7.2-27": 100.0,
        "7.2-28": 100.0,
        "7.2-29": 100.0,
        "7.2-30": 100.0,
        "7.2-31": 100.0,
        "7.2-32": 100.0,
        "7.2-33": 100.0,
        "7.2-34": 100.0,
        "7.2-36": 100.0,
        "7.2-37": 100.0,
        "7.2-38": 100.0,
        "7.2-39": 100.0,
        "7.2-40": 100.0,
        "7.2-41": 100.0,
        "7.2-42": 100.0,
        "7.2-43": 100.0,
        "7.3-1": 100.0,
        "7.4.2-1": 100.0,
        "7.4.4-1": 100.0,
        "7.4.4-2": 100.0,
        "7.4.4-3": 100.0,
        "7.5-1": 100.0,
        "7.5-2": 100.0,
        "7.7-1": 100.0,
        "7.9-1": 100.0,
        "7.9-2": 100.0,
        "7.10-1": 100.0,
        "7.10-2": 100.0,
        "7.11-1": 100.0,
        "7.15-1": 100.0,
        "7.16-1": 100.0,
        "7.18.1-1": 5.0,
        "7.18.1-2": 100.0,
        "7.18.1-3": 100.0,
        "7.18.2-1": 100.0,
        "7.18.3-1": 100.0,
        "7.18.4-1": 100.0,
        "7.18.4-2": 100.0,
        "7.18.5-1": 100.0,
        "7.18.5-2": 100.0,
        "7.18.6.2-1": 100.0,
        "7.18.6.2-2": 100.0,
        "7.18.8-1": 100.0,
        "7.20-1": 100.0,
        "7.20-2": 100.0,
        "7.21.3.1-1": 100.0,
        "7.21.3.2-1": 100.0,
        "7.21.3.3-1": 100.0,
        "7.21.3.3-2": 100.0,
        "7.21.3.3-3": 100.0,
        "7.21.4.1-1": 4.0,
        "7.21.4.1-2": 100.0,
        "7.21.4.2-1": 100.0,
        "7.21.4.2-2": 100.0,
        "7.21.5-1": 100.0,
        "7.21.6-1": 100.0,
        "7.21.6-2": 100.0,
        "7.21.6-3": 100.0,
        "7.21.6-4": 100.0,
        "7.21.7-1": 100.0,
        "7.21.7-2": 100.0,
        "7.21.8-1": 100.0,        
    }

    return rule_id_to_rank_mapping[rule_id]



def map_rule_id_to_syntax_violation_name(rule_id: str) -> str:
    """
    Maps a veraPDF rule ID to its corresponding syntax violation name 
    based on the taxonomy configuration.

    Note that this method is fully LLM-generated and may contain errors!
    
    Args:
        rule_id (str): The rule ID (e.g., "5-1", "7.1-3", "7.18.5-2")
        
    Returns:
        str: The corresponding violation name.
        
    Raises:
        KeyError: If the rule_id is unknown or not a syntax violation.
    """
    # Exaktes Mapping aller Syntax-Violations aus der Taxonomie
    rule_id_to_name_mapping = {
        "5-1": "id-schema-missing",
        "5-2": "invalid-part-property",
        "5-3": "invalid-part-namespace-prefix",
        "5-4": "invalid-amd-property",
        "5-5": "invalid-corr-property",
        "6.1-1": "invalid-pdf-version",
        "6.2-1": "markinfo-dictionary-missing",
        "7.1-1": "artifact-present-inside-tagged-content",
        "7.1-2": "tagged-content-inside-artifact",
        "7.1-3": "content-neither-artifact-nor-tagged-content",
        "7.1-4": "suspects-entry-true",
        "7.1-5": "not-mapped-to-standard-type",
        "7.1-6": "circular-mapping-exists",
        "7.1-7": "standard-type-remapped",
        "7.1-8": "metadata-key-missing",
        "7.1-9": "missing-metadata-stream-dc-title",
        "7.1-10": "display-doc-title-false",
        "7.1-11": "missing-struct-tree-root-entry",
        "7.1-12": "parent-entry-missing",
        "7.2-2": "natural-language-undefined",
        "7.2-3": "table-specific-elements-missing",
        "7.2-4": "tr-element-missing",
        "7.2-5": "thead-element-missing",
        "7.2-6": "tbody-element-missing",
        "7.2-7": "tfoot-element-missing",
        "7.2-8": "th-not-contained-tr",
        "7.2-9": "td-not-contained-tr",
        "7.2-10": "th-td-missing",
        "7.2-11": "table-more-one-thead-kid",
        "7.2-12": "table-more-one-tfoot-kid",
        "7.2-13": "table-tfoot-kid-not-tbody-kids",
        "7.2-14": "table-thead-kid-not-tbody-kids",
        "7.2-15": "table-cell-intersection-other-cells",
        "7.2-16": "table-caption-child",
        "7.2-17": "li-not-contained-l",
        "7.2-18": "lbody-not-contained-li",
        "7.2-19": "invalid-elements-l",
        "7.2-20": "invalid-elements-li",
        "7.2-21": "natural-language-actual-text-attribute-undefined",
        "7.2-22": "natural-language-alt-attribute-undefined",
        "7.2-23": "natural-language-e-attribute-undefined",
        "7.2-24": "natural-language-annotations-undefined",
        "7.2-25": "natural-language-tu-form-fields-undefined",
        "7.2-26": "toci-missing-from-toc",
        "7.2-27": "toc-contains-invalid-element",
        "7.2-28": "toc-caption-child",
        "7.2-29": "invalid-lang-entry",
        "7.2-30": "natural-language-ActualText-span-undetermined",
        "7.2-31": "natural-language-alt-attribute-span-undetermined",
        "7.2-32": "natural-language-e-attribute-span-undetermined",
        "7.2-33": "natural-language-metadata-undetermined",
        "7.2-34": "natural-language-text-page-undetermined",
        "7.2-36": "thead-invalid-elements",
        "7.2-37": "tbody-invalid-elements",
        "7.2-38": "tfoot-invalid-elements",
        "7.2-39": "table-several-captions",
        "7.2-40": "l-caption-child-not-first",
        "7.2-41": "table-columns-different-number-rows",
        "7.2-42": "table-rows-span-different-number-columns",
        "7.2-43": "table-rows-span-different-number-columns-02",
        "7.3-1": "figure-structure-alternate-description-missing",
        "7.4.2-1": "heading-level-skipped",
        "7.4.4-1": "node-more-one-h-tag",
        "7.4.4-2": "document-uses-h-h#-tags",
        "7.4.4-3": "document-uses-hn-h-tags",
        "7.5-1": "td-headers-missing",
        "7.5-2": "td-undefined-headers",
        "7.7-1": "formula-structure-no-alternative-description",
        "7.9-1": "id-note-tag-missing",
        "7.9-2": "id-note-tag-non-unique",
        "7.10-1": "missing-empty-name",
        "7.10-2": "present-optional-content-configuration",
        "7.11-1": "f-uf-key-invalid",
        "7.15-1": "dynamic-xfa-forms-present",
        "7.16-1": "encrypted-file-p-missing",
        "7.18.1-1": "annotation-artifact-not-nested",
        "7.18.1-2": "invalid-annotation",
        "7.18.1-3": "form-field-missing-alt-entry",
        "7.18.2-1": "annotation-subtype-trapnet-exists",
        "7.18.3-1": "page-annotation-tabs-s",
        "7.18.4-1": "widget-annotation-artifact-nested-tag-form",
        "7.18.4-2": "form-multiple-children",
        "7.18.5-1": "link-annotation-artifact-not-nested-tag-link",
        "7.18.5-2": "link-annotation-missing-alternate-description-contents",
        "7.18.6.2-1": "ct-missing-media-clip-data",
        "7.18.6.2-2": "alt-missing-media-clip-data",
        "7.18.8-1": "printermark-annotation-logical-structure",
        "7.20-1": "document-reference-xobject",
        "7.20-2": "form-xobject-mcids-multi-referenced",
        "7.21.3.1-1": "incompatible-CID-entries",
        "7.21.3.2-1": "invalid-type-2-cidfont",
        "7.21.3.3-1": "non-standard-cmap-embedded",
        "7.21.3.3-2": "wmode-embedded-cmap-not-identical",
        "7.21.3.3-3": "cmap-references-another-non-standard-cmap",
        "7.21.4.1-1": "font-program-embedded",
        "7.21.4.1-2": "referenced-glyphs-missing",
        "7.21.4.2-1": "charset-incorrectly-lists-glyphs",
        "7.21.4.2-2": "cid-incorrectly-identifies-glpyhs",
        "7.21.5-1": "glyph-width-inconsistent",
        "7.21.6-1": "non-symbolic-cmap-missing",
        "7.21.6-2": "invalid-non-symbolic-font-Adobe-mapping",
        "7.21.6-3": "symbolic-true-type-font-contains-encoding",
        "7.21.6-4": "embedded-font-program-multiple-cmap-subtables",
        "7.21.7-1": "glyph-cannot-mapped-unicode",
        "7.21.7-2": "glyph-invalid-unicode",
        "7.21.8-1": "document-reference-notdef-glyph",
    }
     
    return rule_id_to_name_mapping[rule_id]
    