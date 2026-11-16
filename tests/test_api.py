"""API contract and business-rule tests."""


def add_product(client, *, sku="APL001", name="Apples", stock=10, price="2.50", reorder=3):
    return client.post(
        "/products",
        json={
            "sku": sku,
            "name": name,
            "price": price,
            "stock": stock,
            "reorder_level": reorder,
        },
    )


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_product(client):
    response = add_product(client)
    assert response.status_code == 201
    item = response.json()
    assert item["sku"] == "APL001"
    assert item["price"] == "2.50"
    assert client.get(f"/products/{item['id']}").json() == item


def test_duplicate_sku_returns_conflict(client):
    assert add_product(client).status_code == 201
    assert add_product(client).status_code == 409


def test_invalid_price_rejected(client):
    assert add_product(client, price="0").status_code == 422
    assert add_product(client, price="-1.00").status_code == 422
    assert add_product(client, price="1.234").status_code == 422


def test_negative_initial_stock_rejected(client):
    assert add_product(client, stock=-1).status_code == 422


def test_blank_name_rejected(client):
    assert add_product(client, name="   ").status_code == 422


def test_invalid_sku_rejected(client):
    assert add_product(client, sku="bad sku").status_code == 422


def test_missing_product_returns_404(client):
    assert client.get("/products/999").status_code == 404
    assert client.patch("/products/999/stock", json={"change": 2}).status_code == 404


def test_search_products(client):
    add_product(client)
    add_product(client, sku="BAN002", name="Bananas")
    results = client.get("/products?search=APPLE").json()
    assert [p["name"] for p in results] == ["Apples"]


def test_low_stock_filter(client):
    add_product(client, stock=2)
    add_product(client, sku="BAN002", name="Bananas", stock=7)
    assert [p["sku"] for p in client.get("/products?low_stock=true").json()] == ["APL001"]


def test_restock_product(client):
    item_id = add_product(client).json()["id"]
    response = client.patch(f"/products/{item_id}/stock", json={"change": 5})
    assert response.status_code == 200
    assert response.json()["stock"] == 15


def test_cannot_remove_more_than_stock(client):
    item_id = add_product(client, stock=2).json()["id"]
    response = client.patch(f"/products/{item_id}/stock", json={"change": -3})
    assert response.status_code == 409
    assert client.get(f"/products/{item_id}").json()["stock"] == 2


def test_zero_stock_change_rejected(client):
    item_id = add_product(client).json()["id"]
    assert client.patch(f"/products/{item_id}/stock", json={"change": 0}).status_code == 422


def test_create_order_updates_stock_and_total(client):
    apples = add_product(client).json()
    bananas = add_product(client, sku="BAN002", name="Bananas", price="1.20").json()
    order_response = client.post(
        "/orders",
        json={"items": [{"product_id": apples["id"], "quantity": 3},
                        {"product_id": bananas["id"], "quantity": 2}]},
    )
    assert order_response.status_code == 201
    order = order_response.json()
    assert order["total"] == "9.90"
    assert len(order["items"]) == 2
    assert order["items"][0]["line_total"] == "7.50"
    assert client.get(f"/products/{apples['id']}").json()["stock"] == 7
    assert client.get(f"/products/{bananas['id']}").json()["stock"] == 8
    assert client.get(f"/orders/{order['id']}").json() == order


def test_order_insufficient_stock_is_atomic(client):
    apples = add_product(client, stock=10).json()
    bananas = add_product(client, sku="BAN002", name="Bananas", stock=1).json()
    response = client.post(
        "/orders",
        json={"items": [{"product_id": apples["id"], "quantity": 3},
                        {"product_id": bananas["id"], "quantity": 2}]},
    )
    assert response.status_code == 409
    assert client.get(f"/products/{apples['id']}").json()["stock"] == 10
    assert client.get("/metrics/inventory").json()["orders"] == 0


def test_order_missing_product_is_atomic(client):
    apples = add_product(client, stock=10).json()
    response = client.post(
        "/orders",
        json={"items": [{"product_id": apples["id"], "quantity": 3},
                        {"product_id": 999, "quantity": 1}]},
    )
    assert response.status_code == 404
    assert client.get(f"/products/{apples['id']}").json()["stock"] == 10


def test_duplicate_product_in_order_rejected(client):
    apples = add_product(client).json()
    response = client.post(
        "/orders",
        json={"items": [{"product_id": apples["id"], "quantity": 1},
                        {"product_id": apples["id"], "quantity": 1}]},
    )
    assert response.status_code == 422


def test_empty_order_rejected(client):
    assert client.post("/orders", json={"items": []}).status_code == 422


def test_negative_order_quantity_rejected(client):
    apples = add_product(client).json()
    response = client.post(
        "/orders", json={"items": [{"product_id": apples["id"], "quantity": -1}]}
    )
    assert response.status_code == 422


def test_order_not_found(client):
    assert client.get("/orders/999").status_code == 404


def test_inventory_metrics(client):
    add_product(client, stock=2, reorder=3)
    add_product(client, sku="BAN002", name="Bananas", stock=8, reorder=3)
    result = client.get("/metrics/inventory").json()
    assert result == {"products": 2, "low_stock_products": 1, "units_in_stock": 10, "orders": 0}


def test_product_list_empty_initially(client):
    assert client.get("/products").json() == []
