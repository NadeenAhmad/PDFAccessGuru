"""
Package containing the logic to detect the affected element 
in the PDF document for a given veraPDF violation (which contains the context path).

This package contains the default way be resolving the context path provided by veraPDF 
(Traversing the step function), but it also provides the possibility to implement alternative 
ways to resolve the context path for specific violations.
"""