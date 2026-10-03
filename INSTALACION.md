# Instalación del agente Cults3D

Una sola vez, ~30 min.

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

