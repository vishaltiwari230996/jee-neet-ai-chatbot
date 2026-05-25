"""Doubt-type classification.

Phase 3 will add:
    * `rules.py`      — regex/keyword fast-paths (no LLM call when confident)
    * `llm_fallback.py` — cheap-tier LLM call when rules are below confidence threshold
    * `service.py`    — combines them, returns a typed `DoubtIntent`
"""

__version__ = "0.1.0"
