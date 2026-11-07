"""Session fixtures and collection rules for PDFAccessGuru tests."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

TEST_ROOT = Path(__file__).resolve().parent
_DELETED_OUTPUT_DIR_PARTS = ("resources", "test_results")
FORBIDDEN_OUTPUT_DIR = TEST_ROOT.joinpath(*_DELETED_OUTPUT_DIR_PARTS)

# Load the developer's local .env (if any) so that live LLM tests run when a key is configured.
load_dotenv(TEST_ROOT.parents[1] / ".env")

# Test files that send real requests to OpenRouter. They are skipped when no API key is set
# (e.g. in CI), because unit tests must not depend on a paid external service.
LIVE_LLM_TEST_FILES = {
    "openrouter_provider_test.py",
    "send_prompt_td_not_containd_tr_test.py",
    "7_2_t21_natural_language_actual_text_attribute_undefined_test.py",
    # Glyph correctors: when the Adobe Glyph List gives no answer, only a language model can
    # propose a character (there is no longer a silent fallback to a space).
    "7_21_7_t01_glyph_cannot_mapped_unicode_test.py",
    "7_21_7_t02_glyph_invalid_unicode_test.py",
}

# Tests that still fail. On 2026-11-06 main had 16; 12 were fixed in Phase 1. The rest belong to
# correctors that are switched off (DISABLED_CORRECTORS) and get rewritten in later phases.
# Remove an entry together with its fix. Listed here so the failures stay visible in CI output.
_P = "src/test/pipeline/"
_C = _P + "PDFAccessGuruCorrect/correctors/syntax/"
_D = _P + "PDFAccessGuruDetect/"
KNOWN_FAILURES = {
}


# Test files that cannot be published (third-party PDFs). The public repository has none of them;
# a test that fails only because one of these is missing is reported as skipped there.
PRIVATE_RESOURCES = ("ProfPDFs", "Thesis_Set", "test_Set", "validation_Set", "image_dummies",
                     "verapdf_ua1_test_pdf_files", "bildOhneAlt", "verapdf_xml_report_dummies")
_MISSING_PRIVATE = tuple(name for name in PRIVATE_RESOURCES
                         if not any((TEST_ROOT / "resources").glob(name + "*")))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if not (report.failed and _MISSING_PRIVATE and call.excinfo is not None):
        return
    text = str(report.longrepr)
    missing = [name for name in _MISSING_PRIVATE if name in text]
    if missing:
        report.outcome = "skipped"
        report.longrepr = (str(item.path), item.location[1] or 0,
                           f"needs test files that are not published ({missing[0]})")


def pytest_collection_modifyitems(config, items):
    has_llm_key = bool(os.environ.get("OPENROUTER_API_KEY"))
    for item in items:
        if Path(str(item.fspath)).name in LIVE_LLM_TEST_FILES:
            item.add_marker(pytest.mark.llm)
            if not has_llm_key:
                item.add_marker(pytest.mark.skip(reason="live LLM test: set OPENROUTER_API_KEY to run it"))
        reason = KNOWN_FAILURES.get(item.nodeid)
        if reason is not None:
            item.add_marker(pytest.mark.xfail(reason=f"known failure (Phase 1): {reason}", strict=False))


@pytest.fixture(autouse=True)
def console_output_is_on_for_every_test():
    """The command line turns console output off; make sure no test leaks that into the next one."""
    from pdfaccessguru.pipeline.reporting.console import set_console_output

    set_console_output(True)
    yield
    set_console_output(True)


@pytest.fixture(scope="session", autouse=True)
def resources_test_results_must_not_be_created():
    """
    Test weather the forbidden test result folder under /test/resources/test_results is used anywhere in the code.
    If it is used, the test will fail.
    """
    yield
    assert not FORBIDDEN_OUTPUT_DIR.exists(), (
        f"{FORBIDDEN_OUTPUT_DIR} was created during this test run. "
        "Write outputs under src/test/test_results instead."
    )
