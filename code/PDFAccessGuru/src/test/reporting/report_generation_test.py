from pdfaccessguru.reporting import (
    build_customer_report_markdown,
    build_report_metrics,
    build_technical_report_markdown,
)
from pdfaccessguru.reporting.taxonomy_loader import get_taxonomy_entry


def _sample_report():
    return {
        "pdf_path": "C:/input/example.pdf",
        "output_path": "C:/output/example_corrected.pdf",
        "started_at": "2026-08-23T18:00:00+00:00",
        "finished_at": "2026-08-23T18:01:00+00:00",
        "reporting": {"debug": 1, "info": 0, "warn": 2, "error": 1},
        "phases": [
            {
                "name": "detection",
                "lines": [],
                "mappings": [],
                "summary": {
                    "total_detected_violations": 3,
                    "total_distinct_violations": 2,
                    "violation_names": [
                        "id-schema-missing",
                        "missing-metadata-stream-dc-title",
                    ],
                    "violations_by_name": {
                        "id-schema-missing": 1,
                        "missing-metadata-stream-dc-title": 2,
                    },
                },
            },
            {"name": "correction", "lines": [], "corrections": []},
            {
                "name": "verification",
                "lines": [],
                "mappings": [],
                "summary": {
                    "total_detected_violations": 1,
                    "total_distinct_violations": 1,
                    "violation_names": ["id-schema-missing"],
                    "violations_by_name": {"id-schema-missing": 1},
                    "total_corrected_violations": 2,
                    "corrected_by_name": {
                        "id-schema-missing": {
                            "corrected_count": 0,
                            "detected_count": 1,
                            "ratio": 0.0,
                        },
                        "missing-metadata-stream-dc-title": {
                            "corrected_count": 2,
                            "detected_count": 2,
                            "ratio": 1.0,
                        },
                    },
                    "contexts_by_name": {
                        "id-schema-missing": [
                            "root/document[0]/pages[14](20 0 obj PDPage)/annots[0]"
                        ],
                    },
                },
            },
        ],
    }


def test_build_report_metrics_extracts_customer_numbers():
    metrics = build_report_metrics(_sample_report())

    assert metrics.detected_count == 3
    assert metrics.corrected_count == 2
    assert metrics.remaining_count == 1
    assert metrics.correction_rate == 2 / 3
    assert metrics.warnings_count == 2
    assert metrics.errors_count == 1


def test_customer_report_uses_customer_facing_explanations():
    markdown = build_customer_report_markdown(_sample_report())

    assert "Problems found: 3" in markdown
    assert "Problems fixed: 2" in markdown
    assert "Problems still open: 1" in markdown
    # Plain names and explanations (Phase 7a), not internal names or the German taxonomy text.
    assert "| PDF/UA label missing |" in markdown
    assert "The file does not say that it follows the accessibility standard PDF/UA." in markdown
    # Open problems are listed with page numbers and what to do, not with technical context paths.
    assert "| PDF/UA label missing | 1 | page 15 | Fix it in the program that made the PDF" in markdown
    assert "root/document" not in markdown
    assert "Raw JSON Report" not in markdown


def test_customer_report_marks_metadata_violation_as_document_level():
    report = _sample_report()
    report["phases"][-1]["summary"]["contexts_by_name"] = {
        "id-schema-missing": ["root/document[0]/metadata[0]"]
    }

    markdown = build_customer_report_markdown(report)

    assert "| PDF/UA label missing | 1 | whole document |" in markdown


def test_customer_report_does_not_guess_page_for_other_page_less_contexts():
    report = _sample_report()
    detection_summary = report["phases"][0]["summary"]
    detection_summary["violation_names"] = ["figure-structure-alternate-description-missing"]
    detection_summary["violations_by_name"] = {
        "figure-structure-alternate-description-missing": 1
    }

    verification_summary = report["phases"][-1]["summary"]
    verification_summary["violation_names"] = [
        "figure-structure-alternate-description-missing"
    ]
    verification_summary["violations_by_name"] = {
        "figure-structure-alternate-description-missing": 1
    }
    verification_summary["corrected_by_name"] = {
        "figure-structure-alternate-description-missing": {
            "corrected_count": 0,
            "detected_count": 1,
            "ratio": 0.0,
        }
    }
    verification_summary["contexts_by_name"] = {
        "figure-structure-alternate-description-missing": [
            "root/document[0]/StructTreeRoot[0]/K[0](SEFigure Figure)"
        ]
    }

    markdown = build_customer_report_markdown(report)

    assert "| Picture without a description | 1 | whole document |" in markdown


def test_customer_report_can_be_german():
    markdown = build_customer_report_markdown(_sample_report(), language="de")
    assert markdown.startswith("# Barrierefreiheitsbericht")
    assert "Gefundene Probleme: 3" in markdown
    assert "| PDF/UA-Kennzeichnung fehlt |" in markdown


def test_technical_report_includes_raw_json_section():
    markdown = build_technical_report_markdown(_sample_report())

    assert "# Technical Pipeline Report" in markdown
    assert "## Raw JSON Report" in markdown
    assert '"pdf_path": "C:/input/example.pdf"' in markdown


def test_taxonomy_loader_reads_german_explanation():
    entry = get_taxonomy_entry("id-schema-missing")

    assert entry is not None
    assert entry.german_explanation.startswith("In den XMP-Metadaten fehlt")
