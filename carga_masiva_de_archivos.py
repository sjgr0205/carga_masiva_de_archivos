import os
import shutil
import oracledb
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import sys
from dotenv import load_dotenv

def obtener_ruta_base():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

ruta_env = os.path.join(obtener_ruta_base(), ".env")
load_dotenv(ruta_env)

print(oracledb.__path__)
oracledb.version

ARCHIVO_CONFIG = os.path.join(obtener_ruta_base(), os.getenv("ARCHIVO_CONFIG", "config.json"))
ORACLE_DSN = os.getenv("ORACLE_DSN")
ORACLE_USER = os.getenv("ORACLE_USER")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")
SQL_QUERY = os.getenv("SQL_QUERY")

def eliminar_ceros(cadena):
    """Elimina los ceros iniciales de una cadena."""
    ceros_eliminados = cadena.lstrip('0')
    return ceros_eliminados if ceros_eliminados else '0'

def cargar_rutas_guardadas():
    """Carga las rutas de archivo y carpeta desde un archivo JSON."""
    if os.path.exists(ARCHIVO_CONFIG):
        with open(ARCHIVO_CONFIG, "r") as archivo:
            try:
                return json.load(archivo)
            except json.JSONDecodeError:
                return {"documento_origen": "", "carpeta_destino": ""}
    return {"documento_origen": "", "carpeta_destino": ""}

def guardar_rutas(rutas):
    """Guarda las rutas de archivo y carpeta en un archivo JSON."""
    with open(ARCHIVO_CONFIG, "w") as archivo:
        json.dump(rutas, archivo, indent=4)

class DocumentProcessorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Selección de Documento y Carpeta")
        self.geometry("600x200")

        self.rutas_guardadas = cargar_rutas_guardadas()
        self.crear_widgets()

    def crear_widgets(self):
        """Crea y organiza los elementos de la interfaz gráfica."""
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(expand=True, fill="both")

        main_frame.columnconfigure(1, weight=1)

        tk.Label(main_frame, text="Documento Origen:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entrada_archivo_origen = tk.Entry(main_frame, width=50)
        self.entrada_archivo_origen.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.entrada_archivo_origen.insert(0, self.rutas_guardadas.get("documento_origen", ""))
        tk.Button(main_frame, text="Seleccionar Archivo", command=self.seleccionar_archivo).grid(row=0, column=2, padx=5, pady=5)

        tk.Label(main_frame, text="Carpeta Destino:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entrada_carpeta_destino = tk.Entry(main_frame, width=50)
        self.entrada_carpeta_destino.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.entrada_carpeta_destino.insert(0, self.rutas_guardadas.get("carpeta_destino", ""))
        tk.Button(main_frame, text="Seleccionar Carpeta", command=self.seleccionar_carpeta).grid(row=1, column=2, padx=5, pady=5)

        tk.Button(main_frame, text="Siguiente", command=self.procesar_documento, bg="green", fg="white").grid(row=2, column=1, padx=5, pady=15, sticky="e")

    def seleccionar_archivo(self):
        archivo = filedialog.askopenfilename(title="Seleccionar archivo")
        if archivo:
            self.entrada_archivo_origen.delete(0, tk.END)
            self.entrada_archivo_origen.insert(0, archivo)

    def seleccionar_carpeta(self):
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if carpeta:
            self.entrada_carpeta_destino.delete(0, tk.END)
            self.entrada_carpeta_destino.insert(0, carpeta)

    def procesar_documento(self):
        documento_origen = self.entrada_archivo_origen.get()
        carpeta_destino = self.entrada_carpeta_destino.get()

        if not documento_origen or not carpeta_destino:
            messagebox.showerror("Error", "Debe seleccionar un documento de origen y una carpeta de destino.")
            return

        if not os.path.isfile(documento_origen):
            messagebox.showerror("Error", "El archivo seleccionado no existe.")
            return

        if not os.path.isdir(carpeta_destino):
            messagebox.showerror("Error", "La carpeta de destino seleccionada no existe.")
            return

        rutas = {"documento_origen": documento_origen, "carpeta_destino": carpeta_destino}
        guardar_rutas(rutas)

        self.ejecutar_logica_negocio(documento_origen, carpeta_destino)

    def ejecutar_logica_negocio(self, documento_origen, carpeta_destino):
        try:
            with oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN) as conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(SQL_QUERY)
                    carpetas_base_datos = [eliminar_ceros(fila[0]) for fila in cursor]

            nombre_archivo_origen = os.path.basename(documento_origen)
            carpetas_con_archivo_existente = []

            for carpeta in carpetas_base_datos:
                ruta_carpeta_destino = os.path.join(carpeta_destino, carpeta)
                os.makedirs(ruta_carpeta_destino, exist_ok=True)

                nombre_archivo_destino = os.path.join(ruta_carpeta_destino, f"{carpeta} {nombre_archivo_origen}")

                if os.path.exists(nombre_archivo_destino):
                    carpetas_con_archivo_existente.append(carpeta)
                else:
                    shutil.copy(documento_origen, nombre_archivo_destino)

            self.crear_archivo_log(carpetas_con_archivo_existente)

        except oracledb.DatabaseError as e:
            messagebox.showerror("Error de conexión a la base de datos", str(e))
        except OSError as e:
            messagebox.showerror("Error de sistema", f"Ocurrió un error de sistema: {e}")
        except Exception as e:
            messagebox.showerror("Error inesperado", f"Ocurrió un error inesperado: {e}")

    def crear_archivo_log(self, carpetas_con_archivo_existente):
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nombre_archivo_txt = os.path.join(obtener_ruta_base(), f"log_archivos_existentes_{fecha_actual}.txt")

        with open(nombre_archivo_txt, "w") as archivo:
            if not carpetas_con_archivo_existente:
                archivo.write("El archivo se copió en todas las carpetas sin problemas.\n")
            else:
                archivo.write("Carpetas donde ya existía el archivo y no fue copiado:\n")
                for carpeta in carpetas_con_archivo_existente:
                    archivo.write(f"- {carpeta}\n")

        messagebox.showinfo("Proceso completado", f"El proceso ha finalizado. Se ha creado el archivo de registro '{nombre_archivo_txt}'.")

if __name__ == "__main__":
    app = DocumentProcessorApp()
    app.mainloop()