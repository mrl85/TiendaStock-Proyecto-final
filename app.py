"""
╔══════════════════════════════════════════════════════════════════╗
║   TiendaStock – Sprint 3                                         ║
║   Código 1: Aplicación Principal — Ejecutable al 100% de avance ║
║                                                                  ║
║   Autores: Sebastian Gil Samaca (137663)                         ║
║            Wilmer Alejandro Londoño Martinez (138397)            ║
║   Materia: Electiva I – Universidad ECCI – 2026                  ║
╚══════════════════════════════════════════════════════════════════╝

INSTRUCCIONES DE EJECUCIÓN:
  1. pip install flask flask-sqlalchemy flask-jwt-extended
  2. python 1_app_principal_ejecutable.py
  3. Abrir en navegador: http://127.0.0.1:5000
  4. Usar Postman o curl para probar los endpoints

CREDENCIALES DE PRUEBA:
  Admin : correo=admin@tiendastock.com  / password=admin123
  Tienda: correo=wilmer@tiendastock.com / password=tendero123

ENDPOINTS OPERATIVOS (Sprint 3 – 100% avance):
  POST   /api/auth/login
  GET    /api/productos          (con filtros: search, categoria, estado)
  POST   /api/productos
  PUT    /api/productos/<id>
  DELETE /api/productos/<id>     ← NUEVO Sprint 3
  POST   /api/entradas
  POST   /api/salidas
  GET    /api/dashboard          ← NUEVO Sprint 3
  GET    /api/alertas            ← NUEVO Sprint 3
  GET    /api/proveedores        ← NUEVO Sprint 3
  POST   /api/proveedores        ← NUEVO Sprint 3
  PUT    /api/proveedores/<id>   ← NUEVO Sprint 3
  POST   /api/usuarios           ← NUEVO Sprint 3
  GET    /api/reportes           ← NUEVO Sprint 3
"""

import csv
import hashlib
import io
from datetime import date, timedelta, datetime

from flask import Flask, request, jsonify, render_template, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity, get_jwt
)

# ── Inicialización ────────────────────────────────────────────────
app = Flask(__name__)

# SQLite para ejecución inmediata (sin instalar PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI']      = 'sqlite:///tiendastock_sprint4.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY']               = 'tiendastock-dev-secret-2026'
app.config['JWT_ACCESS_TOKEN_EXPIRES']     = timedelta(hours=8)

db  = SQLAlchemy(app)
jwt = JWTManager(app)


def parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(value, '%Y-%m-%d').date()


def pesos(value):
    return '${:,.0f}'.format(value or 0).replace(',', '.')


# ══════════════════════════════════════════════════════════════════
# MODELOS DE BASE DE DATOS
# ══════════════════════════════════════════════════════════════════

class CategoriaModel(db.Model):
    __tablename__ = 'categorias'

    id_categoria = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(80), nullable=False)
    descripcion  = db.Column(db.String(200))
    productos    = db.relationship('ProductoModel', backref='categoria', lazy=True)

    def to_dict(self):
        return {'id': self.id_categoria, 'nombre': self.nombre,
                'descripcion': self.descripcion}


class ProveedorModel(db.Model):
    __tablename__ = 'proveedores'

    id_proveedor = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(120), nullable=False)
    nit          = db.Column(db.String(20), unique=True, nullable=False)
    telefono     = db.Column(db.String(20))
    correo       = db.Column(db.String(120))
    ciudad       = db.Column(db.String(80))
    activo       = db.Column(db.Boolean, default=True)
    ordenes      = db.relationship('OrdenCompraModel', backref='proveedor', lazy=True)

    def to_dict(self):
        return {
            'id':       self.id_proveedor,
            'nombre':   self.nombre,
            'nit':      self.nit,
            'telefono': self.telefono,
            'correo':   self.correo,
            'ciudad':   self.ciudad,
            'activo':   self.activo,
        }


class UsuarioModel(db.Model):
    __tablename__ = 'usuarios'

    id_usuario     = db.Column(db.Integer, primary_key=True)
    nombre         = db.Column(db.String(100), nullable=False)
    correo         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash  = db.Column(db.String(256), nullable=False)
    rol            = db.Column(db.String(20), default='tendero')
    activo         = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.Date, default=date.today)

    def set_password(self, password: str):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password: str) -> bool:
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

    def to_dict(self):
        return {
            'id': self.id_usuario, 'nombre': self.nombre,
            'correo': self.correo, 'rol': self.rol, 'activo': self.activo,
        }


class ProductoModel(db.Model):
    __tablename__ = 'productos'

    id_producto       = db.Column(db.Integer, primary_key=True)
    nombre            = db.Column(db.String(150), nullable=False)
    id_categoria      = db.Column(db.Integer, db.ForeignKey('categorias.id_categoria'), nullable=False)
    id_proveedor      = db.Column(db.Integer, db.ForeignKey('proveedores.id_proveedor'), nullable=True)
    unidad_medida     = db.Column(db.String(30), default='unidad')
    precio_compra     = db.Column(db.Float, nullable=False)
    precio_venta      = db.Column(db.Float, nullable=False)
    stock_actual      = db.Column(db.Integer, default=0)
    stock_minimo      = db.Column(db.Integer, default=5)
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    activo            = db.Column(db.Boolean, default=True)
    movimientos       = db.relationship('MovimientoModel', backref='producto', lazy=True)
    proveedor         = db.relationship('ProveedorModel')

    def estado_stock(self) -> str:
        if self.stock_actual == 0:
            return 'sin_stock'
        if self.stock_actual <= self.stock_minimo:
            return 'critico'
        if self.stock_actual <= self.stock_minimo * 1.5:
            return 'bajo'
        return 'normal'

    def to_dict(self):
        return {
            'id':                self.id_producto,
            'nombre':            self.nombre,
            'id_categoria':      self.id_categoria,
            'categoria':         self.categoria.nombre if self.categoria else None,
            'id_proveedor':      self.id_proveedor,
            'proveedor':         self.proveedor.nombre if self.proveedor else None,
            'unidad_medida':     self.unidad_medida,
            'precio_compra':     self.precio_compra,
            'precio_venta':      self.precio_venta,
            'stock_actual':      self.stock_actual,
            'stock_minimo':      self.stock_minimo,
            'fecha_vencimiento': str(self.fecha_vencimiento) if self.fecha_vencimiento else None,
            'estado_stock':      self.estado_stock(),
            'activo':            self.activo,
        }


