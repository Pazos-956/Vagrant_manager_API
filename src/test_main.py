import os
from .main import app
from fastapi.testclient import TestClient

api_key = os.getenv("API_KEY")

client = TestClient(app, client=("127.0.0.1", 50000))
unauth_client = TestClient(app)


def test_api_key_authorization():
    assert api_key
    response = client.get("/usertest/global_state", headers={"x-api-key": api_key})
    assert response.status_code == 200

    response = client.get("/usertest/global_state", headers={"x-api-key": "1234"})
    assert response.status_code == 403

    response = client.get("/usertest/global_state")
    assert response.status_code == 403

    response = unauth_client.get("/usertest/global_state", headers={"x-api-key": api_key})
    assert response.status_code == 403
