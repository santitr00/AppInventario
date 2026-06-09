# DEPLOY — InventarioGLTEC

Guía de despliegue en Ubuntu 24.04 LTS con Nginx, Gunicorn y MySQL 8.0.  
Asume que el servidor ya tiene el stack base de AppMant: UFW activo, Nginx 1.24,
MySQL 8.0, Certbot, usuario `deploy` con sudo y login por SSH key.

---

## Variables de referencia

Reemplazá estos valores a lo largo de la guía antes de ejecutar los comandos.

| Variable | Valor |
|---|---|
| `APP_DIR` | `/home/deploy/apps/InventarioGLTEC` |
| `DB_NAME` | `inventario_gltec` |
| `DB_USER` | `inventario_user` |
| `DB_PASS` | *(generá con `openssl rand -hex 24`)* |
| `SECRET_KEY` | *(generá con `python3 -c "import secrets; print(secrets.token_hex(32))"`)* |
| `DOMINIO` | *(tu dominio real, ej: `inventario.gltec.com.ar`)* |

---

## 1. Crear estructura de directorios y subir el código

```bash
# Conectarse al servidor
ssh deploy@IP_DEL_SERVIDOR

# Crear raíz de la app y directorio de logs
mkdir -p /home/deploy/apps/InventarioGLTEC/logs

# ── Opción A: clonar desde Git (recomendado) ──
cd /home/deploy/apps
git clone https://github.com/TU_USUARIO/TU_REPO.git InventarioGLTEC

# ── Opción B: subir con rsync desde tu máquina local ──
# Ejecutar desde Windows (PowerShell o Git Bash), NO en el servidor:
# rsync -avz --exclude='venv/' --exclude='__pycache__/' --exclude='.env' \
#   /d/ProyectoInventario/ deploy@IP_DEL_SERVIDOR:/home/deploy/apps/InventarioGLTEC/

# Verificar que llegaron los archivos clave
ls /home/deploy/apps/InventarioGLTEC/
# Debe mostrar: app/  gunicorn.conf.py  migrations/  requirements.txt  run.py  scripts/  wsgi.py
```

---

## 2. Paquetes apt adicionales

Esta app no requiere librerías de sistema adicionales.  
Todos los paquetes Python son puro Python (PyMySQL, openpyxl, etc.).

```bash
# Verificar que Python 3.12 está disponible (Ubuntu 24.04 lo incluye por defecto)
python3.12 --version
# Esperado: Python 3.12.x

# Solo instalar si pip falla al compilar cryptography (caso raro en Ubuntu 24.04):
# sudo apt install python3.12-dev libssl-dev libffi-dev -y
```

---

## 3. Crear el entorno virtual e instalar dependencias

```bash
cd /home/deploy/apps/InventarioGLTEC

# Crear venv con Python 3.12
python3.12 -m venv venv

# Activar
source venv/bin/activate

# Actualizar pippip install --upgrade pip
pip install --upgrade pip

# Instalar dependencias (incluye gunicorn)
pip install -r requirements.txt

# Verificar instalación
gunicorn --version
# Esperado: gunicorn (version 22.x.x)

python -c "import flask, flask_sqlalchemy, flask_migrate, pymysql; print('OK')"
```

---

## 4. Crear la base de datos MySQL

```bash
# Acceder a MySQL como root
sudo mysql -u root
```

```sql
-- Pegar y ejecutar en la consola MySQL:
CREATE DATABASE appinv
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'invuser'@'localhost' IDENTIFIED BY 'gdfsd-7437';

GRANT ALL PRIVILEGES ON appinv.* TO 'invuser'@'localhost';

FLUSH PRIVILEGES;

EXIT;
```

```bash
# Verificar que el usuario puede conectarse
mysql -u userinv -p appinv -e "SELECT 1;"
# Ingresar TU_PASSWORD_DB cuando pida contraseña — debe retornar "1"
```

---

## 5. Configurar variables de entorno

```bash
cd /home/deploy/apps/InventarioGLTEC

# Copiar el template
cp .env.production .env

# Editar con los valores reales
nano .env
```

Contenido final de `.env` (reemplazá TODOS los valores en mayúsculas):

