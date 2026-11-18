# Tablero de Power BI · Paso a paso desde cero

**Resultado:** una sola hoja, igual a `powerbi/referencia_tablero.png`.

**Archivos** (todos en la carpeta `ufc_ranking\powerbi`):
- `tablero_ranking_fans.xlsx`: los datos. Los genera `src/preparar_powerbi.py`.
- `tema_esquina_roja.json`: colores (fondo negro y rojo).

---

## 0. Ubicarse en la pantalla

- **Barra izquierda:** 1.er ícono **Vista de informe** (donde se arma la hoja), 2.º **Vista de tabla**,
  3.º **Vista de modelo** (relaciones).
- **Panel derecho:**
  - **Visualizaciones:** tiene dos pestañas. **Compilar objeto visual** (íconos de gráficos y los casilleros
    "Eje X", "Eje Y", "Columnas", etc.) y **Formato** (ícono del **pincel**).
  - **Datos:** las tablas con sus columnas.
  - **Filtros:** si no lo ves, **Ver → Filtros**.
- **Cómo se pone un dato en un gráfico:** se **arrastra** la columna desde **Datos** hasta un casillero de
  **Compilar objeto visual**.
- **Cómo se crea un gráfico nuevo:** primero **clic en un lugar vacío de la hoja** (si no, se cambia el
  gráfico que está seleccionado) y después clic en el ícono del gráfico.
- **Tamaño y posición exactos:** con el gráfico seleccionado, **pincel → General → Propiedades →
  Tamaño y posición** → escribir **Alto**, **Ancho**, **Posición horizontal (X)** y **Posición vertical (Y)**.

---

## 1. Archivo nuevo y datos

1. Cerrar el archivo anterior sin guardar. **Archivo → Nuevo**.
2. **Inicio → Obtener datos → Libro de Excel** → ir a `ufc_ranking\powerbi` → `tablero_ranking_fans.xlsx` →
   **Abrir**.
3. Tildar solo estas 5 hojas: **Categorias**, **Ranking**, **Coincidencias**, **Modelo** y **Variables**
   (Evolucion y Peleas no se usan en esta hoja) → **Cargar**.
4. **Archivo → Guardar como** → `ufc_ranking\powerbi\tablero_ranking_fans.pbix`.
   Guardar seguido con **Ctrl + S**.

## 2. Colores (tema)

1. **Ver → Temas** → flechita **⌄** que abre la lista de temas → **Examinar temas**.
2. Elegir `ufc_ranking\powerbi\tema_esquina_roja.json` → **Abrir**. La hoja queda negra.

## 3. Relaciones

1. **Vista de modelo** (3.er ícono). **Inicio → Administrar relaciones**.
2. Power BI a veces crea relaciones solo. Tienen que quedar **exactamente estas dos**; si hay otras,
   seleccionarlas → **Eliminar**:

| De | Columna | A | Columna | Cardinalidad |
|---|---|---|---|---|
| Categorias | division | Ranking | division | Uno a varios (1:*) |
| Categorias | division | Coincidencias | division | Uno a varios (1:*) |

3. Si falta alguna: **+ Nueva relación** → arriba elegir **Categorias** y hacer clic en la columna
   `division` → abajo elegir la otra tabla y hacer clic en su `division` → **Cardinalidad: Uno a varios** →
   **Guardar** → **Cerrar**.

## 4. Ajustes de columnas (una sola vez)

Se hacen en el panel **Datos**: clic en la columna y se cambia en el panel **Propiedades**, que aparece al lado.
(En la Vista de informe, lo mismo está en la pestaña **Herramientas de columnas**, arriba.)

| Tabla → columna | Qué cambiar |
|---|---|
| Categorias → `division` | **Avanzado → Ordenar por columna → orden** (Mosca primero, Pesado último) |
| Ranking → `puesto` | **Avanzado → Ordenar por columna → puesto_num** (C, 1, 2… y no 1, 10, 11) |
| Ranking → `elo` | **Avanzado → Resumir por → Ninguno** |
| Coincidencias → `pct_coinciden` | **Formato → Porcentaje**, 0 decimales |
| Modelo → `accuracy` | **Formato → Porcentaje**, 1 decimal |

---

## 5. Armar la hoja

Volver a **Vista de informe** (1.er ícono). Doble clic en la pestaña "Página 1" de abajo → escribir **Tablero**.

### 5.1 Título
1. **Insertar → Cuadro de texto**.
2. Escribir `RANKING DE FANS UFC`, **Enter**, y en la segunda línea:
   `Ranking no oficial · hecho con datos de UFCStats · corte 14/11/2026`.
3. Seleccionar la primera línea → tamaño **24**, **negrita**, color blanco. La segunda línea → tamaño **11**,
   color gris.
4. Pincel → **Fondo** → apagar.
5. **Tamaño y posición:** Alto **70** · Ancho **700** · X **20** · Y **5**.

### 5.2 Botones de categoría
1. Clic en vacío → ícono **Segmentación de datos** (embudo con una lista).
2. Arrastrar **Categorias → division** al casillero **Campo**.
3. Pincel → **Configuración de segmentación → Opciones → Estilo → Mosaico**.
4. Pincel → **Configuración de segmentación → Selección** → activar **Selección única**.
5. Pincel → **Encabezado de segmentación** → apagar.
6. **Tamaño y posición:** Alto **45** · Ancho **1240** · X **20** · Y **80**.
7. Hacer clic en **Ligero** para dejarlo elegido.

