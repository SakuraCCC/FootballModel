from fastapi.testclient import TestClient


def test_database_and_worker_health_endpoints_return_explicit_statuses(client: TestClient) -> None:
    database = client.get("/database-health")
    worker = client.get("/worker-health")

    assert database.status_code in {200, 503}
    assert database.json()["status"] in {"ok", "error"}
    assert worker.status_code in {200, 503}
    assert worker.json()["status"] in {"ok", "error"}
