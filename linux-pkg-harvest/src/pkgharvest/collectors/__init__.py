"""
Package collectors for different Linux distributions.
"""

from .rpm.openeuler import OpenEulerCollector
from .rpm.fedora import FedoraCollector

__all__ = [
    "OpenEulerCollector",
    "FedoraCollector",
]

