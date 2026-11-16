# Registro de decisiones: estaciones (T2) y meteorología (T3)

**Proyecto:** Predicción de episodios críticos de MP2.5 en el Gran Concepción
**Fecha:** 15 de noviembre de 2026
**Tareas de la Carta Gantt:** T2 (Adquisición, depuración y clasificación SINCA) y T3 (Georreferenciación y capa meteorológica)

Este documento registra qué se corrigió, por qué y qué se decidió, para poder justificarlo en la tesis y reproducirlo.

---

## 1. Coordenadas de las estaciones

### Problema

14 de las 16 coordenadas de `UTM_ESTACIONES` eran aproximadas (marcadas "A" en el código). Al dibujarlas en un mapa aparecieron errores evidentes: Coronel Norte caía en el mar y las tres estaciones de Hualpén aparecían dentro de la comuna de Talcahuano.

### Solución

Se obtuvieron las coordenadas oficiales desde el listado de estaciones que usa el mapa de SINCA:

```
https://sinca.mma.gob.cl/index.php/json/listadomapa2k19/
```

Se convirtieron a UTM WGS84 huso 18S y se verificó, cruzándolas con los límites comunales, que **las 16 estaciones caen dentro de su comuna**.

### Magnitud del error corregido

| Estación | Error de la coordenada antigua |
|---|---|
| Coronel Norte | 12,5 km |
| Escuadrón ENESA | 8,4 km |
| Escuadrón ENEL | 6,0 km |
| Bocatoma | 5,8 km |
| Hualqui | 4,8 km |
| Cerro Merquín | 4,0 km |
| JUNJI | 3,9 km |
| ENAP Price | 3,9 km |
| Indura | 3,4 km |
| Lota rural | 2,7 km |
| Lagunillas ENEL | 1,9 km |
| Consultorio San Vicente | 1,2 km |
| Lota urbana | 0,4 km |
| Inpesca | 0,3 km |
| Punteras | 0,0 km (ya estaba verificada) |
| Kingston College | 0,0 km (ya estaba verificada) |

**Consecuencia:** toda la meteorología descargada antes de esta corrección se pidió en ubicaciones equivocadas y debe descargarse de nuevo (ver sección 4).

---

## 2. Comuna de Lota rural

### Problema

En `config.py`, la estación Lota rural (859) estaba asignada a la comuna de **Coronel**.

### Por qué ocurrió

SINCA registra las dos estaciones de Lota (rural y urbana) en la comuna de "Coronel", porque pertenecen a la red **ENEL Coronel**. Es decir, SINCA usa el nombre de la red y no la ubicación geográfica. Al revisar el config se había corregido Lota urbana, pero Lota rural quedó con el dato de SINCA.

Con las coordenadas oficiales (-37,10; -73,16) se verificó que **Lota rural está dentro de la comuna de Lota**.

### Corrección

1. En `src/config.py`:
   ```python
   "859": ("Lota rural", "Lota"),
   ```
2. La columna `comuna` de los datos se escribe al descargar desde SINCA, copiando el config de ese momento. Por eso `crudo.parquet` seguía diciendo "Coronel" aunque se corrigiera el config.
   Para no volver a descargar, en `notebooks/02_limpieza.ipynb` la comuna **se reasigna siempre desde el config** al cargar el crudo:
   ```python
   comuna_de = {nombre: comuna for nombre, comuna in ESTACIONES.values()}
   datos["comuna"] = datos["estacion"].map(comuna_de)
   ```
3. Se regeneró `dataset_limpio.parquet`.

**Regla adoptada:** `config.py` es la única fuente de verdad para nombre, comuna, coordenadas y red de cada estación.

---

## 3. Red pública y red privada

### Hallazgo

El listado de SINCA indica quién opera cada estación (campos `calificacion` y `empresa`):

