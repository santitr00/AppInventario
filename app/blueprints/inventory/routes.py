import os
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import Item, Categoria, Historial, Barrio
from app import db

inventory_bp = Blueprint("inventory", __name__, template_folder="../../templates/inventory")

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_PDF = {"pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def allowed_pdf(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PDF


def get_user_barrio_id():
    """Retorna el barrio_id activo: para admin usa la sesión, para otros su barrio asignado."""
    if current_user.is_admin:
        return session.get("admin_barrio_id")
    return current_user.barrio_id


@inventory_bp.route("/set_barrio", methods=["POST"])
@login_required
def set_barrio():
    if current_user.is_admin:
        bid = request.form.get("barrio_id", "").strip()
        if bid:
            session["admin_barrio_id"] = int(bid)
        else:
            session.pop("admin_barrio_id", None)
    return redirect(request.referrer or url_for("inventory.index"))


@inventory_bp.route("/")
@login_required
def index():
    barrio_id = get_user_barrio_id()
    barrio = db.session.get(Barrio, barrio_id) if barrio_id else None

    # Stats
    if barrio_id:
        base_q = Item.query.filter_by(barrio_id=barrio_id, activo=True)
    else:
        base_q = Item.query.filter_by(activo=True)

    total = base_q.count()
    categorias = Categoria.query.all()
    stats_por_cat = []
    for cat in categorias:
        q = base_q.filter_by(categoria_id=cat.id)
        count = q.count()
        if count > 0:
            stats_por_cat.append({"categoria": cat, "count": count})

    # Últimos movimientos
    items = base_q.order_by(Item.updated_at.desc()).limit(20).all()

    barrios = Barrio.query.filter_by(activo=True).all() if current_user.is_admin else []

    return render_template(
        "inventory/index.html",
        barrio=barrio,
        barrios=barrios,
        items=items,
        total=total,
        stats_por_cat=stats_por_cat,
    )


@inventory_bp.route("/item/nuevo", methods=["GET", "POST"])
@login_required
def crear_item():
    if not current_user.puede_editar():
        flash("No tenés permisos para crear ítems.", "danger")
        return redirect(url_for("inventory.index"))

    barrio_id = get_user_barrio_id()
    if not barrio_id:
        flash("Seleccioná un barrio desde el menú superior antes de crear ítems.", "warning")
        return redirect(url_for("inventory.index"))

    categorias = Categoria.query.all()

    if request.method == "POST":
        item = Item(
            nombre=request.form["nombre"],
            codigo=request.form.get("codigo", "").strip() or None,
            descripcion=request.form.get("descripcion", ""),
            categoria_id=int(request.form["categoria_id"]),
            barrio_id=barrio_id,
            ubicacion=request.form.get("ubicacion", ""),
            estado=request.form.get("estado", "Operativo"),
            cantidad=int(request.form.get("cantidad", 1)),
            marca=request.form.get("marca", ""),
            modelo=request.form.get("modelo", ""),
            numero_serie=request.form.get("numero_serie", ""),
            fecha_ingreso=date.today(),
            notas=request.form.get("notas", ""),
            created_by=current_user.id,
        )

        # Foto
        if "foto" in request.files:
            file = request.files["foto"]
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{barrio_id}_{file.filename}")
                file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
                item.foto = filename

        # PDF
        if "pdf" in request.files:
            pfile = request.files["pdf"]
            if pfile and pfile.filename and allowed_pdf(pfile.filename):
                pfilename = secure_filename(f"pdf_{barrio_id}_{pfile.filename}")
                pfile.save(os.path.join(current_app.config["UPLOAD_FOLDER"], pfilename))
                item.pdf = pfilename

        db.session.add(item)
        db.session.flush()

        historial = Historial(
            item_id=item.id,
            user_id=current_user.id,
            accion="alta",
            detalle=f"Alta del ítem: {item.nombre}",
        )
        db.session.add(historial)
        db.session.commit()

        flash(f"Ítem '{item.nombre}' creado correctamente.", "success")
        return redirect(url_for("inventory.ver_item", item_id=item.id))

    return render_template("inventory/form_item.html", item=None, categorias=categorias)


@inventory_bp.route("/item/<int:item_id>")
@login_required
def ver_item(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        flash("Ítem no encontrado.", "warning")
        return redirect(url_for("inventory.index"))

    # Verificar acceso por barrio
    if not current_user.is_admin and item.barrio_id != current_user.barrio_id:
        flash("No tenés acceso a este ítem.", "danger")
        return redirect(url_for("inventory.index"))

    historial = item.historial.limit(20).all()
    return render_template("inventory/detalle_item.html", item=item, historial=historial)


@inventory_bp.route("/item/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def editar_item(item_id):
    if not current_user.puede_editar():
        flash("No tenés permisos para editar.", "danger")
        return redirect(url_for("inventory.index"))

    item = db.session.get(Item, item_id)
    if not item or not item.activo:
        flash("Ítem no encontrado.", "warning")
        return redirect(url_for("inventory.index"))

    categorias = Categoria.query.all()

    if request.method == "POST":
        cambios = []
        for campo in ["nombre", "codigo", "descripcion", "ubicacion", "estado", "marca", "modelo", "numero_serie", "notas"]:
            nuevo = request.form.get(campo, "").strip()
            viejo = getattr(item, campo) or ""
            if nuevo != viejo:
                cambios.append(f"{campo}: '{viejo}' → '{nuevo}'")
                setattr(item, campo, nuevo or None if campo == "codigo" else nuevo)

        nueva_cant = int(request.form.get("cantidad", item.cantidad))
        if nueva_cant != item.cantidad:
            cambios.append(f"cantidad: {item.cantidad} → {nueva_cant}")
            item.cantidad = nueva_cant

        nueva_cat = int(request.form.get("categoria_id", item.categoria_id))
        if nueva_cat != item.categoria_id:
            cambios.append("categoría actualizada")
            item.categoria_id = nueva_cat

        # Foto
        if "foto" in request.files:
            file = request.files["foto"]
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{item.barrio_id}_{file.filename}")
                file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
                item.foto = filename
                cambios.append("foto actualizada")

        # PDF
        if "pdf" in request.files:
            pfile = request.files["pdf"]
            if pfile and pfile.filename and allowed_pdf(pfile.filename):
                pfilename = secure_filename(f"pdf_{item.barrio_id}_{pfile.filename}")
                pfile.save(os.path.join(current_app.config["UPLOAD_FOLDER"], pfilename))
                item.pdf = pfilename
                cambios.append("PDF actualizado")

        if cambios:
            historial = Historial(
                item_id=item.id,
                user_id=current_user.id,
                accion="edicion",
                detalle="; ".join(cambios),
            )
            db.session.add(historial)
            db.session.commit()
            flash("Ítem actualizado.", "success")
        else:
            flash("No se detectaron cambios.", "info")

        return redirect(url_for("inventory.ver_item", item_id=item.id))

    return render_template("inventory/form_item.html", item=item, categorias=categorias)


@inventory_bp.route("/item/<int:item_id>/baja", methods=["POST"])
@login_required
def baja_item(item_id):
    if not current_user.puede_editar():
        flash("No tenés permisos.", "danger")
        return redirect(url_for("inventory.index"))

    item = db.session.get(Item, item_id)
    if item:
        item.activo = False
        historial = Historial(
            item_id=item.id,
            user_id=current_user.id,
            accion="baja",
            detalle=f"Baja del ítem: {item.nombre}",
        )
        db.session.add(historial)
        db.session.commit()
        flash(f"Ítem '{item.nombre}' dado de baja.", "warning")

    return redirect(url_for("inventory.index"))
