"""Shared fixtures for API tests.

Builds an isolated FastAPI app per test with deterministic settings so
suites don't bleed config (e.g., LLM provider) into each other. Uses the
in-memory DB backend and seeds the question bank — every test gets a
clean, fully-functional app.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from neetai_api.container import Container
from neetai_api.main import create_app
from neetai_api.settings import (
    AppEnv,
    DatabaseBackend,
    LLMProvider,
    LogFormat,
    Settings,
)
from neetai_core.ids import QuestionId
from neetai_core.types import ClassLevel, ExamTarget
from neetai_ports import BankQuestion
from neetai_question_bank.models import AnswerType, QuestionCategory


def _seed_questions() -> list[BankQuestion]:
    """A small but realistic seed: one question per critical profile field.

    Covers the same shape as the production CSV so tests exercise the same
    selector + mapper code paths.
    """
    return [
        BankQuestion(
            question_id=QuestionId("Q001"),
            text="Which subject feels hardest right now?",
            category=QuestionCategory.ACADEMIC_DIAGNOSIS.value,
            exam_targets=[target.value for target in ExamTarget],
            audience=[ClassLevel.DROPPER.value, ClassLevel.CLASS_12.value],
            answer_type=AnswerType.SINGLE_CHOICE.value,
            options=["physics", "chemistry", "biology", "math"],
            maps_to="weak_subject",
            priority=90,
            is_required=True,
        ),
        BankQuestion(
            question_id=QuestionId("Q002"),
            text="What's the single biggest thing slowing you down?",
            category=QuestionCategory.BEHAVIOUR.value,
            exam_targets=[target.value for target in ExamTarget],
            audience=[ClassLevel.DROPPER.value, ClassLevel.CLASS_12.value],
            answer_type=AnswerType.SHORT_TEXT.value,
            options=[],
            maps_to="main_problem",
            priority=80,
            is_required=True,
        ),
        BankQuestion(
            question_id=QuestionId("Q003"),
            text="How do you learn best?",
            category=QuestionCategory.LEARNING_STYLE.value,
            exam_targets=[target.value for target in ExamTarget],
            audience=[ClassLevel.DROPPER.value, ClassLevel.CLASS_12.value],
            answer_type=AnswerType.SINGLE_CHOICE.value,
            options=["visual", "auditory", "kinesthetic", "reading_writing"],
            maps_to="learning_style",
            priority=70,
            is_required=True,
        ),
    ]


@pytest_asyncio.fixture
async def app() -> AsyncIterator[FastAPI]:
    settings = Settings(
        env=AppEnv.LOCAL,
        llm_provider=LLMProvider.FAKE,
        database_backend=DatabaseBackend.MEMORY,
        log_format=LogFormat.TEXT,
    )
    application = create_app(settings)
    async with LifespanManager(application):
        # Seed the in-memory question bank now that the container is live.
        container: Container = application.state.container
        await container.questions.upsert_many(_seed_questions())
        yield application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
