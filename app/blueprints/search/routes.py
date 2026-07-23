from datetime import date
from itertools import groupby

from flask import Blueprint, render_template, request, session, make_response, current_app
from flask_login import login_required, current_user
from app.models import Item, Categoria, Area, Ubicacion, Barrio, AuditLog
from app.audit import log_event
from app import db
import csv
import io
import os
from pathlib import Path

search_bp = Blueprint("search", __name__, template_folder="../../templates/search")


def build_items_query(q, categoria_ids, estado, area_ids, ubicacion_ids, user, admin_barrio_id):
    query = Item.query

    if not user.is_admin:
        query = query.filter_by(barrio_id=user.barrio_id)
    elif admin_barrio_id:
        query = query.filter_by(barrio_id=admin_barrio_id)

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
                Item.ubicacion.has(Ubicacion.nombre.ilike(like)),
            )
        )

    # Filtros multi-valor: cada uno acepta varias selecciones (OR dentro del campo,
    # AND entre campos).
    if categoria_ids:
        query = query.filter(Item.categoria_id.in_(categoria_ids))
    if estado:
        query = query.filter_by(estado=estado)
    if area_ids:
        query = query.filter(Item.area_id.in_(area_ids))
    if ubicacion_ids:
        query = query.filter(Item.ubicacion_id.in_(ubicacion_ids))

    return query


@search_bp.route("/buscar")
@login_required
def buscar():
    q = request.args.get("q", "").strip()
    categoria_ids = request.args.getlist("categoria_id", type=int)
    area_ids = request.args.getlist("area_id", type=int)
    ubicacion_ids = request.args.getlist("ubicacion_id", type=int)
    estado = request.args.get("estado", "").strip()
    page = request.args.get("page", 1, type=int)

    admin_barrio_id = session.get("admin_barrio_id")

    query = build_items_query(q, categoria_ids, estado, area_ids, ubicacion_ids, current_user, admin_barrio_id)

    barrio_id_filter = None if current_user.is_admin and not admin_barrio_id else (
        current_user.barrio_id if not current_user.is_admin else admin_barrio_id
    )
    categorias = Categoria.visibles_para_barrio(barrio_id_filter)
    areas = Area.visibles_para_barrio(barrio_id_filter)
    ubicaciones = Ubicacion.visibles_para_barrio(barrio_id_filter)
    estados = [r[0] for r in db.session.query(Item.estado).distinct().all() if r[0]]

    # ── Exportar CSV ──
    if request.args.get("format") == "csv":
        todos = query.order_by(Item.nombre).all()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Nombre", "Código", "Categoría", "Barrio", "Área", "Ubicación", "Estado", "Cantidad", "Marca", "Modelo", "Nro. Serie", "Fecha Ingreso", "Notas"])
        for it in todos:
            writer.writerow([
                it.nombre,
                it.codigo or "",
                it.categoria.nombre if it.categoria else "",
                it.barrio.nombre if it.barrio else "",
                it.area_nombre or "",
                it.ubicacion_nombre or "",
                it.estado or "",
                it.cantidad,
                it.marca or "",
                it.modelo or "",
                it.numero_serie or "",
                it.fecha_ingreso.strftime("%d/%m/%Y") if it.fecha_ingreso else "",
                it.notas or "",
            ])
        # BOM utf-8 para que Excel abra con tildes correctas
        csv_bytes = "﻿" + buf.getvalue()
        output = make_response(csv_bytes.encode("utf-8"))
        output.headers["Content-Disposition"] = "attachment; filename=inventario.csv"
        output.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
        filtros_str = ", ".join(filter(None, [
            f"q={q!r}" if q else "",
            f"categorias={categoria_ids}" if categoria_ids else "",
            f"estado={estado!r}" if estado else "",
            f"areas={area_ids}" if area_ids else "",
            f"ubicaciones={ubicacion_ids}" if ubicacion_ids else "",
        ])) or "ninguno"
        log_event(
            AuditLog.EXPORT_CSV,
            detalle=f"filtros: {filtros_str}; items={len(todos)}",
        )
        return output

    pagination = query.order_by(Item.nombre).paginate(page=page, per_page=20, error_out=False)

    return render_template(
        "search/buscar.html",
        items=pagination.items,
        pagination=pagination,
        categorias=categorias,
        areas=areas,
        ubicaciones=ubicaciones,
        estados=estados,
        q=q,
        categoria_ids=categoria_ids,
        area_ids=area_ids,
        ubicacion_ids=ubicacion_ids,
        estado_sel=estado,
        hl=request.args.get("hl", type=int),
    )


