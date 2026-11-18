# Ranking de Fans UFC · Bitácora

Qué se hizo, en qué orden y por qué. El resumen del proyecto está en el README.

## Etapa 1 · Diagnóstico y propuesta

| Paso | Qué se hizo | Resultado |
|---|---|---|
| 0 | Definición del proyecto | Tercer ranking de fans, 8 categorías masculinas; organización "Esquina Roja"; usuario: mi hermano |
| 1 | Fuente de datos | UFCStats vía GitHub (los datasets de Kaggle estaban desactualizados). Corte: 14/11/2026 |
| 2 | Limpieza (`limpieza.py`) | 9.003 peleas únicas en dos tablas limpias |
| 3 | EDA (`01_EDA.ipynb`) | 7 problemas de calidad (H1–H7) y las reglas del ranking (actividad de 18 meses, etc.) |
| 4 | Notebook portable | Encuentra solo la carpeta y descarga los datos si faltan |

**Problemas de calidad:** H1 espacios invisibles · H2 25 peleas duplicadas · H3 evento sin fecha ·
H4 faltantes disfrazados ("--") · H5 9 homónimos · H6 120 etiquetas de categoría · H7 empates y No Contest.

## Etapa 2 · Solución

| Paso | Qué se hizo | Por qué |
|---|---|---|
| 1 | Ranking Elo v1 (`elo.py`) | Opción A: simple de explicar ("ganás y sumás") |
| 2 | Elo v2: título ×2, K = 48, campeón aparte | El campeón Gaethje quedaba 3.º. Se probó mover la fecha de inicio y empeoraba: se descartó |
| 3 | Ranking RFM (`rfm.py`) | Primera opción B, contenido de la cursada. Coincide con el Elo en quién es élite, pero no puede ordenarla |
| 4 | Comparación con MEDIA y META (`comparar_oficial.py`) | Responde la pregunta de negocio: 8/8 campeones, 75% y 79% del top |
| 5 | Elo v3: los No Contest cuentan como actividad | Tom Aspinall no aparecía |
| 6 | Elo v4: retirados anunciados, con fuente | Dustin Poirier aparecía 5.º en Ligero |
| 7 | App en Streamlit, estética oscura | Formato parecido a ufc.com, conocido por el usuario |
| 8 | Modelo de machine learning (`modelo.py`) | El profesor pidió ML. Reemplaza al RFM como opción B y valida el ranking |
| 9 | Presentación, guion y video (6 min 21 s) | La presentación cubre todo el proyecto, como pidió el profesor |
| 10 | La app se abre sola con ▷ o F5 | Que el profesor no tenga que escribir comandos |
| 11 | Publicación: GitHub (`sanzlucas72-creator/ranking-fans-ufc`) + Streamlit Community Cloud → https://ranking-fans-ufc.streamlit.app/ | Requisito de la Etapa 2: la app tiene que estar online para el profesor y el usuario |
| 12 | Tablero de Power BI (`powerbi/`, guía en `docs/powerbi_paso_a_paso.md`) | Requisito de la Etapa 2. Una sola hoja: top 15 vs. oficiales, coincidencias y modelo. Entregado como `.pbix` + captura en el README |
| 13 | Ficha del peleador: filtro por categoría, búsqueda por nombre (sin importar tildes) y lista en orden del ranking (campeón, #1, #2…) | Iteración por uso: con 616 peleadores en un solo menú había que scrollear demasiado para encontrar a uno |

## Modelo de machine learning, en detalle

- **Fuga de datos evitada:** en UFCStats el primer peleador gana el 57%, así que se sortea quién es A y quién es B.
  Además, split temporal: entrena con 2012–2023 y prueba con 2024–2026.
- **Variables:** se eligieron con validación cruzada solo en el entrenamiento. Ranking (7): 56,5% ·
  + edad: 58,7% · **+ alcance: 59,6%** (elegido).
- **Prueba:** Regresión Logística 61,8% · Random Forest 62,2% · mejor regla simple 60,1% · regla Elo 55,9%.
- **Elección:** Regresión Logística (probabilidad, coeficientes explicables, estable; el RF no mejora lo suficiente).

## Decisiones principales

| # | Decisión | Por qué |
|---|---|---|
| D1 | Solo resultados de peleas en el ranking (sin datos físicos) | Al alcance le faltaban datos en el 46% de los peleadores |
| D2 | Cálculo desde 2010 | Arrancar en 1994 da el mismo ranking (127 de 128 lugares) |
| D3 | Categoría = la de la última pelea | Simple. Limitación conocida: Holloway, Usman y Pereira |
| D4 | No ajustar parámetros para copiar al oficial | Tiene que ser una tercera opinión |
| D5 | Sin excepciones manuales de categoría | El ranking sale 100% de los datos |
| D6 | Estilo deportivo sin logos de la UFC; "Ranking no oficial" | No hacerse pasar por la página oficial |
| D7 | Modelo con orden sorteado y split temporal | Evaluación honesta, sin fuga de datos |
| D8 | Datos del tablero en Excel, no CSV | Con Windows en español, Power BI lee "0.618" de un CSV como 618 |
| D9 | Tablero entregado como `.pbix` en GitHub, con captura en el README | "Publicar en la web" está deshabilitado en la cuenta del INA por seguridad. Lo indicó el profesor (18/11/2026) |
