"""
Carga un barrio de demostración con categorías, items variados y un usuario gestor.

Uso:
    python scripts/seed_ejemplo.py          # crea si no existe
    python scripts/seed_ejemplo.py --reset  # borra el barrio demo y lo recrea

Credenciales del gestor demo:
    usuario: ejemplo
    contraseña: ejemplo
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date

from app import create_app, db
from app.models import Barrio, Categoria, Item, User

BARRIO_NOMBRE = "Barrio Ejemplo"
USUARIO_DEMO = "ejemplo"
USUARIO_PASS = "ejemplo"

app = create_app()

with app.app_context():

    # ── Reset opcional ──────────────────────────────────────────────────────
    if "--reset" in sys.argv:
        barrio_viejo = Barrio.query.filter_by(nombre=BARRIO_NOMBRE).first()
        if barrio_viejo:
            Item.query.filter_by(barrio_id=barrio_viejo.id).delete()
            user_viejo = User.query.filter_by(username=USUARIO_DEMO).first()
            if user_viejo:
                db.session.delete(user_viejo)
            db.session.delete(barrio_viejo)
            db.session.commit()
            print("Reset completado.")

    # ── Idempotencia ────────────────────────────────────────────────────────
    barrio = Barrio.query.filter_by(nombre=BARRIO_NOMBRE).first()
    if barrio and Item.query.filter_by(barrio_id=barrio.id).count() > 0:
        print(f'El barrio "{BARRIO_NOMBRE}" ya existe con items. '
              "Usá --reset para recrearlo.")
        sys.exit(0)

    # ── Barrio demo ─────────────────────────────────────────────────────────
    if not barrio:
        barrio = Barrio(nombre=BARRIO_NOMBRE, direccion="Demo, Argentina")
        db.session.add(barrio)
        db.session.commit()
    print(f'✓ Barrio: {barrio.nombre} (id={barrio.id})')

    # ── Categorías (asignadas al barrio demo) ───────────────────────────────
    cats_data = [
        {"nombre": "Cámaras y CCTV",       "color": "#2E86C1", "icono": "bi-camera-video"},
        {"nombre": "Redes e Informática",   "color": "#1A7A4A", "icono": "bi-router"},
        {"nombre": "Control de Acceso",     "color": "#8E44AD", "icono": "bi-door-closed"},
        {"nombre": "Mantenimiento",         "color": "#E67E22", "icono": "bi-tools"},
        {"nombre": "Luminaria",             "color": "#F1C40F", "icono": "bi-lightbulb"},
    ]
    cats = {}
    for c in cats_data:
        obj = Categoria.query.filter_by(nombre=c["nombre"], barrio_id=barrio.id).first()
        if not obj:
            obj = Categoria(barrio_id=barrio.id, **c)
            db.session.add(obj)
        cats[c["nombre"]] = obj
    db.session.commit()
    print(f'✓ {len(cats)} categorías')

    # ── Items ────────────────────────────────────────────────────────────────
    def item(nombre, cat_nombre, ubicacion, estado="Operativo", cantidad=1,
             codigo=None, marca=None, modelo=None, numero_serie=None,
             fecha_ingreso=None, descripcion=None, notas=None):
        return Item(
            nombre=nombre,
            categoria_id=cats[cat_nombre].id,
            barrio_id=barrio.id,
            ubicacion=ubicacion,
            estado=estado,
            cantidad=cantidad,
            codigo=codigo,
            marca=marca,
            modelo=modelo,
            numero_serie=numero_serie,
            fecha_ingreso=fecha_ingreso,
            descripcion=descripcion,
            notas=notas,
            activo=True,
        )

    items = [
        # ── Cámaras y CCTV ──────────────────────────────────────────────────
        item("Cámara IP Domo interior", "Cámaras y CCTV",
             "Entrada principal", "Operativo", 1,
             "CAM-001", "Hikvision", "DS-2CD2143G2-I", "HK-CAM-001",
             date(2023, 3, 10), "Cámara domo 4MP con IR 40m"),

        item("Cámara IP Domo interior", "Cámaras y CCTV",
             "Salón de usos múltiples", "Operativo", 1,
             "CAM-002", "Hikvision", "DS-2CD2143G2-I", "HK-CAM-002",
             date(2023, 3, 10)),

        item("Cámara IP bala exterior", "Cámaras y CCTV",
             "Perímetro norte", "Operativo", 1,
             "CAM-003", "Dahua", "IPC-HFW2831T-AS", "DH-CAM-003",
             date(2023, 4, 5), "Cámara bala 8MP, IP67"),

        item("Cámara IP bala exterior", "Cámaras y CCTV",
             "Perímetro sur", "En reparación", 1,
             "CAM-004", "Dahua", "IPC-HFW2831T-AS", "DH-CAM-004",
             date(2023, 4, 5), None, "Falla intermitente de imagen, enviada a técnico"),

        item("Cámara IP PTZ exterior", "Cámaras y CCTV",
             "Avenida principal", "Operativo", 1,
             "CAM-005", "Hikvision", "DS-2DE4425IWG-E", "HK-PTZ-005",
             date(2024, 1, 20), "PTZ 4MP 25x zoom óptico"),

        item("DVR 16 canales", "Cámaras y CCTV",
             "Sala de servidores", "Operativo", 1,
             "DVR-001", "Hikvision", "iDS-7216HQHI-M2/S", "HK-DVR-001",
             date(2023, 3, 10), "16 canales AcuSense, 2 bahías HDD"),

        item("Disco duro NAS 4TB", "Cámaras y CCTV",
             "Sala de servidores", "Stock bajo", 3,
             "HDD-001", "WD", "WD40PURZ", None,
             date(2023, 3, 10), "Purple, para uso 24/7 en DVR",
             "Quedan 3 unidades; reponer cuando quede 1"),

        item("Switch PoE 8 puertos", "Cámaras y CCTV",
             "Caja de distribución A", "Operativo", 1,
             "SW-POE-01", "TP-Link", "TL-SG1008P", "TP-SW-001",
             date(2023, 3, 10), "PoE+ 62W total"),

        # ── Redes e Informática ──────────────────────────────────────────────
        item("Router principal", "Redes e Informática",
             "Sala de servidores", "Operativo", 1,
             "NET-001", "MikroTik", "RB750Gr3", "MT-RT-001",
             date(2022, 11, 15), "hEX, 5 puertos Gigabit"),

        item("Access Point exterior", "Redes e Informática",
             "Tanque de agua", "Operativo", 1,
             "AP-001", "Ubiquiti", "UAP-AC-M", "UB-AP-001",
             date(2022, 11, 15), "802.11ac Wave 2, IP65"),

        item("Access Point exterior", "Redes e Informática",
             "Quincho", "Operativo", 1,
             "AP-002", "Ubiquiti", "UAP-AC-M", "UB-AP-002",
             date(2023, 6, 1)),

        item("Access Point exterior", "Redes e Informática",
             "Playgrounds", "Fuera de servicio", 1,
             "AP-003", "Ubiquiti", "UAP-AC-M", "UB-AP-003",
             date(2023, 6, 1), None, "Sin señal desde tormenta del 02/05. Revisar antena"),

        item("Switch administrable 8p", "Redes e Informática",
             "Administración", "Operativo", 1,
             "SW-002", "TP-Link", "TL-SG108E", "TP-SW-002",
             date(2022, 11, 15)),

        item("UPS 1500VA", "Redes e Informática",
             "Sala de servidores", "Operativo", 1,
             "UPS-001", "APC", "BX1500M-AR", "APC-001",
             date(2022, 11, 15), "Autonomía ~25 min con carga actual"),

        item("PC escritorio", "Redes e Informática",
             "Administración", "Operativo", 1,
             "PC-001", "HP", "ProDesk 400 G6", "HP-PC-001",
             date(2022, 11, 15), "Core i5, 8GB RAM, SSD 256GB"),

        item("Notebook guardia", "Redes e Informática",
             "Garita de ingreso", "En reparación", 1,
             "NB-001", "Lenovo", "IdeaPad 3 15ITL6", "LN-NB-001",
             date(2023, 1, 20), None, "Teclado con teclas sueltas, esperando repuesto"),

        item("Impresora multifunción", "Redes e Informática",
             "Administración", "Operativo", 1,
             "IMP-001", "Epson", "L3150", "EP-001",
             date(2022, 11, 15), "Sistema de tinta continuo"),

        # ── Control de Acceso ────────────────────────────────────────────────
        item("Barrera vehicular entrada", "Control de Acceso",
             "Entrada vehicular", "Operativo", 1,
             "BV-001", "FAAC", "B680H", "FC-BV-001",
             date(2022, 10, 5), "3.5m de brazo, motor reductor"),

        item("Barrera vehicular salida", "Control de Acceso",
             "Salida vehicular", "En reparación", 1,
             "BV-002", "FAAC", "B680H", "FC-BV-002",
             date(2022, 10, 5), None, "Motor no responde al comando. Técnico programado para viernes"),

        item("Videoportero color", "Control de Acceso",
             "Entrada peatonal", "Operativo", 1,
             "INT-001", "Hikvision", "DS-KV8113-WME1", "HK-INT-001",
             date(2023, 2, 14), "Con desbloqueo remoto"),

        item("Lector RFID + controlador", "Control de Acceso",
             "Sala de servidores", "Operativo", 1,
             "ACC-001", "ZKTeco", "MA300", "ZK-ACC-001",
             date(2023, 2, 14), "Hasta 3000 usuarios"),

        item("Cámara LPR (lectura de patentes)", "Control de Acceso",
             "Entrada vehicular", "Operativo", 1,
             "LPR-001", "Hikvision", "DS-2CD4A26FWD-IZS", "HK-LPR-001",
             date(2023, 5, 20), "Lectura de matrículas 24/7"),

        item("Tarjetas RFID Mifare", "Control de Acceso",
             "Administración", "Stock bajo", 40,
             None, None, None, None,
             None, "Tarjetas de proximidad 13.56 MHz",
             "Stock mínimo sugerido: 50 unidades"),

        item("Botonera de emergencia", "Control de Acceso",
             "Garita de ingreso", "Operativo", 2,
             None, None, None, None,
             date(2022, 10, 5), "Apertura manual de barrera en caso de emergencia"),

        # ── Mantenimiento ────────────────────────────────────────────────────
        item("Generador eléctrico 7kW", "Mantenimiento",
             "Depósito", "Operativo", 1,
             "GEN-001", "Honda", "EU7000is", "HD-GEN-001",
             date(2021, 8, 15), "Arranque eléctrico, 7kVA", "Último service: 03/2025"),

        item("Cargador de batería 12/24V", "Mantenimiento",
             "Depósito", "Operativo", 1,
             "CARG-001", "Stanley", "BC50BS", None,
             date(2022, 3, 10)),

        item("Escalera de aluminio 6m", "Mantenimiento",
             "Depósito", "Operativo", 1,
             "ESC-001", "Facal", "Extensible 6m", None,
             date(2021, 8, 15)),

        item("Taladro percutor", "Mantenimiento",
             "Depósito", "Operativo", 1,
             "TAL-001", "Bosch", "GSB 600 RE", None,
             date(2021, 8, 15)),

        item("Amoladora angular 115mm", "Mantenimiento",
             "Depósito", "En reparación", 1,
             "AMO-001", "Bosch", "GWS 7-115", None,
             date(2021, 8, 15), None, "Chispa en la esmeriladora. Llevar al service"),

        item("Kit de herramientas eléctricas", "Mantenimiento",
             "Depósito", "Operativo", 1,
             "KIT-001", None, None, None,
             date(2021, 8, 15), "Llaves, destornilladores, pinzas, multímetro"),

        item("Manguera de jardín 50m", "Mantenimiento",
             "Depósito", "Stock bajo", 2,
             None, None, None, None,
             None, None, "Una con pérdida en conector. Reponer"),

        item("Soplete a gas", "Mantenimiento",
             "Depósito", "Operativo", 1,
             None, "Ratio", None, None,
             date(2022, 6, 1)),

        # ── Luminaria ────────────────────────────────────────────────────────
        item("Luminaria LED vial 150W", "Luminaria",
             "Avenida principal", "Operativo", 8,
             "LUM-001", "Osram", "Siteco 5LF", None,
             date(2022, 9, 1), "Temperatura color 4000K, IP66"),

        item("Luminaria LED sendero 80W", "Luminaria",
             "Senderos internos", "Operativo", 12,
             "LUM-002", "Philips", "BGP352", None,
             date(2022, 9, 1), "Temperatura color 3000K, IP65"),

        item("Luminaria LED sendero 80W", "Luminaria",
             "Área de juegos", "Fuera de servicio", 2,
             "LUM-003", "Philips", "BGP352", None,
             date(2022, 9, 1), None, "Dos unidades con driver quemado. Presupuesto solicitado"),

        item("Lámpara de emergencia LED", "Luminaria",
             "Garita de ingreso", "Operativo", 3,
             None, None, None, None,
             date(2023, 1, 10), "Autonomía 3hs"),

        item("Transformador de luminaria 150W", "Luminaria",
             "Sala de servidores", "Fuera de servicio", 1,
             None, None, None, None,
             date(2022, 9, 1), None, "En stock para repuesto de avería"),

        item("Proyector LED exterior 200W", "Luminaria",
             "Cancha de tenis", "Operativo", 4,
             "PROY-001", "Ledvance", "FL 200W", None,
             date(2024, 2, 15), "IP65, 20000 lm"),
    ]

    for it in items:
        db.session.add(it)
    db.session.commit()
    print(f'✓ {len(items)} items cargados')

    # ── Usuario gestor demo ──────────────────────────────────────────────────
    u = User.query.filter_by(username=USUARIO_DEMO).first()
    if not u:
        u = User(
            username=USUARIO_DEMO,
            email="ejemplo@gltec.com.ar",
            nombre_completo="Usuario Demo",
            rol="gestor",
            barrio_id=barrio.id,
        )
        u.set_password(USUARIO_PASS)
        db.session.add(u)
        db.session.commit()
        print(f'✓ Gestor demo creado: {USUARIO_DEMO} / {USUARIO_PASS}')
    else:
        print(f'✓ Gestor demo ya existe: {USUARIO_DEMO}')

    print()
    print("Seed de ejemplo completado.")
    print(f"  Barrio:   {BARRIO_NOMBRE}")
    print(f"  Items:    {Item.query.filter_by(barrio_id=barrio.id).count()}")
    print(f"  Usuario:  {USUARIO_DEMO} / {USUARIO_PASS}  (rol: gestor)")
