# Guía de Estilo — InventarioGLTEC

Sistema de diseño **extraído del código existente**, no inventado. Todo lo que
está acá se corresponde con lo que hoy renderiza la app; donde propongo algo
nuevo, está marcado como tal.

| | |
|---|---|
| **Fuente de verdad** | [`app/templates/layouts/base.html`](../app/templates/layouts/base.html) (bloque `<style>`) |
| **Tokens** | [`tokens.css`](tokens.css) |
| **Componentes** | [`components.css`](components.css) |
| **Referencia visual** | [`index.html`](index.html) — abrila en el navegador, tiene toggle de tema |
| **Base externa** | Bootstrap 5.3.3 · Bootstrap Icons 1.11.3 · DM Sans (Google Fonts) |

> **Estos archivos son documentación, no build.** La app sigue sirviendo sus
> estilos inline desde `base.html`. Si algún día se extraen a `static/css/`,
> `tokens.css` + `components.css` son el punto de partida ya ordenado.

---

## 1. Principios

1. **Extender Bootstrap, no reemplazarlo.** La app agrega ~15 clases propias
   sobre Bootstrap. `.btn-gltec` es un skin de `.btn`; `.table-container`
   envuelve una `.table.table-borderless`. Ante la duda: usá la utilidad de
   Bootstrap antes de escribir CSS.
2. **Todo color pasa por un token.** Ningún hex nuevo en las plantillas. Las
   únicas excepciones legítimas son los colores que vienen de la base de datos
   (`categoria.color`) — eso es dato, no diseño.
3. **Un tema, dos superficies.** Cada color de texto/fondo tiene su par en
   oscuro. Si agregás un token, agregá su contraparte.
4. **La marca no cambia de tema.** `--primary` y `--accent` son rellenos
   sólidos con texto blanco encima: idénticos en claro y oscuro. Para azul
   como *texto* existen `--brand-ink` / `--accent-ink`, que sí se aclaran.
5. **Densidad alta.** Es una herramienta de gestión, no una landing. Cuerpo de
   13.5px, celdas de 14/20px, mucha información por pantalla.

---

## 2. Temas

El tema se aplica en `<html>` con **dos** atributos, escritos por un script
inline en `<head>` **antes del primer pintado** (evita el flash de claro):

```js
document.documentElement.setAttribute('data-theme',    t); // tokens propios
document.documentElement.setAttribute('data-bs-theme', t); // componentes Bootstrap
```

- Valores: `'light'` | `'dark'`.
- Persistencia: `localStorage['tema']`.
- **Sin preferencia guardada → `light`.** La app *no* consulta
  `prefers-color-scheme`; es una decisión deliberada, el default es claro.
- El toggle (`#theme-toggle`) sólo mueve los atributos y reescribe localStorage.

**Los dos atributos se mueven siempre juntos.** Si sólo cambiás `data-theme`,
los tokens se invierten pero los dropdowns, alerts y `.form-control` de
Bootstrap quedan en claro.

### Puente hacia Bootstrap

`data-bs-theme="dark"` por sí solo no alcanza: deja los controles de Bootstrap
con sus grises genéricos, que no son los de la app. Por eso el bloque oscuro
reasigna seis variables de Bootstrap a tokens propios:

```css
:root[data-theme="dark"] {
  --bs-body-bg:         var(--bg);
  --bs-body-color:      var(--ink-700);
  --bs-emphasis-color:  var(--ink-900);
  --bs-secondary-color: var(--ink-400);
  --bs-border-color:    var(--border-3);
  --bs-tertiary-bg:     var(--surface-2);
}
```

**Sólo en oscuro.** En claro se usan los valores de fábrica de Bootstrap,
intactos — los tokens propios ya coinciden con ellos.

Hay un segundo puente, local, en las tablas: Bootstrap pinta cada celda con
`--bs-table-bg` (por defecto el fondo del body), así que `.table-container table`
lo ata a `--surface`. En claro resuelve a `#fff` (sin cambio visible); en oscuro
evita que las celdas queden más claras que la tarjeta que las contiene.

