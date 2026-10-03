# Cults3D Agent – tienda de diseños 3D en piloto automático

Corre solo en GitHub Actions; tu PC no necesita estar prendida. Cada semana hace esto:

| Cuándo (hora de Buenos Aires) | Qué hace |
|---|---|
| **Domingo 20:07** | Analiza el mercado de Cults3D (los 500 diseños pagos más descargados de los últimos 90 días, más 200 gratis) y revisa tus ventas. Después agrega productos nuevos a la cola, los verifica (medidas, pieza única, cama, slicer) y reordena la cola: lo más rentable sale primero. |
| **Lunes y jueves 10:17** | Publica el primer diseño de la cola, con imágenes, archivos 3MF, versión de licencia comercial y traducciones. |
| **Todos los días 09:07** | Aplica los descuentos de temporada (Black Friday, Navidad) y suma productos de temporada a la cola. |

## Cómo funciona

1. `tools/analizador_v2.py` baja el mercado y calcula, para cada nicho, las ventas por día, el porcentaje de oferta gratis y un índice de oportunidad.
2. `tools/generar.py` crea productos desde las plantillas para los nichos rentables que todavía no cubrís.
3. `tools/build.py` genera los STL con OpenSCAD y controla cada pieza:
   - malla cerrada;
   - una sola pieza;
   - medidas clave medidas sobre la malla;
   - que entre en una cama de 220 × 220 mm.

   Después la verifica con PrusaSlicer y genera las imágenes.
4. `tools/publish.py` sube los archivos **de forma temporal** a un repo público (`cults-cdn`) y llama a `createCreation`. Cuando Cults3D termina de bajar todo, **borra las copias temporales**: tus STL pagos no quedan expuestos.
5. El producto publicado pasa de `queue/` a `published/`, con su ID y el link de Cults3D.

## Instalación paso a paso (una sola vez, ~30 min)

Necesitás una cuenta de GitHub (gratis) y tu cuenta de Cults3D. No hace falta instalar nada en tu PC.

### Paso 0 – Cambiar la API key de Cults3D (obligatorio)
Tu key anterior quedó escrita en scripts viejos y en un chat, así que hay que darla por expuesta.
1. Entrá a https://cults3d.com/en/api/keys.
2. **Borrá** la key vieja y generá una nueva.
3. Copiala a un bloc de notas temporal. La vas a pegar en el paso 5 y después borrás esa nota.
4. Borrá los scripts viejos que tenían la key escrita (`agente_creador.py`, `analizador.py`, `agente_multitarget.py`).

### Paso 1 – Repo privado con el agente
1. Descomprimí `cults3d-agent.zip` en tu PC.
2. Hacé visibles los archivos ocultos, porque hay una carpeta `.github` que es imprescindible:
   - **Windows:** Explorador → Vista → Mostrar → "Elementos ocultos".
   - **Mac:** en Finder, `Cmd + Shift + .`
3. En GitHub, arriba a la derecha: **+ → New repository**.
   - Repository name: `cults3d-agent`
   - Marcá **Private**.
   - **No** tildes "Add a README".
   - **Create repository**.
4. En la página del repo vacío, hacé clic en el link **"uploading an existing file"**.
5. Arrastrá **todo el contenido** de la carpeta descomprimida, no la carpeta en sí: `.github`, `designs`, `queue`, `templates`, `tools`, `specs`, `published`, `agente.py`, `README.md`, `requirements.txt` y `.gitignore`.
6. Abajo, **Commit changes**.
7. Verificá que en el repo aparezca la carpeta `.github/workflows` con 4 archivos: `publish.yml`, `semanal.yml`, `diario.yml` y `validate.yml`.

   Si no está, el navegador no subió la carpeta oculta. En ese caso: **Add file → Create new file**, escribí como nombre `.github/workflows/semanal.yml`, pegá el contenido de ese archivo y repetí con los otros tres.

### Paso 2 – Repo público para el hosting temporal
1. **+ → New repository**.
   - Nombre: `cults-cdn`
   - Marcá **Public**.
   - **Sí** tildá "Add a README".
2. **Create repository**.

