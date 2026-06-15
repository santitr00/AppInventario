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


categoria_barrios = db.Table(
    "categoria_barrios",
    db.Column("categoria_id", db.Integer, db.ForeignKey("categorias.id"), primary_key=True),
    db.Column("barrio_id", db.Integer, db.ForeignKey("barrios.id"), primary_key=True),
)


class Categoria(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), default="#2E86C1")
    icono = db.Column(db.String(50), default="bi-box")
    es_global = db.Column(db.Boolean, default=False, nullable=False)

    barrios = db.relationship(
        "Barrio",
        secondary=categoria_barrios,
        lazy="subquery",
        backref=db.backref("categorias", lazy=True),
    )
    items = db.relationship("Item", backref="categoria", lazy="dynamic")

    @classmethod
    def visibles_para_barrio(cls, barrio_id):
        """Categorías visibles para un barrio: globales + asignadas a ese barrio.
        Si barrio_id es None (admin sin barrio activo), retorna todas."""
        if barrio_id is None:
            return cls.query.order_by(cls.nombre).all()
        return (
            cls.query
            .filter(
                db.or_(
                    cls.es_global == True,
                    cls.barrios.any(id=barrio_id),
                )
            )
            .order_by(cls.nombre)
            .all()
        )

    def es_exclusiva_de_barrio(self, barrio_id):
        """True si la categoría pertenece exclusivamente a ese barrio y no es global.
        Es la única condición bajo la cual un gestor puede editarla o eliminarla."""
        if self.es_global or barrio_id is None:
            return False
        return [b.id for b in self.barrios] == [barrio_id]

    @classmethod
    def nombre_disponible(cls, nombre, es_global, barrio_ids, exclude_id=None):
        """Unicidad multi-tenant del nombre (case-insensitive, trim).

        El nombre debe ser único dentro del conjunto visible de cada barrio que
        la categoría toca (visible de un barrio = sus locales + las globales).
        Dos categorías con el mismo nombre chocan si alguna es global, o si ambas
        son locales y comparten al menos un barrio.
        Retorna True si el nombre está disponible.
        """
        nombre_norm = (nombre or "").strip().lower()
        if not nombre_norm:
            return False
        barrio_ids = set(barrio_ids or [])
        q = cls.query.filter(db.func.lower(cls.nombre) == nombre_norm)
        if exclude_id is not None:
            q = q.filter(cls.id != exclude_id)
        for otra in q.all():
            if es_global or otra.es_global:
                return False
            if {b.id for b in otra.barrios} & barrio_ids:
                return False
        return True

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
