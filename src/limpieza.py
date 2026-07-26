"""Reglas de limpieza del dataset de contaminantes."""
import pandas as pd
import numpy as np

from .config import UMBRAL_RUIDO_NEG, UMBRAL_SATURACION


def reindexar_gaps(df):
    """Inserta filas NaN en las horas sin medición (gaps explícitos)."""
    tablas = []
    for est, grupo in df.groupby("estacion"):
        grilla = pd.date_range(grupo["timestamp"].min(), grupo["timestamp"].max(), freq="h")
        g = grupo.set_index("timestamp").reindex(grilla)
        g.index.name = "timestamp"
        g["estacion"] = est
        g["comuna"] = grupo["comuna"].iloc[0]
        tablas.append(g.reset_index())
    return pd.concat(tablas, ignore_index=True)


def limpiar_negativos(df, columnas):
    """Negativos pequeños (ruido de sensor) → 0; negativos grandes (falla) → NaN."""
    df = df.copy()
    print("REPORTE DE LIMPIEZA DE NEGATIVOS")
    print("-" * 45)
    for col in columnas:
        mascara_ruido = (df[col] >= UMBRAL_RUIDO_NEG) & (df[col] < 0)
        mascara_falla = df[col] < UMBRAL_RUIDO_NEG
        print(f"  {col:6} | ruido → 0: {mascara_ruido.sum():6,} | falla → NaN: {mascara_falla.sum():3,}")
        df.loc[mascara_ruido, col] = 0
        df.loc[mascara_falla, col] = np.nan
    return df


def limpiar_saturados(df, columnas, umbral=UMBRAL_SATURACION):
    """Valores saturados (código de error / tope de instrumento) → NaN."""
    df = df.copy()
    print("\nREPORTE DE LIMPIEZA DE SATURADOS")
    print("-" * 45)
    for col in columnas:
        mascara_sat = df[col] >= umbral
        n_sat = mascara_sat.sum()
        print(f"  {col:6} | saturado → NaN: {n_sat:3,}")
        if n_sat > 0:
            print(df.loc[mascara_sat, ["timestamp", "estacion", col]].to_string(index=False))
        df.loc[mascara_sat, col] = np.nan
    return df


def limpiar_inconsistentes(df):
    """mp2.5 físicamente imposible (> 1.5x mp10 en valores altos) → NaN. Código 1985 en mp10 → NaN."""
    df = df.copy()
    print("\nREPORTE DE INCONSISTENCIAS FÍSICAS")
    print("-" * 45)
    mascara = (df["mp2.5"] > 500) & df["mp10"].notna() & (df["mp2.5"] > 1.5 * df["mp10"])
    print(f"  mp2.5 inconsistente → NaN: {mascara.sum()}")
    df.loc[mascara, "mp2.5"] = np.nan
    mascara_1985 = df["mp10"] == 1985.0
    print(f"  mp10 código 1985 → NaN: {mascara_1985.sum()}")
    df.loc[mascara_1985, "mp10"] = np.nan
    return df