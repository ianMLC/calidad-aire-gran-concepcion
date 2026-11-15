
# Umbrales episodios MP2.5 (DS 12/2011, promedio 24h)
UMBRALES_EPISODIO = {"Regular": 50, "Alerta": 80, "Preemergencia": 110, "Emergencia": 170}
ARCHIVE_URL_METEO = "https://archive-api.open-meteo.com/v1/archive"


# Limpieza
UMBRAL_RUIDO_NEG = -2
UMBRAL_SATURACION = 1990
HORAS_MIN_DIA_VALIDO = 18

# Contaminantes que queremos traer, con su código SINCA
# nombre_legible: codigo_sinca
CONTAMINANTES = {
    "mp2.5": "PM25",
    "mp10":  "PM10",
    "so2":   "0001",
    "no":    "0002",
    "no2":   "0003",
    "co":    "0004",
    "o3":    "0008",
    "nox":   "0NOX",
}


BASE_URL = "https://sinca.mma.gob.cl/cgi-bin/APUB-MMA/apub.tsindico2.cgi"

# Estaciones del gran concepción que miden MP2,5  -> despues podria medir para toda la region
# codigo: (nombre, comuna)

ESTACIONES = {
    "854": ("Punteras", "Chiguayante"),
    "827": ("Kingston College", "Concepcion"),
    "831": ("Cerro Merquin", "Coronel"),
    "878": ("Coronel Norte", "Coronel"),
    "880": ("Escuadron ENEL", "Coronel"),
    "881": ("Escuadron ENESA", "Coronel"),
    "879": ("Lagunillas ENEL", "Coronel"),
    "859": ("Lota rural", "Coronel"),
    "860": ("Lota urbana", "Lota"),
    "805": ("Bocatoma", "Hualpen"),
    "838": ("ENAP Price", "Hualpen"),
    "804": ("JUNJI", "Hualpen"),
    "841": ("Hualqui", "Hualqui"),
    "802": ("Consultorio San Vicente", "Talcahuano"),
    "807": ("Indura", "Talcahuano"),
    "806": ("Inpesca", "Talcahuano"),
}

# Red a la que pertenece cada estación (fuente: SINCA, campos "calificacion" y "empresa")
# publica = red del MMA, la que usa la autoridad para declarar episodios
# privada = estación de empresa, instalada por exigencia de su permiso ambiental
RED_ESTACIONES = {
    "854": ("publica", "MMA"),       # Punteras
    "827": ("publica", "MMA"),       # Kingston College
    "831": ("publica", "MMA"),       # Cerro Merquín
    "841": ("publica", "MMA"),       # Hualqui
    "802": ("publica", "MMA"),       # Consultorio San Vicente
    "878": ("privada", "Colbún"),    # Coronel Norte
    "879": ("privada", "ENEL"),      # Lagunillas ENEL
    "880": ("privada", "ENEL"),      # Escuadrón ENEL
    "859": ("privada", "ENEL"),      # Lota rural
    "860": ("privada", "ENEL"),      # Lota urbana
    "881": ("privada", "ENESA"),     # Escuadrón ENESA
    "804": ("privada", "ENAP"),      # JUNJI
    "805": ("privada", "ENAP"),      # Bocatoma
    "838": ("privada", "ENAP"),      # ENAP Price
    "806": ("privada", "ENAP"),      # Inpesca
    "807": ("privada", "ENAP"),      # Indura
}

ESTACIONES_PUBLICAS = [c for c, (red, _) in RED_ESTACIONES.items() if red == "publica"]


# Coordenadas oficiales SINCA (listadomapa2k19), UTM WGS84 huso 18S
UTM_ESTACIONES = {
    "854": (674922, 5911832),   # Punteras, Chiguayante
    "827": (673817, 5927247),   # Kingston College, Concepción
    "831": (664608, 5901177),   # Cerro Merquín, Coronel
    "878": (664675, 5902525),   # Coronel Norte, Coronel
    "879": (664411, 5905243),   # Lagunillas ENEL, Coronel
    "880": (664672, 5908597),   # Escuadrón ENEL, Coronel
    "881": (664516, 5910896),   # Escuadrón ENESA, Coronel
    "859": (663884, 5892366),   # Lota rural, Lota
    "860": (664078, 5894923),   # Lota urbana, Lota
    "804": (668151, 5927806),   # JUNJI, Hualpén
    "805": (667667, 5925330),   # Bocatoma, Hualpén
    "838": (667815, 5926637),   # ENAP Price, Hualpén
    "841": (684066, 5905633),   # Hualqui, Hualqui
    "802": (667560, 5934137),   # Consultorio San Vicente, Talcahuano
    "806": (669248, 5932605),   # Inpesca, Talcahuano
    "807": (668348, 5929004),   # Indura, Talcahuano
}

VARIABLES_METEO = [
    "boundary_layer_height", "temperature_2m", "relative_humidity_2m",
    "dew_point_2m", "precipitation", "wind_speed_10m", "wind_speed_100m",
    "wind_direction_10m", "surface_pressure", "cloud_cover", "shortwave_radiation",
]