> Al agregar un componente de Bootstrap que se vea "fuera de paleta" en oscuro,
> el arreglo casi siempre es mapear su variable `--bs-*` acá, no escribir CSS nuevo.

---

## 3. Color

### 3.1 Marca — constante en ambos temas

| Token | Valor | Uso |
|---|---|---|
| `--primary` | `#1B4F72` | Inicio del gradiente de `.btn-gltec`, `.avatar`, sidebar; fondo del badge de código |
| `--accent` | `#2E86C1` | Fin del gradiente; borde de foco; borde izquierdo de fila editada |
| `--primary-600` | `#154360` | Hover del gradiente (inicio) |
| `--accent-600` | `#2471a3` | Hover del gradiente (fin) |

### 3.2 Azul como texto — sí cambia

| Token | Claro | Oscuro | Uso |
|---|---|---|---|
| `--brand-ink` | `#1B4F72` | `#7fbeea` | `.stat-value`, títulos de card, nombre de categoría |
| `--accent-ink` | `#2E86C1` | `#6cb6e8` | Links de breadcrumb |

### 3.3 Superficies y bordes

| Token | Claro | Oscuro | Uso |
|---|---|---|---|
| `--bg` | `#f0f2f5` | `#0d1117` | Fondo de página |
| `--surface` | `#fff` | `#161b22` | Cards, tablas |
| `--surface-2` | `#f8f9fb` | `#1b222b` | Hover de fila, bloques embebidos |
| `--surface-3` | `#fafafc` | `#1a212a` | `thead` |
| `--surface-hover` | `#eef2f7` | `#232b35` | Hover de controles |
| `--border` | `#eee` | `#21262d` | Divisores suaves |
| `--border-2` | `#e9ecef` | `#262d36` | Bordes de card/control |
| `--border-3` | `#ddd` | `#30363d` | Bordes marcados (swatch de color) |

### 3.4 Escala de tinta

`--ink-900` es el máximo contraste, `--ink-200` el mínimo. **En oscuro la escala
se invierte** (900 pasa a ser el más claro), así que el significado —"más/menos
contraste"— se mantiene sin tocar las plantillas.

| Token | Claro | Oscuro | Uso típico |
|---|---|---|---|
| `--ink-900` | `#1a1a2e` | `#e6edf3` | `h1` del topbar |
| `--ink-800` | `#333` | `#d7dee6` | Énfasis en texto secundario |
| `--ink-700` | `#444` | `#c9d1d9` | Label de sección colapsable |
| `--ink-600` | `#555` | `#b3bdc7` | Cuerpo secundario |
| `--ink-500` | `#666` | `#9aa5b1` | Metadatos, icono del toggle |
| `--ink-400` | `#888` | `#8b949e` | `th`, labels, hints |
| `--ink-300` | `#999` | `#808a95` | Iconos decorativos |
| `--ink-200` | `#aaa` | `#6e7681` | Timestamps, texto mínimo |

### 3.5 Semánticos

Siempre en pares `bg` + `fg`, pensados para píldoras (fondo tenue, texto saturado).

| Estado | `bg` claro / oscuro | `fg` claro / oscuro |
|---|---|---|
| OK | `#e6f9ee` / `rgba(46,160,67,.16)` | `#1a8a4a` / `#56d364` |
| Advertencia | `#fff8e1` / `rgba(210,153,34,.16)` | `#b8860b` / `#e3b341` |
| Peligro | `#fde8e8` / `rgba(218,54,51,.16)` | `#c0392b` / `#f97171` |
| Neutro | `#f0f2f5` / `rgba(255,255,255,.08)` | `#555` / `#c9d1d9` |
| Chip (azul) | `#e8f0fe` / `rgba(46,134,193,.20)` | `#1B4F72` / `#9ecdf0` |

En oscuro los fondos pasan a **rgba sobre la superficie** en vez de hex opaco:
así el badge se apoya sobre `--surface` o sobre una fila con hover sin cortarse.

Extras: `--danger-bg-2` + `--danger-border` (badge "Dado de baja", con borde),
`--chip-bg-2` (chip tenue de barrio), `--row-alerta` / `--row-editada`
(resaltado de fila completa), `--photo-ph` (gradiente placeholder de foto).

---

