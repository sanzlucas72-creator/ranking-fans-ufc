"""
Etapa 2 · Opción B - Ranking RFM.

¿Qué es?
    Una adaptación de la segmentación RFM vista en la cursada (Bloque 3, clase 6):
    Recencia, Frecuencia y Monto, sin entrenar modelos. En vez de clientes, peleadores:

        R - Recencia:  ¿cuánto hace que peleó?               (menos días = mejor)
        F - Frecuencia: ¿cuántas peleas tuvo en 3 años?      (más peleas = mejor)
        M - "Monto":   ¿qué tan buenos fueron sus resultados en 3 años? (calidad neta)

    Cada dimensión se convierte en un puntaje de 1 a 5 DENTRO de cada categoría
    (quintiles: el 20% más bajo saca 1, el 20% más alto saca 5).

¿Para qué sirve?
    Para validar el ranking Elo (opción A) con un método distinto e independiente:
    el RFM NO usa el puntaje Elo para nada. Si los dos coinciden, el Elo no es arbitrario.

Cómo se calcula M (calidad neta), mirando las peleas de los últimos 3 años:
    - Cada victoria suma 1 punto + la "calidad del rival" (su % de victorias en la UFC desde 2010).
      Ganarle a alguien que gana el 80% de sus peleas suma 1,8; a uno que gana el 30%, suma 1,3.
    - Si la victoria fue por KO/TKO o sumisión, se multiplica por 1,25 (igual que en el Elo).
    - Si fue por el título, se multiplica por 2 (igual que en el Elo).
    - Cada derrota resta 1 punto + lo "flojo" del rival (1 - su % de victorias):
      perder con alguien malo resta más que perder con alguien bueno.

Ponderación final:
    RFM = R + F + 2 x M  (máximo 20 puntos)
    M vale el doble porque es la única dimensión que mide CALIDAD; R y F miden actividad,
    que además ya es requisito para estar en el ranking. Se decidió antes de ver los
    resultados, para no ajustar el método hasta que coincida con el Elo.

Uso:
    python src/rfm.py      (antes hay que correr src/elo.py)
"""

import numpy as np          # para redondear hacia arriba (ceil)
import pandas as pd         # tablas

import elo as E             # reutilizamos datos, homónimos, campeones y categorías del Elo

AÑOS_VENTANA = 3            # las peleas de los últimos 3 años son las que cuentan para F y M
PESO_M = 2                  # M pesa el doble (ver explicación arriba)


def puntaje_1_a_5(serie):
    """Convierte valores en puntajes de 1 a 5 según su posición dentro del grupo (quintiles)."""
    posicion = serie.rank(method="average", pct=True)   # posición relativa: 0 (el peor) a 1 (el mejor)
    return np.ceil(posicion * 5).clip(1, 5).astype(int)  # 0-20% -> 1, 20-40% -> 2 ... 80-100% -> 5


def calcular_rfm(peleas, ranking_elo):
    corte = peleas["fecha"].max()                                       # fecha de corte
    desde = corte - pd.DateOffset(years=AÑOS_VENTANA)                   # inicio de la ventana de 3 años
    validas = peleas[(peleas["fecha"] >= "2010-01-01")                  # mismo período que el Elo
                     & (peleas["resultado"] != "Sin resultado")]        # sin No Contest

    # --- Calidad de cada peleador como rival: % de victorias en la UFC desde 2010 ---
    gana = validas["ganador"].value_counts()                            # victorias de cada peleador
    pierde = validas["perdedor"].value_counts()                         # derrotas de cada peleador
    nombres = set(validas["peleador_1"]) | set(validas["peleador_2"])   # todos los peleadores
    calidad = {n: gana.get(n, 0) / max(gana.get(n, 0) + pierde.get(n, 0), 1)  # % de victorias
               for n in nombres}

    # --- Puntos de cada pelea en la ventana de 3 años ---
    recientes = validas[validas["fecha"] >= desde]                      # solo los últimos 3 años
    puntos = []                                                         # una fila por peleador y pelea
    for p in recientes.itertuples():                                    # recorremos pelea por pelea
        mult = 1.25 if p.metodo_grupo in ("KO/TKO", "Sumisión") else 1  # bonus por finish
        mult *= 2 if p.por_titulo else 1                                # bonus por título
        if p.resultado == "Empate":                                     # empate: no suma ni resta
            puntos += [(p.peleador_1, 0), (p.peleador_2, 0)]
            continue
        puntos.append((p.ganador, (1 + calidad[p.perdedor]) * mult))    # el ganador suma
        puntos.append((p.perdedor, -(1 + (1 - calidad[p.ganador]))))    # el perdedor resta
    puntos = pd.DataFrame(puntos, columns=["peleador", "puntos"])       # a tabla

    # --- Las tres dimensiones, para los mismos peleadores activos del ranking Elo ---
    tabla = ranking_elo[["division", "peleador", "campeon", "dias_inactivo"]].copy()  # mismo universo
    tabla["peleas_3a"] = tabla["peleador"].map(puntos["peleador"].value_counts()).fillna(0).astype(int)  # F
    tabla["calidad_neta"] = tabla["peleador"].map(puntos.groupby("peleador")["puntos"].sum()).fillna(0)  # M

    por_div = tabla.groupby("division", observed=True)                  # todo se puntúa dentro de la categoría
    tabla["R"] = por_div["dias_inactivo"].transform(lambda s: puntaje_1_a_5(-s))  # menos días = más puntaje
    tabla["F"] = por_div["peleas_3a"].transform(puntaje_1_a_5)          # más peleas = más puntaje
    tabla["M"] = por_div["calidad_neta"].transform(puntaje_1_a_5)       # más calidad = más puntaje
    tabla["RFM"] = tabla["R"] + tabla["F"] + PESO_M * tabla["M"]        # puntaje total (máximo 20)

    # --- Orden: campeón aparte; después RFM, y si empatan, la calidad neta desempata ---
    tabla = tabla.sort_values(["division", "campeon", "RFM", "calidad_neta"],
                              ascending=[True, False, False, False])
    resto = ~tabla["campeon"]                                           # todos menos el campeón
    tabla["puesto"] = "C"                                               # el campeón lleva "C"
    tabla.loc[resto, "puesto"] = (tabla[resto].groupby("division", observed=True).cumcount() + 1).astype(str)
    tabla["calidad_neta"] = tabla["calidad_neta"].round(2)              # dos decimales
    return tabla[["division", "puesto", "peleador", "RFM", "R", "F", "M",
                  "dias_inactivo", "peleas_3a", "calidad_neta", "campeon"]]


if __name__ == "__main__":
    peleas = E.cargar_peleas_masculinas()                               # mismos datos que el Elo
    ranking_elo = pd.read_csv(E.PROCESSED / "ranking_elo.csv")          # universo de activos y campeones
    ranking_elo["division"] = pd.Categorical(ranking_elo["division"], E.MASCULINAS, ordered=True)
    rfm = calcular_rfm(peleas, ranking_elo)                             # cálculo
    rfm.to_csv(E.PROCESSED / "ranking_rfm.csv", index=False)            # guardamos
    for div, grupo in rfm.groupby("division", observed=True):           # top 5 de cada categoría
        print(f"\n{div}")
        print(grupo.head(6)[["puesto", "peleador", "RFM", "R", "F", "M", "calidad_neta"]].to_string(index=False))