class MovimientoModel(db.Model):
    __tablename__ = 'movimientos_inventario'

    id_movimiento  = db.Column(db.Integer, primary_key=True)
    id_producto    = db.Column(db.Integer, db.ForeignKey('productos.id_producto'), nullable=False)
    tipo           = db.Column(db.String(10), nullable=False)   # 'entrada' | 'salida'
    cantidad       = db.Column(db.Integer, nullable=False)
    precio_unidad  = db.Column(db.Float, nullable=False)
    total          = db.Column(db.Float, nullable=False)
    motivo         = db.Column(db.String(200))
    fecha          = db.Column(db.DateTime, default=datetime.utcnow)
    id_usuario     = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=True)

    def to_dict(self):
        return {
            'id':           self.id_movimiento,
            'id_producto':  self.id_producto,
            'tipo':         self.tipo,
            'cantidad':     self.cantidad,
            'precio_unidad': self.precio_unidad,
            'total':        self.total,
            'motivo':       self.motivo,
            'fecha':        self.fecha.isoformat() if self.fecha else None,
        }


class OrdenCompraModel(db.Model):
    __tablename__ = 'ordenes_compra'

    id_orden     = db.Column(db.Integer, primary_key=True)
    fecha        = db.Column(db.Date, default=date.today)
    total        = db.Column(db.Float, default=0)
    estado       = db.Column(db.String(20), default='pendiente')
    observacion  = db.Column(db.String(200))
    id_proveedor = db.Column(db.Integer, db.ForeignKey('proveedores.id_proveedor'), nullable=False)
    detalles     = db.relationship(
        'DetalleOrdenModel',
        backref='orden',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def recalcular_total(self):
        self.total = sum(d.subtotal for d in self.detalles)

    def to_dict(self, incluir_detalles=True):
        data = {
            'id': self.id_orden,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'total': round(self.total or 0, 2),
            'estado': self.estado,
            'observacion': self.observacion,
            'id_proveedor': self.id_proveedor,
            'proveedor': self.proveedor.nombre if self.proveedor else None,
        }
        if incluir_detalles:
            data['detalles'] = [d.to_dict() for d in self.detalles]
        return data


class DetalleOrdenModel(db.Model):
    __tablename__ = 'detalles_orden'

    id_detalle      = db.Column(db.Integer, primary_key=True)
    id_orden        = db.Column(db.Integer, db.ForeignKey('ordenes_compra.id_orden'), nullable=False)
    id_producto     = db.Column(db.Integer, db.ForeignKey('productos.id_producto'), nullable=False)
    cantidad        = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal        = db.Column(db.Float, nullable=False)
    producto        = db.relationship('ProductoModel')

    def to_dict(self):
        return {
            'id': self.id_detalle,
            'id_producto': self.id_producto,
            'producto': self.producto.nombre if self.producto else None,
            'cantidad': self.cantidad,
            'precio_unitario': round(self.precio_unitario, 2),
            'subtotal': round(self.subtotal, 2),
        }


# ══════════════════════════════════════════════════════════════════
# SEED: DATOS INICIALES DE PRUEBA
# ══════════════════════════════════════════════════════════════════

def seed_datos():
    """Carga datos de prueba si la BD está vacía."""
    if UsuarioModel.query.first():
        return

    # Usuarios
    admin = UsuarioModel(nombre='Administrador TiendaStock',
                         correo='admin@tiendastock.com', rol='admin')
    admin.set_password('admin123')

    tendero = UsuarioModel(nombre='Wilmer Londoño',
                           correo='wilmer@tiendastock.com', rol='tendero')
    tendero.set_password('tendero123')

    db.session.add_all([admin, tendero])

    # Categorías
    cats = [
        CategoriaModel(nombre='Abarrotes',   descripcion='Productos no perecederos'),
        CategoriaModel(nombre='Lácteos',      descripcion='Derivados de leche'),
        CategoriaModel(nombre='Bebidas',      descripcion='Líquidos y jugos'),
        CategoriaModel(nombre='Aseo',         descripcion='Productos de limpieza'),
        CategoriaModel(nombre='Snacks',       descripcion='Paquetes y dulces'),
    ]
    db.session.add_all(cats)
    db.session.flush()

    # Proveedores
    provs = [
        ProveedorModel(nombre='Distribuidora Alimentos SA', nit='900123456-1',
                       telefono='3001234567', correo='ventas@disalimentos.com', ciudad='Bogotá'),
        ProveedorModel(nombre='Lácteos del Valle',          nit='800987654-2',
                       telefono='3117654321', correo='pedidos@lacteosvalle.com', ciudad='Cali'),
        ProveedorModel(nombre='Bebidas Premium SAS',        nit='901456789-3',
                       telefono='3209876543', correo='info@bebidaspremium.com', ciudad='Medellín'),
    ]
    db.session.add_all(provs)
    db.session.flush()

    # Productos
    productos = [
        ProductoModel(nombre='Arroz Roa x 5kg', id_categoria=cats[0].id_categoria,
                      id_proveedor=provs[0].id_proveedor, unidad_medida='bulto',
                      precio_compra=18500, precio_venta=22000, stock_actual=42, stock_minimo=10),
        ProductoModel(nombre='Aceite Girasol 1L', id_categoria=cats[0].id_categoria,
                      id_proveedor=provs[0].id_proveedor,
                      precio_compra=9800, precio_venta=12500, stock_actual=3, stock_minimo=8),
        ProductoModel(nombre='Leche Entera 1L', id_categoria=cats[1].id_categoria,
                      id_proveedor=provs[1].id_proveedor,
                      precio_compra=2800, precio_venta=3500, stock_actual=25, stock_minimo=15,
                      fecha_vencimiento=date.today() + timedelta(days=6)),
        ProductoModel(nombre='Queso Doble Crema x500g', id_categoria=cats[1].id_categoria,
                      id_proveedor=provs[1].id_proveedor,
                      precio_compra=11200, precio_venta=14000, stock_actual=0, stock_minimo=5,
                      fecha_vencimiento=date.today() + timedelta(days=3)),
        ProductoModel(nombre='Gaseosa Cola 1.5L', id_categoria=cats[2].id_categoria,
                      id_proveedor=provs[2].id_proveedor,
                      precio_compra=3200, precio_venta=4500, stock_actual=60, stock_minimo=20),
        ProductoModel(nombre='Jabón Rey x3', id_categoria=cats[3].id_categoria,
                      id_proveedor=provs[0].id_proveedor,
                      precio_compra=4500, precio_venta=6200, stock_actual=18, stock_minimo=10),
        ProductoModel(nombre='Papas Margarita Sal', id_categoria=cats[4].id_categoria,
                      id_proveedor=provs[0].id_proveedor,
                      precio_compra=1800, precio_venta=2500, stock_actual=4, stock_minimo=12),
        ProductoModel(nombre='Azúcar Manuelita 1kg', id_categoria=cats[0].id_categoria,
                      id_proveedor=provs[0].id_proveedor,
                      precio_compra=3900, precio_venta=4800, stock_actual=30, stock_minimo=10),
    ]
    db.session.add_all(productos)
    db.session.flush()

    # Movimientos de ejemplo
    movs = [
        MovimientoModel(id_producto=productos[0].id_producto, tipo='entrada',
                        cantidad=50, precio_unidad=18500, total=925000,
                        motivo='Compra inicial Sprint 3'),
        MovimientoModel(id_producto=productos[0].id_producto, tipo='salida',
                        cantidad=8, precio_unidad=22000, total=176000,
                        motivo='Venta mostrador'),
        MovimientoModel(id_producto=productos[2].id_producto, tipo='entrada',
                        cantidad=30, precio_unidad=2800, total=84000,
                        motivo='Pedido semanal'),
        MovimientoModel(id_producto=productos[4].id_producto, tipo='salida',
                        cantidad=10, precio_unidad=4500, total=45000,
                        motivo='Venta al por mayor'),
    ]
    db.session.add_all(movs)
    orden = OrdenCompraModel(
        id_proveedor=provs[0].id_proveedor,
        fecha=date.today(),
        estado='pendiente',
        observacion='Pedido sugerido por stock bajo'
    )
    orden.detalles = [
        DetalleOrdenModel(
            id_producto=productos[1].id_producto,
            cantidad=24,
            precio_unitario=productos[1].precio_compra,
            subtotal=24 * productos[1].precio_compra,
        ),
        DetalleOrdenModel(
            id_producto=productos[6].id_producto,
            cantidad=36,
            precio_unitario=productos[6].precio_compra,
            subtotal=36 * productos[6].precio_compra,
        ),
    ]
    orden.recalcular_total()
    db.session.add(orden)
    db.session.commit()
    print("✅  Datos semilla cargados correctamente.")


# ══════════════════════════════════════════════════════════════════
# ENDPOINTS – AUTENTICACIÓN
# ══════════════════════════════════════════════════════════════════

@app.route('/api/auth/login', methods=['POST'])
def login():
    """POST /api/auth/login — Genera token JWT."""
    data = request.get_json()
    if not data or not data.get('correo') or not data.get('password'):
        return jsonify({'error': 'correo y password son requeridos'}), 400

    usuario = UsuarioModel.query.filter_by(correo=data['correo'], activo=True).first()
    if not usuario or not usuario.check_password(data['password']):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    token = create_access_token(
        identity=str(usuario.id_usuario),
        additional_claims={'rol': usuario.rol, 'nombre': usuario.nombre}
    )
    return jsonify({'access_token': token, 'token_type': 'Bearer',
                    'usuario': usuario.to_dict()}), 200


# ══════════════════════════════════════════════════════════════════
# ENDPOINTS – PRODUCTOS (CRUD COMPLETO)
# ══════════════════════════════════════════════════════════════════

@app.route('/api/productos', methods=['GET'])
@jwt_required()
def listar_productos():
    """GET /api/productos?search=&categoria=&estado="""
    search = request.args.get('search', '')
    id_cat = request.args.get('categoria', type=int)
    estado = request.args.get('estado', '')

    query = ProductoModel.query.filter_by(activo=True)
    if search:
        query = query.filter(ProductoModel.nombre.ilike(f'%{search}%'))
    if id_cat:
        query = query.filter_by(id_categoria=id_cat)

    productos = query.all()
    if estado == 'critico':
        productos = [p for p in productos if p.estado_stock() in ('critico', 'sin_stock')]
    elif estado == 'bajo':
        productos = [p for p in productos if p.estado_stock() in ('critico', 'bajo', 'sin_stock')]

    return jsonify({'total': len(productos), 'productos': [p.to_dict() for p in productos]}), 200


@app.route('/api/productos', methods=['POST'])
@jwt_required()
def crear_producto():
    """POST /api/productos — Crea un producto nuevo."""
    data = request.get_json()
    requeridos = ('nombre', 'id_categoria', 'precio_compra', 'precio_venta')
    if not data or not all(k in data for k in requeridos):
        return jsonify({'error': f'Campos requeridos: {", ".join(requeridos)}'}), 400

    p = ProductoModel(
        nombre=data['nombre'], id_categoria=data['id_categoria'],
        id_proveedor=data.get('id_proveedor'),
        unidad_medida=data.get('unidad_medida', 'unidad'),
        precio_compra=data['precio_compra'], precio_venta=data['precio_venta'],
        stock_actual=data.get('stock_actual', 0),
        stock_minimo=data.get('stock_minimo', 5),
        fecha_vencimiento=parse_date(data.get('fecha_vencimiento')),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'mensaje': 'Producto creado', 'producto': p.to_dict()}), 201