## 4. Tipografía

**DM Sans** (400/500/600/700), aplicada con un selector universal:

```css
* { font-family: 'DM Sans', sans-serif; }
```

Es deliberadamente agresivo — pisa la familia de todo. Bootstrap Icons
sobrevive porque dibuja con `::before` y su propia `font-family`.

### Escala real en uso

Los tamaños viven hoy **hardcodeados** en atributos `style` de las plantillas.
`tokens.css` los normaliza como variables opt-in (`--fs-*`); ver §9.

| Token propuesto | px | Dónde |
|---|---|---|
| `--fs-3xs` | 10 | `.nav-section`, `.logo-sub`, badge de barrio |
| `--fs-2xs` | 11 | Labels uppercase de dato (vista detalle) |
| `--fs-xs` | 11.5 | `th`, `.badge-estado`, texto auxiliar bajo un dato |
| `--fs-sm` | 12 | Chips, hints, links de filtro, `.stat-label` |
| `--fs-md` | 13 | Labels de formulario, `.nav-item-custom`, meta del topbar |
| **`--fs-base`** | **13.5** | **Cuerpo — celdas de tabla, texto de lectura** |
| `--fs-lg` | 14 | Inputs, botones, alerts, `.avatar` |
| `--fs-xl` | 16 | `h5` de encabezado de card/tabla |
| `--fs-2xl` | 20 | Logo del sidebar |
| `--fs-3xl` | 24 | `h1` del topbar |
| `--fs-4xl` | 26 | `.stat-value` |

### Reglas

- **Todo `text-transform: uppercase` lleva `letter-spacing`.** Sin excepción:
  `.6px` a 11px, `.8px` a 10–11.5px en tablas, `1.2px` en `.nav-section`.
- Pesos: 400 cuerpo · 500 nav y labels de stat · 600 labels, `th`, badges,
  botones · 700 títulos y `.stat-value`.
- El uppercase es sólo para **etiquetas**, nunca para contenido.

---

## 5. Espaciado, radios y sombras

Espaciado: se usan las utilidades de Bootstrap (`p-3`, `p-4`, `g-3`, `mb-4`).
Los valores propios aparecen sólo dentro de los componentes.

| Radio | Valor | Aplica a |
|---|---|---|
| `--radius-sm` | 6px | Badge cuadrado ("Dado de baja") |
| `--radius-md` | 8px | Preview de imagen, alert de login |
| `--radius-lg` | 10px | `.barrio-badge`, `.section-toggle` |
| `--radius-xl` | 12px | `.stat-card`, `.cat-card` |
| `--radius-2xl` | 14px | `.card-custom`, `.table-container` |
| `--radius-pill` | 20px | `.badge-estado`, chips |
| — | 50% | `.avatar`, `.theme-toggle`, `.cat-dot` |

| Sombra | Claro | Oscuro |
|---|---|---|
| `--shadow-card` | `0 1px 3px rgba(0,0,0,.06)` | `0 1px 3px rgba(0,0,0,.4)` |
| `--shadow-hover` | `0 4px 12px rgba(27,79,114,.12)` | `0 4px 12px rgba(0,0,0,.55)` |

**Transiciones:** `.15s` para color/fondo/borde, `.2s` para rotación de flecha,
`.3s` para el desplazamiento del sidebar. No hay `easing` explícito.

---

## 6. Componentes

### 6.1 Navegación — Sidebar

Fijo, 230px (`--sidebar-w`), gradiente vertical `--sidebar-1` → `--sidebar-2`.

```html
<nav class="sidebar" id="sidebar">
  <div class="logo">GLTEC</div>
  <div class="logo-sub">Tecnología sin Límites</div>

  <div class="barrio-badge"><small>Barrio actual</small>Villa Alegre</div>

  <div class="nav-section">Menú Principal</div>
  <a href="…" class="nav-item-custom active"><i class="bi bi-clipboard-data"></i> Inventario</a>
  <a href="…" class="nav-item-custom"><i class="bi bi-search"></i> Búsqueda</a>
</nav>
```

- El texto del sidebar **no usa la escala `--ink-*`**: va sobre el gradiente
  oscuro, así que usa `rgba(255,255,255,α)` fijo en ambos temas.