```ini
FLASK_APP=wsgi:app
FLASK_ENV=production
SECRET_KEY=<salida de: python3 -c "import secrets; print(secrets.token_hex(32))">

DB_HOST=localhost
DB_PORT=3306
DB_USER=inventario_user
DB_PASS=<TU_PASSWORD_DB>
DB_NAME=inventario_gltec

GUNICORN_WORKERS=3
```

```bash
# Permisos seguros — solo el owner puede leer
chmod 600 /home/deploy/apps/appinv/.env
ls -la /home/deploy/apps/appinv/.env
# Debe mostrar: -rw------- 1 deploy deploy
```

---

## 6. Preparar directorio de uploads

La app crea `app/static/uploads/` automáticamente al iniciar, pero es mejor
crearlo manualmente con los permisos correctos antes del primer arranque.

```bash
# Crear directorio
mkdir -p /home/deploy/apps/appinv/app/static/uploads

# Propietario: deploy (Gunicorn escribe aquí)
chown deploy:deploy /home/deploy/apps/appinv/app/static/uploads

# Permisos 755: deploy puede escribir, www-data (Nginx) puede leer y atravesar
chmod 755 /home/deploy/apps/appinv/app/static/uploads

# Verificar
ls -la /home/deploy/apps/appinv/app/static/
# Debe mostrar: drwxr-xr-x deploy deploy uploads/
```

> **Nota:** Nginx sirve los estáticos con `alias /home/deploy/apps/appinv/app/static/`.
> Para que `www-data` pueda traversar el path hasta ese directorio, `/home/deploy/`
> debe tener permisos `o+x` (al menos 750 → 755). Si ya funciona con AppMant, esto
> ya está resuelto. Si no, ejecutar: `chmod 755 /home/deploy/`

---

## 7. Aplicar migraciones y cargar datos iniciales

```bash
cd /home/deploy/apps/appinv
source venv/bin/activate

# 7a. Crear las tablas con Alembic (NO usar db.create_all())
flask db upgrade

# Confirmar que las tablas existen
mysql -u invuser -p appinv -e "SHOW TABLES;"
# Debe mostrar: barrios, categorias, historial, items, users

# 7b. Cargar datos iniciales: barrios, categorías globales y usuario admin
# Las credenciales del admin se pasan inline — no quedan en ningún archivo persistente
# Usá comillas simples alrededor de contraseñas con caracteres especiales
ADMIN_USER=admin \
ADMIN_PASS='<contraseña-segura>' \
ADMIN_EMAIL=<tu@email.com> \
python scripts/seed.py
# Salida esperada:
# ✓ Admin creado: admin
# ✓ 3 barrios
# ✓ 5 categorías
# ✓ 1 usuarios
# Seed completado.
```

> `seed.py` es **idempotente**: podés correrlo varias veces sin duplicar datos.  
> Si omitís `ADMIN_PASS`, el script usa el default `"admin2026"` — en ese caso cambiá
> la contraseña inmediatamente desde el panel de admin tras el primer login.

---

## 8. Crear el servicio systemd

```bash
sudo nano /etc/systemd/system/InventarioGLTEC.service
```

Pegar el contenido completo:

```ini
[Unit]
Description=InventarioGLTEC — Sistema de inventario multi-barrio
After=network.target mysql.service

[Service]
User=deploy
Group=www-data
WorkingDirectory=/home/deploy/apps/appinv
EnvironmentFile=/home/deploy/apps/appinv/.env
ExecStart=/home/deploy/apps/appinv/venv/bin/gunicorn \
    --config /home/deploy/apps/appinv/gunicorn.conf.py \
    wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

```bash
# Recargar systemd y activar el servicio
sudo systemctl daemon-reload
sudo systemctl enable appinv
sudo systemctl start appinv

# Verificar estado (debe mostrar "active (running)")
sudo systemctl status appinv

