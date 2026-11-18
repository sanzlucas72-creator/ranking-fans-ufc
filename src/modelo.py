"""
Etapa 2 · Opción B - Modelo de machine learning: ¿quién gana la pelea?

Objetivo:
    Predecir el ganador de una pelea usando las estadísticas de nuestro ranking
    (Elo y otras variables del historial de cada peleador) ANTES de la pelea.
    Sirve de sustento a la opción A: si el Elo es una buena medida del nivel,
    tiene que ayudar a predecir quién gana.

Tipo de problema:
    Clasificación binaria (aprendizaje supervisado).
    Target = 1 si gana el peleador A, 0 si gana el peleador B.

Cuidados para que la evaluación sea honesta (data leakage):
    1. Solo información PREVIA a cada pelea: el Elo y las estadísticas se calculan
       recorriendo las peleas en orden y guardando el estado de cada peleador ANTES
       de que pelee.
    2. Orden aleatorio de los peleadores: en UFCStats el que aparece primero gana el
       57% de las veces. Si no se mezcla, el modelo aprende el orden y no la pelea.
       Se sortea quién es A y quién es B (con semilla fija, para que sea reproducible).
    3. Split temporal: se entrena con el pasado y se evalúa con el futuro
       (entrenamiento 2012-2023, prueba 2024-2026), como se usaría en la realidad.
    4. Escalado dentro de un Pipeline: el escalador se ajusta solo con los datos de entrenamiento.

Modelos comparados (vistos en la cursada):
    - Baseline 1: "gana el de más victorias".
    - Baseline 2: "gana el de más Elo" (nuestro ranking, sin machine learning).
    - Regresión Logística.
    - Random Forest.

Genera:
    data/processed/dataset_modelo.csv   -> una fila por pelea con sus variables
    data/processed/resultados_modelo.csv -> métricas de cada modelo
    data/processed/importancia_variables.csv
    data/processed/estado_peleadores.csv -> cómo llega cada peleador hoy (lo usa la app)
    data/processed/modelo_rl.joblib      -> el modelo entrenado
    (La app reentrena la Regresión Logística con TODAS las peleas al abrirse: tarda menos de un
     segundo y evita problemas de versiones al compartir el archivo .joblib.)

Uso:
    python src/modelo.py
"""

import numpy as np                                            # cálculos numéricos
import pandas as pd                                           # tablas
import joblib                                                 # guardar el modelo entrenado
from sklearn.ensemble import RandomForestClassifier           # Random Forest
from sklearn.linear_model import LogisticRegression           # Regresión Logística
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.pipeline import Pipeline                         # encadena escalado + modelo
from sklearn.preprocessing import StandardScaler              # escalado (media 0, desvío 1)

import elo as E                                               # mismas reglas que el ranking


def datos_fisicos():
    """Fecha de nacimiento y alcance de cada peleador (los homónimos quedan sin dato)."""
    fisico = pd.read_csv(E.RAW / "ufc_fighter_tott.csv")                 # datos físicos
    fisico = fisico.apply(lambda c: c.str.strip() if c.dtype == object else c)  # sin espacios (H1)
    fisico = fisico.drop_duplicates("FIGHTER", keep=False)              # homónimos: sin dato (H5)
    nacimiento = pd.to_datetime(fisico["DOB"], format="%b %d, %Y", errors="coerce")  # "--" -> vacío (H4)
    alcance = pd.to_numeric(fisico["REACH"].str.extract(r"(\d+)")[0], errors="coerce")
    return dict(zip(fisico["FIGHTER"], nacimiento)), dict(zip(fisico["FIGHTER"], alcance))

SEMILLA = 42                                                  # para que todo sea reproducible
INICIO_ENTRENAMIENTO = "2012-01-01"   # 2010-2011 quedan como "calentamiento" del Elo
INICIO_PRUEBA = "2024-01-01"          # desde acá, datos que el modelo nunca vio