- El estado activo lo decide **el servidor** comparando `request.endpoint`, no JS.
- `.barrio-badge` muestra el contexto activo: rol para admin, barrio para el resto.
- Bajo 768px el sidebar sale de pantalla y vuelve con `.show` (toggle manual).

### 6.2 Toggle de tema

Botón circular en el topbar que alterna claro ⇄ oscuro. Es el único control
global de apariencia de la app.

```html
<button type="button" class="theme-toggle" id="theme-toggle"
        title="Cambiar tema" aria-label="Cambiar entre modo claro y oscuro">
  <i class="bi bi-moon-stars icon-light"></i>
  <i class="bi bi-sun icon-dark"></i>
</button>
```

**Anatomía**

| Propiedad | Valor |
|---|---|
| Tamaño | 34 × 34 px, `border-radius: 50%`, `flex-shrink: 0` |
| Borde | `1px solid var(--border-2)` |
| Fondo | `var(--surface)` |
| Icono | 15px, `var(--ink-500)` |
| Hover | fondo `--surface-hover` · icono `--brand-ink` · borde `--accent` |
| Transición | `.15s` en `background`, `color`, `border-color` |

Los 34px lo dejan **deliberadamente más chico que el avatar** (36px): es un
control auxiliar, no debe competir con la identidad del usuario.

**Los dos iconos viven siempre en el DOM.** El CSS decide cuál se ve según el
tema; el JS nunca toca clases ni `innerHTML`, sólo mueve el atributo en `<html>`:

```css
.theme-toggle .icon-dark { display: none; }
:root[data-theme="dark"] .theme-toggle .icon-dark  { display: inline-block; }
:root[data-theme="dark"] .theme-toggle .icon-light { display: none; }
```

> Ojo con los nombres: `.icon-light` es **el icono que se ve en tema claro**
> (la luna), no "el icono claro". Igual `.icon-dark` (el sol).

**El icono muestra el destino, no el estado actual.** En claro se ve una luna
(`bi-moon-stars`) = "tocá para ir a oscuro"; en oscuro se ve un sol (`bi-sun`).
Es la convención más extendida y evita el bucle de "¿esto me dice dónde estoy o
adónde voy?". Si alguna vez se cambia por un switch con etiqueta, hay que
invertir la lógica del icono.

**Ubicación.** Siempre en el clúster derecho del topbar, en este orden:

```
[selector de barrio (sólo admin)] · [toggle] · [nombre de usuario] · [avatar]
```

Va **antes** del nombre para no separar al usuario de su avatar. El contenedor
es `d-flex align-items-center gap-3`.

**Dónde no aparece:** en el login, que está fuera del sistema de diseño y es
sólo oscuro (ver §9). Es la única pantalla de la app sin control de tema.

**Contraste** — el icono cumple AA holgadamente en ambos temas:

| | Reposo | Hover |
|---|---|---|
| Claro | 5.74:1 | 7.76:1 |
| Oscuro | 6.91:1 | 7.12:1 |

El borde en reposo sí queda muy tenue (1.19:1 en claro, 1.36:1 en oscuro),
por debajo del 3:1 que pide WCAG 1.4.11 para bordes de controles. En la práctica
el icono es lo que identifica el botón, pero si se quiere cumplir al pie de la
letra, subir el borde a `--border-3` alcanza.

**Accesibilidad — pendiente:** el botón tiene `aria-label` y `title`, pero **no
anuncia el estado**. Un lector de pantalla dice "Cambiar entre modo claro y
oscuro" sin decir cuál está activo. El arreglo es agregar `aria-pressed` y
mantenerlo sincronizado con el atributo del `<html>`.

### 6.3 Botones

Tres niveles. **Uno solo primario por vista.**

| Nivel | Clases | Uso |
|---|---|---|
| Primario | `.btn.btn-gltec` | Guardar, Buscar, Nuevo ítem, página actual en paginación |
| Secundario | `.btn.btn-outline-secondary` | Cancelar, iconos de fila, exportar, paginación |
| Destructivo | `.btn.btn-outline-danger` | Eliminar — **siempre** con `confirm()` |

