# Inventario de Barrios — GLTEC

Plataforma web de gestión de inventario multi-barrio desarrollada con Flask + MySQL.

<img width="1917" height="904" alt="image" src="https://github.com/user-attachments/assets/42d8a286-4aec-4a23-9e66-7501c3a17975" />

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