Este repo queda casi siempre vacío: los archivos están ahí solo unos minutos mientras Cults3D los descarga.

### Paso 3 – Token para que el agente pueda escribir en `cults-cdn`
1. Tu foto (arriba a la derecha) → **Settings** → abajo de todo, **Developer settings**.
2. **Personal access tokens → Fine-grained tokens → Generate new token**.
3. Completá:
   - Token name: `cults-cdn`
   - Expiration: **1 año**. Anotá la fecha en tu calendario para renovarlo.
   - Repository access: **Only select repositories** → elegí `cults-cdn`.
   - Permissions → Repository permissions → **Contents: Read and write**. El resto queda como está.
4. **Generate token**. Copialo ya: GitHub no lo vuelve a mostrar.

### Paso 4 – Permitir que los workflows guarden cambios
En `cults3d-agent` → **Settings → Actions → General**:
1. "Actions permissions": **Allow all actions and reusable workflows**.
2. "Workflow permissions": **Read and write permissions**.
3. **Save**.

### Paso 5 – Cargar las claves (secrets) y las variables
En `cults3d-agent` → **Settings → Secrets and variables → Actions**.

En la pestaña **Secrets**, usá **New repository secret** para cada uno:

| Name | Value |
|---|---|
| `CULTS_USERNAME` | `AdvancedUrbanDesignLaborator1`, tu nick de Cults3D |
| `CULTS_API_KEY` | la key **nueva** del paso 0 |
| `CDN_TOKEN` | el token del paso 3 |

En la pestaña **Variables**, usá **New repository variable**:

| Name | Value | ¿Obligatoria? |
|---|---|---|
| `CDN_REPO` | `TU-USUARIO-DE-GITHUB/cults-cdn` | Sí |
| `AUTO_PRECIOS` | `1` para que el análisis del domingo ajuste precios solo | No (sin ella solo te recomienda precios) |
| `LICENSE_CODE` / `LICENSE_CODE_COMMERCIAL` | código de licencia de Cults, si querés forzar una | No (el agente la elige solo) |
| `MADE_WITH_AI` | `0` solo para piezas que diseñaste vos | No (por defecto `1`) |

Las claves quedan encriptadas: no aparecen en los logs ni las puede leer nadie, ni siquiera vos.

### Paso 6 – Primera corrida del análisis
1. Pestaña **Actions**. Si aparece un botón verde "I understand my workflows, go ahead and enable them", hacé clic.
2. A la izquierda, elegí **Análisis semanal del mercado (agente completo)** → **Run workflow** → **Run workflow**. Dejá "Ajustar precios" sin tildar.
3. Tarda entre 10 y 30 minutos. Al terminar:
   - el run queda en verde;
   - abriéndolo, el **resumen** muestra el top de nichos, los productos nuevos y la cola;
   - en el repo aparece la carpeta `reportes/` con `RESUMEN.md`, `cults3d_mercado.xlsx` y los CSV.

   Para bajar un Excel: abrilo en GitHub y tocá **Download raw file**.
4. Si falla en el paso "1. Analizar el mercado", revisá que `CULTS_USERNAME` y `CULTS_API_KEY` estén bien escritos, sin espacios.

### Paso 7 – Prueba de publicación sin publicar (dry run)
1. **Actions → Publish next design to Cults3D → Run workflow**, con **Dry run tildado**.
2. Al terminar, abajo del run, en **Artifacts**, bajá `build-N`. Revisá:
   - las imágenes;
   - los STL;
   - el texto de la descripción;
   - el zip de 3MF.

### Paso 8 – Primera publicación real
1. **Run workflow** otra vez, con **Dry run sin tildar**.
2. El resumen del run muestra el link a tu publicación en Cults3D. Entrá y revisala.
3. Revisá en Cults3D que la licencia y el precio sean los correctos. Esto valida los campos de la API, que todavía no se habían probado con tu cuenta real.

Listo. Desde ese momento todo corre solo: análisis los domingos, publicación lunes y jueves, descuentos todos los días.

## Uso diario

