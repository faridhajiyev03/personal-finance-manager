import pytest


def test_create_transaction(client, account):
    _, headers = account()

    response = client.post(
        "/transactions",
        json={
            "type": "income",
            "amount": "1250.50",
            "category": "  Salary  ",
            "date": "2026-11-01",
            "description": "November salary",
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "type": "income",
        "amount": "1250.50",
        "category": "Salary",
        "date": "2026-11-01",
        "description": "November salary",
        "currency": "EUR",
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"amount": "0"},
        {"amount": "-5.00"},
        {"amount": "10.999"},
        {"amount": "10000000000.00"},
        {"type": "transfer"},
        {"category": ""},
        {"date": "2026-13-01"},
        {"user_id": 2},
    ],
    ids=[
        "zero",
        "negative",
        "three-decimals",
        "too-large",
        "unknown-type",
        "empty-category",
        "invalid-date",
        "user-id-not-allowed",
    ],
)
def test_invalid_transaction_is_rejected(client, account, changes):
    _, headers = account()
    payload = {
        "type": "expense",
        "amount": "10.00",
        "category": "Food",
        "date": "2026-11-01",
        **changes,
    }

    response = client.post("/transactions", json=payload, headers=headers)

    assert response.status_code == 422


def test_get_update_and_delete_own_transaction(client, account, add_transaction):
    _, headers = account()
    created = add_transaction(headers, description="Groceries")
    url = f"/transactions/{created['id']}"

    assert client.get(url, headers=headers).json() == created

    updated = client.patch(url, json={"amount": "12.30"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["amount"] == "12.30"
    assert updated.json()["description"] == "Groceries"

    deleted = client.delete(url, headers=headers)
    assert deleted.status_code == 204
    assert client.get(url, headers=headers).status_code == 404


def test_description_can_be_cleared_with_null(client, account, add_transaction):
    _, headers = account()
    created = add_transaction(headers, description="Old note")

    response = client.patch(
        f"/transactions/{created['id']}",
        json={"description": None},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["description"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"amount": None},
        {"type": None},
        {"category": None},
        {"date": None},
        {"amount": "-1.00"},
        {"user_id": 2},
    ],
)
def test_invalid_update_is_rejected(client, account, add_transaction, payload):
    _, headers = account()
    created = add_transaction(headers)

    response = client.patch(
        f"/transactions/{created['id']}", json=payload, headers=headers
    )

    assert response.status_code == 422


def test_missing_transaction_returns_404(client, account):
    _, headers = account()

    response = client.get("/transactions/999", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Transaction not found"}


def test_list_is_sorted_newest_first(client, account, add_transaction):
    _, headers = account()
    add_transaction(headers, category="Old", date="2026-10-01")
    add_transaction(headers, category="New", date="2026-11-15")
    add_transaction(headers, category="Middle", date="2026-11-01")

    response = client.get("/transactions", headers=headers)

    assert response.status_code == 200
    assert [t["category"] for t in response.json()["items"]] == ["New", "Middle", "Old"]


def test_list_filters(client, account, add_transaction):
    _, headers = account()
    add_transaction(headers, type="income", category="Salary", date="2026-11-01")
    add_transaction(headers, type="expense", category="Food", date="2026-11-10")
    add_transaction(headers, type="expense", category="Rent", date="2026-11-20")
    add_transaction(headers, type="expense", category="Food", date="2026-12-05")

    def categories(**params):
        response = client.get("/transactions", params=params, headers=headers)
        assert response.status_code == 200, response.text
        return sorted(t["category"] for t in response.json()["items"])

    assert categories(type="income") == ["Salary"]
    assert categories(category="Food") == ["Food", "Food"]
    # Date boundaries are inclusive.
    assert categories(date_from="2026-11-10", date_to="2026-11-20") == ["Food", "Rent"]


def test_pagination(client, account, add_transaction):
    _, headers = account()
    for day in range(1, 6):
        add_transaction(headers, category=f"Day {day}", date=f"2026-11-0{day}")

    response = client.get(
        "/transactions", params={"limit": 2, "offset": 1}, headers=headers
    )

    body = response.json()
    assert [t["category"] for t in body["items"]] == ["Day 4", "Day 3"]
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 1


def test_total_counts_only_matching_transactions(client, account, add_transaction):
    _, headers = account()
    add_transaction(headers, category="Food")
    add_transaction(headers, category="Food")
    add_transaction(headers, category="Rent")

    response = client.get(
        "/transactions", params={"category": "Food", "limit": 1}, headers=headers
    )

    assert len(response.json()["items"]) == 1
    assert response.json()["total"] == 2


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"type": "transfer"},
        {"date_from": "2026-12-01", "date_to": "2026-11-01"},
    ],
)
def test_invalid_list_parameters_are_rejected(client, account, params):
    _, headers = account()

    response = client.get("/transactions", params=params, headers=headers)

    assert response.status_code == 422


def test_summary(client, account, add_transaction):
    _, headers = account()
    add_transaction(headers, type="income", amount="2000.00", date="2026-11-01")
    add_transaction(headers, type="expense", amount="750.25", date="2026-11-03")
    add_transaction(headers, type="expense", amount="49.75", date="2026-11-30")
    add_transaction(headers, type="income", amount="100.00", date="2026-12-01")

    november = client.get(
        "/transactions/summary",
        params={"date_from": "2026-11-01", "date_to": "2026-11-30"},
        headers=headers,
    )

    assert november.status_code == 200
    assert november.json() == {
        "income": "2000.00",
        "expense": "800.00",
        "balance": "1200.00",
        "currency": "EUR",
    }


def test_summary_without_transactions_is_zero(client, account):
    _, headers = account()

    response = client.get("/transactions/summary", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "income": "0.00",
        "expense": "0.00",
        "balance": "0.00",
        "currency": "EUR",
    }


def test_transaction_endpoints_require_a_token(client):
    assert client.get("/transactions").status_code == 401
    assert client.get("/transactions/summary").status_code == 401
    assert client.post("/transactions", json={}).status_code == 401
