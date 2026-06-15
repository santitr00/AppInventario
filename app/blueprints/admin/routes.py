from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import User, Barrio, Categoria, Area, Ubicacion, AuditLog
from app.audit import log_event
from app.blueprints.inventory.routes import get_user_barrio_id
from app import db
from functools import wraps

admin_bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="../../templates/admin")

# Catálogos por barrio gestionados de forma idéntica (CRUD genérico con pestañas).
# 'tiene_estilo' = la entidad tiene color/icono (solo categorías).
CATALOGOS = {
    "categorias": {
        "model": Categoria, "singular": "Categoría", "plural": "Categorías",
        "tiene_estilo": True, "target_tipo": "categoria",
        "audit_crear": AuditLog.CATEGORIA_CREADA, "audit_eliminar": AuditLog.CATEGORIA_ELIMINADA,
    },
    "areas": {
        "model": Area, "singular": "Área", "plural": "Áreas",
        "tiene_estilo": False, "target_tipo": "area",
        "audit_crear": AuditLog.AREA_CREADA, "audit_eliminar": AuditLog.AREA_ELIMINADA,
    },
    "ubicaciones": {
        "model": Ubicacion, "singular": "Ubicación", "plural": "Ubicaciones",
        "tiene_estilo": False, "target_tipo": "ubicacion",
        "audit_crear": AuditLog.UBICACION_CREADA, "audit_eliminar": AuditLog.UBICACION_ELIMINADA,
    },
}
CATALOGOS_TABS = [(s, CATALOGOS[s]["plural"]) for s in ("categorias", "areas", "ubicaciones")]

# Categorías sembradas automáticamente al crear un barrio, para que ningún
# gestor arranque sin nada. Después puede editarlas/eliminarlas a gusto.
DEFAULT_CATEGORIAS = [
    {"nombre": "Equipos de Seguridad", "color": "#2E86C1", "icono": "bi-camera-video"},
    {"nombre": "Materiales de Mantenimiento", "color": "#27AE60", "icono": "bi-tools"},
    {"nombre": "Mobiliario", "color": "#E67E22", "icono": "bi-house"},
    {"nombre": "Otros", "color": "#7F8C8D", "icono": "bi-box"},
]

AUDIT_ACCIONES = [
    (AuditLog.LOGIN_OK,            "Login exitoso"),
    (AuditLog.LOGIN_FAIL,          "Login fallido"),
    (AuditLog.LOGOUT,              "Logout"),
    (AuditLog.ACCESO_DENEGADO,     "Acceso denegado"),
    (AuditLog.USUARIO_CREADO,      "Usuario creado"),
    (AuditLog.USUARIO_EDITADO,     "Usuario editado"),
    (AuditLog.PRIVILEGIO_CAMBIADO, "Privilegio cambiado"),
    (AuditLog.PASSWORD_RESET,      "Reseteo de contraseña"),
    (AuditLog.USUARIO_ACTIVADO,    "Usuario activado"),
    (AuditLog.USUARIO_DESACTIVADO, "Usuario desactivado"),
    (AuditLog.ITEM_BAJA,           "Baja de ítem"),
    (AuditLog.ITEM_ELIMINADO,      "Eliminación de ítem"),
    (AuditLog.BARRIO_CREADO,       "Barrio creado"),
    (AuditLog.BARRIO_ELIMINADO,    "Barrio eliminado"),
    (AuditLog.CATEGORIA_CREADA,    "Categoría creada"),
    (AuditLog.CATEGORIA_ELIMINADA, "Categoría eliminada"),
    (AuditLog.AREA_CREADA,         "Área creada"),
    (AuditLog.AREA_ELIMINADA,      "Área eliminada"),
    (AuditLog.UBICACION_CREADA,    "Ubicación creada"),
    (AuditLog.UBICACION_ELIMINADA, "Ubicación eliminada"),
    (AuditLog.EXPORT_CSV,          "Exportación CSV"),
    (AuditLog.EXPORT_PDF,          "Exportación PDF"),
]
AUDIT_ACCIONES_MAP = dict(AUDIT_ACCIONES)