@app.route('/api/productos/<int:id_p>', methods=['PUT'])
@jwt_required()
def actualizar_producto(id_p):
    """PUT /api/productos/<id> — Actualiza campos de un producto."""
    p = ProductoModel.query.get_or_404(id_p)
    data = request.get_json()
    campos = ('nombre', 'id_categoria', 'id_proveedor', 'unidad_medida',
              'precio_compra', 'precio_venta', 'stock_minimo', 'fecha_vencimiento')
    for campo in campos:
        if campo in data:
            setattr(p, campo, parse_date(data[campo]) if campo == 'fecha_vencimiento' else data[campo])
    db.session.commit()
    return jsonify({'mensaje': 'Producto actualizado', 'producto': p.to_dict()}), 200


@app.route('/api/productos/<int:id_p>', methods=['DELETE'])
@jwt_required()
def eliminar_producto(id_p):
    """DELETE /api/productos/<id> — Baja lógica (activo=False). NUEVO Sprint 3."""
    claims = get_jwt()
    if claims.get('rol') != 'admin':
        return jsonify({'error': 'Solo administradores pueden eliminar productos'}), 403
    p = ProductoModel.query.get_or_404(id_p)
    p.activo = False
    db.session.commit()
    return jsonify({'mensaje': f'Producto "{p.nombre}" desactivado correctamente'}), 200


# ══════════════════════════════════════════════════════════════════
# ENDPOINTS – MOVIMIENTOS (ENTRADAS / SALIDAS)
# ══════════════════════════════════════════════════════════════════