# Variables del modelo: todas son DIFERENCIAS entre A y B (A menos B)
VARIABLES = {
    "dif_elo": "Diferencia de puntos Elo",
    "dif_peleas": "Diferencia de peleas en la UFC (experiencia)",
    "dif_pct_victorias": "Diferencia de % de victorias",
    "dif_pct_finish": "Diferencia de % de victorias por KO o sumisión",
    "dif_racha": "Diferencia de racha (+ ganando, − perdiendo)",
    "dif_ultimas3": "Diferencia de victorias en las últimas 3 peleas",
    "dif_dias_inactivo": "Diferencia de días sin pelear",
    "dif_edad": "Diferencia de edad el día de la pelea (años)",
    "dif_alcance": "Diferencia de alcance (pulgadas)",
}
# Se eligió este conjunto (9 variables) porque fue el de mejor accuracy en la validación cruzada
# temporal sobre el entrenamiento, sin mirar los datos de prueba (ver seleccion_variables.csv).


# ------------------------------------------------------------------ 1. variables por pelea
def construir_dataset(peleas):
    """Recorre las peleas en orden y arma una fila por pelea con el estado PREVIO de cada peleador."""
    datos = peleas[(peleas["fecha"] >= E.FECHA_INICIO)                  # mismo período que el ranking
                   & (peleas["resultado"] != "Sin resultado")]          # los No Contest no tienen ganador
    datos = datos.sort_values("fecha")                                  # orden cronológico (clave)
    rng = np.random.default_rng(SEMILLA)                                # sorteo reproducible de A y B

    estado = {}                                                         # peleador -> sus estadísticas hasta hoy
    def nuevo():
        return {"elo": E.ELO_INICIAL, "peleas": 0, "victorias": 0, "finishes": 0,
                "racha": 0, "ultimas": [], "ultima_fecha": None}

    filas = []
    for p in datos.itertuples():                                        # pelea por pelea
        s1 = estado.setdefault(p.peleador_1, nuevo())                   # estado previo del peleador 1
        s2 = estado.setdefault(p.peleador_2, nuevo())                   # estado previo del peleador 2

        # --- (a) guardamos la fila con información PREVIA a la pelea ---
        if p.resultado != "Empate":                                     # los empates no tienen ganador
            invertir = rng.random() < 0.5                               # sorteo: ¿el 1 pasa a ser B?
            a, b = (s2, s1) if invertir else (s1, s2)                   # A y B según el sorteo
            gana_1 = p.resultado == "Gana 1"
            gana_a = (not gana_1) if invertir else gana_1               # target: ¿ganó A?

            def pct(x, n):                                              # porcentaje seguro (sin dividir por 0)
                return x / n if n else 0.5
            def dias(s):                                                # días sin pelear (debut = 365)
                return (p.fecha - s["ultima_fecha"]).days if s["ultima_fecha"] is not None else 365

            filas.append({
                "fecha": p.fecha, "evento": p.evento, "division": p.division,
                "peleador_a": p.peleador_2 if invertir else p.peleador_1,
                "peleador_b": p.peleador_1 if invertir else p.peleador_2,
                "dif_elo": a["elo"] - b["elo"],
                "dif_peleas": a["peleas"] - b["peleas"],
                "dif_pct_victorias": pct(a["victorias"], a["peleas"]) - pct(b["victorias"], b["peleas"]),
                "dif_pct_finish": pct(a["finishes"], a["victorias"]) - pct(b["finishes"], b["victorias"]),
                "dif_racha": a["racha"] - b["racha"],
                "dif_ultimas3": sum(a["ultimas"][-3:]) - sum(b["ultimas"][-3:]),
                "dif_dias_inactivo": dias(a) - dias(b),
                "gana_a": int(gana_a),
            })

        # --- (b) DESPUÉS de guardar la fila, actualizamos el estado con el resultado ---
        esperado_1 = E.probabilidad_esperada(s1["elo"], s2["elo"])      # Elo con las mismas reglas del ranking
        real_1 = {"Gana 1": 1.0, "Gana 2": 0.0}.get(p.resultado, 0.5)
        k = E.K * (E.BONUS_FINISH if p.metodo_grupo in ("KO/TKO", "Sumisión") else 1)
        k *= E.BONUS_TITULO if p.por_titulo else 1
        s1["elo"] += k * (real_1 - esperado_1)
        s2["elo"] += k * ((1 - real_1) - (1 - esperado_1))
        for s, real in [(s1, real_1), (s2, 1 - real_1)]:
            s["peleas"] += 1
            s["ultima_fecha"] = p.fecha
            if real == 1.0:                                             # ganó
                s["victorias"] += 1
                s["finishes"] += p.metodo_grupo in ("KO/TKO", "Sumisión")
                s["racha"] = s["racha"] + 1 if s["racha"] > 0 else 1
            elif real == 0.0:                                           # perdió
                s["racha"] = s["racha"] - 1 if s["racha"] < 0 else -1
            else:                                                       # empate
                s["racha"] = 0
            s["ultimas"].append(1 if real == 1.0 else 0)
    df = pd.DataFrame(filas)
    actual = pd.DataFrame([{"peleador": n, "elo": round(v["elo"], 1), "peleas": v["peleas"],
                            "victorias": v["victorias"], "finishes": v["finishes"], "racha": v["racha"],
                            "ultimas3": sum(v["ultimas"][-3:]), "ultima_fecha": v["ultima_fecha"]}
                           for n, v in estado.items()])                 # cómo llega cada uno HOY
    return agregar_fisico(df), actual


