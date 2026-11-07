from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.resolve_context import _parse_segments


def have_equal_segment_parsing(context1: str, context2: str) -> bool:
    """
    Compares if the iteration over two strings representing context paths is the same.
    Context paths can differ in the content of (e.g.) brackets.
    Used for comparison of context paths in context of step function related tests.
    """
    generator1 = _parse_segments(context1)
    generator2 = _parse_segments(context2)

    for segment1, segment2 in zip(generator1, generator2):
        if segment1 != segment2:
            return False
    return True