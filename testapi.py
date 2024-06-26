import pytest
from fastapi.testclient import TestClient
from main import app, get_db_connection, create_table, get_password_hash

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Setup: create tables and test user
    create_table()
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create a test user
    cursor.execute('INSERT INTO users (username, hashed_password, email, full_name, disabled) VALUES (?, ?, ?, ?, ?)', 
                   ("testuser", get_password_hash("testpassword"), "test@example.com", "Test User", 0))
    conn.commit()
    conn.close()
    yield
    # Teardown: clear tables
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM todos')
    cursor.execute('DELETE FROM users')
    conn.commit()
    conn.close()

def test_register_user():
    response = client.post("/register", json={
        "username": "newuser",
        "password": "newpassword",
        "email": "newuser@example.com",
        "full_name": "New User"
    })
    assert response.status_code == 200
    assert response.json() == {"username": "newuser"}

def test_register_user_duplicate_username():
    response = client.post("/register", json={
        "username": "testuser",
        "password": "anotherpassword",
        "email": "another@example.com",
        "full_name": "Another User"
    })
    assert response.status_code == 400
    assert response.json() == {"detail": "Username already registered"}

def test_login_user():
    response = client.post("/login", data={
        "username": "testuser",
        "password": "testpassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["message"] == "Login successful"

def test_create_todo_item():
    login_response = client.post("/login", data={
        "username": "testuser",
        "password": "testpassword"
    })
    access_token = login_response.json()["access_token"]
    response = client.post("/todos", json={
        "title": "Test Todo",
        "description": "Test Description"
    }, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Todo"
    assert data["description"] == "Test Description"

def test_read_todo_items():
    login_response = client.post("/login", data={
        "username": "testuser",
        "password": "testpassword"
    })
    access_token = login_response.json()["access_token"]

    # Create a test todo item
    client.post("/todos", json={
        "title": "Test Todo",
        "description": "Test Description"
    }, headers={"Authorization": f"Bearer {access_token}"})

    response = client.get("/todos", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["title"] == "Test Todo"
    assert data[0]["description"] == "Test Description"

def test_update_todo_item():
    login_response = client.post("/login", data={
        "username": "testuser",
        "password": "testpassword"
    })
    access_token = login_response.json()["access_token"]

    # Create a test todo item
    create_response = client.post("/todos", json={
        "title": "Test Todo",
        "description": "Test Description"
    }, headers={"Authorization": f"Bearer {access_token}"})
    todo_id = create_response.json()["id"]

    # Update the todo item
    update_response = client.patch(f"/todos/{todo_id}", json={
        "title": "Updated Todo",
        "description": "Updated Description"
    }, headers={"Authorization": f"Bearer {access_token}"})
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["title"] == "Updated Todo"
    assert data["description"] == "Updated Description"

def test_delete_todo_item():
    login_response = client.post("/login", data={
        "username": "testuser",
        "password": "testpassword"
    })
    access_token = login_response.json()["access_token"]

    # Create a test todo item
    create_response = client.post("/todos", json={
        "title": "Test Todo",
        "description": "Test Description"
    }, headers={"Authorization": f"Bearer {access_token}"})
    todo_id = create_response.json()["id"]

    # Delete the todo item
    delete_response = client.delete(f"/todos/{todo_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Todo item deleted successfully"}

    # Verify the item was deleted
    get_response = client.get(f"/todos/{todo_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Todo item not found"}
