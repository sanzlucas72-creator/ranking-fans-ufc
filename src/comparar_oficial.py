"""
Etapa 2 · Comparación con los rankings oficiales de la UFC (MEDIA y META).

Fuente de los oficiales:
    Capturas de ufc.com/rankings del 16/11/2026, transcriptas a mano en
    data/external/ranking_media_2026-11-16.csv y ranking_meta_2026-11-16.csv
    (las capturas originales están en la misma carpeta, como respaldo).
    La captura del ranking MEDIA no incluye la categoría Pesado.

Qué calcula, categoría por categoría y para cada par de rankings:
    - Si coincide el campeón.
    - Cuántos de los 16 (campeón + top 15) están en ambos rankings.
    - Spearman entre los puestos de los peleadores que están en los dos top 16.

Y para tener una referencia: lo mismo entre MEDIA y META. Si los dos rankings oficiales
tampoco coinciden del todo, sabemos cuánta diferencia es "normal".

Genera:
    data/processed/comparacion_oficial_resumen.csv -> una fila por categoría y par de rankings
    data/processed/comparacion_oficial_detalle.csv -> cada peleador con su puesto en los 3 rankings

Uso:
    python src/comparar_oficial.py     (antes: src/elo.py)
"""

import re                                # expresiones regulares, para limpiar nombres
import unicodedata                       # para sacar tildes (Procházka -> Prochazka)

import pandas as pd                      # tablas
from scipy.stats import spearmanr        # correlación de Spearman

import elo as E                          # rutas y categorías

EXTERNOS = E.RAIZ / "data" / "external"  # carpeta de los rankings oficiales

# Nombres que se escriben distinto en ufc.com y en UFCStats (y no se resuelven sacando tildes)
ALIAS = {"Jean Silva": "Jean Silva (Pluma)"}   # homónimo resuelto en elo.py (H5)


def normalizar(nombre):
    """Pasa un nombre a una forma comparable: sin tildes, en minúsculas, sin signos."""
    nombre = nombre.replace("ł", "l").replace("Ł", "L")                      # la ł polaca no se descompone sola
    nombre = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()  # saca tildes
    return re.sub(r"[^a-z ]", "", nombre.lower().replace("-", " ")).strip()  # minúsculas y solo letras


def puesto_a_numero(puesto):
    """'C' (campeón) -> 0; '1' -> 1; ... así se pueden ordenar y correlacionar."""
    return 0 if str(puesto) == "C" else int(puesto)


# ---------------------------------------------------------------- 1. cargar los tres rankings
elo = pd.read_csv(E.PROCESSED / "ranking_elo.csv")                     # nuestro ranking
historial = pd.read_csv(E.PROCESSED / "elo_historial.csv")             # para conocer todos los nombres
por_normal = {normalizar(n): n for n in set(historial["peleador"])}    # nombre normalizado -> nombre UFCStats

oficiales = pd.concat([pd.read_csv(EXTERNOS / "ranking_media_2026-11-16.csv"),   # ranking MEDIA
                       pd.read_csv(EXTERNOS / "ranking_meta_2026-11-16.csv")])   # ranking META
oficiales["peleador"] = [ALIAS.get(n, por_normal.get(normalizar(n), n))         # mismo nombre que UFCStats
                         for n in oficiales["peleador"]]

tablas = {"ELO": elo[["division", "puesto", "peleador"]].copy()}       # los tres rankings en un diccionario
for fuente in ["MEDIA", "META"]:
    tablas[fuente] = oficiales[oficiales["fuente"] == fuente][["division", "puesto", "peleador"]].copy()
for t in tablas.values():                                              # en los tres...
    t["n"] = t["puesto"].map(puesto_a_numero)                          # ...puesto como número (C = 0)

# ---------------------------------------------------------------- 2. comparar de a pares
filas = []                                                             # resumen: una fila por categoría y par
for a, b in [("ELO", "MEDIA"), ("ELO", "META"), ("MEDIA", "META")]:    # los tres pares posibles
    for division in E.MASCULINAS:                                      # las 8 categorías
        ta = tablas[a][tablas[a]["division"] == division]              # ranking A de esta categoría
        tb = tablas[b][tablas[b]["division"] == division]              # ranking B de esta categoría
        if ta.empty or tb.empty:                                       # ej. MEDIA no tiene Pesado
            continue
        top_a = ta[ta["n"] <= 15]                                      # campeón + top 15 de A
        top_b = tb[tb["n"] <= 15]                                      # campeón + top 15 de B
        comunes = top_a.merge(top_b, on="peleador", suffixes=("_a", "_b"))  # los que están en ambos
        rho = spearmanr(comunes["n_a"], comunes["n_b"]).correlation if len(comunes) > 2 else None
        campeon_a = top_a.loc[top_a["n"] == 0, "peleador"].tolist()    # campeón según A
        campeon_b = top_b.loc[top_b["n"] == 0, "peleador"].tolist()    # campeón según B
        filas.append({"comparacion": f"{a} vs {b}", "division": division,
                      "mismo_campeon": campeon_a == campeon_b,
                      "coinciden_de_16": len(comunes),
                      "spearman_comunes": None if rho is None else round(rho, 2)})
resumen = pd.DataFrame(filas)                                          # tabla resumen

# ---------------------------------------------------------------- 3. detalle por peleador
detalle = tablas["ELO"].rename(columns={"puesto": "puesto_elo"})[["division", "peleador", "puesto_elo"]]
for fuente in ["MEDIA", "META"]:                                       # sumamos el puesto en cada oficial
    t = tablas[fuente].rename(columns={"puesto": f"puesto_{fuente.lower()}",
                                       "division": f"division_{fuente.lower()}"})
    detalle = detalle.merge(t[["peleador", f"puesto_{fuente.lower()}", f"division_{fuente.lower()}"]],
                            on="peleador", how="outer")                # outer: no perder a nadie
detalle["division"] = detalle["division"].fillna(detalle["division_meta"]).fillna(detalle["division_media"])

resumen.to_csv(E.PROCESSED / "comparacion_oficial_resumen.csv", index=False)
detalle.to_csv(E.PROCESSED / "comparacion_oficial_detalle.csv", index=False)

if __name__ == "__main__":
    tabla = resumen.pivot_table(index="division", columns="comparacion",
                                values=["coinciden_de_16", "spearman_comunes"], aggfunc="first")
    print(tabla.reindex(E.MASCULINAS).to_string())
    print("\nCampeón distinto:", resumen.loc[~resumen["mismo_campeon"], ["comparacion", "division"]].values.tolist())
