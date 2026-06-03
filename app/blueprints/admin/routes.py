from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import User, Barrio, Categoria
from app import db
from functools import wraps

admin_bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="../../templates/admin")


def admin_or_gestor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.is_cliente:
            flash("No tenés permisos para acceder.", "danger")
            return redirect(url_for("inventory.index"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
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
        user.nombre_completo = request.form.get("nombre_completo", "")
        user.email = request.form.get("email", "")
        if current_user.is_admin:
            user.rol = request.form.get("rol", user.rol)
            user.barrio_id = int(request.form["barrio_id"]) if request.form.get("barrio_id") else None

        new_pass = request.form.get("password", "").strip()
        if new_pass:
            user.set_password(new_pass)

        db.session.commit()
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
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        if Categoria.query.filter_by(nombre=nombre).first():
            flash("Ya existe una categoría con ese nombre.", "danger")
        else:
            cat = Categoria(
                nombre=nombre,
                color=request.form.get("color", "#2E86C1"),
                icono=request.form.get("icono", "bi-box"),
            )
            db.session.add(cat)
            db.session.commit()
            flash(f"Categoría '{nombre}' creada.", "success")
            return redirect(url_for("admin.categorias"))
    return render_template("admin/form_categoria.html", categoria=None)


@admin_bp.route("/categorias/<int:cat_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_categoria(cat_id):
    cat = db.session.get(Categoria, cat_id)
    if not cat:
        flash("Categoría no encontrada.", "warning")
        return redirect(url_for("admin.categorias"))

    if request.method == "POST":
        cat.nombre = request.form["nombre"].strip()
        cat.color = request.form.get("color", cat.color)
        cat.icono = request.form.get("icono", cat.icono)
        db.session.commit()
        flash("Categoría actualizada.", "success")
        return redirect(url_for("admin.categorias"))

    return render_template("admin/form_categoria.html", categoria=cat)


@admin_bp.route("/categorias/<int:cat_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def eliminar_categoria(cat_id):
    cat = db.session.get(Categoria, cat_id)
    if cat:
        if cat.items.count() > 0:
            flash("No podés eliminar una categoría con ítems asignados.", "danger")
        else:
            db.session.delete(cat)
            db.session.commit()
            flash(f"Categoría '{cat.nombre}' eliminada.", "success")
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
        flash(f"Barrio '{barrio.nombre}' creado.", "success")
        return redirect(url_for("admin.barrios"))
    return render_template("admin/form_barrio.html", barrio=None)
