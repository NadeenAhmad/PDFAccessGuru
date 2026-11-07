from pathlib import Path

import pikepdf
from pikepdf import Object

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
    correct_printermark_annotation_logical_structure,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collect_supplementary_information import (
    collect_supplementary_information,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.utils import (
    assert_verapdf_violation_removed,
    build_detected_syntax_violation,
    build_verapdf_violation,
    generate_resource_path,
    generate_test_output_path,
)


def test_correct_printermark_annotation_logical_structure(tmp_path: Path):
    """
    corrector test for rule 7.18.8-1.

    The affected element is the PrinterMark annotation dictionary in the page's
    /Annots array. After correction, veraPDF should no longer report that the
    annotation is included in the logical structure.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.8-t01-fail-a.pdf")
    context_path = "root/document[0]/pages[0](7 0 obj PDPage)/annots[0](12 0 obj PDPrinterMarkAnnot)"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj.get("/Annots")[0]  # type: ignore[index]
        supplementary_information = collect_supplementary_information(
            build_verapdf_violation("7.18.8-1", context_path),
            pdf,
            affected_element,
        )
        detected_violation = build_detected_syntax_violation(
            "printermark-annotation-logical-structure",
            affected_element,
            supplementary_information,
        )

        correct_printermark_annotation_logical_structure(detected_violation, pdf)

        result_path = generate_test_output_path("7.18.8-1-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.18.8-1", context_path)