```html
<button type="submit" class="btn btn-gltec"><i class="bi bi-check-lg"></i> Guardar Cambios</button>
<a href="…" class="btn btn-outline-secondary">Cancelar</a>
```

- `.btn-gltec` es gradiente 135°, sin borde, peso 600, texto blanco. En hover el
  gradiente se oscurece a los `-600`.
- En tablas siempre `.btn-sm` + sólo icono + `title="…"`, agrupados en
  `<div class="d-flex gap-1">`.
- Toda acción destructiva es **POST con token CSRF**, nunca un link.

### 6.4 Tablas

Estructura canónica, idéntica en inventario / búsqueda / usuarios / barrios /
catálogos / auditoría:

```html
<div class="table-container">
  <!-- cabecera: título + acción -->
  <div class="d-flex justify-content-between align-items-center p-3 border-bottom">
    <h5 class="mb-0" style="font-size:16px">Últimos movimientos</h5>
    <a href="…" class="btn btn-sm btn-gltec"><i class="bi bi-plus-lg"></i> Nuevo Ítem</a>
  </div>

  <div class="table-responsive">
    <table class="table table-borderless mb-0">
      <thead><tr><th>Ítem</th>…<th>Acciones</th></tr></thead>
      <tbody>…</tbody>
    </table>
  </div>

  <!-- paginación -->
  <div class="d-flex justify-content-center gap-1 p-3">…</div>
</div>
```

- `overflow: hidden` en el contenedor es lo que recorta las esquinas del `thead`.
- `th`: 11.5px, uppercase, `.8px` de tracking, `--ink-400`, fondo `--surface-3`.
- `td`: 13.5px, padding `14px 20px`, `vertical-align: middle`.
- Hover de fila → `--surface-2`.
- **Celda de nombre:** `<strong>` + salto de línea + marca/modelo en 11.5px `text-muted`.
- **Última columna siempre "Acciones"**, alineada a la izquierda con `gap-1`.
- Estado vacío: `<div class="text-center text-muted py-5">` con icono de 40px.

**Paginación:** botones `.btn-sm`, la página actual usa `.btn-gltec`, el resto
`.btn-outline-secondary`; elipsis como `<span class="btn btn-sm disabled">…</span>`.
Se genera con `pagination.iter_pages(left_edge=1, right_edge=1, left_current=1, right_current=2)`
y **todos los filtros activos viajan en cada `url_for`**.

### 6.5 Badges de estado

```html
<span class="badge-estado badge-operativo">Operativo</span>
```

| Clase | Fondo / texto |
|---|---|
| `.badge-operativo` | `--ok-bg` / `--ok-fg` |
| `.badge-stock-bajo`, `.badge-revisar` | `--warn-bg` / `--warn-fg` |
| `.badge-reparacion`, `.badge-fuera` | `--danger-bg` / `--danger-fg` |
| `.badge-prestamo` | `--chip-bg` / `--chip-fg` |
| `.badge-default` | `--neutral-bg` / `--neutral-fg` |

El mapeo estado → clase se resuelve en Jinja por **coincidencia parcial** sobre
`item.estado|lower`, con `badge-default` como fallback:

```jinja
{% set estado_lower = item.estado|lower|replace(' ', '-') %}
{% if 'operat' in estado_lower %}<span class="badge-estado badge-operativo">…
{% elif 'bajo'  in estado_lower %}…
{% else %}<span class="badge-estado badge-default">…
{% endif %}
```

> Este bloque está **duplicado** en `inventory/index.html`, `search/buscar.html` y
> `detalle_item.html`, y las tres copias divergen (detalle contempla `'baja'`, las
> otras no). Ver §9.

`.cat-dot` es el punto de 8px que precede al nombre de categoría; su color viene
de la DB por `style` inline.

### 6.6 Chips de filtro

Píldora azul que representa un filtro activo, con "×" para quitarlo. El link del
"×" reconstruye la URL **sin ese filtro y con todos los demás intactos**:

