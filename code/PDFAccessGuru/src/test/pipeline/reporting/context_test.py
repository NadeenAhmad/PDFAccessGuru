from pdfaccessguru.pipeline.reporting.context import get_current_report, pipeline_report_session

from test.pipeline.reporting.conftest import (
    OUTPUT_PATH,
    PDF_PATH,
    build_expected_report_dict,
)


def test_get_current_report_outside_session():
    assert get_current_report() is None


def test_pipeline_report_session_empty_run():
    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        assert actual == {}

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, lambda _report: None)
    assert actual == expected
    assert actual["finished_at"] is not None
    assert actual["pdf_path"] == PDF_PATH
    assert actual["output_path"] == OUTPUT_PATH


def test_pipeline_report_session_exposes_current_report():
    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        assert actual == {}
        current = get_current_report()
        assert current is not None
        assert current.pdf_path == PDF_PATH
        assert current.output_path == OUTPUT_PATH
