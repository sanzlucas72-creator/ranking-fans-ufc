"""
Ranking de Fans UFC · App (Etapa 2)

Usuario: mi hermano, fan de la UFC que conoce los rankings oficiales pero no el proyecto.
Por eso la app:
    - muestra primero el ranking, igual que lo vería en ufc.com (campeón arriba, 1 a 15);
    - pone al lado los rankings oficiales (MEDIA y META) para comparar de un vistazo;
    - explica cada puesto con las peleas que lo justifican (caja blanca);
    - suma un modelo de machine learning que estima quién ganaría entre dos peleadores;
    - no usa jerga técnica: "puntos" en vez de "rating", "le ganó a" en vez de "outcome".

ESTRUCTURA DEL ARCHIVO
    0. Configuración general (librerías, rutas, constantes, estética)
    1. Datos comunes
    2. Encabezado y pestañas
    PARTE A · EL RANKING (opción A: sistema Elo)
        A1. Función que explica cada pelea en una frase
        A2. Pestaña "Ranking"
        A3. Pestaña "Ficha del peleador"
        A4. Pestaña "Contra los oficiales"
    PARTE B · EL MODELO DE PREDICCIÓN (opción B: machine learning)
        B1. Variables del modelo
        B2. Entrenamiento del modelo
        B3. Cálculo de las variables para una pelea
        B4. Pestaña "¿Quién gana?"
    3. Pestañas generales: "Tablero" (Power BI) y "Cómo funciona"

Cómo abrirla (cualquiera sirve):
    - Botón ▷ "Run Python File" de VS Code sobre este archivo, o F5.
    - En una terminal: python app.py
La primera vez instala sola las librerías que falten y después abre la app en el navegador.
"""

# =============================================================================================
# ARRANQUE AUTOMÁTICO: la app se abre sin escribir comandos
# =============================================================================================
# Una app de Streamlit normalmente se abre con "streamlit run app.py". Si alguien la ejecuta
# como un archivo de Python común (botón ▷ de VS Code o "python app.py"), este bloque:
#   1. instala las librerías que falten (solo la primera vez);
#   2. vuelve a abrir este mismo archivo con Streamlit;
#   3. abre el navegador en la app.
# Cuando el archivo ya está corriendo dentro de Streamlit, este bloque no hace nada.

import subprocess                                       # para ejecutar otros programas
import sys                                              # para saber qué Python se está usando
import time                                             # para esperar unos segundos
import webbrowser                                       # para abrir el navegador
from pathlib import Path                                # para armar rutas de archivos en cualquier sistema

LIBRERIAS_APP = ["streamlit", "pandas", "scikit-learn", "altair"]   # lo mínimo que necesita la app
PUERTO = 8501                                           # dirección local: http://localhost:8501


def abrir_con_streamlit():
    try:                                                # ¿están instaladas las librerías?
        import altair, pandas, sklearn, streamlit       # noqa: F401  (solo se prueba que existan)
    except ImportError:                                 # si falta alguna, se instalan
        print("Instalando las librerías necesarias (solo la primera vez, puede tardar unos minutos)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *LIBRERIAS_APP])

    from streamlit import runtime                       # ¿ya estamos corriendo dentro de Streamlit?
    if runtime.exists():
        return                                          # sí: seguimos con la app normalmente

    carpeta = Path(__file__).resolve().parent           # carpeta del proyecto (ahí está .streamlit/config.toml)
    print(f"Abriendo la app en http://localhost:{PUERTO} ... (para cerrarla: Ctrl + C)")
    proceso = subprocess.Popen(                         # relanzamos este archivo con Streamlit
        [sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve()),
         "--server.headless", "true",                   # sin preguntas en la terminal
         "--server.port", str(PUERTO),
         "--browser.gatherUsageStats", "false"],
        cwd=carpeta)
    time.sleep(4)                                       # le damos unos segundos para arrancar
    webbrowser.open(f"http://localhost:{PUERTO}")       # y abrimos el navegador
    try:
        proceso.wait()                                  # la app queda abierta hasta cerrar la terminal
    except KeyboardInterrupt:
        proceso.terminate()                             # Ctrl + C la cierra prolijamente
    sys.exit(0)                                         # no seguimos ejecutando el resto "a mano"


abrir_con_streamlit()

# =============================================================================================
# 0. CONFIGURACIÓN GENERAL
# =============================================================================================

import html                                             # para escribir nombres de forma segura dentro del HTML
import unicodedata                                      # para buscar nombres sin importar las tildes

import altair as alt                                    # gráficos (viene incluido con Streamlit)
import pandas as pd                                     # tablas
import streamlit as st                                  # la librería que arma la app web
from sklearn.linear_model import LogisticRegression     # modelo de machine learning (parte B)
from sklearn.pipeline import Pipeline                   # encadena escalado + modelo (parte B)
from sklearn.preprocessing import StandardScaler        # escala las variables (parte B)

