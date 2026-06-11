"""
Inicializa la base de datos con datos de ejemplo.
Uso: flask shell < scripts/seed.py  O  python scripts/seed.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Barrio, Categoria

app = create_app()

with app.app_context():
    # ── Barrios ──
    barrios_data = [
        {"nombre": "Vida Barrio Cerrado", "direccion": "Rosario, Santa Fe"},
        {"nombre": "Vida Club de Campo", "direccion": "Rosario, Santa Fe"},
        {"nombre": "Vida Lagoon", "direccion": "Rosario, Santa Fe"},
    ]
    for b_data in barrios_data:
        if not Barrio.query.filter_by(nombre=b_data["nombre"]).first():
            db.session.add(Barrio(**b_data))

    db.session.commit()

    # ── Categorías globales ──
    categorias_data = [
        {"nombre": "Equipos de Seguridad", "color": "#2E86C1", "icono": "bi-camera-video"},
        {"nombre": "Materiales de Mantenimiento", "color": "#27AE60", "icono": "bi-tools"},
        {"nombre": "Biblioteca", "color": "#8E44AD", "icono": "bi-book"},
        {"nombre": "Mobiliario", "color": "#E67E22", "icono": "bi-house"},
        {"nombre": "Otros", "color": "#7F8C8D", "icono": "bi-box"},
    ]
    for c_data in categorias_data:
        if not Categoria.query.filter_by(nombre=c_data["nombre"]).first():
            db.session.add(Categoria(es_global=True, **c_data))

    db.session.commit()

    # ── Admin user ──
    admin_user = os.getenv("ADMIN_USER", "admin")
    if not User.query.filter_by(username=admin_user).first():
        u = User(
            username=admin_user,
            email=os.getenv("ADMIN_EMAIL", "admin@gltec.com.ar"),
            nombre_completo="Administrador GLTEC",
            rol="admin",
        )
        u.set_password(os.getenv("ADMIN_PASS", "admin2026"))
        db.session.add(u)
        db.session.commit()
        print(f"✓ Admin creado: {admin_user}")

    print(f"✓ {Barrio.query.count()} barrios")
    print(f"✓ {Categoria.query.count()} categorías")
    print(f"✓ {User.query.count()} usuarios")
    print("Seed completado.")
