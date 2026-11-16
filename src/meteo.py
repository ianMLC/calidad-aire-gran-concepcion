"""Descarga de meteorología horaria (Open-Meteo / ERA5) y variables derivadas."""
import os
import time
import requests
import numpy as np
import pandas as pd
from pyproj import Transformer


from .config import ARCHIVE_URL_METEO, VARIABLES_METEO, METEO_MODELO, METEO_CELDA

def utm_a_latlon(utm_dict):
    """Convierte {codigo: (este, norte)} UTM huso 18S → {codigo: (lat, lon)}."""
    t = Transformer.from_crs("EPSG:32718", "EPSG:4326", always_xy=True)
    coords = {}
    for codigo, (este, norte) in utm_dict.items():
        lon, lat = t.transform(este, norte)
        coords[codigo] = (round(lat, 4), round(lon, 4))
    return coords


def pedir_openmeteo(lat, lon, desde, hasta, variables=VARIABLES_METEO, reintentos=4, modelo=METEO_MODELO, celda=METEO_CELDA):
    """
        Baja meteo horaria para un punto y la devuelve como DataFrame.
        Agrega las columnas celda_lat, celda_lon y celda_elev: el centro de la celda de la
        grilla que Open-Meteo usó realmente (puede estar a unos km del punto pedido).
    """    
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": desde,
        "end_date": hasta,
        "hourly": ",".join(variables),
        "timezone": "America/Santiago",
        "cell_selection": celda,
    }
    if modelo: # None = "best_match" (por defecto de la API)
        params["models"] = modelo
        
    for intento in range(reintentos):
        try:
            r = requests.get(ARCHIVE_URL_METEO, params=params, timeout=120)
            if r.status_code == 429:          # rate limit: esperar y reintentar
                time.sleep(10 * (intento + 1))
                continue
            r.raise_for_status()
            js = r.json()
            df = pd.DataFrame(js.get("hourly"))
            df["timestamp"] = pd.to_datetime(df.pop("time"))
            df["celda_lat"] = js.get("latitude")
            df["celda_lon"] = js.get("longitude")
            df["celda_elev"] = js.get("elevation")
            return df
        except requests.RequestException as e:
            if intento == reintentos - 1:
                raise
            time.sleep(5 * (intento + 1))
    raise RuntimeError(f"Open-Meteo no respondió tras {reintentos} intentos ({lat}, {lon})")


def traer_meteo(estaciones, coordenadas, desde, hasta, variables=VARIABLES_METEO,
                carpeta_cache=None, modelo=METEO_MODELO, celda=METEO_CELDA):
    """
    Descarga meteo para cada estación en su coordenada exacta (sin agrupar en celdas).
    Si dos estaciones caen en la misma celda de la grilla, Open-Meteo devolverá la misma
    serie: eso queda registrado en celda_lat/celda_lon y lo mide informe_resolucion().
    """
    print(f"Descargando meteo para {len(estaciones)} estaciones "
          f"(modelo: {modelo or 'best_match'}, celda: {celda})")
    tablas = []
    for codigo, (nombre, comuna) in estaciones.items():
        lat, lon = coordenadas[codigo]
        print(f"  {nombre:25} ({lat}, {lon})...", end=" ")
        t = pedir_por_tramos(lat, lon, desde, hasta, variables, carpeta_cache, modelo, celda)
        t["codigo"] = codigo
        t["estacion"] = nombre
        t["comuna"] = comuna
        t["lat_estacion"] = lat
        t["lon_estacion"] = lon
        print(f"{len(t):,} horas · celda usada ({t['celda_lat'].iloc[0]}, {t['celda_lon'].iloc[0]})")
        tablas.append(t)
    return pd.concat(tablas, ignore_index=True)


def informe_resolucion(meteo, variables=("temperature_2m", "wind_speed_10m",
                                         "boundary_layer_height", "relative_humidity_2m")):
    """
    Mide si la meteorología distingue entre estaciones (entregable de T3).
    Devuelve un diccionario con tres tablas:
      - "estaciones": celda usada por cada estación, distancia al punto pedido y elevación
      - "celdas": qué estaciones comparten la misma celda (es decir, la misma serie)
      - "variables": cuán parecidas son las series entre estaciones, por variable
    """
    # 1. Celda usada por cada estación
    est = (meteo.groupby(["codigo", "estacion", "comuna"])
                [["lat_estacion", "lon_estacion", "celda_lat", "celda_lon", "celda_elev"]]
                .first().reset_index())
    # distancia (km) entre el punto pedido y el centro de la celda usada
    r = 6371.0
    la1, lo1 = np.radians(est["lat_estacion"]), np.radians(est["lon_estacion"])
    la2, lo2 = np.radians(est["celda_lat"]), np.radians(est["celda_lon"])
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    est["dist_celda_km"] = (2 * r * np.arcsin(np.sqrt(a))).round(2)
    est["id_celda"] = est.groupby(["celda_lat", "celda_lon"]).ngroup() + 1

    # 2. Estaciones que comparten celda
    celdas = (est.groupby("id_celda")
                 .agg(celda_lat=("celda_lat", "first"), celda_lon=("celda_lon", "first"),
                      elevacion=("celda_elev", "first"), n_estaciones=("estacion", "size"),
                      estaciones=("estacion", lambda s: ", ".join(sorted(s))))
                 .reset_index())

    # 3. Parecido entre series, por variable
    filas = []
    for v in variables:
        if v not in meteo.columns:
            continue
        ancho = meteo.pivot_table(index="timestamp", columns="estacion", values=v)
        corr = ancho.corr().to_numpy()
        fuera_diag = corr[~np.eye(len(corr), dtype=bool)]
        n_distintas = ancho.T.drop_duplicates().shape[0]   # series idénticas cuentan como una
        filas.append({"variable": v, "series_distintas": n_distintas,
                      "corr_mediana": round(float(np.nanmedian(fuera_diag)), 3),
                      "corr_minima": round(float(np.nanmin(fuera_diag)), 3)})
    variables_df = pd.DataFrame(filas)

    return {"estaciones": est.drop(columns=["codigo"]), "celdas": celdas, "variables": variables_df}


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


def pedir_por_tramos(lat, lon, desde, hasta, variables=VARIABLES_METEO, carpeta_cache=None,
                     modelo=METEO_MODELO, celda=METEO_CELDA):
    """Pide año por año (peticiones chicas no hacen timeout) y guarda cada año completo en disco."""
    inicio, fin = pd.Timestamp(desde), pd.Timestamp(hasta)
    etiqueta = f"{modelo or 'best_match'}_{celda}"   # si cambia el modelo, no se reusa el caché viejo
    tramos = []
    for anio in range(inicio.year, fin.year + 1):
        d = max(inicio, pd.Timestamp(f"{anio}-01-01"))
        h = min(fin, pd.Timestamp(f"{anio}-12-31"))
        anio_completo = (h == pd.Timestamp(f"{anio}-12-31"))

        cache = None
        if carpeta_cache:
            cache = os.path.join(carpeta_cache, f"meteo_{etiqueta}_{lat}_{lon}_{anio}.parquet")
            if os.path.exists(cache):
                tramos.append(pd.read_parquet(cache))
                continue

        t = pedir_openmeteo(lat, lon, d.strftime("%Y-%m-%d"), h.strftime("%Y-%m-%d"),
                            variables, modelo=modelo, celda=celda)
        if cache and anio_completo:      # el año en curso no se cachea: aún le faltan días
            t.to_parquet(cache, index=False)
        tramos.append(t)
        time.sleep(1)                    # cortesía con la API
    return pd.concat(tramos, ignore_index=True)