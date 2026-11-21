from __future__ import annotations

from conftest import ts


def push(client, device, *changes):
    return client.post("/sync/push", json={"device_id": device, "changes": list(changes)})


def change(entity="clientes", id="c1", minutes_ago=10, **extra):
    return {"entity": entity, "id": id, "updated_at": ts(minutes_ago), "payload": '{"cifrado":"abc"}', **extra}


def test_push_and_pull_between_two_machines(client):
    response = push(client, "maquina-a", change(id="c1"), change(entity="processos", id="p1"))
    assert response.status_code == 200
    body = response.json()
    assert [item["seq"] for item in body["accepted"]] == [1, 2]
    assert body["stale"] == []
    assert body["cursor"] == 2

    pulled = client.get("/sync/changes", params={"since": 0, "device_id": "maquina-b"}).json()
    assert [(c["entity"], c["id"]) for c in pulled["changes"]] == [("clientes", "c1"), ("processos", "p1")]
    assert pulled["changes"][0]["payload"] == '{"cifrado":"abc"}'
    assert pulled["cursor"] == 2
    assert pulled["has_more"] is False

    assert client.get("/sync/changes", params={"since": 2}).json()["changes"] == []


def test_own_changes_are_skipped_but_cursor_advances(client):
    push(client, "maquina-a", change(id="c1"))
    pulled = client.get("/sync/changes", params={"since": 0, "device_id": "maquina-a"}).json()
    assert pulled["changes"] == []
    assert pulled["cursor"] == 1


def test_last_write_wins_and_stale_returns_server_version(client):
    push(client, "maquina-a", change(id="c1", minutes_ago=5, payload="novo"))
    response = push(client, "maquina-b", change(id="c1", minutes_ago=30, payload="antigo")).json()
    assert response["accepted"] == []
    assert response["stale"][0]["payload"] == "novo"
    assert response["stale"][0]["device_id"] == "maquina-a"

    newer = push(client, "maquina-b", change(id="c1", minutes_ago=1, payload="mais-novo")).json()
    assert newer["accepted"][0]["seq"] == 2
    latest = client.get("/sync/changes", params={"since": 1}).json()["changes"]
    assert latest[0]["payload"] == "mais-novo"


def test_delete_becomes_tombstone_without_payload(client):
    push(client, "maquina-a", change(entity="prazos", id="z1", minutes_ago=10, due_date="2026-12-01", done=False))
    push(client, "maquina-a", change(entity="prazos", id="z1", minutes_ago=1, deleted=True, payload="ignorado"))
    record = client.get("/sync/changes", params={"since": 1}).json()["changes"][0]
    assert record["deleted"] is True
    assert record["payload"] == ""
    assert record["due_date"] is None


def test_pagination(client):
    push(client, "maquina-a", *[change(id=f"c{i}") for i in range(5)])
    first = client.get("/sync/changes", params={"since": 0, "limit": 2}).json()
    assert len(first["changes"]) == 2 and first["has_more"] is True and first["cursor"] == 2
    rest = client.get("/sync/changes", params={"since": first["cursor"], "limit": 10}).json()
    assert len(rest["changes"]) == 3 and rest["has_more"] is False and rest["cursor"] == 5


def test_rejects_future_timestamp_without_echoing_payload(client):
    future = change(id="c1", payload="dado-sensivel")
    future["updated_at"] = "2999-01-01T00:00:00+00:00"
    response = push(client, "maquina-a", future)
    assert response.status_code == 422
    assert "dado-sensivel" not in response.text
    assert client.get("/sync/changes").json()["changes"] == []


def test_rejects_due_date_outside_prazos(client):
    assert push(client, "maquina-a", change(entity="clientes", due_date="2026-12-01")).status_code == 422


def test_rejects_unknown_entity_and_bad_ids(client):
    assert push(client, "maquina-a", change(entity="usuarios")).status_code == 422
    assert push(client, "maquina-a", change(id="../etc")).status_code == 422
    assert push(client, "maquina a", change()).status_code == 422


def test_limits(app, client):
    app.state.settings.max_push_changes = 2
    assert push(client, "m", *[change(id=f"c{i}") for i in range(3)]).status_code == 413
    big = change(payload="x" * (app.state.settings.max_payload_bytes + 1))
    assert push(client, "m", big).status_code == 422


def test_requires_token(client):
    client.headers.pop("Authorization")
    assert client.get("/sync/changes").status_code == 401
    assert client.get("/sync/changes", headers={"Authorization": "Bearer errado"}).status_code == 401
    assert push(client, "m", change()).status_code == 401
    assert client.get("/agenda").status_code == 401
