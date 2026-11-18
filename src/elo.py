"""
Etapa 2 · Opción A - Ranking Elo.

¿Qué hace?
    Recorre todas las peleas masculinas en orden de fecha y, después de cada una,
    actualiza el puntaje (Elo) de los dos peleadores. Al final arma el ranking de
    las 8 categorías masculinas con los peleadores activos.

Genera:
    data/processed/elo_historial.csv  -> cada pelea vista por cada peleador: puntaje antes,
                                         puntos ganados o perdidos y puntaje después.
                                         Es lo que permite explicar cualquier puesto.
    data/processed/ranking_elo.csv    -> el ranking final por categoría.

La fórmula (en palabras):
    1. Antes de la pelea se calcula qué tan "esperable" era que ganara cada uno,
       según la diferencia de puntaje (la probabilidad esperada).
    2. El ganador suma y el perdedor resta. Si gana el que no era favorito, se mueven
       muchos puntos (sorpresa); si gana el favorito, se mueven pocos (era lo esperable).
    3. Ganar por KO/TKO o sumisión mueve un 25% más de puntos que ganar por decisión.
    4. Las peleas por el título mueven el doble de puntos.
    5. El campeón de cada categoría se muestra aparte (como en el ranking oficial):
       es quien ganó la última pelea por el título de esa categoría.

Historial de versiones:
    v1 (16/11/2026): K = 32, sin bonus por título, sin campeón.
    v2 (16/11/2026): K = 48, título x2 y campeón aparte. Motivo: en v1 Justin Gaethje,
        que le ganó el título a Topuria en junio de 2026, quedaba 3.º en Ligero. Una pelea
        por el título valía lo mismo que cualquier otra, y los resultados recientes pesaban poco.
    v4 (16/11/2026): se excluyen los retirados anunciados (data/external/retirados_anunciados.csv),
        salvo que hayan vuelto a pelear después del anuncio. Motivo: Dustin Poirier (retirado en
        julio de 2025) aparecía 5.º en Ligero porque su última pelea entraba en los 18 meses.
    v3 (16/11/2026): los No Contest cuentan para la ACTIVIDAD (no para los puntos). Motivo: al
        comparar con el ranking oficial, Tom Aspinall no aparecía: su última pelea (contra Gane,
        octubre de 2025) fue un No Contest y el ranking lo daba por inactivo.

Uso:
    python src/elo.py
"""

from pathlib import Path   # para manejar rutas de carpetas

import pandas as pd        # para trabajar con tablas

RAIZ = Path(__file__).resolve().parent.parent   # carpeta raíz del proyecto
RAW = RAIZ / "data" / "raw"                     # datos crudos
PROCESSED = RAIZ / "data" / "processed"         # datos limpios y resultados

# ------------------------------------------------------------------ parámetros
ELO_INICIAL = 1500            # puntaje con el que arranca todo peleador nuevo
K = 48                        # cuántos puntos se mueven como máximo en una pelea "normal" (v1: 32)
BONUS_FINISH = 1.25           # ganar por KO/TKO o sumisión mueve 25% más puntos
BONUS_TITULO = 2.0            # una pelea por el título mueve el doble de puntos (v2)
FECHA_INICIO = "2010-01-01"   # desde cuándo se cuentan las peleas
DIAS_ACTIVO = 548             # 18 meses: límite para considerar a alguien activo

# Las 8 categorías masculinas y su peso límite en libras (lbs)
LIMITE_LBS = {"Mosca": 125, "Gallo": 135, "Pluma": 145, "Ligero": 155,
              "Wélter": 170, "Mediano": 185, "Semipesado": 205, "Pesado": 265}
MASCULINAS = list(LIMITE_LBS)  # la lista de nombres, de la más liviana a la más pesada