# Verificar que el socket Unix fue creado por Gunicorn
ls -la /home/deploy/apps/appinv/appinv.sock
# Debe mostrar: srw-rw---- deploy www-data appinv.sock
```

---

## 9. Configurar Nginx

```bash
sudo nano /etc/nginx/sites-available/appinv
```

Pegar el contenido completo:

```nginx
server {
    listen 80;

    # ⚠️  Reemplazá TU_DOMINIO.com con el dominio real ANTES de ejecutar certbot
    server_name TU_DOMINIO.com www.TU_DOMINIO.com;

    client_max_body_size 10M;

    access_log /var/log/nginx/appinv_access.log;
    error_log  /var/log/nginx/appinv_error.log;

    # Archivos estáticos servidos directamente por Nginx
    location /static/ {
        alias /home/deploy/apps/appinv/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Todo lo demás → Gunicorn via socket Unix
    location / {
        include proxy_params;
        proxy_pass http://unix:/home/deploy/apps/appinv/appinv.sock:/;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
```

```bash
# Activar el sitio (symlink en sites-enabled)
sudo ln -s /etc/nginx/sites-available/appinv \
           /etc/nginx/sites-enabled/appinv

# Verificar que no hay errores de sintaxis en la config
sudo nginx -t
# Esperado: syntax is ok / test is successful

# Recargar Nginx para aplicar el nuevo sitio
sudo systemctl reload nginx
```

---

## 10. HTTPS con Certbot

> **Requisitos previos:**
> - El DNS del dominio ya apunta al IP del VPS (verificar con `dig TU_DOMINIO.com`)
> - El `server_name` en Nginx está con el dominio real (sin "TU_DOMINIO.com")
> - Nginx responde en el puerto 80: `curl -I http://TU_DOMINIO.com`

```bash
# Obtener certificado y configurar HTTPS (modifica el server block automáticamente)
sudo certbot --nginx -d TU_DOMINIO.com -d www.TU_DOMINIO.com

# Probar renovación automática
sudo certbot renew --dry-run
```

---

## 11. Verificar que todo funciona

```bash
# Estado del servicio systemd
sudo systemctl status appinv

# Logs de Gunicorn en tiempo real (Ctrl+C para salir)
sudo journalctl -u appinv -f

# Log de la app (RotatingFileHandler)
tail -f /home/deploy/apps/appinv/logs/app.log

# Logs de acceso y error de Gunicorn
tail -f /home/deploy/apps/appinv/logs/access.log
tail -f /home/deploy/apps/appinv/logs/error.log

# Probar el socket directamente (sin pasar por Nginx)
curl --unix-socket /home/deploy/apps/appinv/appinv.sock \
     http://localhost/
# Debe retornar el HTML del login

# Probar HTTP (después de Nginx)
curl -I http://TU_DOMINIO.com
# Esperado: HTTP/1.1 200 OK  (o 301 si certbot ya configuró HTTPS)

# Probar HTTPS (después de certbot)
curl -I https://TU_DOMINIO.com
# Esperado: HTTP/2 200
```

Verificar en el navegador:
- `https://TU_DOMINIO.com` → pantalla de login de appinv
- Login con `admin` / el `ADMIN_PASS` que pasaste inline al correr `seed.py`
- Crear un ítem de prueba con foto para confirmar que uploads funciona

---

## 12. Troubleshooting

### El servicio no arranca — `systemctl status` muestra "failed"

```bash
# Ver el error completo
sudo journalctl -u appinv -n 50 --no-pager
```

**Causas frecuentes:**

| Error en el log | Causa | Solución |
|---|---|---|
| `RuntimeError: La variable de entorno 'X' no está definida` | Falta una variable en `.env` | Revisá que DB_USER, DB_PASS, DB_NAME y SECRET_KEY están en `.env` |
| `PermissionError: [Errno 13]` al crear el socket | El directorio no es escribible por `deploy` | `chown -R deploy:deploy /home/deploy/apps/appinv` |
| `Can't connect to MySQL server` | MySQL no corre o credenciales incorrectas | `sudo systemctl status mysql` · probar con `mysql -u inventario_user -p` |
| `No module named 'flask'` | venv no activado o deps no instaladas | `source venv/bin/activate && pip install -r requirements.txt` |

### Nginx retorna **502 Bad Gateway**

```bash
# Verificar que el socket existe y el servicio corre
ls -la /home/deploy/apps/appinv/appinv.sock
sudo systemctl status appinv

# Si el socket no existe, el servicio falló — ver causa con:
sudo journalctl -u appinv -n 30 --no-pager

# Verificar que la ruta del socket en Nginx coincide exactamente con gunicorn.conf.py
grep proxy_pass /etc/nginx/sites-available/appinv
grep bind /home/deploy/apps/appinv/gunicorn.conf.py
```

### **403 Forbidden** en `/static/uploads/` (fotos no se muestran)

```bash
# Verificar que Nginx puede leer el directorio
sudo -u www-data ls /home/deploy/apps/appinv/app/static/uploads/
# Si da "Permission denied":

# Opción 1: asegurar que /home/deploy/ es traversable por otros
chmod o+x /home/deploy/

# Opción 2: verificar permisos del directorio uploads
chmod 755 /home/deploy/apps/appinv/app/static/uploads/

sudo systemctl reload nginx
```

### **Error 500** — la app falla en runtime

```bash
# Los traceback de Python van al log de la app
tail -100 /home/deploy/apps/appinv/logs/app.log

# También en el log de error de Gunicorn
tail -100 /home/deploy/apps/appinv/logs/error.log

# O en journalctl
sudo journalctl -u appinv -n 100 --no-pager
```

---

## 13. Workflow de updates (futuros deploys)

```bash
# Conectarse al servidor
ssh deploy@IP_DEL_SERVIDOR

cd /home/deploy/apps/appinv

# 1. Traer cambios del repositorio
git pull origin main

# 2. Activar venv
source venv/bin/activate

# 3. Actualizar dependencias si requirements.txt cambió
pip install -r requirements.txt

# 4. Aplicar migraciones nuevas (si las hay)
flask db upgrade

# 5. Reiniciar el servicio
sudo systemctl restart appinv

# 6. Verificar
sudo systemctl status appinv
tail -20 /home/deploy/apps/appinv/logs/app.log
```

> **Nginx** no necesita reiniciarse salvo que cambies la config del site.  
> **Los estáticos** (CSS, JS, imágenes) se sirven directamente por Nginx sin
> involucrar a Gunicorn — cambios en `app/static/` se reflejan inmediatamente.

---

## 14. Backup de uploads (fotos de ítems)

Las fotos subidas por los usuarios se guardan en `app/static/uploads/` y **no forman
parte de la base de datos**. Hay que respaldarlas por separado del dump de MySQL.

### Backup remoto desde tu máquina local (recomendado)

```bash
# Ejecutar desde tu máquina (Windows con Git Bash, o Linux/Mac)
# Crea una carpeta con fecha en el destino local
rsync -avz deploy@IP_DEL_SERVIDOR:/home/deploy/apps/appinv/app/static/uploads/ \
            ./backups/appinv-uploads-$(date +%Y%m%d)/
```

### Backup incremental (solo archivos nuevos o modificados)

```bash
# Más rápido para ejecuciones frecuentes — mantiene un único directorio actualizado
rsync -avz --update \
      deploy@IP_DEL_SERVIDOR:/home/deploy/apps/appinv/app/static/uploads/ \
      ./backups/appinv-uploads/
```

### Backup local en el servidor (si querés una copia rápida en disco)

```bash
mkdir -p /home/deploy/backups
rsync -a /home/deploy/apps/appinv/app/static/uploads/ \
         /home/deploy/backups/appinv-uploads-$(date +%Y%m%d)/
```

### Backup completo (uploads + base de datos)

```bash
# En el servidor — genera un dump comprimido de MySQL
mysqldump -u inventario_user -p appinv \
  | gzip > /home/deploy/backups/appinv-db-$(date +%Y%m%d).sql.gz

# Luego bajarlo a tu máquina local junto con uploads:
rsync -avz deploy@IP_DEL_SERVIDOR:/home/deploy/backups/ ./backups/
```

> Un restore completo requiere ambas piezas: el dump de MySQL **y** la carpeta `uploads/`.
> Sin los archivos de imagen, los ítems con foto mostrarán imagen rota aunque la DB esté intacta.