@app.route('/api/entradas', methods=['POST'])
@jwt_required()
def registrar_entrada():
    """POST /api/entradas — Incrementa stock."""
    data = request.get_json()
    if not data or not all(k in data for k in ('id_producto', 'cantidad', 'precio_unidad')):
        return jsonify({'error': 'id_producto, cantidad y precio_unidad son requeridos'}), 400

    p = ProductoModel.query.get_or_404(data['id_producto'])
    cantidad = int(data['cantidad'])
    if cantidad <= 0:
        return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400

    p.stock_actual += cantidad
    mov = MovimientoModel(
        id_producto=p.id_producto, tipo='entrada', cantidad=cantidad,
        precio_unidad=data['precio_unidad'],
        total=cantidad * data['precio_unidad'],
        motivo=data.get('motivo', 'Entrada de mercancía'),
        id_usuario=int(get_jwt_identity())
    )
    db.session.add(mov)
    db.session.commit()
    return jsonify({'mensaje': 'Entrada registrada',
                    'stock_actualizado': p.stock_actual,
                    'movimiento': mov.to_dict()}), 201


@app.route('/api/salidas', methods=['POST'])
@jwt_required()
def registrar_salida():
    """POST /api/salidas — Decrementa stock validando disponibilidad."""
    data = request.get_json()
    if not data or not all(k in data for k in ('id_producto', 'cantidad', 'precio_unidad')):
        return jsonify({'error': 'id_producto, cantidad y precio_unidad son requeridos'}), 400

    p = ProductoModel.query.get_or_404(data['id_producto'])
    cantidad = int(data['cantidad'])
    if cantidad <= 0:
        return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
    if p.stock_actual < cantidad:
        return jsonify({'error': f'Stock insuficiente. Disponible: {p.stock_actual}'}), 409

    p.stock_actual -= cantidad
    mov = MovimientoModel(
        id_producto=p.id_producto, tipo='salida', cantidad=cantidad,
        precio_unidad=data['precio_unidad'],
        total=cantidad * data['precio_unidad'],
        motivo=data.get('motivo', 'Venta'),
        id_usuario=int(get_jwt_identity())
    )
    db.session.add(mov)
    db.session.commit()
    return jsonify({'mensaje': 'Salida registrada',
                    'stock_actualizado': p.stock_actual,
                    'movimiento': mov.to_dict()}), 201


# ══════════════════════════════════════════════════════════════════
# ENDPOINTS – DASHBOARD  ← NUEVO Sprint 3
# ══════════════════════════════════════════════════════════════════

