"""
Etapa 2 · Controles del ranking Elo (para la defensa).

Control 1 - ¿Importa desde cuándo se calcula?
    Calcula el ranking arrancando en 1994 y en 2010, y compara el top 15 de cada categoría:
    cuántos peleadores coinciden y la correlación de Spearman entre los dos órdenes.

Control 2 - ¿Es coherente con lo que ya pasó?
    En las peleas desde 2020, ¿qué porcentaje ganó el que tenía más Elo antes de la pelea?
    Se compara con un criterio simple (baseline): "gana el que tenía más victorias en la UFC".
    No es una predicción: es revisar que el ranking sea consistente con los resultados.

Uso:
    python src/controles_elo.py
"""

import pandas as pd                     # tablas
from scipy.stats import spearmanr       # correlación de Spearman (vista en la cursada)

import elo as E                         # nuestro módulo del ranking Elo

peleas = E.cargar_peleas_masculinas()                       # peleas masculinas, con homónimos resueltos
corte = peleas["fecha"].max()                               # fecha de corte
campeones = E.buscar_campeones(peleas)                      # campeones actuales

# ---------------------------------------------------------------- Control 1
elo_10, hist_10 = E.calcular_elo(peleas, "2010-01-01")      # versión oficial del proyecto: desde 2010
elo_94, hist_94 = E.calcular_elo(peleas, "1994-01-01")      # versión de comparación: desde 1994
rank_10 = E.armar_ranking(elo_10, hist_10, corte, campeones, peleas)  # ranking desde 2010
rank_94 = E.armar_ranking(elo_94, hist_94, corte, campeones, peleas)  # ranking desde 1994

filas = []                                                  # una fila por categoría
for division in E.MASCULINAS:                               # recorremos las 8 categorías
    top_10 = rank_10[rank_10["division"] == division].head(16)          # campeón + top 15 (desde 2010)
    otro = rank_94[rank_94["division"] == division].reset_index(drop=True)  # ranking completo (desde 1994)
    posicion_94 = {n: i for i, n in enumerate(otro["peleador"])}       # posición de cada uno en 1994
    rho = spearmanr(range(len(top_10)),                                # orden en 2010 (0, 1, 2...)
                    [posicion_94.get(n, len(otro)) for n in top_10["peleador"]]).correlation  # orden en 1994
    coinciden = len(set(top_10["peleador"]) & set(otro.head(16)["peleador"]))  # cuántos están en ambos tops
    filas.append({"division": division, "coinciden_de_16": coinciden, "spearman": round(rho, 3)})
control_1 = pd.DataFrame(filas)                             # tabla del control 1
print("CONTROL 1 · Desde 1994 vs. desde 2010 (campeón + top 15)")
print(control_1.to_string(index=False))

# ---------------------------------------------------------------- Control 2
h = hist_10.sort_values("fecha").copy()                     # historial en orden de fecha
h["victorias_previas"] = (h["resultado"] == "Victoria").groupby(h["peleador"]).cumsum() \
    - (h["resultado"] == "Victoria").astype(int)            # victorias que tenía ANTES de esta pelea
h = h[(h["fecha"] >= "2020-01-01") & (h["resultado"] != "Empate")]  # peleas desde 2020, sin empates

favorito_elo = h[h["prob_esperada"] > 0.5]                  # una fila por pelea: la del que tenía más Elo
acierto_elo = (favorito_elo["resultado"] == "Victoria").mean()      # ¿ganó el de más Elo?

rival = h.set_index(["fecha", "evento", "peleador"])["victorias_previas"]  # victorias de cada uno, por pelea
h["victorias_rival"] = [rival.get((f, e, r), 0) for f, e, r in zip(h["fecha"], h["evento"], h["rival"])]
con_mas = h[h["victorias_previas"] > h["victorias_rival"]]  # el que tenía más victorias (sin empates)
acierto_base = (con_mas["resultado"] == "Victoria").mean()  # ¿ganó el de más victorias?

control_2 = pd.DataFrame([
    {"criterio": "Gana el de más Elo (nuestro ranking)", "peleas": len(favorito_elo), "acierto": round(acierto_elo, 3)},
    {"criterio": "Gana el de más victorias en la UFC (baseline)", "peleas": len(con_mas), "acierto": round(acierto_base, 3)},
])
print("\nCONTROL 2 · Coherencia con los resultados (peleas desde 2020)")
print(control_2.to_string(index=False))

control_1.to_csv(E.PROCESSED / "control_1_inicio.csv", index=False)       # guardamos los resultados
control_2.to_csv(E.PROCESSED / "control_2_coherencia.csv", index=False)
