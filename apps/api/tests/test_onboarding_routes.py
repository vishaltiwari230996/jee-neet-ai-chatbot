"""End-to-end tests for the onboarding HTTP surface.

These hit the real FastAPI app, real `OnboardingService`, real
in-memory repositories — only the LLM is faked. If wiring breaks, this
suite goes red.
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
async def test_start_onboarding_returns_first_question(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/onboarding/start",
        json={
            "student_id": "stu_alpha",
            "class_level": "dropper",
            "exam_target": "neet",
        },
    )
    assert resp.status_code == 200, resp.text

    payload = resp.json()
    assert payload["status"] == "in_progress"
    assert payload["profile"]["student_id"] == "stu_alpha"
    assert payload["profile"]["archetype"] == "unclassified"
    assert payload["next_question"]["question_id"] == "Q001"
    assert "physics" in payload["next_question"]["options"]


@pytest.mark.asyncio
async def test_start_is_idempotent_and_resumes(client: httpx.AsyncClient) -> None:
    body = {
        "student_id": "stu_resume",
        "class_level": "dropper",
        "exam_target": "neet",
    }
    first = (await client.post("/api/v1/onboarding/start", json=body)).json()
    second = (await client.post("/api/v1/onboarding/start", json=body)).json()
    # Without an answer in between, the resumed call must re-offer the same
    # question — the user shouldn't lose their place by reopening the tab.
    assert first["next_question"]["question_id"] == second["next_question"]["question_id"]


@pytest.mark.asyncio
async def test_full_onboarding_flow_completes(client: httpx.AsyncClient) -> None:
    student = "stu_full"
    start = await client.post(
        "/api/v1/onboarding/start",
        json={
            "student_id": student,
            "class_level": "dropper",
            "exam_target": "neet",
        },
    )
    state = start.json()
    answers = {
        "Q001": "physics",
        "Q002": "I forget what I revise within a week",
        "Q003": "visual",
    }

    while state["status"] == "in_progress":
        qid = state["next_question"]["question_id"]
        resp = await client.post(
            "/api/v1/onboarding/answer",
            json={
                "student_id": student,
                "question_id": qid,
                "raw_answer": answers[qid],
            },
        )
        assert resp.status_code == 200, resp.text
        state = resp.json()

    assert state["status"] == "complete"
    assert state["next_question"] is None
    assert state["profile"]["weak_subject"] == "physics"
    assert state["profile"]["learning_style"] == "visual"
    # All three critical fields were filled, so the list should be empty.
    assert state["profile"]["missing_critical_fields"] == []
    # The archetype classifier should have moved off "unclassified".
    assert state["profile"]["archetype"] != "unclassified"


@pytest.mark.asyncio
async def test_invalid_choice_returns_400(client: httpx.AsyncClient) -> None:
    student = "stu_bad"
    await client.post(
        "/api/v1/onboarding/start",
        json={
            "student_id": student,
            "class_level": "dropper",
            "exam_target": "neet",
        },
    )
    resp = await client.post(
        "/api/v1/onboarding/answer",
        json={
            "student_id": student,
            "question_id": "Q001",
            "raw_answer": "swahili",
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "validation_error"


@pytest.mark.asyncio
async def test_unknown_student_returns_404_on_answer(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/onboarding/answer",
        json={
            "student_id": "stu_ghost",
            "question_id": "Q001",
            "raw_answer": "physics",
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_state_does_not_advance_questions(client: httpx.AsyncClient) -> None:
    student = "stu_peek"
    await client.post(
        "/api/v1/onboarding/start",
        json={
            "student_id": student,
            "class_level": "dropper",
            "exam_target": "neet",
        },
    )

    first = (await client.get(f"/api/v1/onboarding/state/{student}")).json()
    second = (await client.get(f"/api/v1/onboarding/state/{student}")).json()
    assert first["next_question"]["question_id"] == second["next_question"]["question_id"]


@pytest.mark.asyncio
async def test_profile_route_returns_summary(client: httpx.AsyncClient) -> None:
    student = "stu_profile"
    await client.post(
        "/api/v1/onboarding/start",
        json={
            "student_id": student,
            "class_level": "dropper",
            "exam_target": "neet",
        },
    )
    resp = await client.get(f"/api/v1/profile/{student}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["student_id"] == student
    assert body["class_level"] == "dropper"
    assert body["weak_subject"] is None  # not yet answered


@pytest.mark.asyncio
async def test_profile_route_404_for_unknown_student(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/profile/stu_does_not_exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_extra_fields_in_request_are_rejected(client: httpx.AsyncClient) -> None:
    """`extra="forbid"` on the request schema should reject unknown fields."""
    resp = await client.post(
        "/api/v1/onboarding/start",
        json={
            "student_id": "stu_extra",
            "class_level": "dropper",
            "exam_target": "neet",
            "secretField": "oops",
        },
    )
    assert resp.status_code == 422
