"""Tests for employee endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_employees_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/employees", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_employee(client: AsyncClient, auth_headers: dict):
    payload = {
        "employee_id": "TEST001",
        "first_name": "Test",
        "last_name": "User",
        "email": "testuser@bioattend.app",
    }
    resp = await client.post("/api/v1/employees", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["employee_id"] == "TEST001"
    assert data["email"] == "testuser@bioattend.app"
    assert data["full_name"] == "Test User"
    return data


@pytest.mark.asyncio
async def test_create_employee_duplicate(client: AsyncClient, auth_headers: dict):
    payload = {
        "employee_id": "DUP001",
        "first_name": "Dup",
        "last_name": "User",
        "email": "dup@bioattend.app",
    }
    await client.post("/api/v1/employees", json=payload, headers=auth_headers)
    resp = await client.post("/api/v1/employees", json=payload, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_employee(client: AsyncClient, auth_headers: dict):
    # Create first
    payload = {
        "employee_id": "GET001",
        "first_name": "Get",
        "last_name": "Test",
        "email": "gettest@bioattend.app",
    }
    create_resp = await client.post("/api/v1/employees", json=payload, headers=auth_headers)
    emp_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/employees/{emp_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["employee_id"] == "GET001"


@pytest.mark.asyncio
async def test_update_employee(client: AsyncClient, auth_headers: dict):
    payload = {
        "employee_id": "UPD001",
        "first_name": "Upd",
        "last_name": "Test",
        "email": "updtest@bioattend.app",
    }
    create_resp = await client.post("/api/v1/employees", json=payload, headers=auth_headers)
    emp_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/employees/{emp_id}",
        json={"designation": "Lead Engineer"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["designation"] == "Lead Engineer"


@pytest.mark.asyncio
async def test_get_nonexistent_employee(client: AsyncClient, auth_headers: dict):
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/employees/{fake_uuid}", headers=auth_headers)
    assert resp.status_code == 404
