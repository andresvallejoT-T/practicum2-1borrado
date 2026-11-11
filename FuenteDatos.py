class FuenteDatos:
    def __init__(self, origen, licencia, formato, fecha, version):
        self.origen = origen
        self.licencia = licencia
        self.formato = formato
        self.fecha = fecha
        self.version = version

    def registrar_fuente(self):
        # Lógica para registrar la fuente en la base de datos
        pass
    
    def consultar_metadatos(self):
        # Devuelve la información de procedencia, licencia, etc.
        pass