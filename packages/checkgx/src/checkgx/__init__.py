"""Inspect a check registry for checks that cannot fail."""

from gxcore import ERROR, INFO, WARN, BBox, Problem, Report

from .model import Registry, load_registry

__all__ = ["ERROR", "INFO", "WARN", "BBox", "Problem", "Report", "Registry", "load_registry"]