RAIZ = Path(__file__).resolve().parent                  # carpeta donde está este archivo (la del proyecto)
PROC = RAIZ / "data" / "processed"                      # resultados: ranking, historial, modelo
EXT = RAIZ / "data" / "external"                        # rankings oficiales (MEDIA y META)
CATEGORIAS = ["Mosca", "Gallo", "Pluma", "Ligero",      # las 8 categorías masculinas,
              "Wélter", "Mediano", "Semipesado", "Pesado"]  # de la más liviana a la más pesada
LIMITES = {"Mosca": "125 lb", "Gallo": "135 lb", "Pluma": "145 lb", "Ligero": "155 lb",   # peso límite
           "Wélter": "170 lb", "Mediano": "185 lb", "Semipesado": "205 lb", "Pesado": "265 lb"}
LIMITACION = {"Max Holloway": "Ligero",                 # limitación conocida (decisión D24): peleadores
              "Kamaru Usman": "Wélter",                 # cuya última pelea fue en otra categoría; acá se
              "Alex Pereira": "Semipesado"}             # anota en qué categoría los ubican los oficiales
POWER_BI_URL = ""                                       # link del tablero de Power BI ("Publicar en la web")

st.set_page_config(page_title="Ranking de Fans UFC",    # título de la pestaña del navegador
                   page_icon="🥊", layout="wide")        # ícono y ancho completo de pantalla

# --- Estética: fondo negro y estilo deportivo, inspirado en las páginas de rankings oficiales.
# --- No usa logos ni marcas de la UFC. Los colores están forzados acá para que la app se vea igual
# --- aunque Streamlit no encuentre .streamlit/config.toml (pasa si se abre desde otra carpeta).
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&display=swap');
/* Tamaño de letra general: Streamlit mide casi todo en "rem" (relativo a esta base).
   Por defecto es 16px; con 19px todo el texto de la app queda un 20% más grande. */
