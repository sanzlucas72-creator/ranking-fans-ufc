"""
Paso 1 - Descarga de datos crudos.

¿Qué hace?
    Baja las 6 tablas de UFCStats.com (la web oficial de estadísticas de la UFC)
    desde un repositorio público de GitHub que las scrapea automáticamente todos
    los días: https://github.com/Greco1899/scrape_ufc_stats

¿Por qué así y no scrapeando directo?
    - Los datos son los mismos de UFCStats, ya en formato tabla (CSV).
    - Evitamos hacer miles de pedidos al sitio oficial.
    - Cualquiera puede repetir la descarga y obtener los datos actualizados
      (reproducibilidad): se corre este script después de cada evento.

Uso:
    python src/descargar_datos.py
"""

import json
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

BASE_URL = "https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main"

TABLAS = {
    "ufc_event_details": "Eventos: nombre, fecha y lugar",
    "ufc_fight_details": "Peleas: evento, cruce y link a la pelea",
    "ufc_fight_results": "Resultados: ganador, método, round, categoría",
    "ufc_fight_stats": "Estadísticas por round y por peleador (golpes, derribos...)",
    "ufc_fighter_details": "Peleadores: nombre, apellido, apodo",
    "ufc_fighter_tott": "Físico del peleador: altura, peso, alcance, guardia, nacimiento",
}

CARPETA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def descargar():
    CARPETA_RAW.mkdir(parents=True, exist_ok=True)
    registro = {"fecha_descarga": datetime.now().isoformat(timespec="seconds"),
                "fuente": BASE_URL, "tablas": {}}
    for nombre, descripcion in TABLAS.items():
        url = f"{BASE_URL}/{nombre}.csv"
        contenido = urlopen(url, timeout=120).read()
        (CARPETA_RAW / f"{nombre}.csv").write_bytes(contenido)
        registro["tablas"][nombre] = {"descripcion": descripcion,
                                      "bytes": len(contenido)}
        print(f"OK  {nombre:22s} {len(contenido)/1e6:6.2f} MB  - {descripcion}")
    # Guardamos cuándo se bajaron los datos: es nuestra "fecha de corte".
    (CARPETA_RAW / "metadata_descarga.json").write_text(
        json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    descargar()