- **Pausar todo:** creá en el repo un archivo vacío llamado `PAUSED` (**Add file → Create new file**). Para reanudar, borralo.
- **Ver qué hizo el agente:** abrí `reportes/RESUMEN.md` en el repo, o la pestaña Actions.
- **Nichos que necesitan diseño nuevo:** el resumen del domingo lista los nichos rentables que no tienen plantilla. Pasale esa lista a Claude en el proyecto *CULTS 3D*: diseña el `.scad` y la ficha `.yaml`, que subís a `designs/` y `queue/`.
- **Productos rechazados:** si un producto generado no pasa la verificación, va a `rechazados/` y no se publica. El resumen dice cuál fue.
- **Cambiar horarios:** editá la línea `cron` del workflow correspondiente. Está en UTC: hora de Buenos Aires + 3.
- **Validación automática:** cada vez que subís algo a `queue/` o `designs/`, el workflow *Validate queue* comprueba todo.

## Notas

- **Marca "hecho con IA":** los diseños se generan con asistencia de IA, así que se publican con `madeWithAi: true`. Es lo honesto y lo que piden las reglas de Cults3D.
- **Licencia:** si no la definís, el agente elige una licencia de Cults que permita la venta.
- **Límites de la API:** ~500 llamadas por día. El análisis semanal usa unas 30; cada publicación, menos de 40.
- **Descargas ≠ ventas:** la API no muestra las ventas de otros vendedores. El análisis usa las descargas de los diseños pagos como aproximación.

## Uso opcional desde tu PC (`agente.py`)

No hace falta: GitHub ya hace todo. Sirve si querés correr algo a mano y ver el resultado al instante.

1. Instalá Python 3.12 desde python.org. En Windows, tildá "Add python to PATH".
2. Abrí una terminal en la carpeta del repo y corré `pip install -r requirements.txt`.
3. Creá un archivo `.env` en esa carpeta. El `.gitignore` evita que se suba a GitHub. Contenido:
   ```
   CULTS_USERNAME=tu_nick
   CULTS_API_KEY=tu_key_nueva
   ```
4. Para `construir` necesitás además OpenSCAD (openscad.org) y, opcionalmente, PrusaSlicer.

Si corrés `todo` en la PC, después subí la carpeta `queue/` actualizada a GitHub.

**Comandos:**

| Comando | Qué hace |
|---|---|
| `python agente.py analizar` | Baja hasta 500 diseños pagos de los últimos 90 días y genera `cults3d_mercado.xlsx` (hojas resumen, tags, categorias y disenos). |
| `python agente.py priorizar` | Muestra qué diseños de la cola coinciden con los nichos que más venden, y arma `nichos_sin_cubrir.csv`. |
| `python agente.py priorizar --aplicar` | Además reordena la cola: lo más rentable sale primero. |
| `python agente.py generar` | Crea fichas nuevas en `queue/` a partir de las plantillas de `templates/`, para los nichos rentables que todavía no tenés cubiertos. Ajusta el precio a la mediana del nicho. |
| `python agente.py ventas` | Reporte de **tus** ventas (`ventas_propias.xlsx`): clasifica cada diseño en ESTRELLA / NO CONVIERTE / NO SE VE / VENDE POCO / NUEVO / GRATIS y dice qué hacer con cada uno. |
| `python agente.py ventas --aplicar-precios` | Además cambia los precios en Cults3D: +10 % a las estrellas y −20 % a los que tienen vistas pero no venden (piso USD 1.49, techo USD 4.99, nunca toca los gratis). |
| `python agente.py calendario` | Próximas fechas comerciales y si hay que publicar ya. `--generar` agrega a la cola los productos de temporada. |
| `python agente.py descuentos` | Muestra si hoy empieza una promo (Black Friday 30 %, Navidad 20 %). `--aplicar` la crea; `--forzar 25 --dias 3 --aplicar` lanza una promo manual. |
| `python agente.py todo` | Hace todo de una: analizar, ventas, temporada, priorizar, generar y reordenar la cola. |
| `python agente.py construir` | Genera los STL y las imágenes del próximo diseño en `build/`, para revisarlos. |
| `python agente.py publicar --prueba` | Simula la publicación sin publicar nada. |

## Calidad sin imprimir: verificación, renders y archivos

