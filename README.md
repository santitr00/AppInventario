# Inventario de Barrios — GLTEC

Plataforma web de gestión de inventario multi-barrio desarrollada con Flask + MySQL.

## Setup rápido

```bash
# 1. Crear base de datos MySQL
mysql -u root -e "CREATE DATABASE inventario_barrios CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. Configurar
cp .env.example .env
# Editar .env con tus credenciales de MySQL

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear tablas y datos iniciales
python scripts/seed.py

# 5. Ejecutar
python run.py
```

Acceder a http://localhost:5000 — Login: `admin` / `admin2026`

## Importar datos desde Excel

```bash
python scripts/import_excel.py datos_inventario.xlsx 1
# El "1" es el ID del barrio destino
```

## Estructura del proyecto

```
inventario/
├── app/
│   ├── __init__.py              # App factory + extensions
│   ├── models.py                # Modelos: Barrio, User, Categoria, Item, Historial
│   ├── blueprints/
│   │   ├── auth/routes.py       # Login / logout
│   │   ├── inventory/routes.py  # CRUD de ítems, dashboard
│   │   ├── search/routes.py     # Búsqueda con filtros
│   │   └── admin/routes.py      # Gestión de usuarios y barrios
│   ├── templates/
│   │   ├── layouts/base.html    # Layout con sidebar, topbar, estilos
│   │   ├── auth/login.html      # Pantalla de login
│   │   ├── inventory/           # index, detalle_item, form_item
│   │   ├── search/buscar.html   # Búsqueda con filtros
│   │   └── admin/               # usuarios, form_usuario, barrios, form_barrio
│   └── static/
├── scripts/
│   ├── seed.py                  # Datos iniciales
│   └── import_excel.py          # Importador de Excel
├── requirements.txt
├── run.py
└── .env.example
```
