# Calidad del Aire — Gran Concepción

Pipeline de datos y análisis de MP2.5 en el Gran Concepción (Chile),
a partir de datos públicos de SINCA (2017-2026). Base para un modelo
de predicción de episodios críticos de contaminación.

## Datos
- Fuente: SINCA (sinca.mma.gob.cl), Ministerio del Medio Ambiente
- 16 estaciones, 6 comunas, 8 contaminantes, resolución horaria
- ~8M registros horarios crudos (2011-2026); análisis sobre 2017-2026
- ~1.2M registros (2017-2026)

## Estructura
- `src/config.py` — estaciones, contaminantes, umbrales
- `src/sinca.py` — cliente de descarga SINCA
- `src/limpieza.py` — reglas de limpieza (negativos, saturación, consistencia física, gaps)
- `src/episodios.py` — agregación diaria y clasificación según DS 12/2011
- `notebooks/` — pipeline en orden: 01 descarga → 02 limpieza → 03 análisis

## Uso
1. Crear entorno e instalar dependencias:
```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
```
2. Correr `notebooks/01_descarga.ipynb` (genera `data/crudo.parquet`, ~20-40 min la primera vez; después carga del archivo en segundos)
3. Correr `notebooks/02_limpieza.ipynb` (genera `data/dataset_limpio.parquet`)
4. Correr `notebooks/03_analisis.ipynb` (episodios, estacionalidad, mapas)

Los datos no se versionan; se regeneran con los notebooks.

## Hallazgos preliminares (2017 – jul 2026)
- 420 días con episodio crítico (Alerta o superior) a nivel de cuenca
- Coronel Norte gatilla más de la mitad de las emergencias
- Fuerte estacionalidad: episodios concentrados en mayo-agosto
- El panel es desbalanceado: 4 estaciones (Coronel Norte, ENEL/ENESA) inician entre 2019 y 2021