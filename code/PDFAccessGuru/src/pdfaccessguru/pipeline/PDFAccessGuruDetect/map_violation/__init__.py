"""
Package used for the mapping between 
{@link VeraPdfViolations} and the corresponding {@link DetectedViolation} 
(including a mapping from {@link VeraPdfViolations} to {@link Violation}).

This part is not a trivial mapping because the context attribute of the {@link VeraPdfViolations} 
must be resolved to a pikePdf element that is part of the pdfs structured tag tree.
"""