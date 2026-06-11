from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import User, Barrio, Categoria, AuditLog
from app.audit import log_event
from app import db
from functools import wraps

admin_bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="../../templates/admin")


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


@admin_bp.route("/categorias")
@login_required
@admin_required
def categorias():
    cats = Categoria.query.order_by(Categoria.nombre).all()
    return render_template("admin/categorias.html", categorias=cats)


@admin_bp.route("/categorias/nueva", methods=["GET", "POST"])
@login_required
@admin_required
def crear_categoria():
    barrios = Barrio.query.filter_by(activo=True).order_by(Barrio.nombre).all()
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        es_global = "es_global" in request.form
        barrio_ids = [int(bid) for bid in request.form.getlist("barrio_ids") if bid]

        if not es_global and not barrio_ids:
            flash("Seleccioná al menos un barrio o marcá la categoría como global.", "warning")
            return render_template("admin/form_categoria.html", categoria=None, barrios=barrios)

        if Categoria.query.filter_by(nombre=nombre).first():
            flash("Ya existe una categoría con ese nombre.", "danger")
            return render_template("admin/form_categoria.html", categoria=None, barrios=barrios)

        cat = Categoria(
            nombre=nombre,
            color=request.form.get("color", "#2E86C1"),
            icono=request.form.get("icono", "bi-box"),
            es_global=es_global,
        )
        if not es_global:
            cat.barrios = Barrio.query.filter(Barrio.id.in_(barrio_ids)).all()
        db.session.add(cat)
        db.session.commit()
        log_event(
            AuditLog.CATEGORIA_CREADA,
            target_tipo="categoria",
            target_id=cat.id,
            target_label=cat.nombre,
            detalle=f"global={cat.es_global}",
        )
        flash(f"Categoría '{nombre}' creada.", "success")
        return redirect(url_for("admin.categorias"))
    return render_template("admin/form_categoria.html", categoria=None, barrios=barrios)


@admin_bp.route("/categorias/<int:cat_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_categoria(cat_id):
    cat = db.session.get(Categoria, cat_id)
    if not cat:
        flash("Categoría no encontrada.", "warning")
        return redirect(url_for("admin.categorias"))

    barrios = Barrio.query.filter_by(activo=True).order_by(Barrio.nombre).all()

    if request.method == "POST":
        es_global = "es_global" in request.form
        barrio_ids = [int(bid) for bid in request.form.getlist("barrio_ids") if bid]

        if not es_global and not barrio_ids:
            flash("Seleccioná al menos un barrio o marcá la categoría como global.", "warning")
            return render_template("admin/form_categoria.html", categoria=cat, barrios=barrios)

        cat.nombre = request.form["nombre"].strip()
        cat.color = request.form.get("color", cat.color)
        cat.icono = request.form.get("icono", cat.icono)
        cat.es_global = es_global
        cat.barrios = [] if es_global else Barrio.query.filter(Barrio.id.in_(barrio_ids)).all()
        db.session.commit()
        flash("Categoría actualizada.", "success")
        return redirect(url_for("admin.categorias"))

    return render_template("admin/form_categoria.html", categoria=cat, barrios=barrios)


@admin_bp.route("/categorias/<int:cat_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def eliminar_categoria(cat_id):
    cat = db.session.get(Categoria, cat_id)
    if cat:
        if cat.items.count() > 0:
            flash("No podés eliminar una categoría con ítems asignados.", "danger")
        else:
            nombre_cat = cat.nombre
            cat_id_log = cat.id
            db.session.delete(cat)
            db.session.commit()
            log_event(
                AuditLog.CATEGORIA_ELIMINADA,
                nivel=AuditLog.ADVERTENCIA,
                target_tipo="categoria",
                target_id=cat_id_log,
                target_label=nombre_cat,
            )
            flash(f"Categoría '{nombre_cat}' eliminada.", "success")
    return redirect(url_for("admin.categorias"))


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
        log_event(
            AuditLog.BARRIO_CREADO,
            target_tipo="barrio",
            target_id=barrio.id,
            target_label=barrio.nombre,
        )
        flash(f"Barrio '{barrio.nombre}' creado.", "success")
        return redirect(url_for("admin.barrios"))
    return render_template("admin/form_barrio.html", barrio=None)