@search_bp.route("/buscar/export/pdf")
@login_required
def export_pdf():
    q = request.args.get("q", "").strip()
    categoria_ids = request.args.getlist("categoria_id", type=int)
    area_ids = request.args.getlist("area_id", type=int)
    ubicacion_ids = request.args.getlist("ubicacion_id", type=int)
    estado = request.args.get("estado", "").strip()

    admin_barrio_id = session.get("admin_barrio_id")

    todos = build_items_query(
        q, categoria_ids, estado, area_ids, ubicacion_ids, current_user, admin_barrio_id
    ).all()

    todos.sort(key=lambda it: (
        it.categoria.nombre.lower() if it.categoria else "\xff",
        (it.codigo or it.nombre).lower(),
    ))

    grupos = [
        (cat, list(its))
        for cat, its in groupby(todos, key=lambda it: it.categoria)
    ]

    # Resolvemos la ruta absoluta (file://) de cada foto para que WeasyPrint
    # pueda leerla desde el filesystem. Si el archivo no existe, dejamos None
    # y el template cae al placeholder (nunca rompe la generación del PDF).
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    for _, items in grupos:
        for it in items:
            it.foto_uri = None
            if it.foto:
                fpath = os.path.join(upload_folder, it.foto)
                if os.path.isfile(fpath):
                    it.foto_uri = Path(fpath).as_uri()

    if not current_user.is_admin:
        barrio_nombre = current_user.barrio.nombre if current_user.barrio else "—"
    elif admin_barrio_id:
        b = db.session.get(Barrio, admin_barrio_id)
        barrio_nombre = b.nombre if b else "Todos los barrios"
    else:
        barrio_nombre = "Todos los barrios"

    filtros = []
    if q:
        filtros.append(f'texto: "{q}"')
    if categoria_ids:
        cats = Categoria.query.filter(Categoria.id.in_(categoria_ids)).all()
        filtros.append("categorías: " + ", ".join(c.nombre for c in cats))
    if estado:
        filtros.append(f"estado: {estado}")
    if area_ids:
        areas = Area.query.filter(Area.id.in_(area_ids)).all()
        filtros.append("áreas: " + ", ".join(a.nombre for a in areas))
    if ubicacion_ids:
        ubis = Ubicacion.query.filter(Ubicacion.id.in_(ubicacion_ids)).all()
        filtros.append("ubicaciones: " + ", ".join(u.nombre for u in ubis))

    hoy = date.today()
    safe_barrio = barrio_nombre.lower().replace(" ", "_").replace("/", "-")
    filename = f"inventario_{safe_barrio}_{hoy.strftime('%Y%m%d')}.pdf"

    html_str = render_template(
        "search/pdf_inventario.html",
        grupos=grupos,
        barrio_nombre=barrio_nombre,
        fecha=hoy,
        filtros=filtros,
        total=len(todos),
    )

    from weasyprint import HTML as WeasyHTML
    pdf_bytes = WeasyHTML(string=html_str).write_pdf()

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    log_event(
        AuditLog.EXPORT_PDF,
        detalle=f"filtros: {', '.join(filtros) or 'ninguno'}; items={len(todos)}; barrio={barrio_nombre}",
    )
    return response
