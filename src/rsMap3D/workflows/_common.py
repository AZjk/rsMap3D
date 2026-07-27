"""
Copyright (c) 2026, UChicago Argonne, LLC
See LICENSE file.
"""

import logging

_logging_configured = False


def configure_console_logging():
    """
    Add a console handler to the root logger the first time any workflow
    module is used, so `rsMap3D map-angle-scan`/`map-parametric-scan`/
    `powder-scan` all produce visible progress output on stdout. Guarded
    so repeated calls do not add duplicate handlers.
    """
    global _logging_configured
    if _logging_configured:
        return
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(handler)
    _logging_configured = True