Nada de esto requiere impresora: todo se genera y se verifica de forma digital a partir de los STL.

**1. Verificación con slicer (PrusaSlicer, en GitHub Actions).** Cada archivo se slicea con un perfil estándar: boquilla 0.4, capas de 0.2 mm, 3 paredes, 15 % gyroid, PLA.
- La ficha publica el **tiempo y los gramos reales** de cada archivo.
- El slicer vuelve a cortar la pieza con soportes automáticos a 45° y mide qué parte del material serían soportes:

  | Material de soporte | Clasificación | Qué dice la ficha |
  |---|---|---|
  | < 0.5 % | none | "No supports" |
  | 0.5–5 % | minimal | "Minimal supports", con el porcentaje |
  | > 5 % | needed | "Supports needed" |

- La portada muestra "NO SUPPORTS" y el tag "no supports" **solo** si todos los archivos dan none.
- Además se revisa que cada archivo sea una sola pieza (sin partes sueltas), una malla cerrada y que entre en una cama de 220 × 220 mm.

**2. Archivos 3MF listos.** Cada STL también se entrega como .3mf orientado, empaquetado en `…_3mf_print_ready.zip`. Se abre en Bambu Studio, OrcaSlicer y PrusaSlicer.

**3. Renders fotorrealistas (Blender 4.2, en GitHub Actions).**
- Plástico PLA mate con líneas de capa sutiles, fondo de estudio y 3 luces.
- Los colores y ángulos se configuran por producto (`render_colors`, `render_angles`).
- Si Blender no está instalado (por ejemplo en tu PC), se usan las vistas de OpenSCAD.

**Imágenes de cada publicación:**
1. Portada: render fotorrealista con badges.
2. Segundo render, en otro color y ángulo.
3. Todas las variantes lado a lado.
4. Tarjeta de especificaciones: medidas, tiempo y gramos reales.
5. Vista técnica.

**4. Medidas en mm y en pulgadas** para cada archivo, dentro de la descripción.

**5. Control dimensional sobre la malla (`tools/medidas.py`).** No se confía en el código: se corta el STL ya generado y se miden las medidas clave. Si una no da, el build se corta y no se publica nada.

| Tipo de check | Qué mide | Ejemplo |
|---|---|---|
| `bbox` | tamaño total | bin Gridfinity 1×1×3 = 41.5 × 41.5 × 25.4 mm |
| `outer` | contorno exterior a una altura | pie Gridfinity: 35.6 → 37.2 → 41.5 mm |
| `hole` | ancho mínimo de cada agujero y cuántos hay | 21 agujeros hex de 6.75 mm entre caras |
| `hole_max` | el agujero más grande a una altura | cabeza avellanada M4 = 9.36 mm |
| `fit` | el objeto redondo más grande que pasa | maceta de 12 cm: entra un Ø134 mm |

- Los polígonos se compensan por facetado: el diámetro se divide por cos(180°/lados), así el ancho mínimo real es el nominal.
- La cama se controla girando la pieza de a 1°: si entra en 220 × 220 en diagonal, entra. Una variante puede pedir una cama mayor con `bed: 256`, y la ficha lo avisa.

**Estándares usados para las medidas** (ver `specs/estandares.yaml`, con fuentes):

| Producto | Estándar | Medida en el diseño |
|---|---|---|
| Gridfinity | grilla 42, bin 41.5, 7 mm por unidad, labio 4.4 | perfil de pie y labio exactos |
| Portapuntas | punta 1/4" = 6.35 entre caras | agujero hex 6.75 |
| Portapilas | AA ≤ 14.5 / AAA ≤ 10.5 (IEC) | 15.1 / 11.1 |
| Bandejas de wargame | bases 25 / 28.5 / 32 / 40, imanes 5×2 y 6×2 | alojamiento base + 0.6, imán + 0.3 |
| Escuadra | cabeza ISO 10642, paso ISO 273 | M3 7.12 / M4 9.36 / M5 11.6 avellanado |
| Maceta | macetas de vivero 9 / 12 / 15 cm, alto ≈ 0.87 × Ø | 14 mm de juego a la altura del borde |
| Bandeja de dados | d20 de 23 a 29 mm | ranuras de 26 mm |
| Farol | vela LED tealight Ø38 | boca Ø41 |
| Clips de cable | 3.5 / 4.5 / 6 / 8 mm | + 0.2 mm |
| Soporte de auriculares | AirPods Max 187 mm de alto | 230 mm (y 195 compacto) |
| Soporte de celular | funda rugged 15–17 mm | ranura de 18 mm |