```jinja
<span class="badge rounded-pill" style="background:var(--chip-bg);color:var(--chip-fg);font-weight:600;font-size:12px">
  <span class="cat-dot" style="background:{{ c.color }}"></span>{{ c.nombre }}
  <a href="{{ url_for('search.buscar', q=q, categoria_id=categoria_ids|reject('equalto', c.id)|list, …) }}"
     class="text-decoration-none" style="color:var(--chip-fg);opacity:.6">×</a>
</span>
```

La fila de chips cierra siempre con un link "Limpiar todo" en 12px `--ink-400`.
`components.css` propone una clase `.chip` para reemplazar estas ~9 repeticiones.

### 6.7 Formularios

```html
<div class="card-custom p-4" style="max-width:800px">
  <form method="POST" enctype="multipart/form-data">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

    <div class="row g-3 mb-3">
      <div class="col-md-8">
        <label class="form-label fw-semibold" style="font-size:13px">Nombre *</label>
        <input type="text" name="nombre" class="form-control" required>
      </div>
      <div class="col-md-4">
        <label class="form-label fw-semibold" style="font-size:13px">
          Área <span class="text-muted fw-normal">(opcional)</span>
        </label>
        <select name="area_id" class="form-select">…</select>
        <div class="form-text">Se gestionan en <a href="…">Catálogos</a>.</div>
      </div>
    </div>

    <div class="d-flex gap-2 mt-4">
      <button type="submit" class="btn btn-gltec"><i class="bi bi-check-lg"></i> Guardar</button>
      <a href="…" class="btn btn-outline-secondary">Cancelar</a>
    </div>
  </form>
</div>
```

Reglas:

- Contenedor `.card-custom.p-4` con `max-width` explícito por tipo de formulario:
  **500px** barrio · **540px** catálogo · **600px** usuario · **800px** ítem.
- Grilla `row g-3` + `col-md-*`. Los controles son **Bootstrap puro**; el único
  override es el color de foco (`--accent` + halo `rgba(46,134,193,.15)`).
- Label: `.form-label.fw-semibold` a 13px. Obligatorio marcado con `*`.
  Lo opcional se aclara con `<span class="text-muted fw-normal">(opcional)</span>`.
- Ayuda contextual en `.form-text`, debajo del control.
- Opciones vacías de un `<select>` usan em-dashes: `— General del barrio —`,
  `— Sin especificar —`.
- Acciones al pie en `d-flex gap-2 mt-4`, **primario primero**, cancelar después.
- **Todo POST lleva `csrf_token`.**
- Campos avanzados van en una sección colapsable (`.section-toggle` + Bootstrap
  collapse), abierta por defecto sólo si ya tienen datos.

### 6.8 Cards

| Clase | Uso |
|---|---|
| `.stat-card` | KPI: label 12px `--ink-400` + valor 26px/700 `--brand-ink`. En grilla `col-6 col-md-3` |
| `.card-custom` | Contenedor genérico. Se combina con `p-3`/`p-4` |
| `.cat-card` | Tile clickeable de categoría; en hover levanta `--shadow-hover` y borde `--accent` |

Dentro de `.card-custom`, el título de sección es
`<h6 class="mb-3 pb-2 border-bottom" style="color:var(--brand-ink)">`.

### 6.9 Vista de detalle — pares label/valor

```html
<div class="mb-3">
  <div class="text-muted text-uppercase" style="font-size:11px;letter-spacing:.6px;font-weight:600">Categoría</div>
  <div>…</div>
</div>
```

Se repite ~12 veces; `components.css` lo propone como `.label-dato`.
El último par del bloque usa `mb-0` en vez de `mb-3`.

### 6.10 Mensajes flash

Alerts nativos de Bootstrap, renderizados por `base.html`. La categoría de Flask
debe coincidir con el sufijo de Bootstrap (`success`, `danger`, `warning`, `info`):

```jinja
<div class="alert alert-{{ cat }} alert-dismissible fade show" style="font-size:14px" role="alert">
  {{ msg }}
  <button type="button" class="btn-close btn-sm" data-bs-dismiss="alert"></button>
</div>
```

### 6.11 Iconografía

**Bootstrap Icons**, siempre `<i class="bi bi-*">`. Vocabulario establecido:

| Icono | Significado | | Icono | Significado |
|---|---|---|---|---|
| `bi-clipboard-data` | Inventario | | `bi-pencil` | Editar |
| `bi-search` | Búsqueda | | `bi-eye` | Ver detalle |
| `bi-people` | Usuarios | | `bi-trash` | Eliminar |
| `bi-tags` | Catálogos / categorías | | `bi-plus-lg` | Crear |
| `bi-houses` | Barrios | | `bi-check-lg` | Guardar |
| `bi-shield-check` | Auditoría | | `bi-funnel` | Aplicar filtros |
| `bi-geo-alt` | Ubicación | | `bi-x-lg` | Limpiar filtros |
| `bi-grid-3x3-gap` | Área | | `bi-inbox` | Vacío |

Tamaños: 40px en estados vacíos · 24px en `.cat-card` · 10px dentro de un chip ·
heredado en botones y nav.

---

## 7. Anatomía de una página

```jinja
{% extends "layouts/base.html" %}
{% block title %}Inventario{% endblock %}       {# <title> — se le agrega " | GLTEC" #}
{% block page_title %}Inventario{% endblock %}  {# <h1> del topbar #}

{% block breadcrumb %}                          {# opcional, va sobre el h1 #}
<nav style="font-size:13px" class="mb-1">
  <a href="…" class="text-decoration-none" style="color:var(--accent-ink)">Inventario</a>
  <span class="text-muted">›</span>
  <span class="text-muted">Editar</span>
</nav>
{% endblock %}

{% block extra_css %}<style>…</style>{% endblock %}
{% block content %}…{% endblock %}
{% block extra_js %}<script>…</script>{% endblock %}
```

El topbar lo arma `base.html`: breadcrumb + `h1` a la izquierda; a la derecha
selector de barrio (sólo admin), toggle de tema, nombre de usuario y avatar.

**CSS específico de una vista va en `{% block extra_css %}`**, no en `base.html`.
Si una clase la necesitan dos o más vistas, recién ahí sube a `base.html`.

---

## 8. Accesibilidad

Contrastes calculados (WCAG 2.1) sobre los pares reales de la app. AA pide
**4.5:1** para texto normal y **3:1** para texto grande (≥24px, o ≥18.66px en bold).

### Lo que pasa

| Par | Claro | Oscuro |
|---|---|---|
| `--ink-900` sobre `--surface` | 17.06 ✅ | 14.64 ✅ |
| `--ink-600` sobre `--surface` | 7.46 ✅ | 9.08 ✅ |
| `--brand-ink` sobre `--surface` | 8.72 ✅ | 8.61 ✅ |
| Chip: `--chip-fg` sobre `--chip-bg` | 7.61 ✅ | — |
| Peligro: `--danger-fg` sobre `--danger-bg` | 4.63 ✅ | — |
| `--ink-400` sobre `--surface-3` (`th`) | 3.40 ❌ | 5.27 ✅ |

### Lo que no pasa — pendiente

Todo esto es **tema claro**; el tema oscuro cumple AA en todos los pares medidos.

| Par | Ratio | Dónde duele |
|---|---|---|
| `--ink-400` `#888` / `--surface-3` | **3.40** | Todos los `th` y labels de filtro |
| `--ink-200` `#aaa` / `--surface` | **2.32** | Timestamps del historial, `.section-hint` |
| `--accent-ink` `#2E86C1` / `--surface` | **3.97** | Links de breadcrumb (13px) |
| Blanco / `--accent` (extremo derecho de `.btn-gltec`) | **3.97** | Texto de botón primario, 14px/600 |
| `--warn-fg` / `--warn-bg` | **3.06** | Badges "Stock bajo" y "Revisar" |
| `--ok-fg` / `--ok-bg` | **4.01** | Badge "Operativo" |
| `rgba(255,255,255,.6)` / sidebar | **2.86** | Links de nav en reposo |
| `rgba(255,255,255,.3)` / sidebar | **2.02** | `.nav-section` |

Arreglo mínimo, sin rediseñar nada — oscurecer sólo los `fg` en tema claro:

```css
:root {
  --ink-400: #6b6b6b;   /* 3.40 → 5.5  */
  --ink-200: #767676;   /* 2.32 → 4.6  */
  --accent-ink: #1F6FA8;/* 3.97 → 5.5  */
  --warn-fg: #8a6100;   /* 3.06 → 5.9  */
  --ok-fg: #157a41;     /* 4.01 → 5.0  */
}
.nav-item-custom { color: rgba(255,255,255,.78); }  /* 2.86 → 4.6 */
```

Para `.btn-gltec`, la opción de menor impacto visual es correr el punto final del
gradiente a `--accent-600` (`#2471a3`, 5.0:1) en vez de `--accent`.

### Lo que ya está bien

- El toggle de tema tiene `aria-label` y `title`.
- Los botones de sólo icono en tablas tienen `title`.
- El foco de formulario es visible y usa color de marca (no se anula el outline).
- El texto truncado de auditoría conserva el valor completo en `title`.
- Los `alert` llevan `role="alert"`.

Pendientes de marcado: los botones de icono deberían tener también
`aria-label` (`title` no siempre lo expone el lector de pantalla), el toggle de
tema debería exponer `aria-pressed` para anunciar qué modo está activo (§6.2), y
la paginación debería ir dentro de `<nav aria-label="Paginación">`.

---

## 9. Deuda de diseño

Divergencias reales encontradas al extraer el sistema. **No las toqué** — este
trabajo es documentar, no refactorizar.

1. **El login está fuera del sistema.**
   [`auth/login.html`](../app/templates/auth/login.html) es una página
   autónoma: usa **Inter** en vez de DM Sans, no carga Bootstrap, no importa
   `base.html`, es **sólo oscura** y repite todos los colores hardcodeados
   (`#0d1117`, `#161b22`, `#2E86C1`…). Los valores *coinciden* con los del tema
   oscuro, pero como copia literal: cambiar un token no la afecta.
   Además su `.btn-login` es azul plano, no el gradiente de marca.

2. **El PDF es un tercer sistema.**
   [`search/pdf_inventario.html`](../app/templates/search/pdf_inventario.html)
   (WeasyPrint) tiene su propia paleta hardcodeada, siempre clara, con grises
   propios (`#777`, `#e0e0e0`). Es defendible — no puede usar `var()` con temas
   ni depender de la UI — pero al menos los azules de marca deberían
   documentarse como compartidos.

3. **La escala tipográfica no existe como tokens.** Hay **133** apariciones de
   `style="font-size:…"` en las plantillas de la app (sin contar login ni PDF).
   `tokens.css` ya define los `--fs-*` correspondientes; migrar es mecánico pero
   toca muchos archivos.

4. **El bloque de badge de estado está triplicado** (§6.5) y las tres copias
   divergen. Candidato claro a macro de Jinja:
   `{% macro badge_estado(estado) %}`, importable desde las tres vistas.

5. **Estilos inline repetidos** que ya tienen clase propuesta en
   `components.css`: label de formulario 13px (25×), label de dato uppercase
   (12×), chip de filtro (10×), estado vacío (3×).

6. **`.badge-reparacion` y `.badge-fuera` son idénticos**, igual que
   `.badge-stock-bajo` y `.badge-revisar`. Están separados a propósito (para
   poder diferenciarlos más adelante sin tocar plantillas), pero hoy son alias.

7. **`* { font-family }`** funciona, pero es frágil: cualquier fuente de icono
   futura que no use `::before` va a romperse. Lo idiomático sería fijar la
   familia en `body` y dejar que herede.

---

## 10. Cómo agregar algo nuevo

1. ¿Bootstrap ya lo resuelve? Usalo. No escribas CSS.
2. ¿Necesita un color? Buscá el token en §3. **No inventes un hex.**
3. ¿Falta el token? Agregalo a `tokens.css` **y a `base.html`**, en los dos
   temas, y documentalo acá.
4. ¿Es una clase nueva? Va en `{% block extra_css %}` de la vista. Sube a
   `base.html` recién cuando la use una segunda vista.
5. Verificá contraste en **ambos** temas antes de dar por cerrado el cambio.
6. Actualizá [`index.html`](index.html) si agregaste un componente, así la
   referencia visual no se desactualiza.
