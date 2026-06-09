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

---

## Variables de entorno

Archivo `.env` (ver `.env.example`):

| Variable | Descripción |
|---|---|
| `DB_USER` | Usuario MySQL |
| `DB_PASS` | Contraseña MySQL |
| `DB_NAME` | Nombre de la base de datos |
| `SECRET_KEY` | Clave secreta Flask (generar con `secrets.token_hex(32)`) |
| `DB_HOST` | Host MySQL (default: `127.0.0.1`) |
| `DB_PORT` | Puerto MySQL (default: `3306`) |

---

## Roles y permisos

| Rol | Alcance | Puede hacer |
|---|---|---|
| `admin` | Global | Todo: usuarios, barrios, ítems, exportar |
| `gestor` | Su barrio | Crear/editar/eliminar ítems, importar |
| `cliente` | Su barrio | Solo lectura y búsqueda |

---

## Importar desde Excel

```bash
# Importar planilla al barrio con ID 1
python scripts/import_excel.py datos_inventario.xlsx 1
```

El archivo Excel debe tener columnas: `nombre`, `descripcion`, `categoria`, `cantidad`, `estado`.

---

## Estructura del proyecto

```
inventario-gltec/
├── app/
│   ├── __init__.py              # App factory, extensiones, logging
│   ├── models.py                # Barrio, User, Categoria, Item, Historial
│   ├── blueprints/
│   │   ├── auth/                # Login / logout
│   │   ├── inventory/           # CRUD ítems, dashboard
│   │   ├── search/              # Búsqueda con filtros
│   │   └── admin/               # Gestión de usuarios y barrios
│   ├── templates/
│   │   ├── layouts/base.html
│   │   ├── auth/login.html
│   │   ├── inventory/
│   │   ├── search/
│   │   └── admin/
│   └── static/
│       └── uploads/             # Fotos de ítems
├── migrations/                  # Alembic
├── scripts/
│   ├── seed.py                  # Datos iniciales
│   └── import_excel.py          # Importador Excel
├── logs/                        # Logs de la app (gitignored)
├── wsgi.py                      # Entry point Gunicorn
├── gunicorn.conf.py
├── run.py                       # Dev server
├── requirements.txt
├── .env.example
└── DEPLOY.md                    # Guía de deploy en producción
```

---

## Deploy en producción

Ver [DEPLOY.md](DEPLOY.md) para la guía completa paso a paso en Ubuntu 24.04 con Nginx + Gunicorn + MySQL.

Resumen del stack en producción:

```
Internet → Nginx (SSL/TLS) → Gunicorn (Unix socket) → Flask app → MySQL
```

---

## Licencia

Uso interno — GLTEC Tecnología sin Límites.
