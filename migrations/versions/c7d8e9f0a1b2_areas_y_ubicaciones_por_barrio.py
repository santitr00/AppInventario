"""areas y ubicaciones como catálogos por barrio; item.ubicacion texto -> FK

Agrega las tablas `areas` y `ubicaciones` (catálogos por barrio, igual que
categorias). En `items`:
  - area_id      FK nullable -> areas        (opcional; NULL = general del barrio)
  - ubicacion_id FK nullable -> ubicaciones  (reemplaza el texto libre)

Migra el texto libre de items.ubicacion: por cada barrio, los valores distintos
(normalizados sin espacios/may-min) se convierten en filas de `ubicaciones` y
cada ítem se reapunta a la suya. Luego se elimina la columna de texto.

Revision ID: c7d8e9f0a1b2
Revises: b1c2d3e4f5a6
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = 'c7d8e9f0a1b2'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1. Catálogos por barrio
    op.create_table(
        'areas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('barrio_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['barrio_id'], ['barrios.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre', 'barrio_id', name='uq_area_nombre_barrio'),
    )
    op.create_table(
        'ubicaciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=200), nullable=False),
        sa.Column('barrio_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['barrio_id'], ['barrios.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre', 'barrio_id', name='uq_ubicacion_nombre_barrio'),
    )

    # 2. Columnas nuevas en items (temporalmente sin FK para poder poblar)
    op.add_column('items', sa.Column('area_id', sa.Integer(), nullable=True))
    op.add_column('items', sa.Column('ubicacion_id', sa.Integer(), nullable=True))

    # 3. Fan-out del texto libre de ubicacion -> filas en ubicaciones (por barrio)
    filas = conn.execute(text(
        "SELECT DISTINCT barrio_id, TRIM(ubicacion) AS u FROM items "
        "WHERE ubicacion IS NOT NULL AND TRIM(ubicacion) <> ''"))

    ubic_map = {}  # (barrio_id, nombre_lower) -> ubicacion_id
    for barrio_id, nombre in filas:
        nombre = (nombre or "").strip()
        if not nombre:
            continue
        key = (barrio_id, nombre.lower())
        if key in ubic_map:
            continue
        res = conn.execute(text(
            "INSERT INTO ubicaciones (nombre, barrio_id) VALUES (:n, :b)"),
            {"n": nombre, "b": barrio_id})
        ubic_map[key] = res.lastrowid

    # Reapuntar ítems (incluye variantes de may/min y espacios al mismo destino)
    for (barrio_id, nombre_lower), uid in ubic_map.items():
        conn.execute(text(
            "UPDATE items SET ubicacion_id = :uid "
            "WHERE barrio_id = :b AND LOWER(TRIM(ubicacion)) = :low"),
            {"uid": uid, "b": barrio_id, "low": nombre_lower})

    # 4. Baja de la columna de texto y alta de las FK
    op.drop_column('items', 'ubicacion')
    op.create_foreign_key('fk_items_area_id', 'items', 'areas', ['area_id'], ['id'])
    op.create_foreign_key('fk_items_ubicacion_id', 'items', 'ubicaciones',
                          ['ubicacion_id'], ['id'])


def downgrade():
    conn = op.get_bind()

    op.add_column('items', sa.Column('ubicacion', sa.String(length=200), nullable=True))
    conn.execute(text(
        "UPDATE items SET ubicacion = "
        "(SELECT nombre FROM ubicaciones WHERE ubicaciones.id = items.ubicacion_id) "
        "WHERE ubicacion_id IS NOT NULL"))

    op.drop_constraint('fk_items_ubicacion_id', 'items', type_='foreignkey')
    op.drop_constraint('fk_items_area_id', 'items', type_='foreignkey')
    op.drop_column('items', 'ubicacion_id')
    op.drop_column('items', 'area_id')

    op.drop_table('ubicaciones')
    op.drop_table('areas')
