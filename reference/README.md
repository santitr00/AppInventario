# /reference — Sistema de diseño

Documentación del sistema de diseño de InventarioGLTEC, **extraído del código
existente**. No es un build ni una dependencia: la app sigue funcionando exactamente
igual sin esta carpeta.

| Archivo | Qué es |
|---|---|
| **[STYLEGUIDE.md](STYLEGUIDE.md)** | La guía. Principios, temas (claro/oscuro), color, tipografía, componentes, accesibilidad y deuda de diseño. **Empezá acá.** |

> El sistema de temas claro/oscuro está en **§2** (contrato de atributos y puente
> hacia Bootstrap) y el botón que los alterna en **§6.2** (anatomía, iconos,
> ubicación, contraste).
| [tokens.css](tokens.css) | Los 87 tokens de `base.html`, copiados 1:1 y documentados, + 25 tokens propuestos de tipografía y radios |
| [components.css](components.css) | Las clases de componentes, marcadas por origen: `[BASE]`, `[LOCAL]` o `[PROPUESTO]` |
| [index.html](index.html) | Referencia visual. Abrila en el navegador — tiene toggle de tema |

## Ver la referencia visual

Abrí `reference/index.html` directamente en el navegador (doble clic). No necesita
servidor; sólo conexión a internet para Bootstrap y DM Sans desde CDN.

## Mantenerlo sincronizado

La fuente de verdad sigue siendo el bloque `<style>` de
[`app/templates/layouts/base.html`](../app/templates/layouts/base.html).
Si cambiás un token ahí, actualizá `tokens.css` y este comando debe volver a dar
`faltantes=0 diferentes=0`:

```bash
python - <<'EOF'
import re
def toks(t):
    out={}
    for b in re.finditer(r'(:root(?:\[data-theme="dark"\])?)\s*\{(.*?)\n\s*\}', t, re.S):
        for m in re.finditer(r'(--[\w-]+)\s*:\s*([^;]+);', b.group(2)):
            out[(b.group(1), m.group(1))] = ' '.join(m.group(2).split())
    return out
base = toks(open('app/templates/layouts/base.html', encoding='utf-8').read())
ref  = toks(open('reference/tokens.css', encoding='utf-8').read())
falta = {k for k in base if k not in ref}
dif   = {k for k in base if k in ref and ref[k] != base[k]}
print(f"faltantes={len(falta)} diferentes={len(dif)}")
for k in falta | dif: print("  ", k)
EOF
```

Los tokens que sólo existen en `tokens.css` (`--fs-*`, `--fw-*`, `--ls-*`,
`--radius-*`) son **propuestas** y no se cuentan como divergencia: hoy esos
valores viven hardcodeados en las plantillas. Ver §9 del styleguide.