html { font-size: 19px; }
.stApp { background: #0b0b0b; color: #f2f2f2; }
/* Colores forzados: la app se ve igual aunque Streamlit no lea .streamlit/config.toml
   (pasa si se ejecuta desde otra carpeta, porque Streamlit busca la configuración ahí). */
header[data-testid="stHeader"] { background: #0b0b0b; }
header[data-testid="stHeader"] * { color: #bdbdbd; }
.stApp p, .stApp li, .stApp label, .stApp td, .stApp th,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] p,
[data-testid="stMetricValue"], [data-testid="stRadio"] label p { color: #f2f2f2; }
h1, h2, h3, h4 { color: #ffffff !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #9a9a9a !important; }
button[role="tab"] p { color: #bdbdbd; }
button[role="tab"][aria-selected="true"] p { color: #ffffff; }
button[role="tab"][aria-selected="true"] { border-bottom-color: #d20a0a !important; }
div[data-baseweb="tab-highlight"] { background-color: #d20a0a !important; }
div[data-baseweb="select"] > div { background: #1c1c1c; color: #f2f2f2; border-color: #3a3a3a; }
[data-testid="stAlert"] { background: #1c1c1c; }
[data-testid="stAlert"] p { color: #f2f2f2; }
h1, h2, h3, h4 { font-family: 'Oswald', 'Arial Narrow', sans-serif !important;
                 text-transform: uppercase; letter-spacing: .02em; }
h1 { font-weight: 700 !important; }
/* pestañas en mayúscula */
button[role="tab"] p { font-family: 'Oswald', sans-serif; text-transform: uppercase;
                       letter-spacing: .06em; font-size: 1.02rem; }
/* números grandes (métricas) */
[data-testid="stMetricValue"] { font-family: 'Oswald', sans-serif; text-transform: uppercase; }
[data-testid="stMetricLabel"] p { text-transform: uppercase; letter-spacing: .1em; color: #9a9a9a; }
/* bloque del campeón */
.cat { color: #d20a0a; font-family: 'Oswald', sans-serif; font-weight: 600;
       text-transform: uppercase; letter-spacing: .08em; font-size: 1rem; }
.campeon { font-family: 'Oswald', sans-serif; font-weight: 700; font-size: 2.6rem;
           line-height: 1.05; text-transform: uppercase; margin: .3rem 0 .2rem 0; }
.etiqueta { font-family: 'Oswald', sans-serif; letter-spacing: .25em; font-size: .85rem;
            color: #bdbdbd; text-transform: uppercase; }
.dato { color: #9a9a9a; font-size: .9rem; margin-top: .6rem; }
.linea { border-top: 1px solid #3a3a3a; margin: 1rem 0; }
/* tabla del ranking */
table.rk { width: 100%; border-collapse: collapse; }
table.rk th { font-family: 'Oswald', sans-serif; text-transform: uppercase; letter-spacing: .1em;
              font-weight: 500; color: #8a8a8a; font-size: .8rem; text-align: left;
              padding: .4rem .6rem; border-bottom: 1px solid #3a3a3a; }
table.rk td { padding: .62rem .6rem; border: none; border-bottom: 1px solid #1f1f1f; font-size: 1.1rem; color: #f2f2f2; }
table.rk th { border: none; border-bottom: 1px solid #3a3a3a; }
table.rk tr:hover td { background: #161616; }
table.rk td.n { font-family: 'Oswald', sans-serif; font-weight: 700; width: 3rem; }
table.rk td.p { font-weight: 500; }
table.rk td.num { font-family: 'Oswald', sans-serif; text-align: right; color: #f2f2f2; }
table.rk td.of { text-align: center; color: #bdbdbd; width: 4.5rem; }
table.rk td.of.vacio { color: #555; }
/* columnas de comparación */
.fila { display: flex; gap: .8rem; padding: .45rem 0; border-bottom: 1px solid #1f1f1f; }
.fila .n { font-family: 'Oswald', sans-serif; font-weight: 700; width: 1.6rem; color: #f2f2f2; }
.fila.comun span.nom { color: #ffffff; font-weight: 600; }
.fila span.nom { color: #9a9a9a; }
.fila.comun .n { color: #d20a0a; }
</style>
""", unsafe_allow_html=True)


# =============================================================================================
# 1. DATOS COMUNES (los usan las dos partes)
# =============================================================================================

@st.cache_data                                          # se cargan una sola vez: la app va más rápida
def cargar():
    ranking = pd.read_csv(PROC / "ranking_elo.csv", parse_dates=["ultima_pelea"])  # el ranking (opción A)
    historial = pd.read_csv(PROC / "elo_historial.csv", parse_dates=["fecha"])     # cada pelea, con sus puntos
    detalle = pd.read_csv(PROC / "comparacion_oficial_detalle.csv")                # puesto en los 3 rankings
    resumen = pd.read_csv(PROC / "comparacion_oficial_resumen.csv")                # coincidencias por categoría
    media = pd.read_csv(EXT / "ranking_media_2026-11-16.csv")                      # ranking oficial MEDIA
    meta = pd.read_csv(EXT / "ranking_meta_2026-11-16.csv")                        # ranking oficial META
    return ranking, historial, detalle, resumen, media, meta                       # devolvemos las 6 tablas


ranking, historial, detalle, resumen, media, meta = cargar()                       # cargamos todo
FECHA_CORTE = historial["fecha"].max()                                             # último evento incluido
ULTIMO_EVENTO = historial.loc[historial["fecha"] == FECHA_CORTE, "evento"].iloc[0]  # su nombre


# =============================================================================================
# 2. ENCABEZADO Y PESTAÑAS
# =============================================================================================

st.title("Ranking de Fans UFC")                                                    # título grande
st.caption(f"Ranking no oficial · un tercer ranking, hecho con datos y explicable pelea por pelea · "
           f"Datos al {FECHA_CORTE:%d/%m/%Y} ({ULTIMO_EVENTO}) · Fuente: UFCStats.com")  # subtítulo

pestanas = st.tabs(["🏆 Ranking", "👤 Ficha del peleador",       # parte A
                    "🔮 ¿Quién gana?",                           # parte B
                    "⚖️ Contra los oficiales",                   # parte A
                    "📊 Tablero", "❓ Cómo funciona"])            # generales


# #############################################################################################
#
#                       PARTE A · EL RANKING (opción A: sistema Elo)
#
#   El cálculo se hace en src/elo.py. Acá solo se muestra: el ranking por categoría, la ficha
#   de cada peleador con su historial de puntos y la comparación con los rankings oficiales.
#
# #############################################################################################

# ---------------------------------------------------------------------------------------------
# A1. Función que explica cada pelea en una frase (la "caja blanca" del ranking)
# ---------------------------------------------------------------------------------------------
def explicar(fila):
    """Convierte una fila del historial en una frase, por ejemplo: '+24 · le ganó a X por KO/TKO'."""
    signo = "+" if fila["cambio"] >= 0 else "−"                         # ¿sumó o restó puntos?
    puntos = f"{signo}{abs(fila['cambio']):.0f}"                         # ej. "+24" o "−12"
    if fila["resultado"] == "Victoria":                                  # según el resultado...
        accion = f"le ganó a {fila['rival']}"                            # ...ganó
    elif fila["resultado"] == "Derrota":
        accion = f"perdió con {fila['rival']}"                           # ...perdió
    else:
        accion = f"empató con {fila['rival']}"                           # ...empató
    forma = {"KO/TKO": " por KO/TKO", "Sumisión": " por sumisión",       # cómo terminó la pelea
             "Decisión": " por decisión"}.get(fila["metodo"], "")
    titulo = " · pelea por el título (vale doble)" if fila["por_titulo"] else ""   # ¿fue por el cinturón?
    if fila["prob_esperada"] >= 0.65:                                    # contexto: ¿era favorito?
        contexto = " · era favorito"                                     # (más de 65% de chance según el Elo)
    elif fila["prob_esperada"] <= 0.35:
        contexto = " · no era favorito"                                  # (menos de 35%)
    else:
        contexto = ""                                                    # pelea pareja: sin comentario
    return f"{puntos} · {accion}{forma}{titulo}{contexto}"               # la frase completa


# ---------------------------------------------------------------------------------------------
# A2. Pestaña "Ranking": campeón + top 15 de cada categoría, con los oficiales al lado
# ---------------------------------------------------------------------------------------------
with pestanas[0]:
    cat = st.radio("Categoría", CATEGORIAS, horizontal=True, index=3, key="cat_ranking")  # arranca en Ligero
    tabla = ranking[ranking["division"] == cat].copy()                   # el ranking de esa categoría
    campeon = tabla[tabla["campeon"]].iloc[0]                            # la fila del campeón

    izq, der = st.columns([1, 2])                                        # dos columnas: 1/3 y 2/3 del ancho
    with izq:                                                            # columna izquierda: el campeón
        st.markdown(f"""
<div class="cat">{cat} · {LIMITES[cat]}</div>
<div class="campeon">{html.escape(campeon['peleador'])}</div>
<div class="etiqueta">Campeón</div>
<div class="dato">{campeon['elo']} puntos · récord desde 2010: {campeon['record']}<br>
última pelea: {campeon['ultima_pelea']:%d/%m/%Y}</div>
<div class="linea"></div>""", unsafe_allow_html=True)                  # bloque con estilo propio (CSS)
        ver_todos = st.toggle("Mostrar todos los activos (no solo el top 15)")   # interruptor
        st.caption(f"{len(tabla)} peleadores activos en {cat} (pelearon en los últimos 18 meses "
                   "y no anunciaron su retiro).")                       # cuántos hay en la categoría

    resto = tabla[~tabla["campeon"]]                                     # todos menos el campeón
    if not ver_todos:                                                    # si el interruptor está apagado...
        resto = resto.head(15)                                           # ...solo el top 15, como el oficial
    pos_media = {(p, d): x for p, d, x in zip(detalle["peleador"],      # diccionario (peleador, categoría)
                                              detalle["division_media"], detalle["puesto_media"])}  # -> puesto MEDIA
    pos_meta = {(p, d): x for p, d, x in zip(detalle["peleador"],       # lo mismo para el META
                                             detalle["division_meta"], detalle["puesto_meta"])}
    vista = pd.DataFrame({                                               # la tabla que se va a mostrar
        "Puesto": resto["puesto"].astype(int).values,                    # 1, 2, 3...
        "Peleador": resto["peleador"].values,                            # nombre
        "Puntos": resto["elo"].values,                                   # puntaje Elo
        "Récord": resto["record"].values,                                # victorias-derrotas-empates
        "MEDIA": [pos_media.get((n, cat)) for n in resto["peleador"]],   # su puesto en el MEDIA
        "META": [pos_meta.get((n, cat)) for n in resto["peleador"]],     # su puesto en el META
    })
    oficiales = vista[["MEDIA", "META"]]                                 # las dos columnas oficiales
    vista[["MEDIA", "META"]] = oficiales.astype(object).where(oficiales.notna(), "—")  # "—" = fuera de su top 15
    with der:                                                            # columna derecha: la tabla
        filas = "".join(                                                 # una fila HTML por peleador
            f"<tr><td class='n'>{r.Puesto}</td><td class='p'>{html.escape(r.Peleador)}</td>"
            f"<td class='num'>{r.Puntos}</td><td>{r[3]}</td>"
            f"<td class='of{' vacio' if r.MEDIA == '—' else ''}'>{r.MEDIA}</td>"
            f"<td class='of{' vacio' if r.META == '—' else ''}'>{r.META}</td></tr>"
            for r in vista.itertuples(index=False))
        st.markdown("<table class='rk'><tr><th>#</th><th>Peleador</th><th style='text-align:right'>Puntos</th>"
                    "<th>Récord</th><th style='text-align:center'>Media</th><th style='text-align:center'>Meta</th></tr>"
                    f"{filas}</table>", unsafe_allow_html=True)        # dibujamos la tabla
        st.caption("MEDIA y META: puesto en los rankings oficiales de la UFC (16/11/2026). "
                   "“—” = no figura en su top 15 de esta categoría.")   # aclaración debajo
        for n in [n for n in vista["Peleador"] if n in LIMITACION]:      # si aparece alguien de la limitación...
            st.info(f"**{n}** aparece en {cat} porque su última pelea fue en esta categoría. "
                    f"Los rankings oficiales lo mantienen en {LIMITACION[n]}. "
                    "Es una limitación conocida del método (ver «Cómo funciona»).")   # ...se avisa


# ---------------------------------------------------------------------------------------------
# A3. Pestaña "Ficha del peleador": por qué tiene sus puntos, pelea por pelea
# ---------------------------------------------------------------------------------------------
with pestanas[1]:
    # --- Buscador: primero se acota por categoría y por nombre, después se elige de una lista corta ---
    f1, f2 = st.columns([2, 3])                                          # dos filtros, uno al lado del otro
    cat_f = f1.selectbox("Categoría", ["Todas"] + CATEGORIAS, index=4,   # "Todas" + las 8; arranca en Ligero
                         key="cat_ficha")
    texto = f2.text_input("Buscar por nombre", placeholder="Ej.: Topuria, Pantoja, Gane…",
                          key="buscar_ficha")                            # búsqueda libre por nombre

    def sin_acentos(t):                                                  # "Wélter" -> "welter", "Błachowicz" -> "blachowicz"
        t = t.lower().replace("ł", "l")                                  # la ł no se separa sola de su "acento"
        return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")

    lista = ranking.copy()                                               # todos los peleadores activos
    if cat_f != "Todas":                                                 # si se eligió una categoría...
        lista = lista[lista["division"] == cat_f]                        # ...solo los de esa categoría
    if texto.strip():                                                    # si se escribió algo...
        lista = lista[lista["peleador"].map(sin_acentos)                 # ...los que contienen ese texto
                      .str.contains(sin_acentos(texto.strip()), regex=False)]   # (sin importar mayúsculas ni tildes)
    lista = lista.assign(                                                # columnas auxiliares para ordenar:
        orden_cat=lista["division"].map(CATEGORIAS.index),               # categoría de liviana a pesada
        orden_puesto=lista["puesto"].replace("C", "0").astype(int))      # campeón = 0, después 1, 2, 3…
    lista = lista.sort_values(["orden_cat", "orden_puesto"])             # orden del ranking: campeón primero

    def etiqueta(nombre):                                                # cómo se ve cada opción del menú
        fila = ranking[ranking["peleador"] == nombre].iloc[0]            # su fila en el ranking
        puesto = "Campeón" if fila["puesto"] == "C" else f"#{fila['puesto']}"   # "Campeón" o "#4"
        return f"{nombre}  ·  {fila['division']} {puesto}"               # ej.: "Ilia Topuria  ·  Ligero #1"

    nombres = lista["peleador"].tolist()                                 # los que quedaron después de filtrar
    st.caption(f"{len(nombres)} peleadores encontrados. En el menú también se puede escribir para buscar.")
    elegido = None                                                       # todavía no hay nadie elegido
    if nombres:                                                          # si la búsqueda encontró a alguien...
        elegido = st.selectbox("Elegí un peleador", nombres, format_func=etiqueta,  # menú desplegable
                               index=nombres.index("Ilia Topuria") if "Ilia Topuria" in nombres else 0)
    else:                                                                # si no encontró a nadie...
        st.warning("No hay peleadores activos con ese nombre en esa categoría. "
                   "Probá con otra categoría o con «Todas».")            # ...un aviso, sin cortar la app

    if elegido:                                                          # solo si hay un peleador elegido
        ficha = ranking[ranking["peleador"] == elegido].iloc[0]              # su fila en el ranking
        peleas = historial[historial["peleador"] == elegido].sort_values("fecha")  # sus peleas, en orden

        c1, c2, c3, c4 = st.columns(4)                                       # cuatro datos clave en fila
        c1.metric("Categoría", ficha["division"])                            # categoría actual
        c2.metric("Puesto", "Campeón" if ficha["puesto"] == "C" else f"#{ficha['puesto']}")  # puesto
        c3.metric("Puntos", int(ficha["elo"]))                               # puntaje Elo
        c4.metric("Récord desde 2010", ficha["record"])                      # récord

        st.markdown("**Cómo llegó a este puntaje**: todos arrancan con 1500 puntos; cada pelea suma o resta.")
        grafico = (alt.Chart(peleas)                                         # gráfico de sus puntos en el tiempo
                   .mark_line(point=alt.OverlayMarkDef(color="#ffffff", size=50),   # puntos blancos en cada pelea
                              color="#d20a0a", strokeWidth=2.5)              # línea roja
                   .encode(x=alt.X("fecha:T", title=None, axis=alt.Axis(format="%Y", tickCount="year")),  # eje X: años
                           y=alt.Y("elo_despues:Q", title="Puntos", scale=alt.Scale(zero=False)),         # eje Y: puntos
                           tooltip=[alt.Tooltip("fecha:T", title="Fecha"),   # lo que aparece al pasar el mouse
                                    alt.Tooltip("rival:N", title="Rival"),
                                    alt.Tooltip("resultado:N", title="Resultado"),
                                    alt.Tooltip("cambio:Q", title="Cambio"),
                                    alt.Tooltip("elo_despues:Q", title="Puntos después")])
                   .properties(height=280, background="transparent")         # alto y fondo transparente
                   .configure_axis(labelColor="#9a9a9a", titleColor="#9a9a9a",   # ejes en gris
                                   gridColor="#222222", domainColor="#3a3a3a")
                   .configure_view(strokeWidth=0))                           # sin recuadro
        st.altair_chart(grafico, use_container_width=True)                   # lo mostramos

        peleas = peleas.sort_values("fecha", ascending=False)                # la pelea más reciente primero
        st.dataframe(pd.DataFrame({                                          # tabla con cada pelea explicada
            "Fecha": peleas["fecha"].dt.strftime("%d/%m/%Y"),
            "Evento": peleas["evento"],
            "Qué pasó": peleas.apply(explicar, axis=1),                      # la frase de la función A1
            "Puntos después": peleas["elo_despues"].round(0).astype(int),
        }), hide_index=True, use_container_width=True)
        if elegido in LIMITACION:                                            # aviso de la limitación conocida
            st.info(f"Los rankings oficiales lo ubican en {LIMITACION[elegido]}; acá figura en "
                    f"{ficha['division']} porque es la categoría de su última pelea.")


# ---------------------------------------------------------------------------------------------
# A4. Pestaña "Contra los oficiales": nuestro ranking al lado del MEDIA y del META
# ---------------------------------------------------------------------------------------------
with pestanas[3]:
    cat2 = st.radio("Categoría", CATEGORIAS, horizontal=True, index=3, key="cat_oficial")
    st.markdown("Los tres rankings lado a lado: **campeón + top 15**. "
                "Resaltados en blanco (con el número en rojo), los que aparecen en el top de **los tres**.")

    def top16(df):
        t = df[df["division"] == cat2].head(16)                          # campeón + 15 de la categoría
        return list(zip(t["puesto"].astype(str), t["peleador"]))         # lista de (puesto, nombre)

    nuestro = top16(ranking)                                             # nuestro top 16
    m_media, m_meta = top16(media), top16(meta)                          # top 16 de cada oficial
    en_los_tres = ({n for _, n in nuestro}                               # los que están en los tres:
                   & set(detalle.loc[detalle["division_media"] == cat2, "peleador"])   # en el nuestro y el MEDIA
                   & set(detalle.loc[detalle["division_meta"] == cat2, "peleador"]))   # y el META

    def columna(titulo, lista, nombres_ufcstats):
        """Dibuja una columna con un ranking; resalta a los que están en los tres."""
        st.markdown(f"#### {titulo}")                                    # título de la columna
        filas = "".join(                                                 # una fila por peleador
            f"<div class='fila{' comun' if real in en_los_tres else ''}'>"
            f"<span class='n'>{puesto}</span><span class='nom'>{html.escape(mostrado)}</span></div>"
            for (puesto, mostrado), real in zip(lista, nombres_ufcstats))
        st.markdown(filas, unsafe_allow_html=True)

    def reales(fuente):
        """Nombres de un ranking oficial escritos como en UFCStats (sin tildes), para comparar."""
        col_div, col_p = f"division_{fuente}", f"puesto_{fuente}"
        t = detalle[detalle[col_div] == cat2].copy()                     # los de esta categoría
        t["n"] = t[col_p].map(lambda p: 0 if str(p) == "C" else int(p))  # campeón = 0, para ordenar
        return t.sort_values("n")["peleador"].tolist()

    a, b, c = st.columns(3)                                              # tres columnas
    with a:
        columna("Fans (nuestro)", nuestro, [n for _, n in nuestro])
    with b:
        columna("MEDIA (periodistas)", m_media, reales("media"))
    with c:
        columna("META (UFC + IA)", m_meta, reales("meta"))

    st.divider()                                                         # línea separadora
    st.markdown("**¿Cuánto coinciden?** Cuántos de los 16 (campeón + top 15) están en ambos rankings.")
    tabla_res = resumen.pivot_table(index="division", columns="comparacion",   # categorías en filas,
                                    values="coinciden_de_16",                   # comparaciones en columnas
                                    aggfunc="first").reindex(CATEGORIAS)
    tabla_res.loc["Total"] = tabla_res.sum()                             # fila de totales
    st.dataframe(tabla_res.astype(int), use_container_width=True)
    st.caption("Ni los dos rankings oficiales coinciden del todo entre sí: eso da una idea de cuánta "
               "diferencia es normal entre rankings.")


# #############################################################################################
#
#              PARTE B · EL MODELO DE PREDICCIÓN (opción B: machine learning)
#
#   La evaluación completa (entrenar con 2012-2023 y probar con 2024-2026, baselines, Random
#   Forest, matriz de confusión) está en src/modelo.py. Acá se usa la Regresión Logística,
#   reentrenada con todas las peleas, para estimar quién ganaría entre dos peleadores de hoy.
#
# #############################################################################################

# ---------------------------------------------------------------------------------------------
# B1. Variables del modelo: todas son diferencias entre el peleador A y el B (A menos B)
# ---------------------------------------------------------------------------------------------
VARIABLES = {"dif_elo": "puntos Elo",                                    # nivel según nuestro ranking
             "dif_peleas": "experiencia (peleas en la UFC)",             # rodaje
             "dif_pct_victorias": "% de victorias",                      # efectividad
             "dif_pct_finish": "% de victorias por KO o sumisión",       # poder para terminar peleas
             "dif_racha": "racha actual",                                # momento
             "dif_ultimas3": "victorias en las últimas 3",               # forma reciente
             "dif_dias_inactivo": "días sin pelear",                     # inactividad
             "dif_edad": "edad",                                         # momento de la carrera
             "dif_alcance": "alcance"}                                   # ventaja física


# ---------------------------------------------------------------------------------------------
# B2. Entrenamiento del modelo (una sola vez, al abrir la app)
# ---------------------------------------------------------------------------------------------
@st.cache_resource                                                       # se entrena una sola vez
def modelo_entrenado():
    """Regresión Logística reentrenada con TODAS las peleas desde 2012 (tarda menos de un segundo)."""
    datos = pd.read_csv(PROC / "dataset_modelo.csv", parse_dates=["fecha"])   # una fila por pelea (src/modelo.py)
    datos = datos[datos["fecha"] >= "2012-01-01"]                        # sin el "calentamiento" 2010-2011
    modelo = Pipeline([("escalado", StandardScaler()),                   # paso 1: escalar las variables
                       ("modelo", LogisticRegression(max_iter=1000))])   # paso 2: Regresión Logística
    modelo.fit(datos[list(VARIABLES)], datos["gana_a"])                  # entrenamos: variables -> ¿ganó A?
    estado = pd.read_csv(PROC / "estado_peleadores.csv",                 # cómo llega cada peleador HOY
                         parse_dates=["ultima_fecha", "nacimiento"])
    return modelo, estado.set_index("peleador")                          # modelo + estado (buscable por nombre)


# ---------------------------------------------------------------------------------------------
# B3. Cálculo de las 9 variables para una pelea A vs. B (con lo que cada uno trae hoy)
# ---------------------------------------------------------------------------------------------
def variables_de(a, b, estado, fecha):
    def pct(x, n):                                                       # porcentaje seguro:
        return x / n if n else 0.5                                       # sin peleas -> 50%
    def edad(e):                                                         # edad a la fecha de corte
        return (fecha - e["nacimiento"]).days / 365.25 if pd.notna(e["nacimiento"]) else None
    ea, eb = estado.loc[a], estado.loc[b]                                # estadísticas de A y de B
    dif_edad = (edad(ea) - edad(eb)) if edad(ea) is not None and edad(eb) is not None else 0  # sin dato -> 0
    tiene_alcance = pd.notna(ea["alcance"]) and pd.notna(eb["alcance"])
    dif_alc = (ea["alcance"] - eb["alcance"]) if tiene_alcance else 0   # sin dato -> 0
    return pd.DataFrame([{                                               # una fila con las 9 diferencias
        "dif_elo": ea["elo"] - eb["elo"],
        "dif_peleas": ea["peleas"] - eb["peleas"],
        "dif_pct_victorias": pct(ea["victorias"], ea["peleas"]) - pct(eb["victorias"], eb["peleas"]),
        "dif_pct_finish": pct(ea["finishes"], ea["victorias"]) - pct(eb["finishes"], eb["victorias"]),
        "dif_racha": ea["racha"] - eb["racha"],
        "dif_ultimas3": ea["ultimas3"] - eb["ultimas3"],
        "dif_dias_inactivo": (fecha - ea["ultima_fecha"]).days - (fecha - eb["ultima_fecha"]).days,
        "dif_edad": dif_edad,
        "dif_alcance": dif_alc}])


# ---------------------------------------------------------------------------------------------
# B4. Pestaña "¿Quién gana?": probabilidad de cada uno y qué inclina la balanza
# ---------------------------------------------------------------------------------------------
with pestanas[2]:
    modelo, estado = modelo_entrenado()                                  # modelo listo (B2)
    cat3 = st.radio("Categoría", CATEGORIAS, horizontal=True, index=3, key="cat_pred")
    opciones = ranking[ranking["division"] == cat3]["peleador"].tolist() # peleadores, en orden de ranking
    c1, c2 = st.columns(2)                                               # dos menús, uno al lado del otro
    a = c1.selectbox("Peleador 1", opciones, index=0, key="pa")          # por defecto: el campeón
    b = c2.selectbox("Peleador 2", opciones, index=1, key="pb")          # por defecto: el número 1
    if a == b:
        st.warning("Elegí dos peleadores distintos.")                    # no tiene sentido A contra A
    else:
        x_ab = variables_de(a, b, estado, FECHA_CORTE)                   # variables de A contra B (B3)
        x_ba = variables_de(b, a, estado, FECHA_CORTE)                   # y de B contra A
        prob_a = (modelo.predict_proba(x_ab)[0, 1]                       # promediamos los dos órdenes
                  + 1 - modelo.predict_proba(x_ba)[0, 1]) / 2            # para que no importe quién va primero
        izq, der = st.columns(2)
        for col, nombre, p in [(izq, a, prob_a), (der, b, 1 - prob_a)]: # un bloque por peleador
            col.markdown(f"""<div class="cat">Probabilidad de ganar</div>
<div class="campeon">{html.escape(nombre)}</div>
<div class="campeon" style="color:{'#d20a0a' if p >= 0.5 else '#9a9a9a'}">{p:.0%}</div>""",
                         unsafe_allow_html=True)                         # el favorito en rojo

        # ¿Qué inclina la balanza? En una Regresión Logística, el aporte de cada variable es
        # su coeficiente × su valor escalado: positivo favorece a A, negativo favorece a B.
        esc = modelo.named_steps["escalado"]                             # el escalador entrenado
        rl = modelo.named_steps["modelo"]                                # la Regresión Logística entrenada
        aporte = (x_ab.values[0] - esc.mean_) / esc.scale_ * rl.coef_[0] # aporte de cada variable
        factores = pd.DataFrame({"variable": list(VARIABLES.values()), "aporte": aporte})
        factores = factores.sort_values("aporte", key=abs, ascending=False)   # de mayor a menor peso
        st.markdown("#### ¿Qué inclina la balanza?")
        for f in factores.head(4).itertuples():                          # las 4 variables que más pesan
            favorece = a if f.aporte > 0 else b                          # ¿a quién favorece?
            st.markdown(f"- **{f.variable[0].upper() + f.variable[1:]}** → favorece a **{favorece}**")
        st.caption("Modelo: Regresión Logística entrenada con peleas desde 2012. En peleas de 2024-2026 que "
                   "no vio al entrenar acertó el 62%, contra 60% de la mejor regla simple. El MMA es muy "
                   "impredecible: es una estimación, no una certeza.")


# =============================================================================================
# 3. PESTAÑAS GENERALES
# =============================================================================================

# --- Tablero de Power BI (requisito de la consigna) -------------------------------------------
with pestanas[4]:
    captura = RAIZ / "powerbi" / "captura_tablero.png"                   # captura del tablero (categoría Ligero)
    archivo_pbix = RAIZ / "powerbi" / "Tablero del Ranking.pbix"         # el tablero original de Power BI
    if POWER_BI_URL:                                                     # si algún día se publica en la web...
        st.components.v1.iframe(POWER_BI_URL, height=650)                # ...se muestra embebido
    else:                                                                # si no: captura + archivo para descargar
        st.markdown("Tablero hecho en **Power BI** con datos públicos de UFCStats: el top 15 de cada "
                    "categoría con los rankings oficiales al lado, cuánto coinciden y los resultados del modelo.")
        if captura.exists():                                             # si está la captura en el repositorio...
            st.image(str(captura), caption="Vista del tablero (categoría Ligero)",
                     use_container_width=True)                           # ...se muestra a todo el ancho
        if archivo_pbix.exists():                                        # si está el archivo .pbix...
            st.download_button("⬇ Descargar el tablero (.pbix)",         # ...botón para bajarlo
                               archivo_pbix.read_bytes(), file_name="Tablero del Ranking.pbix")
        st.caption("Para usarlo de forma interactiva, abrir el archivo con Power BI Desktop (gratis). "
                   "Se entrega como archivo porque la publicación web de Power BI está deshabilitada "
                   "en la cuenta del INA, por indicación del profesor.")  # por qué no está embebido

# --- Cómo funciona: explicación para el usuario, sin tecnicismos -------------------------------
with pestanas[5]:
    st.markdown(f"""
### La idea en una frase
**Ganás y sumás puntos; perdés y restás. Si le ganás a alguien mejor que vos, sumás más.**
Es el sistema **Elo**, el mismo que se usa en el ajedrez.

### Las reglas
| Regla | Por qué |
|---|---|
| Todos arrancan con **1500 puntos** | Nadie empieza con ventaja |
| El ganador le "saca" puntos al perdedor | Una victoria contra alguien bueno vale más que contra alguien flojo |
| Si gana el que **no era favorito**, se mueven más puntos | Una sorpresa dice más que un resultado esperable |
| **KO, TKO o sumisión: +25%** | Terminar la pelea es más contundente que ganar por decisión |
| **Pelea por el título: vale el doble** | Es lo que más importa para un fan |
| Empate: cada uno "gana medio"; *No Contest*: no mueve puntos | La pelea no tuvo un ganador |
| Se cuentan las peleas **desde 2010** | Se verificó que arrancar en 1994 da el mismo ranking |
| Solo aparecen los que pelearon en los **últimos 18 meses** | Lo normal es pelear cada 4 a 8 meses |
| Los que **anunciaron su retiro** no aparecen (salvo que vuelvan a pelear) | Ej. Dustin Poirier o Henry Cejudo. La lista tiene la fuente de cada anuncio |
| El **campeón** va aparte, como en el ranking oficial | Es quien ganó la última pelea por el título |

### ¿Quién gana? (machine learning)
Un modelo de **Regresión Logística** aprende de más de 6.000 peleas desde 2012 qué diferencias entre dos
peleadores (puntos Elo, edad, % de victorias, actividad, alcance, etc.) se asocian con ganar.
Se evaluó entrenando con 2012-2023 y probando con 2024-2026: **acertó el 62% de las peleas**,
contra 60% de la mejor regla simple ("gana el de mejor % de victorias"). La **edad** y los
**puntos Elo** son las dos variables que más pesan: el ranking sí dice algo sobre quién gana.

### ¿Por qué un tercer ranking?
- El ranking **MEDIA** lo vota un panel de periodistas: es opinión.
- El ranking **META** lo hace la UFC con inteligencia artificial: no se sabe cómo calcula.
- Este ranking es **caja blanca**: en la ficha de cada peleador se ve, pelea por pelea, por qué tiene sus puntos.

### Limitación conocida
La categoría de cada peleador es **la de su última pelea**. Si alguien hizo una sola pelea en otra
categoría, aparece ahí. Hoy pasa con **Max Holloway** (Wélter), **Kamaru Usman** (Mediano) y
**Alex Pereira** (Pesado). No se corrigió a mano para que el ranking salga 100% de los datos.

### Los datos
UFCStats.com (estadísticas oficiales de la UFC), al {FECHA_CORTE:%d/%m/%Y}.
Rankings oficiales: ufc.com, 16/11/2026. Se actualiza volviendo a correr los scripts después de cada evento.
""")
