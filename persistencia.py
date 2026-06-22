import json
import os

def guardar_datos(datos):
    """Guarda las respuestas en un archivo JSON local."""
    archivo = "respuestas_prestadores.json"
    
    # Si el archivo ya existe, leemos lo que tiene
    if os.path.exists(archivo):
        with open(archivo, "r", encoding="utf-8") as f:
            try:
                lista_datos = json.load(f)
            except json.JSONDecodeError:
                lista_datos = []
    else:
        lista_datos = []
        
    # Agregamos el nuevo registro
    lista_datos.append(datos)
    
    # Volvemos a guardar todo de forma ordenada
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(lista_datos, f, ensure_ascii=False, indent=4)
    print(f"\n[SISTEMA] ¡Datos guardados con éxito en {archivo}!")
