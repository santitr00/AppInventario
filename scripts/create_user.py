"""
Crea o actualiza un usuario en la base de datos.

Uso:
    python scripts/create_user.py <username> <password> <rol> [barrio_id]

Roles:
    admin   — acceso global a todo
    gestor  — crea/edita ítems en su barrio
    cliente — solo lectura

Ejemplos:
    python scripts/create_user.py juan Pass1234 gestor 1
    python scripts/create_user.py laura Pass1234 admin
    python scripts/create_user.py pedro Pass1234 cliente 2
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Barrio

ROLES_VALIDOS = ("admin", "gestor", "cliente")

def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    username  = sys.argv[1]
    password  = sys.argv[2]
    rol       = sys.argv[3].lower()
    barrio_id = int(sys.argv[4]) if len(sys.argv) >= 5 else None

    if rol not in ROLES_VALIDOS:
        print(f"ERROR: rol debe ser uno de {ROLES_VALIDOS}")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        # Verificar barrio si corresponde
        if barrio_id:
            barrio = db.session.get(Barrio, barrio_id)
            if not barrio:
                barrios = Barrio.query.all()
                print(f"ERROR: barrio_id {barrio_id} no existe.")
                print("Barrios disponibles:")
                for b in barrios:
                    print(f"  {b.id} — {b.nombre}")
                sys.exit(1)

        # Crear o actualizar
        user = User.query.filter_by(username=username).first()
        if user:
            user.set_password(password)
            user.rol = rol
            user.barrio_id = barrio_id
            accion = "actualizado"
        else:
            user = User(
                username=username,
                email=f"{username}@gltec.com.ar",
                nombre_completo=username.capitalize(),
                rol=rol,
                barrio_id=barrio_id,
            )
            user.set_password(password)
            db.session.add(user)
            accion = "creado"

        db.session.commit()

        barrio_nombre = db.session.get(Barrio, barrio_id).nombre if barrio_id else "global"
        print(f"✓ Usuario {accion}: {username} | rol: {rol} | barrio: {barrio_nombre}")

        # Mostrar todos los usuarios
        print("\nUsuarios actuales:")
        for u in User.query.order_by(User.id).all():
            b = f"[{u.barrio.nombre}]" if u.barrio_id else "[global]"
            print(f"  {u.id}  {u.username:<20} {u.rol:<10} {b}")


if __name__ == "__main__":
    main()
