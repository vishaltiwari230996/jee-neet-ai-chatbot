"""Admin / operational CLIs that share the API's DI container.

Living next to the API (instead of a top-level `scripts/`) buys us:
    * the same `Settings`, `Container`, adapters, repositories
    * mypy/lint/import-linter coverage for free
    * one obvious place to add new admin commands as the system grows
"""