**6. Soportes, doble control.**
- El slicer usa la regla de los 45° (umbral 44°): una cara a 45° justos (chaflán, agujero en gota, pie Gridfinity) se imprime sin soporte.
- Además se mide sobre la malla el área de caras más planas que 44° (`overhang_mm2`).
- Si el slicer marca soporte pero esa área es menor a 1 mm², lo que marcó son caras a 45° justos redondeadas al límite. En ese caso la pieza queda como "none" y el reporte lo indica con `support_basis: geometry`.
- Un techo plano o un puente real siempre suman área, así que nunca pasan como "no supports".

## Licencias, precios e idiomas

- **Dos publicaciones por diseño pago:**

  | Publicación | Licencia | Precio |
  |---|---|---|
  | Normal | Uso personal | Precio de la ficha |
  | "… \| Commercial License" | Uso comercial: el comprador puede vender las piezas impresas, no los archivos | USD 9.99 |

  Para cambiar el precio comercial de un producto, usá `commercial_price:` en su ficha. Para no crear la versión comercial, usá `commercial: false`. Los productos gratis no la tienen.
- **Precio mínimo: USD 1.49.** Rige para las plantillas y para los ajustes automáticos de precio.
- **Idiomas:** cada ficha tiene `i18n` con título y resumen en francés y alemán.
  - Esos resúmenes se agregan al final de la descripción en inglés.
  - Además, el agente intenta cargar la traducción como versión FR/DE en Cults3D. Si la API no la acepta, lo anota en el log y sigue publicando.

**Plantillas (`templates/`):** cada una asocia palabras clave de nichos con un diseño paramétrico y su ficha de venta. Hay 8:

| Plantilla | Tipo |
|---|---|
| Bins Gridfinity básicos | normal |
| Portapuntas y portapilas Gridfinity | diferenciada, para nichos saturados |
| Maceta facetada con plato | normal |
| Bandeja de dados | normal |
| Soporte de celular y tablet | normal |
| Farol calabaza | temporada: Halloween |
| Copos de nieve | temporada: Navidad |

Cuantas más plantillas haya, más nichos puede cubrir `generar` sin intervención.

**Nichos saturados:** el análisis también baja una muestra de diseños gratis y calcula, para cada tag, qué parte de la oferta es gratis (`pct_gratis`). Si pasa el 60 %, el nicho queda marcado como `saturado` y `generar` solo publica plantillas marcadas `diferenciado: true`. El ranking usa el `indice_oportunidad`: ventas por día × (1 − % gratis) × % de diseños que venden.

**Temporada:** las plantillas con `temporada:` entran a la cola solo dentro de la ventana de publicación de su evento (Halloween: de 7 semanas a 7 días antes; Navidad: de 9 semanas a 10 días antes). Mientras la ventana está abierta, se publican primero. Si la fecha pasa y no salieron, esperan al año siguiente.

## Automatizaciones en GitHub

| Workflow | Cuándo corre | Qué hace |
|---|---|---|
| `publish.yml` | Lunes y jueves 10:17 | Publica el próximo diseño; los de temporada abierta salen primero. |
| `semanal.yml` | Domingos 20:07 | Analiza el mercado y tus ventas, genera y verifica productos nuevos, reordena la cola y guarda los reportes en `reportes/`. |
| `diario.yml` | Todos los días 09:07 | Crea los descuentos del día (Black Friday, Navidad) y suma a la cola los productos de temporada cuya ventana se abrió. Deja registro en `descuentos_aplicados.csv`. |
| `validate.yml` | En cada cambio | Verifica que todo diseño en cola compile, sea una malla cerrada y entre en la cama. |

El archivo `PAUSED` detiene todo: el análisis, la publicación y los descuentos.
