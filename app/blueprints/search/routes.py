from flask import Blueprint, render_template, request, session, make_response
from flask_login import login_required, current_user
from app.models import Item, Categoria
from app import db
import csv
import io

search_bp = Blueprint("search", __name__, template_folder="../../templates/search")


@search_bp.route("/buscar")
@login_required
def buscar():
    q = request.args.get("q", "").strip()
    categoria_id = request.args.get("categoria_id", type=int)
    estado = request.args.get("estado", "").strip()
    ubicacion = request.args.get("ubicacion", "").strip()
    page = request.args.get("page", 1, type=int)

    categoria_sel = db.session.get(Categoria, categoria_id) if categoria_id else None

    query = Item.query.filter_by(activo=True)

    # Filtro por barrio
    if not current_user.is_admin:
        query = query.filter_by(barrio_id=current_user.barrio_id)
    elif session.get("admin_barrio_id"):
        query = query.filter_by(barrio_id=session.get("admin_barrio_id"))

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Item.nombre.ilike(like),
                Item.codigo.ilike(like),
                Item.descripcion.ilike(like),
                Item.marca.ilike(like),
                Item.modelo.ilike(like),
                Item.numero_serie.ilike(like),
                Item.ubicacion.ilike(like),
            )
        )

    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    if estado:
        query = query.filter_by(estado=estado)
    if ubicacion:
        query = query.filter(Item.ubicacion.ilike(f"%{ubicacion}%"))

    barrio_id_filter = None
    if not current_user.is_admin:
        barrio_id_filter = current_user.barrio_id
    elif session.get("admin_barrio_id"):
        barrio_id_filter = session.get("admin_barrio_id")
    categorias = Categoria.visibles_para_barrio(barrio_id_filter)
    estados = [r[0] for r in db.session.query(Item.estado).distinct().all() if r[0]]

    # ── Exportar CSV ──
    if request.args.get("format") == "csv":
        todos = query.order_by(Item.nombre).all()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Nombre", "Código", "Categoría", "Barrio", "Ubicación", "Estado", "Cantidad", "Marca", "Modelo", "Nro. Serie", "Fecha Ingreso", "Notas"])
        for it in todos:
            writer.writerow([
                it.nombre,
                it.codigo or "",
                it.categoria.nombre if it.categoria else "",
                it.barrio.nombre if it.barrio else "",
                it.ubicacion or "",
                it.estado or "",
                it.cantidad,
                it.marca or "",
                it.modelo or "",
                it.numero_serie or "",
                it.fecha_ingreso.strftime("%d/%m/%Y") if it.fecha_ingreso else "",
                it.notas or "",
            ])
        # BOM utf-8 para que Excel abra con tildes correctas
        csv_bytes = "\ufeff" + buf.getvalue()
        output = make_response(csv_bytes.encode("utf-8"))
        output.headers["Content-Disposition"] = "attachment; filename=inventario.csv"
        output.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
        return output

    pagination = query.order_by(Item.nombre).paginate(page=page, per_page=20, error_out=False)

    return render_template(
        "search/buscar.html",
        items=pagination.items,
        pagination=pagination,
        categorias=categorias,
        estados=estados,
        q=q,
        categoria_id=categoria_id,
        categoria_sel=categoria_sel,
        estado_sel=estado,
        ubicacion=ubicacion,
    )
