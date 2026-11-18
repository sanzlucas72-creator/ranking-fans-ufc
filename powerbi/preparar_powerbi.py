# =============================================================================
# preparar_powerbi.py · Arma el archivo de datos para el tablero de Power BI
# -----------------------------------------------------------------------------
# Junta en UN solo Excel (una hoja por tabla) los resultados del proyecto.
# Se usa Excel y no CSV porque Excel guarda los números y las fechas con su tipo:
# así Power BI no confunde "0.618" con 618 en una PC configurada en español.
# Salida: powerbi/tablero_ranking_fans.xlsx
# Correr después de elo.py, comparar_oficial.py y modelo.py.
# =============================================================================

from pathlib import Path  # para armar rutas que funcionan en Windows y en Linux

import pandas as pd  # para leer y transformar las tablas

RAIZ = Path(__file__).resolve().parent.parent  # carpeta ufc_ranking (un nivel arriba de src)
PROC = RAIZ / "data" / "processed"  # carpeta con los resultados del proyecto
SALIDA = RAIZ / "powerbi"  # carpeta donde va el Excel para Power BI
SALIDA.mkdir(exist_ok=True)  # la crea si no existe

# Orden de las categorías de la más liviana a la más pesada (para ordenar en Power BI)
ORDEN = ["Mosca", "Gallo", "Pluma", "Ligero", "Wélter", "Mediano", "Semipesado", "Pesado"]
LIBRAS = [125, 135, 145, 155, 170, 185, 205, 265]  # límite de peso de cada categoría

# --- Tabla 1: Categorias (tabla chica para ordenar y filtrar) -----------------
categorias = pd.DataFrame({  # una fila por categoría
    "division": ORDEN,  # nombre de la categoría
    "orden": range(1, len(ORDEN) + 1),  # 1 = Mosca ... 8 = Pesado
    "libras": LIBRAS,  # límite de peso
})

# --- Tabla 2: Ranking (nuestro ranking con los oficiales al lado) -------------
ranking = pd.read_csv(PROC / "ranking_elo.csv")  # ranking Elo de los activos
ranking["puesto_num"] = ranking["puesto"].replace("C", "0").astype(int)  # campeón = 0, para ordenar
ranking["top15"] = ranking["puesto_num"] <= 15  # True si es campeón o top 15 (lo que muestran los oficiales)
rec = ranking["record"].str.split("-", expand=True).astype(int)  # separa "11-2-0" en tres columnas
ranking["victorias"], ranking["derrotas"], ranking["empates"] = rec[0], rec[1], rec[2]  # las guarda con nombre
ranking["ultima_pelea"] = pd.to_datetime(ranking["ultima_pelea"])  # texto -> fecha

detalle = pd.read_csv(PROC / "comparacion_oficial_detalle.csv")  # puestos en MEDIA y META por peleador
# Un peleador puede figurar en dos categorías de un oficial (ej. Alex Pereira en Semipesado y Pesado del META).
# Solo vale el puesto de la MISMA categoría que en nuestro ranking; si no, la fila se duplica.
for of in ["media", "meta"]:  # para cada ranking oficial...
    otra = detalle[f"division_{of}"] != detalle["division"]  # ...filas donde el oficial lo tiene en otra categoría
    detalle.loc[otra, f"puesto_{of}"] = None  # ese puesto no corresponde a esta categoría
detalle = detalle.sort_values(["puesto_media", "puesto_meta"])  # deja primero las filas con puesto válido
detalle = (detalle.groupby(["division", "peleador"], as_index=False)  # una sola fila por peleador y categoría
           [["puesto_media", "puesto_meta"]].first())  # first() toma el primer valor no vacío de cada columna
ranking = ranking.merge(detalle, on=["division", "peleador"], how="left")  # agrega MEDIA y META al ranking
for col in ["puesto_media", "puesto_meta"]:  # en los oficiales el campeón también figura como "C"
    ranking[col] = ranking[col].replace("C", "0")  # campeón = 0
    ranking[col] = pd.to_numeric(ranking[col], errors="coerce")  # vacío si no está en el oficial
def puesto_texto(x):  # convierte el puesto oficial en texto para mostrar en la tabla
    if pd.isna(x):  # no está en el top 15 oficial de esta categoría
        return ""  # celda vacía
    return "C" if x == 0 else str(int(x))  # 0 -> "C" (campeón); 3.0 -> "3"
ranking["media"] = ranking["puesto_media"].apply(puesto_texto)  # columna para mostrar: C, 1, 2... o vacío
ranking["meta"] = ranking["puesto_meta"].apply(puesto_texto)  # ídem para el META
ranking["en_media"] = ranking["puesto_media"].notna()  # ¿aparece en el ranking MEDIA?
ranking["en_meta"] = ranking["puesto_meta"].notna()  # ¿aparece en el ranking META?