def agregar_fisico(df):
    """Suma edad y alcance desde la tabla física de UFCStats (los faltantes "--" quedan como 0 = sin diferencia)."""
    nac, alc = datos_fisicos()                                          # peleador -> nacimiento / alcance
    edad_a = (df["fecha"] - df["peleador_a"].map(nac)).dt.days / 365.25 # edad de A ese día
    edad_b = (df["fecha"] - df["peleador_b"].map(nac)).dt.days / 365.25 # edad de B ese día
    df["dif_edad"] = (edad_a - edad_b).fillna(0)                        # sin dato -> 0
    df["dif_alcance"] = (df["peleador_a"].map(alc) - df["peleador_b"].map(alc)).fillna(0)
    return df


# ------------------------------------------------------------------ 2. entrenar y evaluar
def metricas(nombre, y_real, y_pred, prob=None):
    return {"modelo": nombre,
            "accuracy": round(accuracy_score(y_real, y_pred), 3),
            "f1": round(f1_score(y_real, y_pred), 3),
            "auc": round(roc_auc_score(y_real, prob), 3) if prob is not None else None}


def entrenar_y_evaluar(df):
    df = df[df["fecha"] >= INICIO_ENTRENAMIENTO]                        # sin el calentamiento 2010-2011
    entreno = df[df["fecha"] < INICIO_PRUEBA]                           # el pasado
    prueba = df[df["fecha"] >= INICIO_PRUEBA]                           # el "futuro"
    X_tr, y_tr = entreno[list(VARIABLES)], entreno["gana_a"]
    X_te, y_te = prueba[list(VARIABLES)], prueba["gana_a"]

    modelos = {
        "Regresión Logística": Pipeline([("escalado", StandardScaler()),          # escalar dentro del Pipeline
                                         ("modelo", LogisticRegression(max_iter=1000))]),
        "Random Forest": RandomForestClassifier(n_estimators=300, max_depth=6,     # árboles poco profundos
                                                min_samples_leaf=20, random_state=SEMILLA),
    }

    # Selección de variables con validación cruzada temporal SOLO sobre el entrenamiento
    tscv = TimeSeriesSplit(n_splits=5)
    del_ranking = [v for v in VARIABLES if v not in ("dif_edad", "dif_alcance")]
    conjuntos = {"Ranking (7 variables)": del_ranking,
                 "Ranking + edad (8)": del_ranking + ["dif_edad"],
                 "Ranking + edad + alcance (9)": list(VARIABLES)}
    seleccion = []
    for nombre_c, cols in conjuntos.items():
        rl_cv = Pipeline([("escalado", StandardScaler()), ("modelo", LogisticRegression(max_iter=1000))])
        acc = cross_val_score(rl_cv, entreno[cols], y_tr, cv=tscv, scoring="accuracy")
        seleccion.append({"conjunto": nombre_c, "accuracy_cv": round(acc.mean(), 3), "desvio": round(acc.std(), 3)})
    seleccion = pd.DataFrame(seleccion)

    resultados, matrices, cv = [], {}, {}
    # Baselines (sin machine learning)
    mas_vict = (X_te["dif_pct_victorias"] >= 0).astype(int)            # empate en % -> se elige A
    resultados.append(metricas("Baseline: gana el de mejor % de victorias", y_te, mas_vict))
    resultados.append(metricas("Baseline: gana el de más Elo (ranking, sin ML)", y_te,
                               (X_te["dif_elo"] >= 0).astype(int),
                               1 / (1 + 10 ** (-X_te["dif_elo"] / 400))))

    for nombre, modelo in modelos.items():
        tscv = TimeSeriesSplit(n_splits=5)                              # validación cruzada temporal
        cv[nombre] = cross_val_score(modelo, X_tr, y_tr, cv=tscv, scoring="accuracy")
        modelo.fit(X_tr, y_tr)                                          # entrenamos con todo el pasado
        prob = modelo.predict_proba(X_te)[:, 1]                         # probabilidad de que gane A
        pred = (prob >= 0.5).astype(int)
        resultados.append(metricas(nombre, y_te, pred, prob))
        matrices[nombre] = confusion_matrix(y_te, pred)

    # Importancia de variables
    rl = modelos["Regresión Logística"].named_steps["modelo"]
    rf = modelos["Random Forest"]
    importancia = pd.DataFrame({
        "variable": list(VARIABLES),
        "descripcion": list(VARIABLES.values()),
        "coef_regresion_logistica": rl.coef_[0].round(3),               # con variables escaladas: comparables
        "importancia_random_forest": rf.feature_importances_.round(3),
    }).sort_values("importancia_random_forest", ascending=False)

    info = {"n_entreno": len(entreno), "n_prueba": len(prueba), "seleccion": seleccion,
            "pct_gana_a_prueba": round(y_te.mean(), 3), "cv": cv, "matrices": matrices}
    return pd.DataFrame(resultados), importancia, modelos, info


