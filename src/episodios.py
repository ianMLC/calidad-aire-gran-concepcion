## clasificar agregar_diario, calcular_cuenta
"""Agregación diaria y clasificación de episodios MP2.5 (DS 12/2011)."""
import pandas as pd
import numpy as np

from .config import UMBRALES_EPISODIO, HORAS_MIN_DIA_VALIDO


def clasificar(v):
    """Clasifica un promedio 24h de MP2.5 según norma chilena."""
    if pd.isna(v):
        return np.nan
    if v < UMBRALES_EPISODIO["Regular"]:
        return "Bueno"
    if v < UMBRALES_EPISODIO["Alerta"]:
        return "Regular"
    if v < UMBRALES_EPISODIO["Preemergencia"]:
        return "Alerta"
    if v < UMBRALES_EPISODIO["Emergencia"]:
        return "Preemergencia"
    return "Emergencia"


def agregar_diario(df):
    """Promedio diario de MP2.5 por estación. Solo días con >= 18h medidas."""
    df = df.copy()
    df["fecha"] = df["timestamp"].dt.floor("D")

    diario = df.groupby(["fecha", "estacion", "comuna"]).agg(
        mp25=("mp2.5", "mean"),
        n_horas=("mp2.5", "count"),
    ).reset_index()

    diario["valido"] = diario["n_horas"] >= HORAS_MIN_DIA_VALIDO
    diario = diario[diario["valido"]].copy()
    diario["episodio"] = diario["mp25"].apply(clasificar)
    return diario


def calcular_cuenca(diario):
    """Episodio de cuenca: máximo entre estaciones cada día (fix idxmax)."""
    idx = diario.groupby("fecha")["mp25"].idxmax()
    cuenca = diario.loc[idx, ["fecha", "estacion", "comuna", "mp25"]].rename(
        columns={"mp25": "mp25_max", "estacion": "estacion_max", "comuna": "comuna_max"}
    )
    n_est = diario.groupby("fecha").size().rename("n_estaciones").reset_index()
    cuenca = cuenca.merge(n_est, on="fecha").reset_index(drop=True)
    cuenca["episodio"] = cuenca["mp25_max"].apply(clasificar)
    return cuenca