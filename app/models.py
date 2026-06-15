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


class _CatalogoPorBarrioMixin:
    """Comportamiento compartido por los catálogos por barrio (Categoría, Área,
    Ubicación): cada uno pertenece a un único barrio y su nombre es único dentro
    de ese barrio. Dos barrios distintos pueden repetir nombres."""

    @classmethod
    def visibles_para_barrio(cls, barrio_id):
        """Filas del barrio. Si barrio_id es None (admin sin barrio activo
        seleccionado), retorna todas las de todos los barrios."""
        q = cls.query
        if barrio_id is not None:
            q = q.filter_by(barrio_id=barrio_id)
        return q.order_by(cls.nombre).all()

    @classmethod
    def nombre_disponible(cls, nombre, barrio_id, exclude_id=None):
        """Unicidad del nombre dentro de un barrio (case-insensitive, trim).
        Retorna True si el nombre está disponible en ese barrio."""
        nombre_norm = (nombre or "").strip().lower()
        if not nombre_norm or barrio_id is None:
            return False
        q = cls.query.filter(
            db.func.lower(cls.nombre) == nombre_norm,
            cls.barrio_id == barrio_id,
        )
        if exclude_id is not None:
            q = q.filter(cls.id != exclude_id)
        return q.first() is None


class Categoria(_CatalogoPorBarrioMixin, db.Model):
    __tablename__ = "categorias"
    __table_args__ = (
        db.UniqueConstraint("nombre", "barrio_id", name="uq_categoria_nombre_barrio"),
    )
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), default="#2E86C1")
    icono = db.Column(db.String(50), default="bi-box")
    barrio_id = db.Column(db.Integer, db.ForeignKey("barrios.id"), nullable=False)

    barrio = db.relationship("Barrio", backref=db.backref("categorias", lazy=True))
    items = db.relationship("Item", backref="categoria", lazy="dynamic")

    def __repr__(self):
        return f"<Categoria {self.nombre}>"


class Area(_CatalogoPorBarrioMixin, db.Model):
    __tablename__ = "areas"
    __table_args__ = (
        db.UniqueConstraint("nombre", "barrio_id", name="uq_area_nombre_barrio"),
    )
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    barrio_id = db.Column(db.Integer, db.ForeignKey("barrios.id"), nullable=False)

    barrio = db.relationship("Barrio", backref=db.backref("areas", lazy=True))
    items = db.relationship("Item", backref="area", lazy="dynamic")

    def __repr__(self):
        return f"<Area {self.nombre}>"


class Ubicacion(_CatalogoPorBarrioMixin, db.Model):
    __tablename__ = "ubicaciones"
    __table_args__ = (
        db.UniqueConstraint("nombre", "barrio_id", name="uq_ubicacion_nombre_barrio"),
    )
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    barrio_id = db.Column(db.Integer, db.ForeignKey("barrios.id"), nullable=False)

    barrio = db.relationship("Barrio", backref=db.backref("ubicaciones", lazy=True))
    items = db.relationship("Item", backref="ubicacion", lazy="dynamic")

    def __repr__(self):
        return f"<Ubicacion {self.nombre}>"


class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    barrio_id = db.Column(db.Integer, db.ForeignKey("barrios.id"), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey("areas.id"), nullable=True)
    ubicacion_id = db.Column(db.Integer, db.ForeignKey("ubicaciones.id"), nullable=True)
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

    @property
    def area_nombre(self):
        return self.area.nombre if self.area else None

    @property
    def ubicacion_nombre(self):
        return self.ubicacion.nombre if self.ubicacion else None

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


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    # ── Constantes de acción ──
    LOGIN_OK = "login_exitoso"
    LOGIN_FAIL = "login_fallido"
    LOGOUT = "logout"
    ACCESO_DENEGADO = "acceso_denegado"
    USUARIO_CREADO = "usuario_creado"
    USUARIO_EDITADO = "usuario_editado"
    PRIVILEGIO_CAMBIADO = "privilegio_cambiado"
    PASSWORD_RESET = "password_reset"
    USUARIO_ACTIVADO = "usuario_activado"
    USUARIO_DESACTIVADO = "usuario_desactivado"
    ITEM_BAJA = "item_baja"
    ITEM_ELIMINADO = "item_eliminado"
    BARRIO_CREADO = "barrio_creado"
    BARRIO_ELIMINADO = "barrio_eliminado"
    CATEGORIA_CREADA = "categoria_creada"
    CATEGORIA_ELIMINADA = "categoria_eliminada"
    AREA_CREADA = "area_creada"
    AREA_ELIMINADA = "area_eliminada"
    UBICACION_CREADA = "ubicacion_creada"
    UBICACION_ELIMINADA = "ubicacion_eliminada"
    EXPORT_CSV = "export_csv"
    EXPORT_PDF = "export_pdf"

    # ── Constantes de nivel ──
    INFO = "info"
    ADVERTENCIA = "advertencia"
    ALERTA = "alerta"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    actor_username = db.Column(db.String(80), nullable=False)
    accion = db.Column(db.String(60), nullable=False, index=True)
    nivel = db.Column(db.String(20), nullable=False, default="info")
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(300))
    target_tipo = db.Column(db.String(30))
    target_id = db.Column(db.Integer)
    target_label = db.Column(db.String(200))
    detalle = db.Column(db.Text)

    actor = db.relationship("User", foreign_keys=[actor_id])

    def __repr__(self):
        return f"<AuditLog {self.accion} by={self.actor_username}>"
