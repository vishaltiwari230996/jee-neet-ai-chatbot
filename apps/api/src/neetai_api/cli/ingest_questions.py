"""CSV → question_bank ingestion.

Behaviour:
    * Reads the CSV from disk (deterministic — no DB roundtrips during parse).
    * Validates every row + cross-checks `maps_to` against the profile mapper.
    * Upserts in one batch via the QuestionBankRepository.
    * Re-running the same CSV is a no-op (idempotent) — safe to wire to CI.

Exit codes:
    0  ok
    1  invalid CSV (validation or parse error)
    2  unexpected runtime error (e.g. DB unreachable)

The orchestration logic (`run_ingest`) is split from the entrypoint so we
can unit-test it against the in-memory question repo.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from neetai_api.container import Container, build_container
from neetai_api.logging import configure_logging, get_logger
from neetai_api.settings import Settings, get_settings
from neetai_core.errors import DomainError, ValidationError
from neetai_ports import QuestionBankRepository
from neetai_profiling.mapper import supported_fields
from neetai_question_bank import (
    load_questions_from_csv,
    to_bank_question,
    validate_maps_to_fields,
)

log = get_logger("neetai_api.cli.ingest_questions")


@dataclass(slots=True, frozen=True)
class IngestResult:
    written: int
    file: Path


async def run_ingest(
    csv_path: Path,
    repo: QuestionBankRepository,
) -> IngestResult:
    """Pure orchestration. Tests pass an in-memory repo."""
    # One-shot CLI on a single small file; switching to anyio just for this
    # existence check would add a dependency for zero benefit.
    if not csv_path.exists():  # noqa: ASYNC240
        raise ValidationError(f"CSV file not found: {csv_path}")

    questions = load_questions_from_csv(csv_path)
    validate_maps_to_fields(questions, supported_fields=supported_fields())

    written = await repo.upsert_many([to_bank_question(q) for q in questions])
    log.info(
        "questions.ingested",
        file=str(csv_path),
        count=written,
    )
    return IngestResult(written=written, file=csv_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest_questions",
        description="Load diagnostic questions from CSV into the question bank.",
    )
    parser.add_argument(
        "csv",
        type=Path,
        help="Path to the questions CSV file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + validate the CSV without writing to the database.",
    )
    return parser


async def _amain(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings: Settings = get_settings()
    configure_logging(settings)

    csv_path: Path = args.csv.resolve()
    dry_run: bool = args.dry_run

    if dry_run:
        questions = load_questions_from_csv(csv_path)
        validate_maps_to_fields(questions, supported_fields=supported_fields())
        log.info("dry_run.ok", file=str(csv_path), count=len(questions))
        return 0

    container: Container = build_container(settings)
    try:
        result = await run_ingest(csv_path, container.questions)
    finally:
        await container.aclose()

    log.info("ingest.done", file=str(result.file), count=result.written)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Sync entrypoint suitable for setuptools console_scripts / `python -m`."""
    try:
        return asyncio.run(_amain(argv))
    except ValidationError as exc:
        logging.getLogger("neetai_api.cli.ingest_questions").error(
            "ingest.invalid_csv",
            extra={"error": str(exc)},
        )
        sys.stderr.write(f"error: {exc}\n")
        return 1
    except DomainError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    except Exception as exc:  # top-level CLI guard; report and exit cleanly
        sys.stderr.write(f"unexpected error: {exc!r}\n")
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