### 5.3 Tabla del ranking
1. Clic en vacío → ícono **Tabla** (grilla).
2. Arrastrar al casillero **Columnas**, en este orden, desde **Ranking**:
   `puesto`, `peleador`, `elo`, `record`, `media`, `meta`.
3. Renombrar los títulos: en el casillero **Columnas**, doble clic sobre cada nombre y escribir:
   `puesto` → **#** · `peleador` → **Peleador** · `elo` → **Puntos** · `record` → **Récord** ·
   `media` → **MEDIA** · `meta` → **META**.
4. **Filtro top 15:** panel **Filtros** → arrastrar **Ranking → top15** a
   **"Filtros en este objeto visual"** → tildar **Verdadero** (o **True**).
5. Pincel → **Totales** → apagar.
6. Pincel → **Valores** → tamaño de letra **12**. **Encabezados de columna** → tamaño **12**.
7. Pincel → **General → Título** → activar → texto: `Top 15 · nuestro ranking vs. los oficiales`.
8. **Tamaño y posición:** Alto **570** · Ancho **610** · X **20** · Y **135**.
9. Clic en el encabezado **#** de la tabla para ordenar: C, 1, 2, 3…

**Probar:** tocar "Pesado". La tabla tiene que mostrar a Ciryl Gane como C. Después volver a "Ligero".

### 5.4 Las 4 tarjetas
**Tarjeta 1 · Peleadores activos**
1. Clic en vacío → ícono **Tarjeta** (un "123").
2. Arrastrar **Ranking → peleador** al casillero → flechita **⌄** → **Recuento**.
3. Doble clic en el nombre dentro del casillero → escribir **Peleadores activos** (es el texto que se ve
   debajo del número).
4. **Tamaño y posición:** Alto **85** · Ancho **145** · X **645** · Y **135**. Tiene que decir **100**.

**Tarjeta 2 · Coincide con MEDIA**
1. Clic en vacío → **Tarjeta** → arrastrar **Coincidencias → pct_coinciden** → flechita **⌄** → **Promedio**.
2. Renombrar a **Coincide con MEDIA**.
3. **Filtros → Filtros en este objeto visual** → arrastrar **Coincidencias → comparacion** → tildar solo
   **ELO vs MEDIA**.
4. **Tamaño y posición:** Alto **85** · Ancho **145** · X **800** · Y **135**. Con Ligero: **69%**.

**Tarjetas 3 y 4:** seleccionar la tarjeta 2 → **Ctrl + C** → **Ctrl + V**. En la copia: cambiar el filtro a
**ELO vs META**, renombrar a **Coincide con META** y poner X **955** · Y **135** (Ligero: **69%**).
Repetir con **MEDIA vs META**, **Oficiales entre sí** y X **1110** · Y **135** (Ligero: **88%**).

### 5.5 ¿Cuánto acierta el modelo?
1. Clic en vacío → ícono **Gráfico de barras agrupadas** (barras horizontales).
2. **Eje Y:** `Modelo → nombre`. **Eje X:** `Modelo → accuracy`.
3. Pincel → **Etiquetas de datos** → activar.
4. Pincel → **Eje X** → apagar. **Eje Y → Título** → apagar.
5. Pincel → **General → Título** → `¿Cuánto acierta el modelo? (peleas 2024–2026)`.
6. **Tamaño y posición:** Alto **190** · Ancho **615** · X **645** · Y **230**.

Este gráfico no cambia con los botones: el modelo es uno solo para todas las categorías.

### 5.6 ¿Qué pesa más para ganar?
1. Clic en vacío → **Gráfico de barras agrupadas**.
2. **Eje Y:** `Variables → nombre`. **Eje X:** `Variables → peso_absoluto`. **Leyenda:** `Variables → efecto`.
3. Pincel → **Etiquetas de datos** → activar. **Eje X** → apagar. **Eje Y → Título** → apagar.
4. Pincel → **General → Título** → `¿Qué pesa más para ganar?`.
5. Si las barras no quedan de mayor a menor: **tres puntos …** del gráfico → **Ordenar eje →
   peso_absoluto** → **Orden descendente**.
6. **Tamaño y posición:** Alto **275** · Ancho **615** · X **645** · Y **430**.

Rojo = ayuda a ganar; gris = juega en contra. Arriba quedan la edad y los puntos Elo.

---

## 6. Revisar, guardar y publicar

1. Comparar con `referencia_tablero.png`. Dejar **Ligero** elegido y guardar (**Ctrl + S**).
2. **Inicio → Publicar → Mi área de trabajo** → al terminar, clic en **Abrir … en Power BI**.
3. En el navegador: **Archivo → Insertar informe → Publicar en la web (público)** →
   **Crear código de inserción** → **Publicar**.
4. Copiar el link que empieza con `https://app.powerbi.com/view?r=...`.
5. En `app.py`, pegarlo entre las comillas de `POWER_BI_URL = ""`. Subir `app.py` a GitHub.

**Si "Publicar en la web" no aparece o está gris:** la cuenta no lo permite. Plan B:
**Archivo → Exportar → Exportar a PDF**, y se muestra el PDF en la app.

**Después de actualizar el ranking:** correr `src/preparar_powerbi.py`, abrir el `.pbix` →
**Inicio → Actualizar** → **Publicar** de nuevo (el link no cambia).
