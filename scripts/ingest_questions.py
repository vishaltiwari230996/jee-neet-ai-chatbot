#!/usr/bin/env python3
"""Thin launcher around `neetai_api.cli.ingest_questions`.

Why this exists:
    Operators expect a top-level `scripts/` to find admin tools quickly.
    Real logic lives in the `neetai_api.cli` module so it's testable and
    sits inside the same DI graph as the API process.
"""

from __future__ import annotations

import sys

from neetai_api.cli.ingest_questions import main

if __name__ == "__main__":
    sys.exit(main())
