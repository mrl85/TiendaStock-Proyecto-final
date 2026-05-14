import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from app import app, db, seed_datos


@pytest.fixture()
def client(tmp_path):
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path/'tiendastock_test.db'}",
        JWT_SECRET_KEY="test-secret-key-for-tiendastock-2026-very-long",
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_datos()

    with app.test_client() as client:
        yield client


def get_admin_token(client):
    response = client.post(
        "/api/auth/login",
        json={"correo": "admin@tiendastock.com", "password": "admin123"},
    )
    assert response.status_code == 200
    return response.get_json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_admin_returns_token(client):
    response = client.post(
        "/api/auth/login",
        json={"correo": "admin@tiendastock.com", "password": "admin123"},
    )
    data = response.get_json()
    assert response.status_code == 200
    assert "access_token" in data
    assert data["usuario"]["rol"] == "admin"


def test_create_category_as_admin(client):
    token = get_admin_token(client)
    response = client.post(
        "/api/categorias",
        json={"nombre": "Limpieza hogar", "descripcion": "Categoria de aseo"},
        headers=auth_headers(token),
    )
    data = response.get_json()
    assert response.status_code == 201
    assert data["categoria"]["nombre"] == "Limpieza hogar"


def test_update_and_delete_category_flow(client):
    token = get_admin_token(client)
    created = client.post(
        "/api/categorias",
        json={"nombre": "Huevos", "descripcion": "Categoria temporal"},
        headers=auth_headers(token),
    )
    cat_id = created.get_json()["categoria"]["id"]

    updated = client.put(
        f"/api/categorias/{cat_id}",
        json={"nombre": "Huevos frescos", "descripcion": "Actualizada"},
        headers=auth_headers(token),
    )
    assert updated.status_code == 200
    assert updated.get_json()["categoria"]["nombre"] == "Huevos frescos"

    deleted = client.delete(
        f"/api/categorias/{cat_id}",
        headers=auth_headers(token),
    )
    assert deleted.status_code == 200


def test_category_delete_is_blocked_when_products_exist(client):
    token = get_admin_token(client)
    response = client.delete(
        "/api/categorias/1",
        headers=auth_headers(token),
    )
    assert response.status_code == 409


def test_dashboard_reports_completed_sprint4(client):
    token = get_admin_token(client)
    response = client.get("/api/dashboard", headers=auth_headers(token))
    data = response.get_json()
    assert response.status_code == 200
    assert data["sprint_avance"] == "100%"
    assert "productos_por_vencer" in data


def test_purchase_order_flow_updates_stock(client):
    token = get_admin_token(client)
    productos_before = client.get("/api/productos", headers=auth_headers(token)).get_json()["productos"]
    producto = productos_before[0]

    created = client.post(
        "/api/ordenes_compra",
        json={
            "id_proveedor": 1,
            "detalles": [
                {
                    "id_producto": producto["id"],
                    "cantidad": 5,
                    "precio_unitario": producto["precio_compra"],
                }
            ],
        },
        headers=auth_headers(token),
    )
    assert created.status_code == 201
    orden_id = created.get_json()["orden"]["id"]

    received = client.post(
        f"/api/ordenes_compra/{orden_id}/recibir",
        headers=auth_headers(token),
    )
    assert received.status_code == 200
    assert received.get_json()["orden"]["estado"] == "recibida"

    productos_after = client.get("/api/productos", headers=auth_headers(token)).get_json()["productos"]
    actualizado = next(p for p in productos_after if p["id"] == producto["id"])
    assert actualizado["stock_actual"] == producto["stock_actual"] + 5


def test_web_pages_render(client):
    for path in ["/web", "/web/productos", "/web/movimientos", "/web/proveedores", "/web/ordenes", "/web/reportes"]:
        response = client.get(path)
        assert response.status_code == 200
