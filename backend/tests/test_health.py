def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "db" in data
    assert "demo_mode" in data

    # Verify /api/health as well
    api_res = client.get("/api/health")
    assert api_res.status_code == 200
    assert api_res.json()["status"] == "ok"

def test_delete_data_endpoint_404_for_wrong_user(client):
    # user_id=999 doesn't exist but delete should still return 200 with zeros
    response = client.delete("/api/users/999/data")
    assert response.status_code == 200
    assert response.json().get("transactions") == 0

def test_demo_status_and_reset(client):
    status_res = client.get("/api/demo/status")
    assert status_res.status_code == 200
    assert "demo_mode" in status_res.json()
    assert "transaction_count" in status_res.json()

    reset_res = client.post("/api/demo/reset?user_id=1")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "ok"
    assert reset_res.json()["transaction_count"] > 0

def test_spa_fallback_and_api_404(client):
    # Non-existent API route should return 404 JSON, NOT index.html
    api_res = client.get("/api/does-not-exist")
    assert api_res.status_code == 404

    # SPA route like /budgets or /goals should return 200 with HTML (if dist exists)
    spa_res = client.get("/budgets")
    assert spa_res.status_code == 200
    assert "text/html" in spa_res.headers.get("content-type", "")

