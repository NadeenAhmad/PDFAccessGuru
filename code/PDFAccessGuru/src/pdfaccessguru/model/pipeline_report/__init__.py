"""
In-memory report for a single pipeline run.

Public types:

- :class:`ReportLevel` — severity of a report line
- :class:`ReportLine` — one leveled message
- :class:`MappingRun` — messages from one veraPDF violation mapping invocation
- :class:`CorrectionRun` — messages from one corrector invocation
- :class:`ReportPhase` — messages for one pipeline phase
- :class:`PipelineReport` — full mutable report for one pipeline execution
"""

from pdfaccessguru.model.pipeline_report.correction_run import CorrectionRun
from pdfaccessguru.model.pipeline_report.mapping_run import MappingRun
from pdfaccessguru.model.pipeline_report.phase_summary import PhaseSummary, ViolationCorrectionSummary
from pdfaccessguru.model.pipeline_report.pipeline_report import PipelineReport
from pdfaccessguru.model.pipeline_report.report_level import ReportLevel
from pdfaccessguru.model.pipeline_report.report_line import ReportLine
from pdfaccessguru.model.pipeline_report.report_phase import ReportPhase

__all__ = [
    "CorrectionRun",
    "MappingRun",
    "PhaseSummary",
    "PipelineReport",
    "ReportLevel",
    "ReportLine",
    "ReportPhase",
    "ViolationCorrectionSummary",
]
