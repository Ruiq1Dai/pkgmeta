"""
RPM-based distribution collectors.
"""

from .openeuler import OpenEulerCollector
from .fedora import FedoraCollector

__all__ = ["OpenEulerCollector", "FedoraCollector"]