| Red | Operador | Estaciones |
|---|---|---|
| Pública | Ministerio del Medio Ambiente | Punteras, Kingston College, Cerro Merquín, Hualqui, Consultorio San Vicente |
| Privada | ENAP | JUNJI, Bocatoma, ENAP Price, Inpesca, Indura |
| Privada | ENEL | Lagunillas, Escuadrón ENEL, Lota rural, Lota urbana |
| Privada | Colbún | Coronel Norte |
| Privada | ENESA | Escuadrón ENESA |

Las estaciones privadas las instalan las empresas, normalmente por exigencia de su permiso ambiental, para medir el impacto de su operación. Sus datos se reportan a SINCA igual que los de la red pública.

### Por qué importa

- La autoridad declara los episodios para toda la zona saturada usando la **red pública de 6 estaciones** (Plan Operacional GEC 2026). Son las 5 públicas de nuestro dataset **más Liceo Polivalente de Tomé (830)**, que no está incluida.
- En el dataset 2017-2026, las estaciones privadas concentran cerca del **83% de los días-estación críticos**. Solo JUNJI, Coronel Norte e Inpesca suman cerca del 72%.

### Decisión

Se registró la red de cada estación en `config.py` (`RED_ESTACIONES` y `ESTACIONES_PUBLICAS`) para poder filtrar en cualquier etapa. Queda pendiente decidir con el equipo:

- si el análisis principal usa las 16 estaciones (lo que establece el anteproyecto), solo la red pública, o ambas como comparación;
- si se agrega la estación de Tomé (830) para completar la red pública.

---

## 4. Meteorología (T3)

### 4.1 Problema

El proyecto compara modelos para toda la cuenca con modelos por sub-zona y por estación. Para que esa comparación tenga sentido, cada estación debería recibir **su propio clima**. La meteorología descargada tenía tres problemas:

1. **Coordenadas equivocadas:** se pidió con las coordenadas aproximadas (sección 1).
2. **El código agrupaba estaciones:** `traer_meteo` redondeaba cada estación a una cuadrícula de 0,25° (unos 25 km) y descargaba una sola serie por cuadro. Las 16 estaciones quedaban en 2 o 3 cuadros, así que muchas recibían **exactamente la misma serie**.
3. **La fuente tiene resolución limitada:** los modelos meteorológicos dividen el territorio en cuadros de varios kilómetros. Estaciones cercanas pueden caer en el mismo cuadro aunque se pida la coordenada exacta.

Si todas las estaciones reciben el mismo clima, un modelo local no puede aprender nada meteorológico propio de su zona, lo que limita la conclusión principal del proyecto. El anteproyecto reconoce este riesgo (sección 3.3) y pide un "informe de resolución espacial" como entregable de T3.

### 4.2 Fuente de los datos

Los datos se obtienen con la **Historical Weather API de Open-Meteo**. Open-Meteo es el servicio que entrega los datos; los datos provienen de modelos del ECMWF:

| Modelo | Resolución | Disponible desde |
|---|---|---|
| ECMWF IFS HRES | 9 km | 2017 |
| ERA5 | 0,25° (~25 km) | 1940 |
| ERA5-Land | 0,1° (~9-11 km) | 1950 |

Con el modo por defecto (`best_match`), Open-Meteo combina estos tres modelos y elige el de mayor resolución disponible. Como el período del proyecto parte en 2017, se espera que la mayor parte de los datos provenga del IFS de 9 km.

Cada respuesta de la API informa el **centro de la celda de la grilla que se usó**, que puede estar a algunos kilómetros del punto pedido, y su elevación.

### 4.3 Decisiones

**Modelo: `best_match`** (`METEO_MODELO = None` en el config)

| Opción | Ventaja | Desventaja |
|---|---|---|
| `best_match` (elegida) | Mayor resolución: lo que más ayuda a distinguir estaciones | Mezcla de modelos; no se sabe cuál se usó en cada momento |
| `era5` | Una sola fuente, consistente en todo el período | 25 km: las estaciones quedarían casi todas con el mismo clima |
| `era5_land` | ~9 km | No trae viento ni precipitación propios; el viento es clave para los episodios |

