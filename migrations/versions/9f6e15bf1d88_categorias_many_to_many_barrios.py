"""categorias-many-to-many-barrios

Revision ID: 9f6e15bf1d88
Revises: 43208155a47c
Create Date: 2026-06-10 21:17:59.148745

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '9f6e15bf1d88'
down_revision = '43208155a47c'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Tabla de asociación muchos-a-muchos
    op.create_table(
        'categoria_barrios',
        sa.Column('categoria_id', sa.Integer(), nullable=False),
        sa.Column('barrio_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['barrio_id'], ['barrios.id']),
        sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id']),
        sa.PrimaryKeyConstraint('categoria_id', 'barrio_id'),
    )

    # 2. Agrega es_global con default False (server_default para filas existentes)
    op.add_column(
        'categorias',
        sa.Column('es_global', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # 3. Migración de datos (ANTES de eliminar barrio_id)
    conn = op.get_bind()

    # Categorías con barrio_id NULL → globales
    conn.execute(sa.text("UPDATE categorias SET es_global = TRUE WHERE barrio_id IS NULL"))

    # Categorías con barrio_id → asociarlas al barrio en la tabla intermedia
    conn.execute(sa.text(
        "INSERT INTO categoria_barrios (categoria_id, barrio_id) "
        "SELECT id, barrio_id FROM categorias WHERE barrio_id IS NOT NULL"
    ))

    # 4. Elimina FK y columna barrio_id
    # Busca el nombre real de la FK en information_schema (evita hardcodear el nombre auto-generado)
    result = conn.execute(sa.text(
        "SELECT CONSTRAINT_NAME "
        "FROM information_schema.KEY_COLUMN_USAGE "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "  AND TABLE_NAME = 'categorias' "
        "  AND COLUMN_NAME = 'barrio_id' "
        "  AND REFERENCED_TABLE_NAME = 'barrios' "
        "LIMIT 1"
    ))
    fk_name = result.scalar()
    if fk_name:
        op.drop_constraint(fk_name, 'categorias', type_='foreignkey')

    op.drop_column('categorias', 'barrio_id')


def downgrade():
    # Recrea barrio_id y restaura datos desde categoria_barrios (toma el primer barrio por categoría)
    op.add_column(
        'categorias',
        sa.Column('barrio_id', mysql.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(None, 'categorias', 'barrios', ['barrio_id'], ['id'])

    conn = op.get_bind()
    # Restaura barrio_id para categorías no globales (primer barrio asociado)
    conn.execute(sa.text(
        "UPDATE categorias c "
        "INNER JOIN ("
        "  SELECT categoria_id, MIN(barrio_id) AS barrio_id "
        "  FROM categoria_barrios GROUP BY categoria_id"
        ") cb ON c.id = cb.categoria_id "
        "SET c.barrio_id = cb.barrio_id "
        "WHERE c.es_global = FALSE"
    ))

    op.drop_column('categorias', 'es_global')
    op.drop_table('categoria_barrios')
