# TiendaStock - Proyecto Final

Proyecto de gestion de inventario construido con Python, Flask y SQLite.

## Requisitos

- Python 3.10 o superior
- Visual Studio Code

## Instalacion en Visual Studio Code

1. Abre la carpeta del proyecto en VS Code.
2. Abre la terminal integrada.
3. Crea el entorno virtual:

```bash
python -m venv .venv
```

4. Activa el entorno virtual:

En Windows:
```bash
.venv\Scripts\activate
```

En macOS o Linux:
```bash
source .venv/bin/activate
```

5. Instala dependencias:

```bash
pip install -r requirements.txt
```

## Ejecucion del proyecto

```bash
python app.py
```

Luego abre en el navegador:

- Index principal: http://127.0.0.1:5000/
- Frontend web: http://127.0.0.1:5000/web
- Productos: http://127.0.0.1:5000/web/productos
- Entradas y salidas: http://127.0.0.1:5000/web/movimientos
- Proveedores: http://127.0.0.1:5000/web/proveedores
- Ordenes de compra: http://127.0.0.1:5000/web/ordenes
- Reportes: http://127.0.0.1:5000/web/reportes
- Gestion de categorias: http://127.0.0.1:5000/web/categorias
- Estado JSON de la API: http://127.0.0.1:5000/api/status

## Credenciales de prueba

- Admin: admin@tiendastock.com / admin123
- Tendero: wilmer@tiendastock.com / tendero123

## Endpoints utiles

- POST /api/auth/login
- GET /api/productos
- GET /api/dashboard
- GET /api/alertas
- GET /api/proveedores
- GET /api/categorias
- POST /api/categorias
- PUT /api/categorias/<id>
- DELETE /api/categorias/<id>
- GET /api/ordenes_compra
- POST /api/ordenes_compra
- POST /api/ordenes_compra/<id>/recibir
- POST /api/ordenes_compra/<id>/cancelar
- GET /api/reportes/exportar.csv

## Pruebas

Ejecuta las pruebas automatizadas con:

```bash
pytest
```

## Proyecto Final

- Se completo el CRUD de categorias.
- Se agregaron pantallas web responsive para productos, entradas, salidas, proveedores, ordenes y reportes.
- Se implementaron ordenes de compra con recepcion automatica de stock.
- Se agregaron alertas por stock bajo y productos proximos a vencer.
- Se ampliaron reportes con filtros por fecha, tipo, categoria, proveedor y exportacion CSV.
- Se incluyeron pruebas automatizadas con pytest.
