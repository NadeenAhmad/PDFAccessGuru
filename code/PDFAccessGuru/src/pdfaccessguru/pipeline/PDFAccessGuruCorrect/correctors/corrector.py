from typing import Callable
from pikepdf import Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation

# A CorrectionFunction takes detected violation and the overall PDF document,
# and applies the necessary modifications to correct the detected violation.

######### Goal Correction Function ############
#
# General: A correction function does correct the affected element of a 
#          given {@link DetectedViolation}.
#
# Specific: correctors have the goal (after the corrected pdf was saved into a directory) that
#           (1) a second execution of PDFAccessGuruDetect does not detect the original DetectedViolation
#               anymore.
#           (2) there wont be any new Violations detected that previously (after the first 
#               PDFAccessGuruDetect execution) were not detected.
#           
# Args: 
#   - detected_violation: DetectedViolation: is to be corrected
#   - pdf: PDF: maybe use full. It is not allowed to modify pdf by calling pdf's methods that modify it.
#   
# Returns:
#   - no returns -
#
# Raises:
#   - CouldNotCorrectDetectedViolationException: if for some expected reason the 
#   corrector was not able to correct the detected violation.
#
######### End Goal ############

CorrectionFunction = Callable[[DetectedViolation, Pdf], None]

# A mapping from violation names to their corresponding correction functions.
CORRECTOR_FUNCTIONS: dict[str, CorrectionFunction] = {}

NOT_CORRECTED_ON_PURPOSE = "Not corrected on purpose"

# Correctors that are switched off because their current implementation removes the
# veraPDF finding by damaging the document (hiding content from assistive technology,
# destroying structure, or corrupting fonts and text). The violation stays in the
# document and is reported as "not corrected on purpose" until the corrector is rewritten.
DISABLED_CORRECTORS: dict[str, str] = {
    # Tagging and structure
    # Document level
    "invalid-pdf-version":
        "would relabel a PDF 2.0 file as PDF 1.7; such a file should be checked against PDF/UA-2 instead",
    # Annotations and forms
    "form-multiple-children":
        "would drop the label and content of form fields from the structure tree (no case was found in 1,000 real web PDFs)",
    "form-xobject-mcids-multi-referenced":
        "would create copies whose content the structure tree does not refer to (6 of 1,000 real web PDFs; a proper fix tags each use of the shared drawing separately, planned with the re-tagging in Phase 6)",
    # Fonts and text
    "non-standard-cmap-embedded":
        "would replace the character map with an empty one, so all text in that font disappears (a proper fix embeds Adobe's CMap file; no case was found in 1,000 real web PDFs)",
    "referenced-glyphs-missing":
        "would replace the embedded font with a substitute, changing appearance and corrupting composite fonts (no case was found in 1,000 real web PDFs)",
}

def corrector(violation_name: str) -> Callable[[CorrectionFunction], CorrectionFunction]:
    """
    Decorator to register a correction function for a specific violation name.

    Parameters:
        violation_name: The name of the violation that this function can correct.

    Returns:
        A decorator that registers the function in the _CORRECTORS registry.
    """
    def decorator(fn: CorrectionFunction) -> CorrectionFunction:
        CORRECTOR_FUNCTIONS[violation_name] = fn
        return fn
    return decorator