import pytest
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart import (
    correct_natural_language_actual_text_attribute_undefined,
    prompt_determine_lang_tag,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart.utils import (
    run_generic_prompt_determine_lang_tag_test,
)


def test_correct_natural_language_actual_text_attribute_undefined():
    """
    Notes for detection: 
    resolve_context is sufficient
    """
    run_generic_corrector_test(
        rule_id="7.2-21",
        test_pdf_file="veraPDF_corpus/7.2-t21-fail-a.pdf",
        corrector=correct_natural_language_actual_text_attribute_undefined,
        context=(
            "root/document[0]/StructTreeRoot[0](5 0 obj PDStructTreeRoot)/K[0]"
            "(11 0 obj SEDocument Document)/K[0](20 0 obj SEHn H1)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot")\
            .get("/K")[0].get("/K")[0],  # type: ignore
    )


def test_prompt_determine_lang_tag_english_actual_text():
    """
    Test for english actual_text
    """
    actual_text = "The sun dips below the horizon, painting the evening sky in shades of deep amber and violet. \
        Soft breezes rustle through the trees as the first faint stars begin to appear overhead. In this quiet \
            moment, the bustling world slows down and embraces the calm of the night."
    language_codes = ["en", "en-GB"]
    run_generic_prompt_determine_lang_tag_test(actual_text, language_codes, iterations=2)


def test_prompt_determine_lang_tag_german_actual_text():
    """
    Test for german actual_text
    """
    actual_text = "Die Sonne versinkt hinter dem Horizont und färbt den Abendhimmel in tiefe Bernstein- und \
        Violetttöne. Ein sanfter Wind raschelt durch die Bäume, während die ersten blassen Sterne am Himmel \
            auftauchen. In diesem stillen Moment kommt die geschäftige Welt zur Ruhe und genießt die \
                friedliche Nacht."
    language_codes = ["de"]
    run_generic_prompt_determine_lang_tag_test(actual_text, language_codes, iterations=2)

def test_prompt_determine_lang_tag_error_case_actual_text_is_empty():
    """
    Test defensive check for empty actual_text.
    """
    with pytest.raises(ValueError) as exc_info:
        prompt_determine_lang_tag("")
    assert "Provided argument actual_text is empty." in str(exc_info.value)

def test_prompt_determine_lang_tag_error_case_actual_text_is_too_long():
    """
    Test defensive check for actual_text that is too long.
    The actual_text is too long if it is longer than 800 characters.
    """
    with pytest.raises(ValueError) as exc_info:
        prompt_determine_lang_tag("a" * 801)
    assert "Provided argument actual_text is longer than 800 characters." in str(exc_info.value)