if __name__ == "__main__":
    peleas = E.cargar_peleas_masculinas()                               # mismos datos que el ranking
    df, actual = construir_dataset(peleas)                              # 1. variables
    nac, alc = datos_fisicos()                                          # para calcular edad y alcance en la app
    actual["nacimiento"] = actual["peleador"].map(nac)
    actual["alcance"] = actual["peleador"].map(alc)
    actual.to_csv(E.PROCESSED / "estado_peleadores.csv", index=False)   # estado actual (lo usa la app)
    df.to_csv(E.PROCESSED / "dataset_modelo.csv", index=False)
    resultados, importancia, modelos, info = entrenar_y_evaluar(df)     # 2. modelos
    resultados.to_csv(E.PROCESSED / "resultados_modelo.csv", index=False)
    importancia.to_csv(E.PROCESSED / "importancia_variables.csv", index=False)
    joblib.dump({"modelo": modelos["Regresión Logística"], "variables": list(VARIABLES)},
                E.PROCESSED / "modelo_rl.joblib")                       # para la app

    print(f"Peleas: entrenamiento {info['n_entreno']} | prueba {info['n_prueba']} "
          f"| gana A en prueba: {info['pct_gana_a_prueba']:.1%} (orden aleatorio: ~50%)")
    print("\nSelección de variables (CV temporal en entrenamiento, Regresión Logística):")
    print(info["seleccion"].to_string(index=False))
    info["seleccion"].to_csv(E.PROCESSED / "seleccion_variables.csv", index=False)
    print("\nValidación cruzada temporal (accuracy, 5 cortes):")
    for n, v in info["cv"].items():
        print(f"  {n}: {v.mean():.3f} ± {v.std():.3f}")
    print("\nPrueba 2024-2026:")
    print(resultados.to_string(index=False))
    for n, m in info["matrices"].items():
        print(f"\nMatriz de confusión · {n}\n{m}")
    print("\nImportancia de variables:")
    print(importancia.to_string(index=False))
