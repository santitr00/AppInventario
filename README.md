# GLTEC Inventario

Sistema web de gestión de inventario multi-barrio. Permite a cada zona administrar sus equipos y materiales de forma independiente, con roles diferenciados y trazabilidad de cambios.

![Login](docs/screenshots/login.png)

---

## Características

- **Multi-barrio** — cada barrio tiene su propio inventario aislado
- **Roles** — admin global, gestor por barrio, cliente de solo lectura
- **Imágenes** — cada ítem puede tener foto adjunta
- **Historial** — registro de altas, bajas y modificaciones
- **Búsqueda avanzada** — filtros por barrio, categoría, estado y texto libre
- **Exportación CSV** — descarga de inventario completo o filtrado
- **Importación Excel** — carga masiva desde planilla `.xlsx`
- **Responsive** — funciona en celular y escritorio

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · Flask 3.1 · Flask-Login · Flask-WTF |
| ORM | SQLAlchemy 2 · Flask-Migrate (Alembic) |
| Base de datos | MySQL 8.0 |
| Servidor | Gunicorn (Unix socket) · Nginx reverse proxy |
| OS destino | Ubuntu 24.04 LTS |

---

## Screenshots

| Dashboard | Detalle de ítem | Panel admin |
|---|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Item](docs/screenshots/item.png) | ![Admin](docs/screenshots/admin.png) |

---

## Instalación local

**Requisitos:** Python 3.10+, MySQL 8.0

```bash
# 1. Clonar y crear entorno virtual
git clone https://github.com/tu-usuario/inventario-gltec.git
cd inventario-gltec
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Crear base de datos
mysql -u root -e "CREATE DATABASE inventario_gltec CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 5. Aplicar migraciones y cargar datos iniciales
flask db upgrade
python scripts/seed.py

# 6. Levantar
python run.py
```

Acceder a `http://localhost:5000` — credenciales por defecto: `admin` / `admin2026`

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
