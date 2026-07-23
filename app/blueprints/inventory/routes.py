import os
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import Item, Categoria, Area, Ubicacion, Historial, Barrio, AuditLog
from app.audit import log_event
from app import db

inventory_bp = Blueprint("inventory", __name__, template_folder="../../templates/inventory")

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_PDF = {"pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def allowed_pdf(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PDF


def opt_fk_en_barrio(model, raw_id, barrio_id):
    """Devuelve el id si pertenece a un objeto de `model` de ese barrio; si no,
    None. Evita que un POST manipulado asigne área/ubicación de otro barrio."""
    if not raw_id:
        return None
    try:
        oid = int(raw_id)
    except (TypeError, ValueError):
        return None
    obj = db.session.get(model, oid)
    return oid if (obj and obj.barrio_id == barrio_id) else None


# ── Contexto de búsqueda (para volver a la lista filtrada tras editar) ──
# Los parámetros viajan con prefijo `ret_` para no chocar con los campos del
# form del ítem (`estado`, por ejemplo). Nunca se redirige a una URL recibida
# del cliente: se reconstruye con url_for a partir de estos valores saneados.
RET_MULTI = {"categoria_id", "area_id", "ubicacion_id"}
RET_SINGLE = {"q", "estado"}


def leer_ret_params(source):
    """Extrae y sanea el contexto de búsqueda desde request.args o request.form.
    Devuelve {} si no viene marcado como proveniente de la búsqueda."""
    if source.get("ret_from") != "search":
        return {}

    ret = {"ret_from": "search"}
    for name in RET_SINGLE:
        val = (source.get(f"ret_{name}") or "").strip()
        if val:
            ret[f"ret_{name}"] = val[:200]
    for name in RET_MULTI:
        ids = []
        for raw in source.getlist(f"ret_{name}"):
            try:
                ids.append(int(raw))
            except (TypeError, ValueError):
                continue
        if ids:
            ret[f"ret_{name}"] = ids
    try:
        page = int(source.get("ret_page") or 1)
    except (TypeError, ValueError):
        page = 1
    ret["ret_page"] = max(1, page)
    return ret


def url_busqueda(ret, hl=None):
    """Reconstruye la URL de la búsqueda a partir del contexto saneado."""
    kwargs = {k[4:]: v for k, v in ret.items() if k != "ret_from"}
    if hl:
        kwargs["hl"] = hl
    return url_for("search.buscar", **kwargs)


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
        base_q = Item.query.filter_by(barrio_id=barrio_id)
    else:
        base_q = Item.query

    total = base_q.count()
    categorias = Categoria.visibles_para_barrio(barrio_id)
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

    categorias = Categoria.visibles_para_barrio(barrio_id)
    areas = Area.visibles_para_barrio(barrio_id)
    ubicaciones = Ubicacion.visibles_para_barrio(barrio_id)

    if request.method == "POST":
        item = Item(
            nombre=request.form["nombre"],
            codigo=request.form.get("codigo", "").strip() or None,
            descripcion=request.form.get("descripcion", ""),
            categoria_id=int(request.form["categoria_id"]),
            barrio_id=barrio_id,
            area_id=opt_fk_en_barrio(Area, request.form.get("area_id"), barrio_id),
            ubicacion_id=opt_fk_en_barrio(Ubicacion, request.form.get("ubicacion_id"), barrio_id),
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

    return render_template(
        "inventory/form_item.html",
        item=None, categorias=categorias, areas=areas, ubicaciones=ubicaciones,
    )


@inventory_bp.route("/item/<int:item_id>")
@login_required
def ver_item(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        flash("Ítem no encontrado.", "warning")
        return redirect(url_for("inventory.index"))

    # Verificar acceso por barrio
    if not current_user.is_admin and item.barrio_id != current_user.barrio_id:
        log_event(
            AuditLog.ACCESO_DENEGADO,
            nivel=AuditLog.ALERTA,
            target_tipo="item",
            target_id=item.id,
            target_label=item.nombre,
            detalle=f"intento de ver ítem de barrio_id={item.barrio_id}",
        )
        flash("No tenés acceso a este ítem.", "danger")
        return redirect(url_for("inventory.index"))

    ret = leer_ret_params(request.args)
    historial = item.historial.limit(20).all()
    return render_template(
        "inventory/detalle_item.html", item=item, historial=historial, ret_params=ret,
    )


@inventory_bp.route("/item/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def editar_item(item_id):
    if not current_user.puede_editar():
        flash("No tenés permisos para editar.", "danger")
        return redirect(url_for("inventory.index"))

    item = db.session.get(Item, item_id)
    if not item:
        flash("Ítem no encontrado.", "warning")
        return redirect(url_for("inventory.index"))

    if not current_user.is_admin and item.barrio_id != current_user.barrio_id:
        log_event(
            AuditLog.ACCESO_DENEGADO,
            nivel=AuditLog.ALERTA,
            target_tipo="item",
            target_id=item.id,
            target_label=item.nombre,
            detalle=f"intento de editar ítem de barrio_id={item.barrio_id}",
        )
        flash("No tenés acceso a este ítem.", "danger")
        return redirect(url_for("inventory.index"))

    ret = leer_ret_params(request.form if request.method == "POST" else request.args)

    # Los desplegables se acotan al barrio del ítem (no al barrio activo del admin).
    categorias = Categoria.visibles_para_barrio(item.barrio_id)
    areas = Area.visibles_para_barrio(item.barrio_id)
    ubicaciones = Ubicacion.visibles_para_barrio(item.barrio_id)

    if request.method == "POST":
        cambios = []
        for campo in ["nombre", "codigo", "descripcion", "estado", "marca", "modelo", "numero_serie", "notas"]:
            nuevo = request.form.get(campo, "").strip()
            viejo = getattr(item, campo) or ""
            if nuevo != viejo:
                cambios.append(f"{campo}: '{viejo}' → '{nuevo}'")
                setattr(item, campo, nuevo or None if campo == "codigo" else nuevo)

        nueva_cant = int(request.form.get("cantidad", item.cantidad))
        if nueva_cant != item.cantidad:
            cambios.append(f"cantidad: {item.cantidad} → {nueva_cant}")
            item.cantidad = nueva_cant

        nueva_cat = opt_fk_en_barrio(Categoria, request.form.get("categoria_id"), item.barrio_id)
        if nueva_cat and nueva_cat != item.categoria_id:
            cambios.append("categoría actualizada")
            item.categoria_id = nueva_cat

        nueva_area = opt_fk_en_barrio(Area, request.form.get("area_id"), item.barrio_id)
        if nueva_area != item.area_id:
            cambios.append("área actualizada")
            item.area_id = nueva_area

        nueva_ubi = opt_fk_en_barrio(Ubicacion, request.form.get("ubicacion_id"), item.barrio_id)
        if nueva_ubi != item.ubicacion_id:
            cambios.append("ubicación actualizada")
            item.ubicacion_id = nueva_ubi

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

        if ret:
            return redirect(url_busqueda(ret, hl=item.id))
        return redirect(url_for("inventory.ver_item", item_id=item.id))

    return render_template(
        "inventory/form_item.html",
        item=item, categorias=categorias, areas=areas, ubicaciones=ubicaciones,
        ret_params=ret,
        cancel_url=url_busqueda(ret) if ret else url_for("inventory.index"),
    )


@inventory_bp.route("/item/<int:item_id>/eliminar", methods=["POST"])
@login_required
def eliminar_item(item_id):
    # Eliminación definitiva del ítem: reservada al administrador global.
    if not current_user.is_admin:
        log_event(
            AuditLog.ACCESO_DENEGADO,
            nivel=AuditLog.ALERTA,
            target_tipo="item",
            target_id=item_id,
            detalle="intento de eliminar ítem sin ser admin",
        )
        flash("Solo un administrador puede eliminar ítems.", "danger")
        return redirect(url_for("inventory.ver_item", item_id=item_id))

    ret = leer_ret_params(request.form)

    item = db.session.get(Item, item_id)
    if not item:
        flash("Ítem no encontrado.", "warning")
        return redirect(url_busqueda(ret) if ret else url_for("inventory.index"))

    nombre = item.nombre
    item_id_log = item.id
    barrio_id_log = item.barrio_id

    # Archivos asociados en disco: se borran best-effort, sin frenar la baja.
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    for adjunto in (item.foto, item.pdf):
        if adjunto:
            try:
                os.remove(os.path.join(upload_folder, adjunto))
            except OSError:
                pass

    # El historial tiene FK NOT NULL a items y la relación no cascadea:
    # lo eliminamos explícitamente antes de borrar el ítem.
    Historial.query.filter_by(item_id=item.id).delete()
    db.session.delete(item)
    db.session.commit()

    log_event(
        AuditLog.ITEM_ELIMINADO,
        nivel=AuditLog.ADVERTENCIA,
        target_tipo="item",
        target_id=item_id_log,
        target_label=nombre,
        detalle=f"barrio_id={barrio_id_log}",
    )
    flash(f"Ítem '{nombre}' eliminado definitivamente.", "success")
    # Volvemos a la búsqueda filtrada de la que veníamos, para seguir depurando
    # rápido; si no hay contexto de búsqueda, al inventario.
    return redirect(url_busqueda(ret) if ret else url_for("inventory.index"))
