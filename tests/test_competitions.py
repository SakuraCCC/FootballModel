from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Competition


def test_lists_competitions_in_code_order(client: TestClient, session: Session) -> None:
    session.add_all(
        [
            Competition(code="MLS", name="Major League Soccer", region="United States and Canada"),
            Competition(code="CSL", name="Chinese Super League", region="China"),
        ]
    )
    session.commit()

    response = client.get("/api/v1/competitions")

    assert response.status_code == 200
    assert [item["code"] for item in response.json()] == ["CSL", "MLS"]


def test_finds_competition_case_insensitively(client: TestClient, session: Session) -> None:
    session.add(Competition(code="CSL", name="Chinese Super League", region="China"))
    session.commit()

    response = client.get("/api/v1/competitions/csl")

    assert response.status_code == 200
    assert response.json()["code"] == "CSL"


def test_returns_structured_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/competitions/unknown")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "competition_not_found"
