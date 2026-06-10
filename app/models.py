from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class Barrio(db.Model):
    __tablename__ = "barrios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False, unique=True)
    direccion = db.Column(db.String(255))
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    usuarios = db.relationship("User", backref="barrio", lazy="dynamic")
    items = db.relationship("Item", backref="barrio", lazy="dynamic")

    def __repr__(self):
        return f"<Barrio {self.nombre}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre_completo = db.Column(db.String(150))
    rol = db.Column(db.String(20), nullable=False, default="cliente")
    # Roles: admin (global), gestor (por barrio), cliente (solo lectura)
    barrio_id = db.Column(db.Integer, db.ForeignKey("barrios.id"), nullable=True)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.rol == "admin"

    @property
    def is_gestor(self):
        return self.rol == "gestor"

    @property
    def is_cliente(self):
        return self.rol == "cliente"

    def puede_editar(self):
        return self.rol in ("admin", "gestor")

    def __repr__(self):
        return f"<User {self.username} ({self.rol})>"


class Categoria(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), default="#2E86C1")  # hex color
    icono = db.Column(db.String(50), default="bi-box")  # Bootstrap icon class
    barrio_id = db.Column(db.Integer, db.ForeignKey("barrios.id"), nullable=True)
    # barrio_id NULL = categoría global (disponible en todos los barrios)
    items = db.relationship("Item", backref="categoria", lazy="dynamic")

    def __repr__(self):
        return f"<Categoria {self.nombre}>"


class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    barrio_id = db.Column(db.Integer, db.ForeignKey("barrios.id"), nullable=False)
    ubicacion = db.Column(db.String(200))
    estado = db.Column(db.String(50), default="Operativo")
    # Estados sugeridos: Operativo, Stock bajo, En reparación, Fuera de servicio, En préstamo
    codigo = db.Column(db.String(50))
    cantidad = db.Column(db.Integer, default=1)
    marca = db.Column(db.String(100))
    modelo = db.Column(db.String(100))
    numero_serie = db.Column(db.String(100))
    fecha_ingreso = db.Column(db.Date)
    foto = db.Column(db.String(255))
    pdf = db.Column(db.String(255))
    notas = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    historial = db.relationship(
        "Historial", backref="item", lazy="dynamic", order_by="Historial.created_at.desc()"
    )
    creator = db.relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Item {self.nombre}>"


class Historial(db.Model):
    __tablename__ = "historial"
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    accion = db.Column(db.String(50), nullable=False)
    # Acciones: alta, edicion, cambio_estado, baja
    detalle = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<Historial {self.accion} item={self.item_id}>"