# ------------------------------------------------------------------ hallazgo H5
def desambiguar_homonimos(peleas):
    """Resuelve el hallazgo H5: dos peleadores distintos con el mismo nombre.

    Regla: cada homónimo tiene un peso registrado en UFCStats (ej. un Bruno Silva
    pesa 125 lbs y el otro 185 lbs). Cada pelea se asigna al homónimo cuyo peso
    está más cerca del límite de la categoría de esa pelea, y se le agrega la
    categoría al nombre: 'Bruno Silva (Mosca)' y 'Bruno Silva (Mediano)'.
    """
    fisico = pd.read_csv(RAW / "ufc_fighter_tott.csv")                 # tabla de datos físicos
    fisico["FIGHTER"] = fisico["FIGHTER"].str.strip()                  # limpiamos espacios (H1)
    fisico["lbs"] = pd.to_numeric(                                     # convertimos el peso a número:
        fisico["WEIGHT"].str.extract(r"(\d+)")[0], errors="coerce")    # "185 lbs." -> 185 ("--" -> vacío)
    repetidos = fisico[fisico["FIGHTER"].duplicated(keep=False)]       # filas de nombres repetidos
    repetidos = repetidos.dropna(subset=["lbs"])                       # solo los que tienen peso cargado

    def nombre_correcto(nombre, division):                             # decide el nombre de una pelea
        opciones = repetidos[repetidos["FIGHTER"] == nombre]           # homónimos con ese nombre
        if len(opciones) < 2 or division not in LIMITE_LBS:            # no es homónimo, o pelea en peso pactado
            return nombre                                              # -> se deja el nombre tal cual
        limite = LIMITE_LBS[division]                                  # límite de la categoría de la pelea
        mas_cercano = opciones.loc[(opciones["lbs"] - limite).abs().idxmin()]  # homónimo de peso más parecido
        etiqueta = min(LIMITE_LBS, key=lambda d: abs(LIMITE_LBS[d] - mas_cercano["lbs"]))  # su categoría
        return f"{nombre} ({etiqueta})"                                # ej. 'Bruno Silva (Mosca)'

    for col in ["peleador_1", "peleador_2", "ganador", "perdedor"]:    # en las 4 columnas con nombres...
        peleas[col] = [nombre_correcto(n, d) if isinstance(n, str) else n   # ...aplicamos la regla
                       for n, d in zip(peleas[col], peleas["division"])]
    return peleas                                                      # devolvemos la tabla corregida


# ------------------------------------------------------------------ cálculo del Elo
def probabilidad_esperada(elo_a, elo_b):
    """Probabilidad de que A le gane a B según sus puntajes (fórmula clásica del Elo).
    Misma puntuación -> 0.5 (50%). 400 puntos de ventaja -> 0.91 (91%)."""
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def calcular_elo(peleas, fecha_inicio=FECHA_INICIO):
    """Recorre las peleas en orden y devuelve (puntajes_finales, historial)."""
    datos = peleas[peleas["fecha"] >= fecha_inicio]                    # solo peleas desde la fecha de inicio
    datos = datos[datos["resultado"] != "Sin resultado"]               # los No Contest no mueven puntos
    datos = datos.sort_values("fecha")                                 # orden cronológico: clave en el Elo

    elo = {}                                                           # diccionario: peleador -> puntaje actual
    historial = []                                                     # lista de filas para explicar cada cambio

    for p in datos.itertuples():                                       # recorremos pelea por pelea
        a, b = p.peleador_1, p.peleador_2                              # los dos peleadores
        elo_a = elo.get(a, ELO_INICIAL)                                # puntaje de A (1500 si es su primera)
        elo_b = elo.get(b, ELO_INICIAL)                                # puntaje de B (1500 si es su primera)
        esperado_a = probabilidad_esperada(elo_a, elo_b)               # chance de A antes de la pelea
        esperado_b = 1 - esperado_a                                    # chance de B (el resto)

        if p.resultado == "Gana 1":                                    # ganó A
            real_a, real_b = 1.0, 0.0                                  # A obtiene 1 punto de resultado, B 0
        elif p.resultado == "Gana 2":                                  # ganó B
            real_a, real_b = 0.0, 1.0
        else:                                                          # empate
            real_a, real_b = 0.5, 0.5                                  # cada uno "gana medio"

        es_finish = p.metodo_grupo in ("KO/TKO", "Sumisión")           # ¿terminó antes de tiempo?
        k = K * BONUS_FINISH if es_finish else K                       # si fue finish, se mueven más puntos
        if p.por_titulo:                                               # si fue por el cinturón...
            k = k * BONUS_TITULO                                       # ...se mueve el doble

        cambio_a = k * (real_a - esperado_a)                           # puntos que gana (o pierde) A
        cambio_b = k * (real_b - esperado_b)                           # puntos que gana (o pierde) B
        elo[a] = elo_a + cambio_a                                      # nuevo puntaje de A
        elo[b] = elo_b + cambio_b                                      # nuevo puntaje de B

        for yo, rival, antes, antes_rival, esperado, real, cambio in [  # guardamos una fila por peleador
                (a, b, elo_a, elo_b, esperado_a, real_a, cambio_a),
                (b, a, elo_b, elo_a, esperado_b, real_b, cambio_b)]:
            historial.append({
                "fecha": p.fecha, "evento": p.evento, "division": p.division,
                "peleador": yo, "rival": rival,
                "resultado": {1.0: "Victoria", 0.0: "Derrota", 0.5: "Empate"}[real],
                "metodo": p.metodo_grupo,
                "por_titulo": p.por_titulo,                            # ¿fue pelea por el título?
                "elo_antes": round(antes, 1),                          # puntaje antes de la pelea
                "elo_rival_antes": round(antes_rival, 1),              # puntaje del rival antes de la pelea
                "prob_esperada": round(esperado, 3),                   # qué tan favorito era
                "cambio": round(cambio, 1),                            # puntos que ganó o perdió
                "elo_despues": round(antes + cambio, 1)})              # puntaje después de la pelea

    return elo, pd.DataFrame(historial)                                # puntajes finales + historial completo


