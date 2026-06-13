"""Report rendering adapters.

``markdown`` and ``html`` rendering need only Jinja2 (a light core dependency);
PDF rendering additionally needs WeasyPrint from the ``report`` extra and is
imported lazily inside :func:`render_clinician_report_pdf`.
"""

from .markdown import render_clinician_report
from .pdf import render_clinician_report_html, render_clinician_report_pdf

__all__ = [
    "render_clinician_report",
    "render_clinician_report_html",
    "render_clinician_report_pdf",
]
