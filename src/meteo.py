"""Descarga de meteorología horaria (Open-Meteo / ERA5) y variables derivadas."""
import os
import time
import requests
import numpy as np
import pandas as pd
from pyproj import Transformer

from .config import ARCHIVE_URL_METEO, VARIABLES_METEO


def utm_a_latlon(utm_dict):
    """Convierte {codigo: (este, norte)} UTM huso 18S → {codigo: (lat, lon)}."""
    t = Transformer.from_crs("EPSG:32718", "EPSG:4326", always_xy=True)
    coords = {}
    for codigo, (este, norte) in utm_dict.items():
        lon, lat = t.transform(este, norte)
        coords[codigo] = (round(lat, 4), round(lon, 4))
    return coords


def pedir_openmeteo(lat, lon, desde, hasta, variables=VARIABLES_METEO, reintentos=4):
    """Baja meteo horaria de una celda ERA5 y la devuelve como DataFrame."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": desde,
        "end_date": hasta,
        "hourly": ",".join(variables),
        "timezone": "America/Santiago",
    }
    for intento in range(reintentos):
        try:
            r = requests.get(ARCHIVE_URL_METEO, params=params, timeout=120)
            if r.status_code == 429:          # rate limit: esperar y reintentar
                time.sleep(10 * (intento + 1))
                continue
            r.raise_for_status()
            horario = r.json()["hourly"]
            df = pd.DataFrame(horario)
            df["timestamp"] = pd.to_datetime(df.pop("time"))
            return df
        except requests.RequestException as e:
            if intento == reintentos - 1:
                raise
            time.sleep(5 * (intento + 1))
    return None


def traer_meteo(estaciones, coordenadas, desde, hasta, variables=VARIABLES_METEO, carpeta_cache=None):
    """
    Descarga meteo para todas las estaciones, deduplicando por celda ERA5
    (~0.25°): estaciones que caen en la misma celda comparten una sola descarga.
    La descarga se hace año por año y se cachea en disco (carpeta_cache).
    """
    # 1. agrupar estaciones por celda (redondeo a la grilla)
    celdas = {}
    for codigo in estaciones:
        lat, lon = coordenadas[codigo]
        celda = (round(lat * 4) / 4, round(lon * 4) / 4)   # snap a 0.25°
        celdas.setdefault(celda, []).append(codigo)

    print(f"{len(estaciones)} estaciones → {len(celdas)} celdas ERA5 a descargar")

    # 2. descargar una vez por celda (por tramos anuales) y replicar a sus estaciones
    tablas = []
    for (clat, clon), codigos in celdas.items():
        print(f"Celda ({clat}, {clon}) — {len(codigos)} estaciones...", end=" ")
        base = pedir_por_tramos(clat, clon, desde, hasta, variables, carpeta_cache)
        print(f"{len(base):,} horas")
        for codigo in codigos:
            nombre, comuna = estaciones[codigo]
            t = base.copy()
            t["codigo"] = codigo
            t["estacion"] = nombre
            t["comuna"] = comuna
            tablas.append(t)

    return pd.concat(tablas, ignore_index=True)


def agregar_derivadas(meteo):
    """Componentes u/v del viento, variables de calendario y proxies de estancamiento."""
    meteo = meteo.copy()

    # viento como vector (promediar grados directamente está mal)
    rad = np.deg2rad(meteo["wind_direction_10m"])
    meteo["viento_u"] = -meteo["wind_speed_10m"] * np.sin(rad)
    meteo["viento_v"] = -meteo["wind_speed_10m"] * np.cos(rad)

    # calendario
    meteo["hora"] = meteo["timestamp"].dt.hour
    meteo["mes"] = meteo["timestamp"].dt.month
    meteo["anio"] = meteo["timestamp"].dt.year

    # proxies (heurísticos, ajustables)
    es_noche = (meteo["hora"] <= 7) | (meteo["hora"] >= 20)
    capa_baja = meteo["boundary_layer_height"] < 200          # metros
    viento_calmo = meteo["wind_speed_10m"] < 2                # m/s
    despejado = meteo["cloud_cover"] < 30                     # %

    meteo["proxy_estancamiento"] = (capa_baja & viento_calmo).astype(int)
    meteo["proxy_inversion"] = (es_noche & capa_baja & viento_calmo & despejado).astype(int)

    return meteo

def actualizar_meteo(estaciones, coordenadas, ruta_parquet, variables=VARIABLES_METEO,
                      carpeta_cache=None, retraso_dias=6, desde_default="2017-01-01"):
    """
    Descarga solo lo que falta desde la última fecha guardada en ruta_parquet
    y lo agrega (append + dedupe). Si el archivo no existe, hace la descarga
    completa desde desde_default.
    """
    existente = None
    if os.path.exists(ruta_parquet):
        existente = pd.read_parquet(ruta_parquet)
        desde = (existente["timestamp"].max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        desde = desde_default

    hasta = (pd.Timestamp.today() - pd.Timedelta(days=retraso_dias)).strftime("%Y-%m-%d")

    if pd.Timestamp(desde) > pd.Timestamp(hasta):
        print("Nada nuevo que traer")
        return existente

    print(f"Descargando meteo desde {desde} hasta {hasta}...")
    nuevos = traer_meteo(estaciones, coordenadas, desde, hasta, variables, carpeta_cache)

    if existente is not None:
        combinado = pd.concat([existente, nuevos], ignore_index=True)
        combinado = combinado.drop_duplicates(subset=["timestamp", "codigo"], keep="last")
        combinado = combinado.sort_values("timestamp").reset_index(drop=True)
    else:
        combinado = nuevos

    combinado.to_parquet(ruta_parquet, index=False)
    print(f"Guardado: {len(combinado):,} filas totales ({len(nuevos):,} descargadas en este run)")
    return combinado


def pedir_por_tramos(lat, lon, desde, hasta, variables=VARIABLES_METEO, carpeta_cache=None):
    """Pide año por año (peticiones chicas no hacen timeout) y guarda cada año completo en disco."""
    inicio, fin = pd.Timestamp(desde), pd.Timestamp(hasta)
    tramos = []
    for anio in range(inicio.year, fin.year + 1):
        d = max(inicio, pd.Timestamp(f"{anio}-01-01"))
        h = min(fin, pd.Timestamp(f"{anio}-12-31"))
        anio_completo = (h == pd.Timestamp(f"{anio}-12-31"))

        cache = None
        if carpeta_cache:
            cache = os.path.join(carpeta_cache, f"meteo_{lat}_{lon}_{anio}.parquet")
            if os.path.exists(cache):
                tramos.append(pd.read_parquet(cache))
                continue

        t = pedir_openmeteo(lat, lon, d.strftime("%Y-%m-%d"), h.strftime("%Y-%m-%d"), variables)
        if cache and anio_completo:      # el año en curso no se cachea: aún le faltan días
            t.to_parquet(cache, index=False)
        tramos.append(t)
        time.sleep(1)                    # cortesía con la API
    return pd.concat(tramos, ignore_index=True)