# ------------------------------------------------------------------ armado del ranking
def buscar_campeones(peleas):
    """Campeón de cada categoría = ganador de la última pelea por el título de esa categoría."""
    titulos = peleas[peleas["por_titulo"] & peleas["division"].isin(MASCULINAS)]  # peleas por el cinturón
    ultimas = titulos.sort_values("fecha").groupby("division").tail(1)            # la última de cada categoría
    return dict(zip(ultimas["division"], ultimas["ganador"]))                      # {categoría: campeón}


def peleas_largo(peleas):
    """Todas las peleas (incluidos los No Contest) con una fila por peleador.
    Se usa para la ACTIVIDAD: un No Contest no mueve puntos, pero el peleador sí peleó (v3)."""
    uno = peleas[["fecha", "division", "peleador_1"]].rename(columns={"peleador_1": "peleador"})  # esquina 1
    dos = peleas[["fecha", "division", "peleador_2"]].rename(columns={"peleador_2": "peleador"})  # esquina 2
    return pd.concat([uno, dos]).sort_values("fecha")                  # juntas y en orden de fecha


def armar_ranking(elo, historial, fecha_corte, campeones, peleas):
    """Ranking por categoría: campeón aparte y debajo los activos ordenados por puntaje."""
    h = historial.sort_values("fecha")                                 # historial en orden de fecha
    todas = peleas_largo(peleas[peleas["fecha"] >= FECHA_INICIO])      # todas las peleas, con No Contest
    ultima_pelea = todas.groupby("peleador")["fecha"].max()            # fecha de la última pelea de cada uno
    en_8 = todas[todas["division"].isin(MASCULINAS)]                   # solo peleas en las 8 categorías
    division_actual = en_8.groupby("peleador")["division"].last()      # categoría de su última pelea (no pactada)

    victorias = h[h["resultado"] == "Victoria"].groupby("peleador").size()  # victorias desde 2010
    derrotas = h[h["resultado"] == "Derrota"].groupby("peleador").size()    # derrotas desde 2010
    empates = h[h["resultado"] == "Empate"].groupby("peleador").size()      # empates desde 2010

    tabla = pd.DataFrame({"elo": pd.Series(elo)})                      # una fila por peleador con su puntaje
    tabla = tabla.reindex(tabla.index.union(ultima_pelea.index), fill_value=ELO_INICIAL)  # + quien solo tuvo NC
    tabla["division"] = division_actual                                # su categoría actual
    tabla["ultima_pelea"] = ultima_pelea                               # su última pelea
    tabla["dias_inactivo"] = (fecha_corte - tabla["ultima_pelea"]).dt.days  # días sin pelear
    tabla["record"] = (victorias.reindex(tabla.index, fill_value=0).astype(str) + "-"   # récord V-D-E
                       + derrotas.reindex(tabla.index, fill_value=0).astype(str) + "-"
                       + empates.reindex(tabla.index, fill_value=0).astype(str))

    retirados = pd.read_csv(RAIZ / "data" / "external" / "retirados_anunciados.csv",  # lista documentada
                            parse_dates=["fecha_retiro"])                             # con fuente
    fecha_retiro = retirados.set_index("peleador")["fecha_retiro"]     # peleador -> fecha del anuncio
    tabla["retirado"] = [n in fecha_retiro.index and u <= fecha_retiro[n]   # retirado = anunció y NO volvió
                         for n, u in zip(tabla.index, tabla["ultima_pelea"])]  # a pelear después

    activos = tabla[(tabla["dias_inactivo"] <= DIAS_ACTIVO)            # filtro: peleó en los últimos 18 meses
                    & tabla["division"].notna()                        # tiene una categoría de las 8
                    & ~tabla["retirado"]].copy()                       # y no anunció su retiro (v4)
    for division, campeon in campeones.items():                        # el campeón figura en la categoría
        if campeon in activos.index:                                   # del título, aunque haya peleado
            activos.loc[campeon, "division"] = division                # después en otra
    activos["campeon"] = [campeones.get(d) == n for n, d in zip(activos.index, activos["division"])]
    activos = activos.sort_values(["division", "campeon", "elo"],      # primero el campeón,
                                  ascending=[True, False, False])      # después por puntaje
    resto = ~activos["campeon"]                                        # todos menos el campeón
    activos["puesto"] = "C"                                            # el campeón lleva "C"
    activos.loc[resto, "puesto"] = (activos[resto].groupby("division").cumcount() + 1).astype(str)  # 1, 2, 3...
    activos["division"] = pd.Categorical(activos["division"], MASCULINAS, ordered=True)  # orden por peso
    activos = activos.sort_values(["division", "campeon", "elo"],      # ordenamos de Mosca a Pesado
                                  ascending=[True, False, False])
    activos["elo"] = activos["elo"].round(0).astype(int)               # puntaje sin decimales
    activos = activos.rename_axis("peleador").reset_index()            # el nombre pasa a ser una columna
    return activos[["division", "puesto", "peleador", "elo", "record",
                    "ultima_pelea", "dias_inactivo", "campeon"]]