# --- Tabla 3: Coincidencias (resumen de la comparación con los oficiales) -----
coincidencias = pd.read_csv(PROC / "comparacion_oficial_resumen.csv")  # una fila por comparación y categoría
coincidencias["pct_coinciden"] = coincidencias["coinciden_de_16"] / 16  # de 16 lugares (C + top 15) a %

# --- Tabla 4: Evolucion (historial de puntos de los peleadores activos) -------
historial = pd.read_csv(PROC / "elo_historial.csv", parse_dates=["fecha"])  # todas las peleas desde 2010
activos = ranking[["peleador", "division"]].rename(columns={"division": "division_actual"})  # activos y su categoría hoy
evolucion = historial.merge(activos, on="peleador", how="inner")  # se queda solo con los activos
evolucion = evolucion[["fecha", "evento", "peleador", "division_actual", "rival", "resultado",
                       "metodo", "por_titulo", "elo_antes", "cambio", "elo_despues"]]  # columnas útiles

# --- Tabla 5: Peleas (contexto: cuántas peleas y cómo terminan, por año) ------
peleas = pd.read_csv(PROC / "peleas.csv", parse_dates=["fecha"])  # todas las peleas limpias
peleas = peleas[(~peleas["femenina"]) & (peleas["division"].isin(ORDEN))]  # solo las 8 masculinas
peleas = peleas[peleas["fecha"] >= "2010-01-01"]  # mismo período que el ranking
peleas["anio"] = peleas["fecha"].dt.year  # año de la pelea
peleas_anio = (peleas.groupby(["anio", "division", "metodo_grupo"])  # agrupa por año, categoría y método
               .size().reset_index(name="peleas"))  # cuenta las peleas de cada grupo

# --- Tabla 6 y 7: Modelo de machine learning ----------------------------------
modelo = pd.read_csv(PROC / "resultados_modelo.csv")  # accuracy, F1 y AUC de cada modelo en 2024-2026
modelo["nombre"] = modelo["modelo"].replace({  # nombres cortos para que entren en el gráfico
    "Baseline: gana el de mejor % de victorias": "Regla: mejor % de victorias",
    "Baseline: gana el de más Elo (ranking, sin ML)": "Regla: más puntos Elo"})
variables = pd.read_csv(PROC / "importancia_variables.csv")  # peso de cada variable
variables["nombre"] = variables["variable"].map({  # nombres cortos para el gráfico
    "dif_edad": "Edad", "dif_elo": "Puntos Elo", "dif_pct_victorias": "% de victorias",
    "dif_dias_inactivo": "Días sin pelear", "dif_alcance": "Alcance", "dif_peleas": "Experiencia",
    "dif_pct_finish": "% de KO o sumisión", "dif_racha": "Racha", "dif_ultimas3": "Últimas 3 peleas"})
variables["peso_absoluto"] = variables["coef_regresion_logistica"].abs()  # tamaño del efecto, sin el signo
variables["efecto"] = variables["coef_regresion_logistica"].apply(  # sentido del efecto, en palabras
    lambda c: "Ayuda a ganar" if c > 0 else "Juega en contra")

# --- Guardar todo en un solo Excel ---------------------------------------------
archivo = SALIDA / "tablero_ranking_fans.xlsx"  # nombre del archivo final
with pd.ExcelWriter(archivo) as excel:  # abre el Excel para escribir varias hojas
    categorias.to_excel(excel, sheet_name="Categorias", index=False)  # hoja 1
    ranking.to_excel(excel, sheet_name="Ranking", index=False)  # hoja 2
    coincidencias.to_excel(excel, sheet_name="Coincidencias", index=False)  # hoja 3
    evolucion.to_excel(excel, sheet_name="Evolucion", index=False)  # hoja 4
    peleas_anio.to_excel(excel, sheet_name="Peleas", index=False)  # hoja 5
    modelo.to_excel(excel, sheet_name="Modelo", index=False)  # hoja 6
    variables.to_excel(excel, sheet_name="Variables", index=False)  # hoja 7

print("✅ Archivo para Power BI listo:", archivo.name)  # aviso final
for nombre, tabla in [("Categorias", categorias), ("Ranking", ranking), ("Coincidencias", coincidencias),
                      ("Evolucion", evolucion), ("Peleas", peleas_anio), ("Modelo", modelo),
                      ("Variables", variables)]:  # muestra cuántas filas tiene cada hoja
    print(f"   {nombre}: {len(tabla)} filas")