@app.route('/api/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    """
    GET /api/dashboard
    Retorna métricas generales del inventario para el panel de control.
    NUEVO en Sprint 3.
    """
    total_productos  = ProductoModel.query.filter_by(activo=True).count()
    total_categorias = CategoriaModel.query.count()
    total_proveedores = ProveedorModel.query.filter_by(activo=True).count()

    productos_activos = ProductoModel.query.filter_by(activo=True).all()
    sin_stock = [p for p in productos_activos if p.estado_stock() == 'sin_stock']
    criticos  = [p for p in productos_activos if p.estado_stock() == 'critico']
    bajos     = [p for p in productos_activos if p.estado_stock() == 'bajo']
    normales  = [p for p in productos_activos if p.estado_stock() == 'normal']
    por_vencer = [
        p for p in productos_activos
        if p.fecha_vencimiento and p.fecha_vencimiento <= date.today() + timedelta(days=7)
    ]

    # Valor total del inventario
    valor_inventario = sum(p.stock_actual * p.precio_venta for p in productos_activos)

    # Últimos 5 movimientos
    ultimos_movimientos = (
        MovimientoModel.query
        .order_by(MovimientoModel.fecha.desc())
        .limit(5).all()
    )

    return jsonify({
        'resumen': {
            'total_productos':    total_productos,
            'total_categorias':   total_categorias,
            'total_proveedores':  total_proveedores,
            'valor_inventario':   round(valor_inventario, 2),
            'ordenes_pendientes':  OrdenCompraModel.query.filter_by(estado='pendiente').count(),
        },
        'estado_stock': {
            'sin_stock': len(sin_stock),
            'critico':   len(criticos),
            'bajo':      len(bajos),
            'normal':    len(normales),
        },
        'alertas_activas': len(sin_stock) + len(criticos) + len(por_vencer),
        'productos_por_vencer': [p.to_dict() for p in por_vencer],
        'ultimos_movimientos': [m.to_dict() for m in ultimos_movimientos],
        'sprint_avance': '100%',
    }), 200


# ══════════════════════════════════════════════════════════════════
# ENDPOINTS – ALERTAS  ← NUEVO Sprint 3
# ══════════════════════════════════════════════════════════════════

@app.route('/api/alertas', methods=['GET'])
@jwt_required()
def listar_alertas():
    """
    GET /api/alertas
    Lista productos con stock crítico o sin stock para generar alertas.
    NUEVO en Sprint 3.
    """
    productos_activos = ProductoModel.query.filter_by(activo=True).all()
    alertas = []

    for p in productos_activos:
        estado = p.estado_stock()
        if estado in ('sin_stock', 'critico', 'bajo'):
            nivel = 'ALTO' if estado in ('sin_stock', 'critico') else 'MEDIO'
            alertas.append({
                'id_producto':   p.id_producto,
                'nombre':        p.nombre,
                'stock_actual':  p.stock_actual,
                'stock_minimo':  p.stock_minimo,
                'estado':        estado,
                'nivel_alerta':  nivel,
                'mensaje':       (
                    f'Producto SIN STOCK. Reabastecer urgente.'
                    if estado == 'sin_stock'
                    else f'Stock bajo el mínimo ({p.stock_actual}/{p.stock_minimo} unidades).'
                ),
                'categoria':     p.categoria.nombre if p.categoria else None,
            })
        if p.fecha_vencimiento and p.fecha_vencimiento <= date.today() + timedelta(days=7):
            dias = (p.fecha_vencimiento - date.today()).days
            alertas.append({
                'id_producto': p.id_producto,
                'nombre': p.nombre,
                'stock_actual': p.stock_actual,
                'stock_minimo': p.stock_minimo,
                'estado': 'por_vencer',
                'nivel_alerta': 'ALTO' if dias <= 3 else 'MEDIO',
                'mensaje': f'Producto vence en {dias} dias. Revisar rotacion o promocion.',
                'categoria': p.categoria.nombre if p.categoria else None,
                'fecha_vencimiento': p.fecha_vencimiento.isoformat(),
            })

    # Ordena por nivel: ALTO primero
    alertas.sort(key=lambda x: 0 if x['nivel_alerta'] == 'ALTO' else 1)

    return jsonify({
        'total_alertas': len(alertas),
        'alertas':       alertas,
    }), 200


# ══════════════════════════════════════════════════════════════════
# ENDPOINTS – PROVEEDORES (CRUD)  ← NUEVO Sprint 3
# ══════════════════════════════════════════════════════════════════

@app.route('/api/proveedores', methods=['GET'])
@jwt_required()
def listar_proveedores():
    """GET /api/proveedores — Lista todos los proveedores activos."""
    provs = ProveedorModel.query.filter_by(activo=True).all()
    return jsonify({'total': len(provs), 'proveedores': [p.to_dict() for p in provs]}), 200


@app.route('/api/proveedores', methods=['POST'])
@jwt_required()
def crear_proveedor():
    """POST /api/proveedores — Registra un proveedor nuevo."""
    data = request.get_json()
    if not data or not all(k in data for k in ('nombre', 'nit')):
        return jsonify({'error': 'nombre y nit son requeridos'}), 400

    if ProveedorModel.query.filter_by(nit=data['nit']).first():
        return jsonify({'error': 'Ya existe un proveedor con ese NIT'}), 409

    prov = ProveedorModel(
        nombre=data['nombre'],  nit=data['nit'],
        telefono=data.get('telefono'), correo=data.get('correo'),
        ciudad=data.get('ciudad'),
    )
    db.session.add(prov)
    db.session.commit()
    return jsonify({'mensaje': 'Proveedor creado', 'proveedor': prov.to_dict()}), 201


@app.route('/api/proveedores/<int:id_prov>', methods=['PUT'])
@jwt_required()
def actualizar_proveedor(id_prov):
    """PUT /api/proveedores/<id> — Actualiza datos del proveedor."""
    prov = ProveedorModel.query.get_or_404(id_prov)
    data = request.get_json()
    for campo in ('nombre', 'telefono', 'correo', 'ciudad'):
        if campo in data:
            setattr(prov, campo, data[campo])
    db.session.commit()
    return jsonify({'mensaje': 'Proveedor actualizado', 'proveedor': prov.to_dict()}), 200


# ══════════════════════════════════════════════════════════════════
# ENDPOINTS – USUARIOS  ← NUEVO Sprint 3
# ══════════════════════════════════════════════════════════════════

@app.route('/api/usuarios', methods=['POST'])
@jwt_required()
def crear_usuario():
    """
    POST /api/usuarios — Crea un usuario nuevo (solo admins).
    NUEVO en Sprint 3.
    """
    claims = get_jwt()
    if claims.get('rol') != 'admin':
        return jsonify({'error': 'Solo administradores pueden crear usuarios'}), 403

    data = request.get_json()
    requeridos = ('nombre', 'correo', 'password')
    if not data or not all(k in data for k in requeridos):
        return jsonify({'error': f'Campos requeridos: {", ".join(requeridos)}'}), 400

    if UsuarioModel.query.filter_by(correo=data['correo']).first():
        return jsonify({'error': 'El correo ya está registrado'}), 409

    u = UsuarioModel(nombre=data['nombre'], correo=data['correo'],
                     rol=data.get('rol', 'tendero'))
    u.set_password(data['password'])
    db.session.add(u)
    db.session.commit()
    return jsonify({'mensaje': 'Usuario creado', 'usuario': u.to_dict()}), 201


# ══════════════════════════════════════════════════════════════════
# ENDPOINTS – REPORTES  ← NUEVO Sprint 3
# ══════════════════════════════════════════════════════════════════

@app.route('/api/reportes', methods=['GET'])
@jwt_required()
def reportes():
    """
    GET /api/reportes
    Genera un reporte de movimientos de inventario.
    NUEVO en Sprint 3 — base para el módulo completo en Sprint 4.
    """
    tipo = request.args.get('tipo', 'todos')
    limite = request.args.get('limite', 100, type=int)
    movimientos = construir_reporte_movimientos(request.args).limit(limite).all()

    total_entradas = sum(m.total for m in movimientos if m.tipo == 'entrada')
    total_salidas  = sum(m.total for m in movimientos if m.tipo == 'salida')
    por_producto = {}
    for m in movimientos:
        nombre = m.producto.nombre if m.producto else 'Sin producto'
        por_producto.setdefault(nombre, {'producto': nombre, 'entradas': 0, 'salidas': 0, 'cantidad': 0})
        por_producto[nombre][m.tipo + 's'] += m.total
        por_producto[nombre]['cantidad'] += m.cantidad

    top_productos = sorted(
        por_producto.values(),
        key=lambda item: item['cantidad'],
        reverse=True
    )[:10]

    return jsonify({
        'tipo_reporte':    tipo,
        'total_registros': len(movimientos),
        'resumen': {
            'total_entradas': round(total_entradas, 2),
            'total_salidas':  round(total_salidas,  2),
            'balance':        round(total_entradas - total_salidas, 2),
        },
        'top_productos': top_productos,
        'movimientos': [m.to_dict() for m in movimientos],
    }), 200


@app.route('/api/reportes/exportar.csv', methods=['GET'])
@jwt_required()
def exportar_reporte_csv():
    movimientos = construir_reporte_movimientos(request.args).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['fecha', 'tipo', 'producto', 'categoria', 'cantidad', 'precio_unidad', 'total', 'motivo'])
    for m in movimientos:
        writer.writerow([
            m.fecha.strftime('%Y-%m-%d %H:%M'),
            m.tipo,
            m.producto.nombre if m.producto else '',
            m.producto.categoria.nombre if m.producto and m.producto.categoria else '',
            m.cantidad,
            m.precio_unidad,
            m.total,
            m.motivo or '',
        ])
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=tiendastock_reporte.csv'}
    )


def construir_reporte_movimientos(args):
    query = MovimientoModel.query.join(ProductoModel).order_by(MovimientoModel.fecha.desc())
    tipo = args.get('tipo', 'todos')
    if tipo in ('entrada', 'salida'):
        query = query.filter(MovimientoModel.tipo == tipo)
    if args.get('producto'):
        query = query.filter(MovimientoModel.id_producto == args.get('producto', type=int))
    if args.get('categoria'):
        query = query.filter(ProductoModel.id_categoria == args.get('categoria', type=int))
    if args.get('proveedor'):
        query = query.filter(ProductoModel.id_proveedor == args.get('proveedor', type=int))
    if args.get('desde'):
        query = query.filter(MovimientoModel.fecha >= datetime.combine(parse_date(args.get('desde')), datetime.min.time()))
    if args.get('hasta'):
        query = query.filter(MovimientoModel.fecha <= datetime.combine(parse_date(args.get('hasta')), datetime.max.time()))
    return query


@app.route('/api/ordenes_compra', methods=['GET'])
@jwt_required()
def listar_ordenes_compra():
    estado = request.args.get('estado')
    query = OrdenCompraModel.query.order_by(OrdenCompraModel.fecha.desc(), OrdenCompraModel.id_orden.desc())
    if estado:
        query = query.filter_by(estado=estado)
    ordenes = query.all()
    return jsonify({'total': len(ordenes), 'ordenes': [o.to_dict() for o in ordenes]}), 200


@app.route('/api/ordenes_compra', methods=['POST'])
@jwt_required()
def crear_orden_compra():
    data = request.get_json() or {}
    detalles_data = data.get('detalles') or []
    if not data.get('id_proveedor') or not detalles_data:
        return jsonify({'error': 'id_proveedor y detalles son requeridos'}), 400

    proveedor = ProveedorModel.query.get_or_404(data['id_proveedor'])
    orden = OrdenCompraModel(
        id_proveedor=proveedor.id_proveedor,
        fecha=parse_date(data.get('fecha')) or date.today(),
        estado=data.get('estado', 'pendiente'),
        observacion=data.get('observacion'),
    )
    for item in detalles_data:
        producto = ProductoModel.query.get_or_404(item.get('id_producto'))
        cantidad = int(item.get('cantidad', 0))
        precio = float(item.get('precio_unitario', producto.precio_compra))
        if cantidad <= 0:
            return jsonify({'error': 'La cantidad de cada detalle debe ser mayor a 0'}), 400
        orden.detalles.append(DetalleOrdenModel(
            id_producto=producto.id_producto,
            cantidad=cantidad,
            precio_unitario=precio,
            subtotal=cantidad * precio,
        ))
    orden.recalcular_total()
    db.session.add(orden)
    db.session.commit()
    return jsonify({'mensaje': 'Orden de compra creada', 'orden': orden.to_dict()}), 201


@app.route('/api/ordenes_compra/<int:id_orden>/recibir', methods=['POST'])
@jwt_required()
def recibir_orden_compra(id_orden):
    orden = OrdenCompraModel.query.get_or_404(id_orden)
    if orden.estado == 'recibida':
        return jsonify({'error': 'La orden ya fue recibida'}), 409
    if orden.estado == 'cancelada':
        return jsonify({'error': 'No se puede recibir una orden cancelada'}), 409

    usuario_id = int(get_jwt_identity())
    for detalle in orden.detalles:
        detalle.producto.stock_actual += detalle.cantidad
        db.session.add(MovimientoModel(
            id_producto=detalle.id_producto,
            tipo='entrada',
            cantidad=detalle.cantidad,
            precio_unidad=detalle.precio_unitario,
            total=detalle.subtotal,
            motivo=f'Recepcion orden de compra #{orden.id_orden}',
            id_usuario=usuario_id,
        ))
    orden.estado = 'recibida'
    db.session.commit()
    return jsonify({'mensaje': 'Orden recibida y stock actualizado', 'orden': orden.to_dict()}), 200


@app.route('/api/ordenes_compra/<int:id_orden>/cancelar', methods=['POST'])
@jwt_required()
def cancelar_orden_compra(id_orden):
    orden = OrdenCompraModel.query.get_or_404(id_orden)
    if orden.estado == 'recibida':
        return jsonify({'error': 'No se puede cancelar una orden ya recibida'}), 409
    orden.estado = 'cancelada'
    db.session.commit()
    return jsonify({'mensaje': 'Orden cancelada', 'orden': orden.to_dict()}), 200


# ══════════════════════════════════════════════════════════════════
# RUTA RAÍZ — Estado general de la API
# ══════════════════════════════════════════════════════════════════

@app.route('/api/status')
def api_status():
    return jsonify({
        'api':      'TiendaStock API REST',
        'version':  '1.0 (Sprint 4)',
        'avance':   '100% del proyecto completado',
        'status':   'running',
        'stack':    'Python 3.11 · Flask 3.0 · SQLAlchemy 2.0 · SQLite (dev)',
        'credenciales_prueba': {
            'admin':   {'correo': 'admin@tiendastock.com',  'password': 'admin123'},
            'tendero': {'correo': 'wilmer@tiendastock.com', 'password': 'tendero123'},
        },
        'endpoints_operativos': [
            'POST   /api/auth/login',
            'GET    /api/productos          (filtros: search, categoria, estado)',
            'POST   /api/productos',
            'PUT    /api/productos/<id>',
            'DELETE /api/productos/<id>     ← NUEVO',
            'POST   /api/entradas',
            'POST   /api/salidas',
            'GET    /api/dashboard          ← NUEVO',
            'GET    /api/alertas            ← NUEVO',
            'GET    /api/proveedores        ← NUEVO',
            'POST   /api/proveedores        ← NUEVO',
            'PUT    /api/proveedores/<id>   ← NUEVO',
            'POST   /api/usuarios           ← NUEVO',
            'GET    /api/reportes           ← NUEVO',
        ],
        'modulos_sprint4': [
            'GET    /api/categorias (CRUD)',
            'GET    /api/ordenes_compra',
            'POST   /api/ordenes_compra',
            'POST   /api/ordenes_compra/<id>/recibir',
            'POST   /api/ordenes_compra/<id>/cancelar',
            'GET    /api/reportes/exportar.csv',
            'Frontend web (HTML + Bootstrap)',
            'Alertas por stock bajo y vencimiento',
            'Tests automatizados (pytest)',
            'Dockerización del proyecto',
        ],
    }), 200


# ══════════════════════════════════════════════════════════════════
# SPRINT 4 - CATEGORÍAS + FRONTEND WEB
# ══════════════════════════════════════════════════════════════════

@app.route('/api/categorias', methods=['GET'])
def listar_categorias():
    """GET /api/categorias — Lista categorías registradas."""
    categorias = CategoriaModel.query.order_by(CategoriaModel.nombre.asc()).all()
    return jsonify({
        'total': len(categorias),
        'categorias': [c.to_dict() for c in categorias]
    }), 200


@app.route('/api/categorias', methods=['POST'])
@jwt_required()
def crear_categoria():
    """POST /api/categorias — Crea una categoría nueva (solo admin)."""
    claims = get_jwt()
    if claims.get('rol') != 'admin':
        return jsonify({'error': 'Solo administradores pueden crear categorías'}), 403

    data = request.get_json() or {}
    nombre = (data.get('nombre') or '').strip()
    descripcion = (data.get('descripcion') or '').strip()

    if not nombre:
        return jsonify({'error': 'El nombre de la categoría es requerido'}), 400

    if CategoriaModel.query.filter_by(nombre=nombre).first():
        return jsonify({'error': 'Ya existe una categoría con ese nombre'}), 409

    categoria = CategoriaModel(nombre=nombre, descripcion=descripcion)
    db.session.add(categoria)
    db.session.commit()
    return jsonify({'mensaje': 'Categoría creada', 'categoria': categoria.to_dict()}), 201


@app.route('/api/categorias/<int:id_cat>', methods=['PUT'])
@jwt_required()
def actualizar_categoria(id_cat):
    """PUT /api/categorias/<id> — Actualiza nombre y descripción."""
    claims = get_jwt()
    if claims.get('rol') != 'admin':
        return jsonify({'error': 'Solo administradores pueden modificar categorías'}), 403

    categoria = CategoriaModel.query.get_or_404(id_cat)
    data = request.get_json() or {}

    if 'nombre' in data:
        nuevo_nombre = (data.get('nombre') or '').strip()
        if not nuevo_nombre:
            return jsonify({'error': 'El nombre no puede estar vacío'}), 400
        existente = CategoriaModel.query.filter_by(nombre=nuevo_nombre).first()
        if existente and existente.id_categoria != categoria.id_categoria:
            return jsonify({'error': 'Ya existe una categoría con ese nombre'}), 409
        categoria.nombre = nuevo_nombre

    if 'descripcion' in data:
        categoria.descripcion = (data.get('descripcion') or '').strip()

    db.session.commit()
    return jsonify({'mensaje': 'Categoría actualizada', 'categoria': categoria.to_dict()}), 200


@app.route('/api/categorias/<int:id_cat>', methods=['DELETE'])
@jwt_required()
def eliminar_categoria(id_cat):
    """DELETE /api/categorias/<id> — Elimina una categoría sin productos asociados."""
    claims = get_jwt()
    if claims.get('rol') != 'admin':
        return jsonify({'error': 'Solo administradores pueden eliminar categorías'}), 403

    categoria = CategoriaModel.query.get_or_404(id_cat)

    if categoria.productos:
        return jsonify({
            'error': 'No se puede eliminar la categoría porque tiene productos asociados'
        }), 409

    db.session.delete(categoria)
    db.session.commit()
    return jsonify({'mensaje': 'Categoría eliminada correctamente'}), 200


@app.route('/')
def index():
    """Index principal para abrir la pagina completa en el navegador."""
    return web_dashboard()


@app.route('/web')
def web_dashboard():
    """Vista web simple con Bootstrap para revisar el inventario."""
    productos_activos = ProductoModel.query.filter_by(activo=True).all()
    hoy = datetime.combine(date.today(), datetime.min.time())
    resumen = {
        'productos': ProductoModel.query.filter_by(activo=True).count(),
        'categorias': CategoriaModel.query.count(),
        'proveedores': ProveedorModel.query.filter_by(activo=True).count(),
        'usuarios': UsuarioModel.query.filter_by(activo=True).count(),
        'movimientos': MovimientoModel.query.count(),
        'movimientos_hoy': MovimientoModel.query.filter(MovimientoModel.fecha >= hoy).count(),
        'valor_inventario': pesos(sum(p.stock_actual * p.precio_venta for p in productos_activos)),
        'alertas_stock': len([p for p in productos_activos if p.estado_stock() in ('sin_stock', 'critico', 'bajo')]),
    }
    categorias = CategoriaModel.query.order_by(CategoriaModel.nombre.asc()).all()
    productos = ProductoModel.query.filter_by(activo=True).order_by(ProductoModel.nombre.asc()).limit(8).all()
    movimientos = MovimientoModel.query.order_by(MovimientoModel.fecha.desc()).limit(6).all()
    alertas = []
    for p in productos_activos:
        estado = p.estado_stock()
        if estado in ('sin_stock', 'critico', 'bajo'):
            alertas.append({
                'nombre': p.nombre,
                'estado': estado,
                'stock_actual': p.stock_actual,
                'stock_minimo': p.stock_minimo,
                'mensaje': f'Stock actual {p.stock_actual}; minimo sugerido {p.stock_minimo}.',
            })
        if p.fecha_vencimiento and p.fecha_vencimiento <= date.today() + timedelta(days=7):
            dias = (p.fecha_vencimiento - date.today()).days
            alertas.append({
                'nombre': p.nombre,
                'estado': 'por_vencer',
                'mensaje': f'Vence en {dias} dias. Conviene rotarlo pronto.',
            })
    return render_template(
        'index.html',
        resumen=resumen,
        categorias=categorias,
        productos=productos,
        movimientos=movimientos,
        alertas=alertas[:5],
        pesos=pesos,
    )


@app.route('/web/categorias')
def web_categorias():
    categorias = CategoriaModel.query.order_by(CategoriaModel.id_categoria.desc()).all()
    return render_template('categorias.html', categorias=categorias)


@app.route('/web/categorias', methods=['POST'])
def web_crear_categoria():
    nombre = (request.form.get('nombre') or '').strip()
    descripcion = (request.form.get('descripcion') or '').strip()

    if nombre and not CategoriaModel.query.filter_by(nombre=nombre).first():
        db.session.add(CategoriaModel(nombre=nombre, descripcion=descripcion))
        db.session.commit()

    return redirect(url_for('web_categorias'))


@app.route('/web/categorias/<int:id_cat>/eliminar', methods=['POST'])
def web_eliminar_categoria(id_cat):
    categoria = CategoriaModel.query.get_or_404(id_cat)
    if categoria.productos:
        return redirect(url_for('web_categorias'))
    db.session.delete(categoria)
    db.session.commit()
    return redirect(url_for('web_categorias'))


@app.route('/web/productos')
def web_productos():
    search = request.args.get('search', '')
    categoria = request.args.get('categoria', type=int)
    query = ProductoModel.query.filter_by(activo=True)
    if search:
        query = query.filter(ProductoModel.nombre.ilike(f'%{search}%'))
    if categoria:
        query = query.filter_by(id_categoria=categoria)
    return render_template(
        'productos.html',
        productos=query.order_by(ProductoModel.nombre.asc()).all(),
        categorias=CategoriaModel.query.order_by(CategoriaModel.nombre.asc()).all(),
        proveedores=ProveedorModel.query.filter_by(activo=True).order_by(ProveedorModel.nombre.asc()).all(),
        pesos=pesos,
    )


@app.route('/web/productos', methods=['POST'])
def web_crear_producto():
    data = request.form
    producto = ProductoModel(
        nombre=data.get('nombre'),
        id_categoria=int(data.get('id_categoria')),
        id_proveedor=int(data.get('id_proveedor')) if data.get('id_proveedor') else None,
        unidad_medida=data.get('unidad_medida') or 'unidad',
        precio_compra=float(data.get('precio_compra') or 0),
        precio_venta=float(data.get('precio_venta') or 0),
        stock_actual=int(data.get('stock_actual') or 0),
        stock_minimo=int(data.get('stock_minimo') or 5),
        fecha_vencimiento=parse_date(data.get('fecha_vencimiento')),
    )
    db.session.add(producto)
    db.session.commit()
    return redirect(url_for('web_productos'))


@app.route('/web/productos/<int:id_producto>/eliminar', methods=['POST'])
def web_eliminar_producto(id_producto):
    producto = ProductoModel.query.get_or_404(id_producto)
    producto.activo = False
    db.session.commit()
    return redirect(url_for('web_productos'))


@app.route('/web/movimientos')
def web_movimientos():
    return render_template(
        'movimientos.html',
        tipo=request.args.get('tipo', 'entrada'),
        productos=ProductoModel.query.filter_by(activo=True).order_by(ProductoModel.nombre.asc()).all(),
        movimientos=MovimientoModel.query.order_by(MovimientoModel.fecha.desc()).limit(20).all(),
        pesos=pesos,
    )


@app.route('/web/movimientos', methods=['POST'])
def web_crear_movimiento():
    producto = ProductoModel.query.get_or_404(int(request.form.get('id_producto')))
    tipo = request.form.get('tipo')
    cantidad = int(request.form.get('cantidad') or 0)
    precio = float(request.form.get('precio_unidad') or 0)
    if cantidad > 0 and tipo in ('entrada', 'salida'):
        if tipo == 'entrada':
            producto.stock_actual += cantidad
        elif producto.stock_actual >= cantidad:
            producto.stock_actual -= cantidad
        else:
            return redirect(url_for('web_movimientos', tipo='salida'))
        db.session.add(MovimientoModel(
            id_producto=producto.id_producto,
            tipo=tipo,
            cantidad=cantidad,
            precio_unidad=precio,
            total=cantidad * precio,
            motivo=request.form.get('motivo') or ('Entrada de mercancia' if tipo == 'entrada' else 'Venta'),
            id_usuario=1,
        ))
        db.session.commit()
    return redirect(url_for('web_movimientos', tipo=tipo))


@app.route('/web/proveedores')
def web_proveedores():
    return render_template(
        'proveedores.html',
        proveedores=ProveedorModel.query.filter_by(activo=True).order_by(ProveedorModel.nombre.asc()).all(),
    )


@app.route('/web/proveedores', methods=['POST'])
def web_crear_proveedor():
    db.session.add(ProveedorModel(
        nombre=request.form.get('nombre'),
        nit=request.form.get('nit'),
        telefono=request.form.get('telefono'),
        correo=request.form.get('correo'),
        ciudad=request.form.get('ciudad'),
    ))
    db.session.commit()
    return redirect(url_for('web_proveedores'))


@app.route('/web/ordenes')
def web_ordenes():
    return render_template(
        'ordenes.html',
        ordenes=OrdenCompraModel.query.order_by(OrdenCompraModel.fecha.desc(), OrdenCompraModel.id_orden.desc()).all(),
        proveedores=ProveedorModel.query.filter_by(activo=True).order_by(ProveedorModel.nombre.asc()).all(),
        productos=ProductoModel.query.filter_by(activo=True).order_by(ProductoModel.nombre.asc()).all(),
        pesos=pesos,
    )


@app.route('/web/ordenes', methods=['POST'])
def web_crear_orden():
    producto = ProductoModel.query.get_or_404(int(request.form.get('id_producto')))
    cantidad = int(request.form.get('cantidad') or 0)
    precio = float(request.form.get('precio_unitario') or producto.precio_compra)
    if cantidad > 0:
        orden = OrdenCompraModel(
            id_proveedor=int(request.form.get('id_proveedor')),
            fecha=date.today(),
            estado='pendiente',
            observacion=request.form.get('observacion'),
        )
        orden.detalles.append(DetalleOrdenModel(
            id_producto=producto.id_producto,
            cantidad=cantidad,
            precio_unitario=precio,
            subtotal=cantidad * precio,
        ))
        orden.recalcular_total()
        db.session.add(orden)
        db.session.commit()
    return redirect(url_for('web_ordenes'))


@app.route('/web/ordenes/<int:id_orden>/recibir', methods=['POST'])
def web_recibir_orden(id_orden):
    orden = OrdenCompraModel.query.get_or_404(id_orden)
    if orden.estado == 'pendiente':
        for detalle in orden.detalles:
            detalle.producto.stock_actual += detalle.cantidad
            db.session.add(MovimientoModel(
                id_producto=detalle.id_producto,
                tipo='entrada',
                cantidad=detalle.cantidad,
                precio_unidad=detalle.precio_unitario,
                total=detalle.subtotal,
                motivo=f'Recepcion orden de compra #{orden.id_orden}',
                id_usuario=1,
            ))
        orden.estado = 'recibida'
        db.session.commit()
    return redirect(url_for('web_ordenes'))


@app.route('/web/reportes')
def web_reportes():
    movimientos = construir_reporte_movimientos(request.args).limit(100).all()
    total_entradas = sum(m.total for m in movimientos if m.tipo == 'entrada')
    total_salidas = sum(m.total for m in movimientos if m.tipo == 'salida')
    return render_template(
        'reportes.html',
        movimientos=movimientos,
        categorias=CategoriaModel.query.order_by(CategoriaModel.nombre.asc()).all(),
        productos=ProductoModel.query.filter_by(activo=True).order_by(ProductoModel.nombre.asc()).all(),
        proveedores=ProveedorModel.query.filter_by(activo=True).order_by(ProveedorModel.nombre.asc()).all(),
        resumen={'entradas': total_entradas, 'salidas': total_salidas, 'balance': total_entradas - total_salidas},
        pesos=pesos,
    )


@app.route('/web/reportes/exportar.csv')
def web_exportar_reporte_csv():
    movimientos = construir_reporte_movimientos(request.args).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['fecha', 'tipo', 'producto', 'categoria', 'cantidad', 'precio_unidad', 'total', 'motivo'])
    for m in movimientos:
        writer.writerow([
            m.fecha.strftime('%Y-%m-%d %H:%M'), m.tipo,
            m.producto.nombre if m.producto else '',
            m.producto.categoria.nombre if m.producto and m.producto.categoria else '',
            m.cantidad, m.precio_unidad, m.total, m.motivo or '',
        ])
    return Response(output.getvalue(), mimetype='text/csv')



# ══════════════════════════════════════════════════════════════════
# INICIALIZACIÓN DE BD (se ejecuta con gunicorn Y con python directo)
# ══════════════════════════════════════════════════════════════════

with app.app_context():
    db.create_all()
    seed_datos()


# ══════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("\n" + "═" * 60)
    print("   TiendaStock API — Sprint 4  |  100% de avance")
    print("═" * 60)
    print("   Index web : http://127.0.0.1:5000/")
    print("   Docs API  : http://127.0.0.1:5000/api/status  (ver endpoints)")
    print("   BD usada  : SQLite (tiendastock_sprint4.db)")
    print("═" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