Open-Meteo recomienda ERA5 o ERA5-Land para estudios de cambio climático de varias décadas. Este proyecto no estudia tendencias de largo plazo: necesita distinguir estaciones dentro de 2017-2026, por lo que se prioriza la resolución. En la metodología se declara como: *"Open-Meteo Historical Weather API, modo best_match (ECMWF IFS 9 km desde 2017, complementado con ERA5/ERA5-Land)"*.

Si el informe de resolución muestra que el clima casi no varía entre estaciones, se evaluará comparar contra `era5`.

**Selección de celda: `land`** (`METEO_CELDA = "land"` en el config)

Open-Meteo busca una celda de tierra con elevación similar al punto pedido. Se elige porque varias estaciones están en la costa (Talcahuano, Coronel, Lota) y, con la celda más cercana, podrían quedar asociadas a un cuadro sobre el mar.

### 4.4 Cambios en el código (en implementación)

Se aplican archivo por archivo, probando cada uno:

1. **`src/config.py`** ✅: fuente documentada, `METEO_MODELO`, `METEO_CELDA` y corrección de Lota rural.
2. **`requirements.txt`**: agregar `openpyxl` para exportar el informe a Excel.
3. **`src/meteo.py`**:
   - pedir el clima en la coordenada exacta de cada estación, sin agrupar en cuadros de 0,25°;
   - guardar la celda que usó Open-Meteo (`celda_lat`, `celda_lon`, `celda_elev`) y la coordenada pedida (`lat_estacion`, `lon_estacion`);
   - detectar si la meteorología guardada es del formato antiguo o de otras coordenadas, renombrarla a `*_obsoleto.parquet` y descargar de nuevo;
   - nueva función `informe_resolucion()`.
4. **`notebooks/03_meteo.ipynb`**: documentar la fuente, generar el informe de resolución y guardarlo en `data/informes/informe_resolucion_meteo.xlsx`.

### 4.5 Cómo leer el informe de resolución

El informe tiene tres tablas:

- **Estaciones:** qué celda usó cada estación, a cuántos kilómetros quedó del punto pedido y su elevación.
- **Celdas:** qué estaciones comparten celda. Las estaciones de una misma celda reciben **la misma serie de clima**.
- **Variables:** cuán parecidas son las series entre estaciones (correlación entre pares) para temperatura, viento, altura de capa límite y humedad.

Interpretación:

- Si hay varias celdas distintas y correlaciones claramente menores que 1, la meteorología **sí distingue** entre estaciones o zonas.
- Si casi todas las estaciones comparten celda o las correlaciones son cercanas a 1, la meteorología **no distingue** entre estaciones. No es una falla: se reporta como **condicionante del estudio**, como prevé el anteproyecto. En ese caso, las diferencias entre modelos locales vendrían principalmente de la historia de MP2.5 de cada estación.

---

## 5. Pendientes

- [ ] Terminar de aplicar los cambios de T3 (requirements, `meteo.py`, notebook 03).
- [ ] Descargar la meteorología por estación y generar el informe de resolución.
- [ ] Interpretar el informe y redactar el párrafo de resolución espacial para la tesis.
- [ ] Decidir con el equipo: 16 estaciones, solo red pública o ambas.
- [ ] Decidir si se agrega la estación de Tomé (830).
- [ ] Cerrar T1: congelar las sub-zonas y completar el documento de esquema predictivo.

---

## Fuentes

- SINCA, listado de estaciones: <https://sinca.mma.gob.cl/index.php/json/listadomapa2k19/>
- Open-Meteo, Historical Weather API: <https://open-meteo.com/en/docs/historical-weather-api>
- Open-Meteo, integración de ECMWF IFS 9 km desde 2017: <https://openmeteo.substack.com/p/processing-90-tb-historical-weather>
- Ministerio del Medio Ambiente, Plan Operacional GEC Concepción Metropolitano 2026: <https://ppda.mma.gob.cl/wp-content/uploads/2026/04/PLAN-OPERACIONAL_GEC_CM_2026.pdf>
