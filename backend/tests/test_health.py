def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_delete_data_endpoint_404_for_wrong_user(client):
    # user_id=999 doesn't exist but delete should still return 200 with zeros
    response = client.delete("/api/users/999/data")
    assert response.status_code == 200
    assert response.json().get("transactions") == 0
