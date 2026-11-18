"""
Paso 2 - Limpieza y armado de tablas útiles.

Convierte las tablas crudas de UFCStats en dos tablas limpias:

    data/processed/peleas.csv
        Una fila por pelea: fecha, evento, categoría, peleador 1 y 2,
        ganador, perdedor, método agrupado, si fue por el título, etc.

    data/processed/peleas_por_peleador.csv
        La misma información "desde los ojos de cada peleador":
        dos filas por pelea (una por cada peleador), con su resultado
        (Victoria / Derrota / Empate / Sin resultado) y su rival.
        Es la tabla que vamos a usar para calcular el ranking.

Cada regla de limpieza está comentada con el problema que resuelve
(los problemas están detallados en el notebook de EDA).

Uso:
    python src/limpieza.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
PROCESSED = RAIZ / "data" / "processed"

# Orden importa: "Light Heavyweight" tiene que buscarse antes que "Heavyweight".
DIVISIONES = [
    ("Light Heavyweight", "Semipesado"),
    ("Heavyweight", "Pesado"),
    ("Middleweight", "Mediano"),
    ("Welterweight", "Wélter"),
    ("Lightweight", "Ligero"),
    ("Featherweight", "Pluma"),
    ("Bantamweight", "Gallo"),
    ("Flyweight", "Mosca"),
    ("Strawweight", "Paja"),
    ("Catch Weight", "Peso pactado"),
    ("Open Weight", "Peso abierto"),
]

# Las 8 categorías masculinas actuales, de más liviana a más pesada.
DIVISIONES_MASCULINAS = ["Mosca", "Gallo", "Pluma", "Ligero",
                         "Wélter", "Mediano", "Semipesado", "Pesado"]


def limpiar_texto(df):
    """Problema: casi todos los textos vienen con espacios de más al final
    (ej. 'UFC 334: Gane vs. Hokit '), y eso rompe los cruces entre tablas."""
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()
    return df


def mapear_division(texto):
    for clave, nombre in DIVISIONES:
        if clave.lower() in texto.lower():
            return nombre
    return "Sin categoría"


def agrupar_metodo(metodo):
    """Agrupa los 10 métodos de UFCStats en 4 que entiende cualquier fan."""
    if metodo.startswith("Decision"):
        return "Decisión"
    if metodo in ("KO/TKO", "TKO - Doctor's Stoppage"):
        return "KO/TKO"
    if metodo == "Submission":
        return "Sumisión"
    return "Otro"  # Overturned, DQ, Could Not Continue, Other


def construir_peleas():
    eventos = limpiar_texto(pd.read_csv(RAW / "ufc_event_details.csv"))
    resultados = limpiar_texto(pd.read_csv(RAW / "ufc_fight_results.csv"))

    eventos["fecha"] = pd.to_datetime(eventos["DATE"], format="%B %d, %Y")

    # Problema: algunos eventos cambiaron de nombre (ej. 'UFC Fight Night: X'
    # pasó a 'Noche UFC: X') y la misma pelea aparece dos veces, una con
    # cada nombre. Solución: el link de la pelea (URL) es único; nos quedamos
    # con la versión cuyo nombre de evento existe en la tabla de eventos.
    resultados["evento_valido"] = resultados["EVENT"].isin(eventos["EVENT"])
    resultados = (resultados.sort_values("evento_valido", ascending=False)
                  .drop_duplicates(subset="URL", keep="first"))

    peleas = resultados.merge(eventos[["EVENT", "fecha", "LOCATION"]],
                              on="EVENT", how="left")

    # El cruce viene como texto: 'Peleador A vs. Peleador B'
    peleas[["peleador_1", "peleador_2"]] = peleas["BOUT"].str.split(
        " vs. ", n=1, expand=True)

    # OUTCOME: 'W/L' = ganó el 1, 'L/W' = ganó el 2, 'D/D' empate, 'NC/NC' sin resultado
    peleas["resultado"] = peleas["OUTCOME"].map(
        {"W/L": "Gana 1", "L/W": "Gana 2", "D/D": "Empate", "NC/NC": "Sin resultado"})
    peleas["ganador"] = np.select(
        [peleas["OUTCOME"] == "W/L", peleas["OUTCOME"] == "L/W"],
        [peleas["peleador_1"], peleas["peleador_2"]], default=None)
    peleas["perdedor"] = np.select(
        [peleas["OUTCOME"] == "W/L", peleas["OUTCOME"] == "L/W"],
        [peleas["peleador_2"], peleas["peleador_1"]], default=None)

    peleas["division"] = peleas["WEIGHTCLASS"].apply(mapear_division)
    peleas["femenina"] = peleas["WEIGHTCLASS"].str.contains("Women", case=False)
    # Pelea por el cinturón UFC (incluye interinos). Excluimos finales de
    # torneos (TUF, Road to UFC, UFC 2-10), que no son por el título de la UFC.
    peleas["por_titulo"] = (peleas["WEIGHTCLASS"].str.startswith("UFC")
                            & peleas["WEIGHTCLASS"].str.contains("Title", case=False)
                            & ~peleas["WEIGHTCLASS"].str.contains("Tournament", case=False))
    peleas["metodo"] = peleas["METHOD"]
    peleas["metodo_grupo"] = peleas["METHOD"].apply(agrupar_metodo)
    peleas["round"] = peleas["ROUND"]

    columnas = ["fecha", "EVENT", "LOCATION", "peleador_1", "peleador_2",
                "resultado", "ganador", "perdedor", "division", "femenina",
                "por_titulo", "WEIGHTCLASS", "metodo", "metodo_grupo",
                "round", "TIME", "URL"]
    peleas = peleas[columnas].rename(columns={
        "EVENT": "evento", "LOCATION": "lugar", "WEIGHTCLASS": "categoria_original",
        "TIME": "tiempo", "URL": "url_pelea"})
    return peleas.sort_values("fecha").reset_index(drop=True)


def construir_peleas_por_peleador(peleas):
    """Formato 'largo': dos filas por pelea, una desde cada esquina."""
    filas = []
    for yo, rival in [("peleador_1", "peleador_2"), ("peleador_2", "peleador_1")]:
        t = peleas.copy()
        t["peleador"] = t[yo]
        t["rival"] = t[rival]
        filas.append(t)
    largo = pd.concat(filas, ignore_index=True)
    largo["resultado_peleador"] = np.select(
        [largo["ganador"] == largo["peleador"],
         largo["perdedor"] == largo["peleador"],
         largo["resultado"] == "Empate"],
        ["Victoria", "Derrota", "Empate"], default="Sin resultado")
    columnas = ["fecha", "evento", "peleador", "rival", "resultado_peleador",
                "division", "femenina", "por_titulo", "metodo_grupo",
                "round", "url_pelea"]
    return largo[columnas].sort_values(["peleador", "fecha"]).reset_index(drop=True)


if __name__ == "__main__":
    PROCESSED.mkdir(parents=True, exist_ok=True)
    peleas = construir_peleas()
    largo = construir_peleas_por_peleador(peleas)
    peleas.to_csv(PROCESSED / "peleas.csv", index=False)
    largo.to_csv(PROCESSED / "peleas_por_peleador.csv", index=False)
    print(f"peleas.csv               {len(peleas):>6} filas")
    print(f"peleas_por_peleador.csv  {len(largo):>6} filas")