def cargar_peleas_masculinas():
    """Carga peleas.csv, deja solo las masculinas y resuelve homónimos."""
    peleas = pd.read_csv(PROCESSED / "peleas.csv", parse_dates=["fecha"])  # tabla limpia de peleas
    peleas = peleas[~peleas["femenina"] & peleas["fecha"].notna()].copy()  # masculinas y con fecha (H3)
    return desambiguar_homonimos(peleas)                                   # resolvemos H5


if __name__ == "__main__":
    peleas = cargar_peleas_masculinas()                                # 1. datos
    fecha_corte = peleas["fecha"].max()                                # 2. fecha de corte
    elo, historial = calcular_elo(peleas)                              # 3. cálculo del Elo
    campeones = buscar_campeones(peleas)                               # 4. campeones actuales
    ranking = armar_ranking(elo, historial, fecha_corte, campeones, peleas)  # 5. ranking
    historial.to_csv(PROCESSED / "elo_historial.csv", index=False)     # 6. guardamos el historial
    ranking.to_csv(PROCESSED / "ranking_elo.csv", index=False)         #    y el ranking
    print(f"Fecha de corte: {fecha_corte.date()}")
    print(f"Peleas usadas: {len(historial) // 2:,} | Activos rankeados: {len(ranking)}")
    for div, grupo in ranking.groupby("division", observed=True):      # top 5 de cada categoría
        print(f"\n{div}")
        print(grupo.head(5)[["puesto", "peleador", "elo", "record"]].to_string(index=False))
