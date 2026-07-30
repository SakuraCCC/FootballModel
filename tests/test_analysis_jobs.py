from fastapi.testclient import TestClient

from app.api.deps import get_analysis_job_dispatcher


def _do_not_enqueue(_job_id: str) -> None:
    return None


def test_creates_and_queries_an_analysis_job(client: TestClient) -> None:
    client.app.dependency_overrides[get_analysis_job_dispatcher] = lambda: _do_not_enqueue
    payload = {
        "competition_name": "中国超级联赛",
        "match_date": "2026-08-01",
        "matches": [{"home_team": "球队A", "away_team": "球队B"}],
        "model_version": "Sakura AI足球预测系统 V2.0",
        "poster_style": "csl",
        "watermark": "Sakura Football Model V2.0",
    }

    create_response = client.post("/api/v1/analysis-jobs", json=payload)

    assert create_response.status_code == 201
    created_job = create_response.json()
    assert created_job["status"] == "pending"
    assert created_job["current_step"] == "created"
    assert created_job["is_completed"] is False
    assert created_job["matches"] == [{"id": created_job["matches"][0]["id"], "home_team": "球队A", "away_team": "球队B"}]

    get_response = client.get(f"/api/v1/analysis-jobs/{created_job['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["batch_id"] == created_job["batch_id"]


def test_result_is_not_available_before_pipeline_completion(client: TestClient) -> None:
    client.app.dependency_overrides[get_analysis_job_dispatcher] = lambda: _do_not_enqueue
    create_response = client.post(
        "/api/v1/analysis-jobs",
        json={
            "competition_name": "中国超级联赛",
            "match_date": "2026-08-01",
            "matches": [{"home_team": "球队A", "away_team": "球队B"}],
            "model_version": "Sakura AI足球预测系统 V2.0",
            "poster_style": "csl",
            "watermark": "Sakura Football Model V2.0",
        },
    )

    response = client.get(f"/api/v1/analysis-jobs/{create_response.json()['id']}/result")

    assert response.status_code == 409
