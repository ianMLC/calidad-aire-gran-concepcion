"""Cliente para descargar datos desde SINCA (sinca.mma.gob.cl)."""
import os
import requests
import pandas as pd

from .config import BASE_URL


def pedir_sinca(region,estacion_cod, parametro, desde, hasta):
    """
    Pide datos a SINCA y devuelve en texto crudo.
        - region: codigo de region (ej: bio bio -> RVIII)
        - estadion_cod : Código de la estacion (ej: "827" para Kingston College)
        - parametro: que medir (ej: "PM25", para MP2,5)
        - desde, hasta: fechas en formato AAMMDD (ej: "240101" => 1 enero 2024)

        sinca response => 240101;0100;23;;;
            - 240101 => 1 de enero 2024
            - 0100   => 01:00 hora 
            - 23;;     => 23 µg/m³ de MP2,5
             │ │ │
             │ │ └─ posición 3: NO validado
             │ └─── posición 2: preliminar
             └───── posición 1: validado
    """
    params = {
        "outtype": "xcl", # fromato de salida (texto/CSV)
        "macro": f"./{region}/{estacion_cod}/Cal/{parametro}/{parametro}.horario.horario.ic",
        "from": desde,
        "to": hasta,
        "path": "/usr/airviro/data/CONAMA/",
        "lang": "esp"
    }
    respuesta = requests.get(BASE_URL, params = params, timeout = 60)
    return respuesta.text


def parsear_sinca(texto):
    """
    Convierte el texto crudo de SINCA en un tabla (dataframe).
    columnas de salida: timestamp, valor, estado
    """
    estados = ["validado","preliminar","no_validado"]
    filas = []
    
    for linea in texto.splitlines()[1:]:
        if not linea.strip():
            continue # saltamos las lineas vacias

        campos = linea.split(";")
        
        if len(campos) < 3:
            continue # saltamos linea incompleta

        fecha = campos[0].strip() # ej: "240101"
        hora = campos[1].strip()  # ej: "0100"
        timestamp = pd.to_datetime(fecha + hora[:2], format="%y%m%d%H")
        
        #buscamos el valor en las 3 posiciones posibles 2,3,4
        valor = None
        estado = None

        for i, nombre_estado in enumerate(estados):
            pos = 2 + i
            if pos < len(campos) and campos[pos].strip():
                valor = float(campos[pos].replace(",", "."))  # valor = float(campos[pos])
                estado = nombre_estado
                break

        if valor is None:
            continue #la hora no tenia medicion
    
        filas.append({"timestamp": timestamp, "valor": valor, "estado": estado})
    
    df = pd.DataFrame(filas)
    return df


def traer_estaciones(estaciones, contaminantes, desde, hasta, region="RVIII"):
    """
    Recorre un diccionario de estaciones, pide cada una a SINCA,
    le agrega nombre/comuna, y junta todo en una sola tabla.
    """
    tablas = []

    for codigo, (nombre, comuna) in estaciones.items():
        for nombre_cont, codigo_cont in contaminantes.items():   # NUEVO: bucle de contaminantes

            print(f"Trayendo {nombre} / {nombre_cont}...", end=" ")
        
            # pedir y parsear (reusamos las funciones que ya hicimos)
            texto = pedir_sinca(region, codigo, codigo_cont, desde, hasta)
            tabla = parsear_sinca(texto)

            if tabla is None or len(tabla) == 0:
                print("sin datos")
                continue

            # agregar de qué estación es cada fila
            tabla["codigo"] = codigo
            tabla["estacion"] = nombre
            tabla["comuna"] = comuna
            tabla["parametro"] = nombre_cont

            tablas.append(tabla)
            print(f"{len(tabla)} registros")

    # juntar todas las tablas en una sola
    if not tablas:
        return None
    return pd.concat(tablas, ignore_index=True)


def actualizar_estaciones(estaciones, contaminantes, ruta_parquet, region="RVIII", dias_solape=3):
    """
    Descarga solo lo que falta desde la última fecha guardada en ruta_parquet
    y lo agrega (append + dedupe). Si el archivo no existe, hace la descarga
    completa desde 2011.

    - dias_solape: re-pide los últimos N días ya guardados, porque SINCA puede
      revalidar un dato de "no_validado"/"preliminar" a "validado" más tarde.
    """
    existente = None
    if os.path.exists(ruta_parquet):
        existente = pd.read_parquet(ruta_parquet)
        desde = (existente["timestamp"].max() - pd.Timedelta(days=dias_solape)).strftime("%y%m%d")
    else:
        desde = "110101"

    hasta = pd.Timestamp.today().strftime("%y%m%d")

    print(f"Descargando SINCA desde {desde} hasta {hasta}...")
    nuevos = traer_estaciones(estaciones, contaminantes, desde, hasta, region)

    if nuevos is None or len(nuevos) == 0:
        print("Nada nuevo que traer")
        return existente

    if existente is not None:
        combinado = pd.concat([existente, nuevos], ignore_index=True)
        combinado = combinado.drop_duplicates(subset=["timestamp", "codigo", "parametro"], keep="last")
        combinado = combinado.sort_values("timestamp").reset_index(drop=True)
    else:
        combinado = nuevos

    combinado.to_parquet(ruta_parquet, index=False)
    print(f"Guardado: {len(combinado):,} filas totales ({len(nuevos):,} descargadas en este run)")
    return combinado
