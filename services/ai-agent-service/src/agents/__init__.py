#services/ai-agent-service/src/agents/__init__.py
"""
AI Agents Package for Legal Case Management

This package contains specialized AI agents for different legal tasks:
- EvidenceAgent: Document analysis and evidence search
- SummaryAgent: Case summarization and overview
- DraftAgent: Legal document drafting assistance
- GeneralAgent: General legal guidance and advice
"""

__version__ = "1.0.0"
__author__ = "Legal AI Team"

from .evidence_agent import EvidenceAgent
from .summary_agent import SummaryAgent
from .draft_agent import DraftAgent
from .general_agent import GeneralAgent

__all__ = [
    'EvidenceAgent',
    'SummaryAgent', 
    'DraftAgent',
    'GeneralAgent'
]