def admin_or_gestor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.is_cliente:
            log_event(
                AuditLog.ACCESO_DENEGADO,
                nivel=AuditLog.ALERTA,
                detalle=f"Intento de acceso a ruta de gestión: {request.path}",
            )
            flash("No tenés permisos para acceder.", "danger")
            return redirect(url_for("inventory.index"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            log_event(
                AuditLog.ACCESO_DENEGADO,
                nivel=AuditLog.ALERTA,
                detalle=f"Intento de acceso a ruta de admin: {request.path}",
            )
            flash("Acceso restringido a administradores.", "danger")
            return redirect(url_for("inventory.index"))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/usuarios")
@login_required
@admin_or_gestor_required
def usuarios():
    if current_user.is_admin:
        users = User.query.order_by(User.nombre_completo).all()
    else:
        users = User.query.filter_by(barrio_id=current_user.barrio_id).order_by(User.nombre_completo).all()
    barrios = Barrio.query.filter_by(activo=True).all()
    return render_template("admin/usuarios.html", users=users, barrios=barrios)


@admin_bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@login_required
@admin_or_gestor_required
def crear_usuario():
    barrios = Barrio.query.filter_by(activo=True).all()

    if request.method == "POST":
        username = request.form["username"].strip()
        if User.query.filter_by(username=username).first():
            flash("Ese nombre de usuario ya existe.", "danger")
            return render_template("admin/form_usuario.html", user=None, barrios=barrios)

        _bid = request.form.get("barrio_id", "").strip()
        user = User(
            username=username,
            email=request.form.get("email", ""),
            nombre_completo=request.form.get("nombre_completo", ""),
            rol=request.form.get("rol", "cliente") if current_user.is_admin else "cliente",
            barrio_id=int(_bid) if (current_user.is_admin and _bid) else (None if current_user.is_admin else current_user.barrio_id),
        )
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        log_event(
            AuditLog.USUARIO_CREADO,
            target_tipo="usuario",
            target_id=user.id,
            target_label=user.username,
            detalle=f"rol={user.rol}, barrio_id={user.barrio_id}",
        )
        flash(f"Usuario '{username}' creado correctamente.", "success")
        return redirect(url_for("admin.usuarios"))

    return render_template("admin/form_usuario.html", user=None, barrios=barrios)


@admin_bp.route("/usuarios/<int:user_id>/editar", methods=["GET", "POST"])
@login_required
@admin_or_gestor_required
def editar_usuario(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("Usuario no encontrado.", "warning")
        return redirect(url_for("admin.usuarios"))

    barrios = Barrio.query.filter_by(activo=True).all()

    if request.method == "POST":
        old_rol = user.rol
        user.nombre_completo = request.form.get("nombre_completo", "")
        user.email = request.form.get("email", "")
        if current_user.is_admin:
            user.rol = request.form.get("rol", user.rol)
            user.barrio_id = int(request.form["barrio_id"]) if request.form.get("barrio_id") else None

        new_pass = request.form.get("password", "").strip()
        if new_pass:
            user.set_password(new_pass)

        db.session.commit()

        rol_cambio = current_user.is_admin and user.rol != old_rol
        if rol_cambio:
            log_event(
                AuditLog.PRIVILEGIO_CAMBIADO,
                nivel=AuditLog.ADVERTENCIA,
                target_tipo="usuario",
                target_id=user.id,
                target_label=user.username,
                detalle=f"rol: {old_rol} → {user.rol}",
            )
        if new_pass:
            log_event(
                AuditLog.PASSWORD_RESET,
                target_tipo="usuario",
                target_id=user.id,
                target_label=user.username,
            )
        if not rol_cambio and not new_pass:
            log_event(
                AuditLog.USUARIO_EDITADO,
                target_tipo="usuario",
                target_id=user.id,
                target_label=user.username,
            )

        flash("Usuario actualizado.", "success")
        return redirect(url_for("admin.usuarios"))

    return render_template("admin/form_usuario.html", user=user, barrios=barrios)


@admin_bp.route("/usuarios/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_or_gestor_required
def toggle_usuario(user_id):
    user = db.session.get(User, user_id)
    if user and user.id != current_user.id:
        user.activo = not user.activo
        db.session.commit()
        accion_toggle = AuditLog.USUARIO_ACTIVADO if user.activo else AuditLog.USUARIO_DESACTIVADO
        log_event(
            accion_toggle,
            target_tipo="usuario",
            target_id=user.id,
            target_label=user.username,
        )
        estado = "activado" if user.activo else "desactivado"
        flash(f"Usuario '{user.username}' {estado}.", "info")
    return redirect(url_for("admin.usuarios"))


def _get_catalogo(seccion):
    """Devuelve la config del catálogo o None si la sección no es válida."""
    return CATALOGOS.get(seccion)


@admin_bp.route("/catalogos")
@login_required
@admin_or_gestor_required
def catalogos_home():
    return redirect(url_for("admin.catalogos", seccion="categorias"))


@admin_bp.route("/catalogos/<seccion>")
@login_required
@admin_or_gestor_required
def catalogos(seccion):
    cfg = _get_catalogo(seccion)
    if not cfg:
        return redirect(url_for("admin.catalogos", seccion="categorias"))

    barrio_id = get_user_barrio_id()
    if barrio_id is None and not current_user.is_admin:
        flash("Tu usuario no tiene un barrio asignado. Pedile al administrador que te asigne uno.", "warning")
        filas = []
    else:
        # Admin sin barrio ("Todos los barrios") ve todo; con barrio, solo ese.
        # El gestor ve únicamente las de su barrio.
        filas = cfg["model"].visibles_para_barrio(barrio_id)

    return render_template(
        "admin/catalogos.html",
        seccion=seccion, cfg=cfg, tabs=CATALOGOS_TABS, filas=filas,
    )


@admin_bp.route("/catalogos/<seccion>/nueva", methods=["GET", "POST"])
@login_required
@admin_or_gestor_required
def catalogo_nuevo(seccion):
    cfg = _get_catalogo(seccion)
    if not cfg:
        return redirect(url_for("admin.catalogos", seccion="categorias"))

    barrio_id = get_user_barrio_id()
    if barrio_id is None:
        if current_user.is_admin:
            flash(f"Seleccioná un barrio desde el menú superior antes de crear {cfg['plural'].lower()}.", "warning")
        else:
            flash("Tu usuario no tiene un barrio asignado; no podés crear.", "danger")
        return redirect(url_for("admin.catalogos", seccion=seccion))

    Model = cfg["model"]
    if request.method == "POST":
        nombre = request.form["nombre"].strip()

        if not nombre:
            flash("El nombre es obligatorio.", "warning")
            return render_template("admin/form_catalogo.html", seccion=seccion, cfg=cfg, fila=None)

        if not Model.nombre_disponible(nombre, barrio_id):
            flash(f"Ya existe {cfg['singular'].lower()} con ese nombre en este barrio.", "danger")
            return render_template("admin/form_catalogo.html", seccion=seccion, cfg=cfg, fila=None)

        fila = Model(nombre=nombre, barrio_id=barrio_id)
        if cfg["tiene_estilo"]:
            fila.color = request.form.get("color", "#2E86C1")
            fila.icono = request.form.get("icono", "bi-box")
        db.session.add(fila)
        db.session.commit()
        log_event(
            cfg["audit_crear"],
            target_tipo=cfg["target_tipo"],
            target_id=fila.id,
            target_label=fila.nombre,
            detalle=f"barrio_id={barrio_id}",
        )
        flash(f"{cfg['singular']} '{nombre}' creada.", "success")
        return redirect(url_for("admin.catalogos", seccion=seccion))

    return render_template("admin/form_catalogo.html", seccion=seccion, cfg=cfg, fila=None)


@admin_bp.route("/catalogos/<seccion>/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
@admin_or_gestor_required
def catalogo_editar(seccion, item_id):
    cfg = _get_catalogo(seccion)
    if not cfg:
        return redirect(url_for("admin.catalogos", seccion="categorias"))

    fila = db.session.get(cfg["model"], item_id)
    if not fila:
        flash("Elemento no encontrado.", "warning")
        return redirect(url_for("admin.catalogos", seccion=seccion))

    # Gestor: solo lo de su propio barrio. Bloquea acceso por URL directa.
    if not current_user.is_admin and fila.barrio_id != current_user.barrio_id:
        log_event(
            AuditLog.ACCESO_DENEGADO,
            nivel=AuditLog.ALERTA,
            target_tipo=cfg["target_tipo"],
            target_id=fila.id,
            target_label=fila.nombre,
            detalle=f"intento de editar {cfg['target_tipo']} de otro barrio",
        )
        flash("No podés editar este elemento.", "danger")
        return redirect(url_for("admin.catalogos", seccion=seccion))

    if request.method == "POST":
        nombre = request.form["nombre"].strip()

        if not nombre:
            flash("El nombre es obligatorio.", "warning")
            return render_template("admin/form_catalogo.html", seccion=seccion, cfg=cfg, fila=fila)

        if not cfg["model"].nombre_disponible(nombre, fila.barrio_id, exclude_id=fila.id):
            flash(f"Ya existe {cfg['singular'].lower()} con ese nombre en este barrio.", "danger")
            return render_template("admin/form_catalogo.html", seccion=seccion, cfg=cfg, fila=fila)

        # El barrio no se cambia desde acá (se recrea si hace falta).
        fila.nombre = nombre
        if cfg["tiene_estilo"]:
            fila.color = request.form.get("color", fila.color)
            fila.icono = request.form.get("icono", fila.icono)
        db.session.commit()
        flash(f"{cfg['singular']} actualizada.", "success")
        return redirect(url_for("admin.catalogos", seccion=seccion))

    return render_template("admin/form_catalogo.html", seccion=seccion, cfg=cfg, fila=fila)


@admin_bp.route("/catalogos/<seccion>/<int:item_id>/eliminar", methods=["POST"])
@login_required
@admin_or_gestor_required
def catalogo_eliminar(seccion, item_id):
    cfg = _get_catalogo(seccion)
    if not cfg:
        return redirect(url_for("admin.catalogos", seccion="categorias"))

    fila = db.session.get(cfg["model"], item_id)
    if not fila:
        return redirect(url_for("admin.catalogos", seccion=seccion))

    # Gestor: solo lo de su propio barrio.
    if not current_user.is_admin and fila.barrio_id != current_user.barrio_id:
        log_event(
            AuditLog.ACCESO_DENEGADO,
            nivel=AuditLog.ALERTA,
            target_tipo=cfg["target_tipo"],
            target_id=fila.id,
            target_label=fila.nombre,
            detalle=f"intento de eliminar {cfg['target_tipo']} de otro barrio",
        )
        flash("No podés eliminar este elemento.", "danger")
        return redirect(url_for("admin.catalogos", seccion=seccion))

    if fila.items.count() > 0:
        flash(f"No podés eliminar {cfg['singular'].lower()} con ítems asignados.", "danger")
    else:
        nombre = fila.nombre
        fila_id_log = fila.id
        db.session.delete(fila)
        db.session.commit()
        log_event(
            cfg["audit_eliminar"],
            nivel=AuditLog.ADVERTENCIA,
            target_tipo=cfg["target_tipo"],
            target_id=fila_id_log,
            target_label=nombre,
        )
        flash(f"{cfg['singular']} '{nombre}' eliminada.", "success")
    return redirect(url_for("admin.catalogos", seccion=seccion))


@admin_bp.route("/barrios")
@login_required
@admin_required
def barrios():
    barrios = Barrio.query.order_by(Barrio.nombre).all()
    return render_template("admin/barrios.html", barrios=barrios)


@admin_bp.route("/barrios/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def crear_barrio():
    if request.method == "POST":
        barrio = Barrio(
            nombre=request.form["nombre"],
            direccion=request.form.get("direccion", ""),
        )
        db.session.add(barrio)
        db.session.commit()

        # Sembrar categorías por defecto para que el barrio no arranque vacío.
        for c in DEFAULT_CATEGORIAS:
            db.session.add(Categoria(barrio_id=barrio.id, **c))
        db.session.commit()

        log_event(
            AuditLog.BARRIO_CREADO,
            target_tipo="barrio",
            target_id=barrio.id,
            target_label=barrio.nombre,
        )
        flash(f"Barrio '{barrio.nombre}' creado.", "success")
        return redirect(url_for("admin.barrios"))
    return render_template("admin/form_barrio.html", barrio=None)


@admin_bp.route("/auditoria")
@login_required
@admin_required
def auditoria():
    accion_f       = request.args.get("accion", "").strip()
    actor_f        = request.args.get("actor_username", "").strip()
    ip_f           = request.args.get("ip", "").strip()
    nivel_f        = request.args.get("nivel", "").strip()
    fecha_desde_f  = request.args.get("fecha_desde", "").strip()
    fecha_hasta_f  = request.args.get("fecha_hasta", "").strip()
    page           = request.args.get("page", 1, type=int)

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())

    if accion_f:
        query = query.filter(AuditLog.accion == accion_f)
    if actor_f:
        query = query.filter(AuditLog.actor_username.ilike(f"%{actor_f}%"))
    if ip_f:
        query = query.filter(AuditLog.ip.ilike(f"%{ip_f}%"))
    if nivel_f:
        query = query.filter(AuditLog.nivel == nivel_f)
    if fecha_desde_f:
        try:
            query = query.filter(AuditLog.timestamp >= datetime.strptime(fecha_desde_f, "%Y-%m-%d"))
        except ValueError:
            fecha_desde_f = ""
    if fecha_hasta_f:
        try:
            hasta = datetime.strptime(fecha_hasta_f, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(AuditLog.timestamp < hasta)
        except ValueError:
            fecha_hasta_f = ""

    pagination = query.paginate(page=page, per_page=30, error_out=False)

    return render_template(
        "admin/auditoria.html",
        logs=pagination.items,
        pagination=pagination,
        acciones=AUDIT_ACCIONES,
        acciones_map=AUDIT_ACCIONES_MAP,
        accion_f=accion_f,
        actor_f=actor_f,
        ip_f=ip_f,
        nivel_f=nivel_f,
        fecha_desde_f=fecha_desde_f,
        fecha_hasta_f=fecha_hasta_f,
    )
