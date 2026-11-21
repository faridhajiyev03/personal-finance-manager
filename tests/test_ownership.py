import pytest


@pytest.fixture
def owner_and_intruder(account, add_transaction):
    _, owner = account("owner@example.com")
    _, intruder = account("intruder@example.com")
    transaction = add_transaction(owner, amount="99.99", description="Private")
    return owner, intruder, transaction


@pytest.mark.parametrize(
    "method, body",
    [("get", None), ("patch", {"amount": "1.00"}), ("delete", None)],
)
def test_other_users_transaction_looks_like_it_does_not_exist(
    client, owner_and_intruder, method, body
):
    owner, intruder, transaction = owner_and_intruder
    url = f"/transactions/{transaction['id']}"

    kwargs = {"headers": intruder}
    if body is not None:
        kwargs["json"] = body
    response = getattr(client, method)(url, **kwargs)

    assert response.status_code == 404
    assert response.json() == {"detail": "Transaction not found"}
    # The owner's transaction is unchanged.
    assert client.get(url, headers=owner).json() == transaction


def test_list_and_summary_show_only_own_transactions(
    client, owner_and_intruder, add_transaction
):
    _, intruder, _ = owner_and_intruder
    add_transaction(intruder, type="income", amount="5.00", category="Gift")

    listing = client.get("/transactions", headers=intruder)
    summary = client.get("/transactions/summary", headers=intruder)

    assert [t["category"] for t in listing.json()["items"]] == ["Gift"]
    assert listing.json()["total"] == 1
    assert summary.json()["income"] == "5.00"
    assert summary.json()["expense"] == "0.00"
