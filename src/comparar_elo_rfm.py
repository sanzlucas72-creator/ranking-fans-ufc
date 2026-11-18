"""
Etapa 2 · Comparación opción A (Elo) vs. opción B (RFM).

Responde dos preguntas, categoría por categoría:

    1. ¿Coinciden en general sobre quién es bueno y quién no?
       -> Correlación de Spearman entre el Elo y el RFM, con todos los activos de la categoría.

    2. ¿Coinciden sobre quién está en la élite?
       -> De los 16 primeros del Elo (campeón + top 15), ¿cuántos están en el segmento de élite
          del RFM (M = 5, el 20% con mejor calidad de resultados)? Por azar serían unos 3 de 16.

    Y una tercera, para entender la diferencia entre los dos métodos:

    3. ¿Coinciden en el ORDEN dentro de la élite?
       -> Spearman entre el Elo y la calidad neta, solo con esos 16.

Uso:
    python src/comparar_elo_rfm.py     (antes: src/elo.py y src/rfm.py)
"""

import pandas as pd                     # tablas
from scipy.stats import spearmanr       # correlación de Spearman

import elo as E                         # rutas y lista de categorías

elo = pd.read_csv(E.PROCESSED / "ranking_elo.csv")          # ranking A
rfm = pd.read_csv(E.PROCESSED / "ranking_rfm.csv")          # ranking B
juntos = elo.merge(rfm[["peleador", "RFM", "M", "calidad_neta"]], on="peleador")  # un peleador por fila, con ambos

filas = []                                                  # una fila por categoría
for division in E.MASCULINAS:                               # recorremos las 8 categorías
    g = juntos[juntos["division"] == division]              # todos los activos de la categoría
    elite = g.sort_values("elo", ascending=False).head(16)  # los 16 primeros según el Elo
    filas.append({
        "division": division,
        "activos": len(g),                                                   # cuántos peleadores hay
        "spearman_general": round(spearmanr(g["elo"], g["RFM"]).correlation, 2),   # pregunta 1
        "elite_elo_en_elite_rfm": f"{(elite['M'] == 5).sum()} de 16",       # pregunta 2
        "spearman_dentro_elite": round(spearmanr(elite["elo"], elite["calidad_neta"]).correlation, 2),  # pregunta 3
    })
tabla = pd.DataFrame(filas)                                 # resultado final
print(tabla.to_string(index=False))
tabla.to_csv(E.PROCESSED / "comparacion_elo_rfm.csv", index=False)  # lo guardamos
