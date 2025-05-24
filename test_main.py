import pytest
from fastapi.testclient import TestClient
from main import app
from database import new_session
from repository import TaskRepository, UserRepository, ExecutorRepository

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
async def setup_database():
    from database import create_tables, delete_tables
    await create_tables()
    yield
    await delete_tables()


def test_register_user():
    response = client.post("/users/register", json={"username": "testuser", "password": "password123"})
    assert response.status_code == 200
    assert "id" in response.json()


def test_login_user():
    response = client.post("/users/login", json={"username": "testuser", "password": "password123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_get_users_and_executors():
    response = client.get("/users")
    assert response.status_code == 200
    users_data = response.json()
    assert isinstance(users_data, list)
    assert any(user["role"] == "user" for user in users_data)
    assert any(user["role"] == "executor" for user in users_data)


def test_add_task():
    task_data = {
        "name": "Test Task",
        "description": "+",
        "author_id": 1
    }

    response = client.post("/tasks", json=task_data)
    #response = client.post("/tasks", json={"name": "Test", "description": "+", "author_id": 1})
    if response.status_code != 200:
        print(response.json())
    assert response.status_code == 200
    assert "id" in response.json()


def test_update_task_name():
    response = client.put("/tasks/1/name", json={"name": "Updated Task Name"})

    assert response.status_code == 200

    response_data = response.json()
    assert "message" in response_data
    assert response_data["message"] == "Имя задачи обновлено"


def test_close_task():
    response = client.post("/tasks/1/close", json={"executor_id": 1, "score": 8})
    assert response.status_code == 200
    assert response.json() == {"message": "Задача закрыта и оценка выставлена"}


def test_assign_executor():
    response = client.put("/tasks/1/assign?executor_id=1")
    assert response.status_code == 200
    assert response.json() == {"message": "Исполнитель назначен"}


def test_assign_best_executor_greedy():
    response = client.post("/tasks/1/assign-greedy")
    assert response.status_code == 200
    assert "executor_id" in response.json()
    assert "executor_username" in response.json()


def test_create_executor():
    response = client.post("/executors", json={"username": "new_executor"})
    assert response.status_code == 200
    assert "id" in response.json()


def test_get_executors_with_tasks_and_avg_score():
    response = client.get("/executors/with-tasks")
    assert response.status_code == 200
    executors_data = response.json()
    assert isinstance(executors_data, list)
    assert all("executor_id" in executor for executor in executors_data)
    assert all("tasks" in executor for executor in executors_data)


def test_delete_user():

    token_response = client.post("/users/login", json={"username": "testuser", "password": "password123"})
    token = token_response.json()["access_token"]

    response = client.delete("/users/delete", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Пользователь удален"}
