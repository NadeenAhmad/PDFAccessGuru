from pdfaccessguru.reporting.violation_reference import (
    VIOLATION_REFERENCE_FILENAME,
    build_violation_reference_markdown,
    violation_reference_link,
)


def test_violation_reference_contains_syntax_taxonomy_information():
    markdown = build_violation_reference_markdown()

    assert "# Violation Reference" in markdown
    assert "| Violation | Rule | Guideline | Description | Explanation |" in markdown
    assert '<a id="violation-id-schema-missing"></a>`id-schema-missing`' in markdown
    assert "The document metadata stream doesn't contain PDF/UA Identification Schema" in markdown
    assert "In den XMP-Metadaten fehlt" in markdown


def test_violation_reference_omits_category_and_non_syntax_violations():
    markdown = build_violation_reference_markdown()

    assert "| Category |" not in markdown
    assert "image-alt-not-descriptive" not in markdown
    assert "color-contrast-enhanced" not in markdown


def test_violation_reference_link_targets_companion_file_row():
    assert violation_reference_link("id-schema-missing") == (
        f"[id-schema-missing]({VIOLATION_REFERENCE_FILENAME}"
        "#violation-id-schema-missing)"
    )
