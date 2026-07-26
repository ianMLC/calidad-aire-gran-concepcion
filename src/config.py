
# Umbrales episodios MP2.5 (DS 12/2011, promedio 24h)
UMBRALES_EPISODIO = {"Regular": 50, "Alerta": 80, "Preemergencia": 110, "Emergencia": 170}

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
    "860": ("Lota urbana", "Coronel"),
    "805": ("Bocatoma", "Hualpen"),
    "838": ("ENAP Price", "Hualpen"),
    "804": ("JUNJI", "Hualpen"),
    "841": ("Hualqui", "Hualqui"),
    "802": ("Consultorio San Vicente", "Talcahuano"),
    "807": ("Indura", "Talcahuano"),
    "806": ("Inpesca", "Talcahuano"),
}


#verificar coordenadas UTM de las estaciones, para poder graficarlas en un mapa
UTM_ESTACIONES = {
    "854": (674923, 5911833),   # Punteras, Chiguayante        - V
    "827": (673817, 5927247),   # Kingston College, Concepcion - V
    "831": (663500, 5905000),   # Cerro Merquin, Coronel       - A
    "878": (664000, 5915000),   # Coronel Norte, Coronel       - A
    "880": (662500, 5903000),   # Escuadron ENEL, Coronel      - A
    "881": (662400, 5902800),   # Escuadron ENESA, Coronel     - A
    "879": (663000, 5904000),   # Lagunillas ENEL, Coronel     - A
    "859": (664500, 5895000),   # Lota rural, Coronel          - A
    "860": (664200, 5894500),   # Lota urbana, Coronel         - A
    "805": (669000, 5931000),   # Bocatoma, Hualpen            - A
    "838": (668500, 5930500),   # ENAP Price, Hualpen          - A
    "804": (669500, 5931500),   # JUNJI, Hualpen               - A
    "841": (682000, 5910000),   # Hualqui, Hualqui             - A
    "802": (668000, 5933000),   # Consultorio San Vicente, Talcahuano - A
    "807": (670000, 5932000),   # Indura, Talcahuano           - A
    "806": (669000, 5932500),   # Inpesca, Talcahuano          - A
}

