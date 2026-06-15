"""categoria pertenece a un solo barrio (FK), elimina M2M y es_global

Vuelve al modelo de una categoría = un barrio. Las categorías globales y
compartidas se "abren" (fan-out): cada una se copia como categoría local en
cada barrio donde aplicaba o donde tenía ítems, y los ítems se reapuntan a la
copia de su propio barrio. Si en un barrio ya existía una categoría con el
mismo nombre, se fusionan (los ítems van a la existente) para respetar el
nuevo UNIQUE(nombre, barrio_id).

Revision ID: b1c2d3e4f5a6
Revises: c542fbfe8b80
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = 'b1c2d3e4f5a6'
down_revision = 'c542fbfe8b80'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1. Nueva columna barrio_id (temporalmente nullable para poder poblarla)
    op.add_column('categorias', sa.Column('barrio_id', sa.Integer(), nullable=True))

    # 2. Estado actual
    cats = list(conn.execute(text(
        "SELECT id, nombre, color, icono, es_global FROM categorias ORDER BY id")))
    barrios = [r[0] for r in conn.execute(text("SELECT id FROM barrios"))]

    asignados = {}  # categoria_id -> {barrio_id, ...} (tabla M2M)
    for cid, bid in conn.execute(text(
            "SELECT categoria_id, barrio_id FROM categoria_barrios")):
        asignados.setdefault(cid, set()).add(bid)

    item_barrios = {}  # categoria_id -> {barrio_id, ...} (de los ítems)
    for cid, bid in conn.execute(text(
            "SELECT DISTINCT categoria_id, barrio_id FROM items")):
        item_barrios.setdefault(cid, set()).add(bid)

    def destinos(c):
        """Barrios donde la categoría debe existir tras el fan-out."""
        t = set(barrios) if c.es_global else set(asignados.get(c.id, set()))
        t |= item_barrios.get(c.id, set())
        return sorted(b for b in t if b is not None)

    claimed = {}      # (barrio_id, nombre_lower) -> categoria_id final
    item_remap = {}   # (categoria_id_vieja, barrio_id) -> categoria_id final

    # Pass 1: cada categoría conserva su propia fila en el primer barrio libre
    for c in cats:
        for b in destinos(c):
            key = (b, c.nombre.strip().lower())
            if key not in claimed:
                claimed[key] = c.id
                conn.execute(text(
                    "UPDATE categorias SET barrio_id = :b WHERE id = :id"),
                    {"b": b, "id": c.id})
                break

    # Pass 2: clones para el resto de los barrios (o merge si el nombre ya existe)
    for c in cats:
        for b in destinos(c):
            key = (b, c.nombre.strip().lower())
            if key in claimed:
                final_id = claimed[key]
            else:
                res = conn.execute(text(
                    "INSERT INTO categorias (nombre, color, icono, barrio_id) "
                    "VALUES (:n, :co, :ic, :b)"),
                    {"n": c.nombre, "co": c.color, "ic": c.icono, "b": b})
                final_id = res.lastrowid
                claimed[key] = final_id
            item_remap[(c.id, b)] = final_id

    # 3. Reapuntar cada ítem a la categoría de su propio barrio
    for (old_cat, b), final_id in item_remap.items():
        if final_id != old_cat:
            conn.execute(text(
                "UPDATE items SET categoria_id = :new "
                "WHERE categoria_id = :old AND barrio_id = :b"),
                {"new": final_id, "old": old_cat, "b": b})

    # 4. Borrar categorías que no conservaron fila (todas sus copias se fusionaron
    #    o no tenían barrios ni ítems). Sus ítems ya fueron reapuntados arriba.
    conn.execute(text("DELETE FROM categorias WHERE barrio_id IS NULL"))

    # 5. Estructura final: FK + NOT NULL + UNIQUE, y baja del M2M / es_global
    op.drop_table('categoria_barrios')
    op.drop_column('categorias', 'es_global')
    op.alter_column('categorias', 'barrio_id',
                    existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key('fk_categorias_barrio_id', 'categorias', 'barrios',
                          ['barrio_id'], ['id'])
    op.create_unique_constraint('uq_categoria_nombre_barrio', 'categorias',
                                ['nombre', 'barrio_id'])


def downgrade():
    conn = op.get_bind()

    op.drop_constraint('uq_categoria_nombre_barrio', 'categorias', type_='unique')
    op.drop_constraint('fk_categorias_barrio_id', 'categorias', type_='foreignkey')

    op.add_column('categorias', sa.Column(
        'es_global', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        'categoria_barrios',
        sa.Column('categoria_id', sa.Integer(), nullable=False),
        sa.Column('barrio_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['barrio_id'], ['barrios.id']),
        sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id']),
        sa.PrimaryKeyConstraint('categoria_id', 'barrio_id'),
    )
    conn.execute(text(
        "INSERT INTO categoria_barrios (categoria_id, barrio_id) "
        "SELECT id, barrio_id FROM categorias WHERE barrio_id IS NOT NULL"))

    op.drop_column('categorias', 'barrio_id')
