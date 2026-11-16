"""
Núcleo de Diagnóstico - Sistema de gestión clínica (rediseño integral)
Interfaz gráfica en Tkinter conectada a PostgreSQL (el mismo servidor de pgAdmin 4).

Flujo del programa (igual que antes):
    1. Login (usuario y contraseña de un rol de PostgreSQL).
    2. Ventana principal: barra lateral + barra superior + panel de inicio.
    3. RECEPCIONISTAS -> Registrar recepcionista / Consultas generales
    4. DOCTORES       -> Registrar doctor         / Consultas generales

Requisitos:   pip install psycopg2-binary pillow
Imagen:       guarda tu foto junto a este archivo como imagen_nucleo.jpg (o .jpeg/.png).
                Si no hay imagen, se dibuja una ilustración de respaldo.
Teclas:       Enter = iniciar sesión | F11 = pantalla completa | Esc = salir (en el login)

ORGANIZACIÓN DEL ARCHIVO
    1. Configuración y sistema de diseño (colores, tipografía, espaciados)
    2. Entidades (tablas) y su SQL empotrado        <- la lógica de datos NO cambió
    3. Validación y utilidades                      <- convertir(), codigo_error(), ...
    4. Componentes visuales reutilizables           <- Icono, Boton, CampoFormulario, ...
    5. Aplicación (pantallas y acciones)            <- clase App
"""
import os
import tkinter as tk
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from tkinter import ttk

# Funciona con psycopg (versión 3) o con psycopg2, el que tengas instalado
try:
    import psycopg as pg
except ImportError:
    import psycopg2 as pg

# Pillow es opcional: solo se necesita para usar una foto como imagen principal
try:
    from PIL import Image, ImageOps, ImageTk
    HAY_PIL = True
except ImportError:
    HAY_PIL = False

# ====================================================================
# 1. CONFIGURACIÓN Y SISTEMA DE DISEÑO
# ====================================================================
# --- Datos del servidor (los mismos que ves en pgAdmin 4) ---
HOST = "localhost"
PUERTO = 5432
BASE_DE_DATOS = "Nucleo_De_Diagnostico"
NOMBRE_APP = "Nucleo_Diagnostico_GUI"   # aparece en pg_stat_activity (sirve para comprobar el login)

# --- Paleta: azul médico (principal) + verde azulado (secundario) ---
PRIMARIO = "#1366b8"
PRIMARIO_HOVER = "#0f56a0"
PRIMARIO_PRESS = "#0c4783"
PRIMARIO_SUAVE = "#e7f0fa"
SECUNDARIO = "#0f766e"
SECUNDARIO_HOVER = "#0c5f58"
SECUNDARIO_PRESS = "#0a4f49"
SECUNDARIO_SUAVE = "#e0f2f1"
ACENTO = "#2dd4bf"                 # detalle vivo (indicador del menú activo)

# --- Fondos y bordes: blancos y grises muy claros ---
FONDO_APP = "#f3f6fa"
SUPERFICIE = "#ffffff"
SUPERFICIE_ALT = "#f8fafc"
BORDE = "#dbe3ec"
BORDE_FUERTE = "#b8c5d4"

# --- Texto: azul oscuro ---
TEXTO = "#0b2545"
TEXTO_SEC = "#4a5d75"
TEXTO_TENUE = "#7b8da3"            # solo decorativo (no usar en texto importante)

# --- Barra lateral ---
LATERAL = "#0b2d52"
LATERAL_HOVER = "#12406f"
LATERAL_ACTIVO = "#1a5190"
LATERAL_TEXTO = "#cfe0f2"
LATERAL_TENUE = "#8aa8c7"

# --- Estados y notificaciones: verde, amarillo y rojo ---
EXITO, EXITO_SUAVE, EXITO_TEXTO = "#1e9e5a", "#e6f6ec", "#146c3c"
AVISO, AVISO_SUAVE, AVISO_TEXTO = "#d99a00", "#fff6dc", "#7a5600"
ERROR, ERROR_SUAVE, ERROR_TEXTO = "#d33b3b", "#fdecec", "#a52626"

DESHABILITADO, DESHABILITADO_TEXTO = "#e3e9f0", "#8a9bb0"
BLANCO = "#ffffff"
FOCO = "#0b2545"                   # anillo de foco (accesibilidad por teclado)

# tipo -> (color, fondo suave, color de texto, icono)
ESTADOS = {
    "exito": (EXITO, EXITO_SUAVE, EXITO_TEXTO, "check"),
    "advertencia": (AVISO, AVISO_SUAVE, AVISO_TEXTO, "alerta"),
    "error": (ERROR, ERROR_SUAVE, ERROR_TEXTO, "error"),
    "info": (PRIMARIO, PRIMARIO_SUAVE, PRIMARIO_PRESS, "info"),
}

# --- Tipografía (escala única para toda la aplicación) ---
FUENTE = "Segoe UI"


def fuente(tam=11, peso="normal"):
    return (FUENTE, tam, peso)


# ====================================================================
# 2. ENTIDADES (TABLAS) Y SU SQL EMPOTRADO
#    campos: (columna, etiqueta del formulario, tipo, opciones)
#    Se agregó "icono" y "sql_contar" (para las tarjetas del inicio).
# ====================================================================
SEXOS = ["FEMENINO", "MASCULINO"]
TURNOS = ["MATUTINO", "VESPERTINO", "NOCTURNO"]

ENTIDADES = {
    "Recepcionista": {
        "singular": "recepcionista",
        "plural": "Recepcionistas",
        "icono": "usuario",
        "campos": [
            ("id_Recepcionista", "Código", "entero", None),
            ("nombre", "Nombre completo", "texto", None),
            ("direccion", "Dirección", "texto", None),
            ("telefono", "Teléfono (10 dígitos)", "telefono", None),
            ("fecha_nac", "Fecha de nacimiento (DD-MM-AAAA)", "fecha", None),
            ("sexo", "Sexo", "lista", SEXOS),
            ("salario", "Salario", "decimal", None),
            ("turno", "Turno", "lista", TURNOS),
            ("contrasena", "Contraseña", "password", None),
        ],
        "encabezados": ["CODIGO", "NOMBRE", "DIRECCION", "TELEFONO", "FECHA_NAC",
                        "SEXO", "SALARIO", "TURNO", "CONTRASEÑA"],
        "anchos": [80, 280, 200, 120, 120, 110, 110, 120, 130],
        # ---- SQL empotrado ----
        "sql_siguiente": "SELECT COALESCE(MAX(id_recepcionista), 0) + 1 FROM recepcionista",
        "sql_contar": "SELECT COUNT(*) FROM recepcionista",
        "sql_insertar": (
            "INSERT INTO recepcionista (id_recepcionista, nombre, direccion, telefono, "
            "fecha_nacimiento, sexo, salario, turno, contrasena) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        ),
        "sql_consultar": (
            "SELECT id_recepcionista, nombre, direccion, telefono, "
            "to_char(fecha_nacimiento, 'DD-MM-YYYY'), sexo, salario, turno, contrasena "
            "FROM recepcionista ORDER BY id_recepcionista"
        ),
    },
    "Doctor": {
        "singular": "doctor",
        "plural": "Doctores",
        "icono": "doctor",
        "campos": [
            ("codigo", "Código", "entero", None),
            ("nombre", "Nombre completo", "texto", None),
            ("direccion", "Dirección", "texto", None),
            ("telefono", "Teléfono (10 dígitos)", "telefono", None),
            ("fecha_nac", "Fecha de nacimiento (DD-MM-AAAA)", "fecha", None),
            ("sexo", "Sexo", "lista", SEXOS),
            ("especialidad", "Especialidad", "texto", None),
            ("contrasena", "Contraseña", "password", None),
        ],
        "encabezados": ["CODIGO", "NOMBRE", "DIRECCION", "TELEFONO", "FECHA_NAC",
                        "SEXO", "ESPECIALIDAD", "CONTRASEÑA"],
        "anchos": [80, 300, 200, 120, 120, 110, 180, 130],
        # ---- SQL empotrado ----
        "sql_siguiente": "SELECT COALESCE(MAX(codigo), 0) + 1 FROM Doctor",
        "sql_contar": "SELECT COUNT(*) FROM Doctor",
        "sql_insertar": (
            "INSERT INTO Doctor (codigo, nombre, direccion, telefono, fecha_nac, "
            "sexo, especialidad, contrasena) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        ),
        "sql_consultar": (
            "SELECT codigo, nombre, direccion, telefono, "
            "to_char(fecha_nac, 'DD-MM-YYYY'), sexo, especialidad, contrasena "
            "FROM Doctor ORDER BY codigo"
        ),
    },
}

# ====================================================================
# 3. VALIDACIÓN Y UTILIDADES (lógica sin cambios)
# ====================================================================
CARPETA = os.path.dirname(os.path.abspath(__file__))


def buscar_imagen():
    for nombre in ("imagen_nucleo.jpg", "imagen_nucleo.jpeg", "imagen_nucleo.png"):
        ruta = os.path.join(CARPETA, nombre)
        if os.path.exists(ruta):
            return ruta
    return None


IMAGEN_ORIGINAL = None
if HAY_PIL:
    _ruta = buscar_imagen()
    if _ruta:
        try:
            IMAGEN_ORIGINAL = Image.open(_ruta).convert("RGB")
        except Exception:
            IMAGEN_ORIGINAL = None


def convertir(tipo, texto, etiqueta):
    """Valida el texto escrito y lo convierte al tipo que espera PostgreSQL."""
    if not texto:
        raise ValueError(f"El campo «{etiqueta}» es obligatorio.")

    if tipo == "entero":
        if not texto.isdigit() or int(texto) < 1:
            raise ValueError(f"«{etiqueta}» debe ser un número entero mayor a 0.")
        return int(texto)

    if tipo == "texto":
        return texto.upper()

    if tipo == "telefono":
        if not (texto.isdigit() and len(texto) == 10):
            raise ValueError(f"«{etiqueta}» debe tener exactamente 10 dígitos.")
        return texto

    if tipo == "fecha":
        try:
            fecha = datetime.strptime(texto.replace("/", "-"), "%d-%m-%Y").date()
        except ValueError:
            raise ValueError(f"«{etiqueta}» debe tener el formato DD-MM-AAAA "
                                "(por ejemplo 07-02-1972).")
        if fecha > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        return fecha

    if tipo == "decimal":
        try:
            numero = Decimal(texto.replace(",", ""))
        except InvalidOperation:
            raise ValueError(f"«{etiqueta}» debe ser un número (por ejemplo 14500.75).")
        if numero <= 0:
            raise ValueError(f"«{etiqueta}» debe ser mayor a 0.")
        return numero

    return texto   # "lista" y "password" ya vienen listos


def codigo_error(error):
    """Código SQLSTATE del error (psycopg3 usa sqlstate, psycopg2 usa pgcode)."""
    return getattr(error, "sqlstate", None) or getattr(error, "pgcode", None)


def mezclar(c1, c2, t):
    """Color intermedio entre dos colores RGB (para el degradado)."""
    return "#%02x%02x%02x" % tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def puntos_ecg(ancho, y0, k, x_ini=0):
    """Puntos de una línea de electrocardiograma que cubre el ancho indicado."""
    latido = [(0, 0), (30, 0), (42, -14), (54, 0), (80, 0), (90, 12),
                (102, -80), (114, 46), (124, 0), (150, 0), (168, -20),
                (186, 0), (230, 0)]
    puntos = []
    x0 = x_ini
    while x0 < ancho:
        for x, y in latido:
            puntos += [x0 + x * k, y0 + y * k]
        x0 += 230 * k
    return puntos


def tarjeta(padre, fondo=SUPERFICIE):
    """Contenedor tipo tarjeta: fondo blanco con borde fino."""
    return tk.Frame(padre, bg=fondo, highlightthickness=1, highlightbackground=BORDE)


# ====================================================================
# 4. COMPONENTES VISUALES REUTILIZABLES
# ====================================================================
class Icono(tk.Canvas):
    """Icono vectorial dibujado con el Canvas (sin depender de fuentes ni imágenes)."""

    def __init__(self, padre, nombre, tam=22, color=TEXTO, fondo=SUPERFICIE,
                    circulo=None, grosor=2):
        super().__init__(padre, width=tam, height=tam, bg=fondo,
                            highlightthickness=0, bd=0)
        self.nombre, self.tam, self.color = nombre, tam, color
        self.circulo, self.grosor = circulo, grosor
        self._dibujar()

    def cambiar(self, color=None, fondo=None, circulo=None):
        if color is not None:
            self.color = color
        if fondo is not None:
            self.configure(bg=fondo)
        if circulo is not None:
            self.circulo = circulo
        self.delete("all")
        self._dibujar()

    def _dibujar(self):
        t = self.tam
        if self.circulo:
            self.create_oval(1, 1, t - 1, t - 1, fill=self.circulo, outline=self.circulo)
            s, d = t / 24 * 0.52, t * 0.24
            g = max(1.6, self.grosor * s * 1.25)
        else:
            s, d = t / 24, 0
            g = max(1.6, self.grosor * s)
        c = self.color

        def p(*v):
            return [x * s + d for x in v]

        def linea(*v):
            self.create_line(*p(*v), fill=c, width=g, capstyle="round", joinstyle="round")

        def punto(x, y, r=1.4):
            self.create_oval(*p(x - r, y - r, x + r, y + r), fill=c, outline=c)

        def circ(x0, y0, x1, y1):
            self.create_oval(*p(x0, y0, x1, y1), outline=c, width=g)

        n = self.nombre
        if n == "inicio":
            linea(3, 12, 12, 3, 21, 12)
            linea(6, 10, 6, 20, 18, 20, 18, 10)
            linea(10, 20, 10, 14, 14, 14, 14, 20)
        elif n == "usuario":
            circ(8, 3, 16, 11)
            self.create_arc(*p(4, 14, 20, 30), start=0, extent=180, style="arc",
                            outline=c, width=g)
        elif n == "doctor":
            circ(2, 2, 22, 22)
            linea(12, 7, 12, 17)
            linea(7, 12, 17, 12)
        elif n == "mas":
            linea(12, 5, 12, 19)
            linea(5, 12, 19, 12)
        elif n == "lista":
            linea(9, 7, 20, 7)
            linea(9, 12, 20, 12)
            linea(9, 17, 20, 17)
            punto(4.5, 7)
            punto(4.5, 12)
            punto(4.5, 17)
        elif n == "salida":
            linea(10, 4, 4, 4, 4, 20, 10, 20)
            linea(9, 12, 20, 12)
            linea(16, 8, 20, 12, 16, 16)
        elif n == "check":
            linea(4, 12, 9.5, 17.5, 20, 6.5)
        elif n == "alerta":
            self.create_polygon(*p(12, 3, 22, 20, 2, 20), outline=c, fill="",
                                width=g, joinstyle="round")
            linea(12, 9, 12, 14)
            punto(12, 17.3)
        elif n == "error":
            circ(2, 2, 22, 22)
            linea(8, 8, 16, 16)
            linea(16, 8, 8, 16)
        elif n == "info":
            circ(2, 2, 22, 22)
            punto(12, 7.5)
            linea(12, 11, 12, 17)
        elif n == "base":
            self.create_oval(*p(5, 3, 19, 9), outline=c, width=g)
            linea(5, 6, 5, 18)
            linea(19, 6, 19, 18)
            self.create_arc(*p(5, 9, 19, 15), start=180, extent=180, style="arc",
                            outline=c, width=g)
            self.create_arc(*p(5, 15, 19, 21), start=180, extent=180, style="arc",
                            outline=c, width=g)
        elif n == "buscar":
            circ(3, 3, 16, 16)
            linea(14, 14, 20, 20)


class Boton(tk.Label):
    """Botón con estados: normal, hover, presionado, foco por teclado y deshabilitado."""

    ESTILOS = {
        "primario": dict(bg=PRIMARIO, fg=BLANCO, hover=PRIMARIO_HOVER,
                            press=PRIMARIO_PRESS, borde=PRIMARIO),
        "secundario": dict(bg=SECUNDARIO, fg=BLANCO, hover=SECUNDARIO_HOVER,
                            press=SECUNDARIO_PRESS, borde=SECUNDARIO),
        "contorno": dict(bg=SUPERFICIE, fg=PRIMARIO, hover=PRIMARIO_SUAVE,
                            press="#d3e4f6", borde=BORDE_FUERTE),
        "fantasma": dict(bg=SUPERFICIE, fg=TEXTO_SEC, hover=FONDO_APP,
                            press=BORDE, borde=SUPERFICIE),
        "peligro": dict(bg=ERROR, fg=BLANCO, hover="#b82f2f",
                        press="#962525", borde=ERROR),
    }

    def __init__(self, padre, texto, comando=None, estilo="primario", tam=11, ancho=None):
        e = self.ESTILOS[estilo]
        opciones = dict(text=texto, font=fuente(tam, "bold"), bg=e["bg"], fg=e["fg"],
                        cursor="hand2", padx=20, pady=8, takefocus=True,
                        highlightthickness=2, highlightbackground=e["borde"],
                        highlightcolor=FOCO)
        if ancho:
            opciones["width"] = ancho
        super().__init__(padre, **opciones)
        self.estilo_boton = e
        self.comando = comando
        self.habilitado = True
        self.bind("<Enter>", self._entrar)
        self.bind("<Leave>", self._salir)
        self.bind("<ButtonPress-1>", self._presionar)
        self.bind("<ButtonRelease-1>", self._soltar)
        self.bind("<Return>", self._teclado)
        self.bind("<space>", self._teclado)

    def _entrar(self, evento=None):
        if self.habilitado:
            self.configure(bg=self.estilo_boton["hover"])

    def _salir(self, evento=None):
        if self.habilitado:
            self.configure(bg=self.estilo_boton["bg"])

    def _presionar(self, evento=None):
        if self.habilitado:
            self.configure(bg=self.estilo_boton["press"])

    def _soltar(self, evento):
        if not self.habilitado:
            return
        dentro = 0 <= evento.x < self.winfo_width() and 0 <= evento.y < self.winfo_height()
        self.configure(bg=self.estilo_boton["hover" if dentro else "bg"])
        if dentro:
            self.invocar()      # al final: la acción puede destruir este botón

    def _teclado(self, evento=None):
        self.invocar()
        return "break"

    def invocar(self):
        if self.habilitado and self.comando:
            self.comando()

    def habilitar(self, valor=True):
        self.habilitado = valor
        if valor:
            self.configure(bg=self.estilo_boton["bg"], fg=self.estilo_boton["fg"],
                            cursor="hand2")
        else:
            self.configure(bg=DESHABILITADO, fg=DESHABILITADO_TEXTO, cursor="arrow")

    def set_texto(self, texto):
        self.configure(text=texto)


class CampoFormulario(tk.Frame):
    """Etiqueta + campo (texto, contraseña o lista) con foco, error y mensaje integrados."""

    def __init__(self, padre, etiqueta, tipo="texto", opciones=None, ancho=30,
                    fondo=SUPERFICIE):
        super().__init__(padre, bg=fondo)
        self.tipo, self.fondo, self.caja, self._error = tipo, fondo, None, False
        self.etiqueta = tk.Label(self, text=etiqueta, font=fuente(10, "bold"),
                                    fg=TEXTO, bg=fondo, anchor="w")
        self.etiqueta.pack(fill="x", pady=(0, 4))

        if tipo == "lista":
            self.var = tk.StringVar()
            self.entrada = ttk.Combobox(self, textvariable=self.var,
                                        values=list(opciones or []), state="readonly",
                                        font=fuente(11), style="Nucleo.TCombobox",
                                        width=ancho)
            self.entrada.pack(fill="x")
            self.entrada.bind("<<ComboboxSelected>>", lambda e: self.quitar_error())
        else:
            self.var = None
            self.caja = tk.Frame(self, bg=BLANCO, highlightthickness=1,
                                    highlightbackground=BORDE)
            self.caja.pack(fill="x")
            self.entrada = tk.Entry(self.caja, font=fuente(11), bg=BLANCO, fg=TEXTO,
                                    relief="flat", bd=0, highlightthickness=0,
                                    insertbackground=TEXTO, width=ancho,
                                    show="*" if tipo == "password" else "")
            self.entrada.pack(side="left", fill="x", expand=True, padx=(10, 6), ipady=8)
            self.entrada.bind("<FocusIn>", self._enfoque)
            self.entrada.bind("<FocusOut>", self._desenfoque)
            self.entrada.bind("<KeyRelease>", lambda e: self.quitar_error())
            if tipo == "password":
                self.ver = tk.Label(self.caja, text="Mostrar", font=fuente(9, "bold"),
                                    fg=PRIMARIO, bg=BLANCO, cursor="hand2", padx=10)
                self.ver.pack(side="right")
                self.ver.bind("<Button-1>", self._alternar_ver)

        self.msg = tk.Label(self, text="", font=fuente(9), fg=ERROR_TEXTO, bg=fondo,
                            anchor="w", justify="left", wraplength=300)

    def _alternar_ver(self, evento=None):
        oculto = self.entrada.cget("show") == "*"
        self.entrada.configure(show="" if oculto else "*")
        self.ver.configure(text="Ocultar" if oculto else "Mostrar")

    def _enfoque(self, evento=None):
        if not self._error:
            self.caja.configure(highlightbackground=PRIMARIO)
            self.etiqueta.configure(fg=PRIMARIO)

    def _desenfoque(self, evento=None):
        if not self._error:
            self.caja.configure(highlightbackground=BORDE)
            self.etiqueta.configure(fg=TEXTO)

    def obtener(self):
        return self.var.get() if self.tipo == "lista" else self.entrada.get()

    def fijar(self, valor):
        if self.tipo == "lista":
            self.var.set(valor)
        else:
            self.entrada.delete(0, "end")
            self.entrada.insert(0, valor)

    def limpiar(self):
        self.fijar("")

    def enfocar(self):
        self.entrada.focus_set()

    def marcar_error(self, mensaje):
        self._error = True
        if self.caja is not None:
            self.caja.configure(highlightbackground=ERROR)
        else:
            self.entrada.configure(style="Error.Nucleo.TCombobox")
        self.etiqueta.configure(fg=ERROR_TEXTO)
        self.msg.configure(text=mensaje)
        self.msg.pack(fill="x", pady=(4, 0))

    def quitar_error(self):
        if not self._error:
            return
        self._error = False
        if self.caja is not None:
            self.caja.configure(highlightbackground=BORDE)
        else:
            self.entrada.configure(style="Nucleo.TCombobox")
        self.etiqueta.configure(fg=TEXTO)
        self.msg.pack_forget()


class Alerta(tk.Frame):
    """Aviso en línea (dentro del formulario) con color e icono según el estado."""

    def __init__(self, padre, fondo=SUPERFICIE):
        super().__init__(padre, bg=fondo)
        self._caja = None

    def mostrar(self, tipo, mensaje):
        self.ocultar()
        color, suave, texto_c, icono = ESTADOS[tipo]
        caja = tk.Frame(self, bg=suave, highlightthickness=1, highlightbackground=color)
        caja.pack(fill="x", pady=(14, 0))
        Icono(caja, icono, 20, color, suave).pack(side="left", padx=(12, 8), pady=10,
                                                    anchor="n")
        tk.Label(caja, text=mensaje, font=fuente(10), fg=texto_c, bg=suave,
                    justify="left", anchor="w", wraplength=300).pack(
            side="left", fill="x", expand=True, padx=(0, 12), pady=10)
        self._caja = caja

    def ocultar(self):
        if self._caja is not None:
            self._caja.destroy()
            self._caja = None


class Toast(tk.Frame):
    """Notificación flotante (esquina inferior derecha) que desaparece sola."""

    def __init__(self, padre, tipo, titulo, mensaje, duracion=4200):
        color, suave, texto_c, icono = ESTADOS[tipo]
        super().__init__(padre, bg=SUPERFICIE, highlightthickness=1,
                            highlightbackground=BORDE)
        self._tarea = None
        tk.Frame(self, bg=color, width=5).pack(side="left", fill="y")
        Icono(self, icono, 24, color, SUPERFICIE).pack(side="left", padx=(14, 10), pady=14)
        cuerpo = tk.Frame(self, bg=SUPERFICIE)
        cuerpo.pack(side="left", pady=10)
        tk.Label(cuerpo, text=titulo, font=fuente(11, "bold"), fg=TEXTO,
                    bg=SUPERFICIE, anchor="w").pack(anchor="w")
        tk.Label(cuerpo, text=mensaje, font=fuente(10), fg=TEXTO_SEC, bg=SUPERFICIE,
                    anchor="w", justify="left", wraplength=320).pack(anchor="w")
        cerrar = tk.Label(self, text="×", font=fuente(14), fg=TEXTO_SEC,
                            bg=SUPERFICIE, cursor="hand2", padx=12)
        cerrar.pack(side="right", anchor="n")
        cerrar.bind("<Button-1>", lambda e: self.destroy())
        self.place(relx=1.0, rely=1.0, x=-28, y=-28, anchor="se")
        self.lift()
        self._tarea = self.after(duracion, self.destroy)

    def destroy(self):
        if self._tarea is not None:
            try:
                self.after_cancel(self._tarea)
            except tk.TclError:
                pass
            self._tarea = None
        super().destroy()


class Dialogo(tk.Toplevel):
    """Cuadro de diálogo modal con icono de estado y botones (reemplaza a messagebox)."""

    def __init__(self, padre, tipo, titulo, mensaje, botones=None):
        super().__init__(padre)
        self.withdraw()
        self.resultado = None
        botones = botones or [("Aceptar", "primario")]
        color, suave, texto_c, icono = ESTADOS[tipo]
        self.title("Núcleo de Diagnóstico")
        self.configure(bg=SUPERFICIE)
        self.resizable(False, False)

        tk.Frame(self, bg=color, height=4).pack(fill="x")
        cuerpo = tk.Frame(self, bg=SUPERFICIE)
        cuerpo.pack(fill="both", expand=True, padx=28, pady=(24, 8))
        Icono(cuerpo, icono, 52, color, SUPERFICIE, circulo=suave).pack(
            side="left", anchor="n", padx=(0, 18))
        textos = tk.Frame(cuerpo, bg=SUPERFICIE)
        textos.pack(side="left", fill="both", expand=True)
        tk.Label(textos, text=titulo, font=fuente(14, "bold"), fg=TEXTO, bg=SUPERFICIE,
                    anchor="w", justify="left", wraplength=380).pack(anchor="w")
        tk.Label(textos, text=mensaje, font=fuente(11), fg=TEXTO_SEC, bg=SUPERFICIE,
                    anchor="w", justify="left", wraplength=380).pack(anchor="w", pady=(6, 0))

        tk.Frame(self, bg=BORDE, height=1).pack(fill="x", pady=(18, 0))
        pie = tk.Frame(self, bg=SUPERFICIE_ALT)
        pie.pack(fill="x")
        for texto, estilo in reversed(botones):     # el último queda a la derecha
            Boton(pie, texto, lambda t=texto: self._elegir(t), estilo=estilo).pack(
                side="right", padx=(0, 14), pady=12)

        self.bind("<Return>", lambda e: self._elegir(botones[-1][0]))
        self.bind("<Escape>", lambda e: self._elegir(None))
        self.protocol("WM_DELETE_WINDOW", lambda: self._elegir(None))

        # Centrar sobre la ventana principal y volverlo modal
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = padre.winfo_rootx() + (padre.winfo_width() - w) // 2
        y = padre.winfo_rooty() + (padre.winfo_height() - h) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.transient(padre)
        self.deiconify()
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.lift()
        self.focus_force()

    def _elegir(self, texto):
        self.resultado = texto
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()


class ItemMenu(tk.Frame):
    """Opción de la barra lateral con icono, hover y marca de opción activa."""

    def __init__(self, padre, texto, icono, comando, sangria=0):
        super().__init__(padre, bg=LATERAL, cursor="hand2")
        self.comando, self.activo, self._hover = comando, False, False
        self.barra = tk.Frame(self, bg=LATERAL, width=4)
        self.barra.pack(side="left", fill="y")
        self.icono = Icono(self, icono, 20, LATERAL_TEXTO, LATERAL)
        self.icono.pack(side="left", padx=(18 + sangria, 12), pady=11)
        self.texto = tk.Label(self, text=texto, font=fuente(11), fg=LATERAL_TEXTO,
                                bg=LATERAL, anchor="w")
        self.texto.pack(side="left", fill="x", expand=True)
        for w in (self, self.barra, self.icono, self.texto):
            w.bind("<Enter>", self._entrar)
            w.bind("<Leave>", self._salir)
            w.bind("<Button-1>", self._clic)

    def _entrar(self, evento=None):
        self._hover = True
        self._pintar()

    def _salir(self, evento=None):
        try:
            x, y = self.winfo_pointerxy()
            destino = self.winfo_containing(x, y)
        except (KeyError, tk.TclError):
            destino = None
        if destino is not None:
            ruta, propia = str(destino), str(self)
            if ruta == propia or ruta.startswith(propia + "."):
                return          # el puntero sigue dentro (pasó a un hijo)
        self._hover = False
        self._pintar()

    def _clic(self, evento=None):
        if self.comando:
            self.comando()

    def activar(self, valor):
        self.activo = valor
        self._pintar()

    def _pintar(self):
        if self.activo:
            bg, fg, barra = LATERAL_ACTIVO, BLANCO, ACENTO
        elif self._hover:
            bg, fg, barra = LATERAL_HOVER, BLANCO, LATERAL_HOVER
        else:
            bg, fg, barra = LATERAL, LATERAL_TEXTO, LATERAL
        self.configure(bg=bg)
        self.barra.configure(bg=barra)
        self.texto.configure(bg=bg, fg=fg)
        self.icono.cambiar(color=fg, fondo=bg)


class TarjetaDato(tk.Frame):
    """Tarjeta informativa: icono, título, valor destacado y detalle."""

    def __init__(self, padre, titulo, valor, icono, color, suave, detalle="",
                    color_detalle=TEXTO_SEC, tam_valor=24):
        super().__init__(padre, bg=SUPERFICIE, highlightthickness=1,
                            highlightbackground=BORDE)
        Icono(self, icono, 54, color, SUPERFICIE, circulo=suave).pack(
            side="left", padx=(20, 16), pady=20)
        datos = tk.Frame(self, bg=SUPERFICIE)
        datos.pack(side="left", fill="x", expand=True, pady=16)
        tk.Label(datos, text=titulo, font=fuente(10, "bold"), fg=TEXTO_SEC,
                    bg=SUPERFICIE, anchor="w").pack(anchor="w")
        tk.Label(datos, text=str(valor), font=fuente(tam_valor, "bold"), fg=TEXTO,
                    bg=SUPERFICIE, anchor="w").pack(anchor="w")
        tk.Label(datos, text=detalle, font=fuente(9), fg=color_detalle,
                    bg=SUPERFICIE, anchor="w").pack(anchor="w")


class Hero(tk.Canvas):
    """Imagen del núcleo de diagnóstico (foto o ilustración de respaldo) con texto encima.
    modo="completo": panel alto del login | modo="banner": franja del panel de inicio."""

    def __init__(self, padre, kicker, titulo, subtitulo, pie, modo="completo", alto=None):
        opciones = {"highlightthickness": 0, "bg": LATERAL}
        if alto:
            opciones["height"] = alto
        super().__init__(padre, **opciones)
        self.kicker, self.titulo, self.subtitulo, self.pie = kicker, titulo, subtitulo, pie
        self.modo = modo
        self.foto = None
        self._tarea = None
        self.bind("<Configure>", self._programar)

    def _programar(self, event=None):
        """Espera un instante para no redibujar mil veces al cambiar de tamaño."""
        if self._tarea:
            self.after_cancel(self._tarea)
        self._tarea = self.after(60, self._dibujar)

    def destroy(self):
        if self._tarea:
            self.after_cancel(self._tarea)
            self._tarea = None
        super().destroy()

    def _cruz(self, cx, cy, r):
        self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=ACENTO, width=3)
        brazo, grosor = r * 0.55, r * 0.17
        self.create_rectangle(cx - grosor, cy - brazo, cx + grosor, cy + brazo,
                                fill=BLANCO, outline=BLANCO)
        self.create_rectangle(cx - brazo, cy - grosor, cx + brazo, cy + grosor,
                                fill=BLANCO, outline=BLANCO)

    def _ilustracion(self, w, h):
        """Respaldo: degradado azul + cruz médica + electrocardiograma."""
        pasos = 50
        if self.modo == "banner":
            for i in range(pasos):
                color = mezclar((11, 45, 82), (19, 102, 184), i / pasos)
                self.create_rectangle(w * i / pasos, 0, w * (i + 1) / pasos + 1, h,
                                        fill=color, outline=color)
            self._cruz(w * 0.9, h * 0.30, h * 0.13)
            puntos = puntos_ecg(w, h * 0.68, max(0.5, h / 420), x_ini=w * 0.52)
            self.create_line(*puntos, fill=SECUNDARIO, width=7, joinstyle="round")
            self.create_line(*puntos, fill=ACENTO, width=2, joinstyle="round")
        else:
            for i in range(pasos):
                color = mezclar((11, 45, 82), (15, 118, 110), i / pasos)
                self.create_rectangle(0, h * i / pasos, w, h * (i + 1) / pasos + 1,
                                        fill=color, outline=color)
            self._cruz(w * 0.5, h * 0.21, min(w, h) * 0.11)
            puntos = puntos_ecg(w, h * 0.43, max(0.9, h / 700))
            self.create_line(*puntos, fill=SECUNDARIO, width=9, joinstyle="round")
            self.create_line(*puntos, fill=ACENTO, width=3, joinstyle="round")

    def _dibujar(self):
        self._tarea = None
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50 or h < 50:
            return
        self.delete("all")

        if IMAGEN_ORIGINAL is not None:
            img = ImageOps.fit(IMAGEN_ORIGINAL, (w, h), Image.LANCZOS)
            capa = Image.new("RGB", (w, h), LATERAL)
            img = Image.blend(img, capa, 0.58)   # oscurece para que el texto se lea
            self.foto = ImageTk.PhotoImage(img)
            self.create_image(0, 0, image=self.foto, anchor="nw")
        else:
            self._ilustracion(w, h)

        if self.modo == "banner":
            x = 40
            t_titulo = max(20, min(32, h // 7))
            self.create_text(x, h * 0.24, anchor="w", fill=ACENTO, text=self.kicker,
                                font=fuente(10, "bold"))
            self.create_text(x, h * 0.46, anchor="w", fill=BLANCO, text=self.titulo,
                                font=fuente(t_titulo, "bold"))
            self.create_text(x, h * 0.70, anchor="w", fill="#d7e3ee", text=self.subtitulo,
                                font=fuente(12))
            if self.pie:
                self.create_text(x, h * 0.90, anchor="w", fill="#9fb4c8", text=self.pie,
                                    font=fuente(10))
            return

        x = w * 0.08
        t_titulo = max(26, min(54, w // 18))
        t_sub = max(12, min(20, w // 70))
        t_peq = max(10, min(14, w // 90))
        self.create_text(x, h * 0.58, anchor="w", fill=ACENTO, text=self.kicker,
                            font=fuente(t_peq, "bold"))
        self.create_text(x, h * 0.67, anchor="w", fill=BLANCO, text=self.titulo,
                            font=fuente(t_titulo, "bold"))
        self.create_text(x, h * 0.77, anchor="w", fill="#d7e3ee", text=self.subtitulo,
                            font=fuente(t_sub))
        self.create_text(x, h * 0.92, anchor="w", fill="#9fb4c8", text=self.pie,
                            font=fuente(t_peq))


# ====================================================================
# 5. APLICACIÓN
# ====================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Núcleo de Diagnóstico")
        self.configure(bg=SUPERFICIE)
        self.attributes("-fullscreen", True)
        self.minsize(1000, 640)
        self.protocol("WM_DELETE_WINDOW", self.salir)

        self.conexion = None
        self.usuario = None
        self.pantalla = None
        self.contenido = None
        self.campos = {}
        self.items_menu = {}
        self.lbl_titulo = None
        self.lbl_ruta = None
        self._toast = None
        self._fila_hover = None

        self._configurar_estilos()
        self.bind("<F11>", self.alternar_pantalla_completa)
        self.mostrar_login()

    # ---------------- utilidades ----------------
    def _configurar_estilos(self):
        """Estilos ttk (tablas, listas desplegables, barras de desplazamiento)."""
        estilo = ttk.Style(self)
        estilo.theme_use("clam")

        estilo.configure("Nucleo.Treeview", rowheight=40, font=fuente(11),
                            background=SUPERFICIE, fieldbackground=SUPERFICIE,
                            foreground=TEXTO, borderwidth=0, relief="flat")
        estilo.configure("Nucleo.Treeview.Heading", font=fuente(10, "bold"),
                            background="#eaf0f7", foreground=TEXTO_SEC,
                            relief="flat", padding=(12, 11), borderwidth=0)
        estilo.map("Nucleo.Treeview.Heading", background=[("active", PRIMARIO_SUAVE)])
        estilo.map("Nucleo.Treeview",
                    background=[("selected", PRIMARIO_SUAVE)],
                    foreground=[("selected", TEXTO)])

        estilo.configure("Nucleo.TCombobox", fieldbackground=BLANCO, background=BLANCO,
                            foreground=TEXTO, bordercolor=BORDE, lightcolor=BLANCO,
                            darkcolor=BLANCO, arrowcolor=TEXTO_SEC, padding=7)
        estilo.map("Nucleo.TCombobox",
                    bordercolor=[("focus", PRIMARIO)],
                    fieldbackground=[("readonly", BLANCO)],
                    foreground=[("readonly", TEXTO)],
                    selectbackground=[("readonly", BLANCO)],
                    selectforeground=[("readonly", TEXTO)])
        estilo.configure("Error.Nucleo.TCombobox", bordercolor=ERROR)
        self.option_add("*TCombobox*Listbox.font", fuente(11))
        self.option_add("*TCombobox*Listbox.background", BLANCO)
        self.option_add("*TCombobox*Listbox.selectBackground", PRIMARIO)
        self.option_add("*TCombobox*Listbox.selectForeground", BLANCO)

        for orientacion in ("Vertical", "Horizontal"):
            estilo.configure(f"Nucleo.{orientacion}.TScrollbar", troughcolor=FONDO_APP,
                                background=BORDE_FUERTE, bordercolor=FONDO_APP,
                                arrowcolor=TEXTO_SEC, relief="flat")

    def alternar_pantalla_completa(self, event=None):
        self.attributes("-fullscreen", not self.attributes("-fullscreen"))
        return "break"

    def limpiar(self):
        if self.pantalla is not None:
            self.pantalla.destroy()
            self.pantalla = None
        self._toast = None

    def salir(self, event=None):
        self.cerrar_conexion()
        self.destroy()

    def cerrar_conexion(self):
        if self.conexion is not None:
            try:
                self.conexion.close()
            except Exception:
                pass
            self.conexion = None

    def ejecutar(self, sql, parametros=None, consulta=False):
        """Ejecuta una sentencia SQL (autocommit activado) y devuelve las filas si es consulta."""
        with self.conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchall() if consulta else None

    def contar(self, clave):
        """Total de registros de una entidad (None si la tabla no está disponible)."""
        try:
            return self.ejecutar(ENTIDADES[clave]["sql_contar"], consulta=True)[0][0]
        except pg.Error:
            return None

    # ---------------- notificaciones y diálogos ----------------
    def notificar(self, tipo, titulo, mensaje, botones=None):
        """Diálogo modal. Devuelve el texto del botón elegido (o None si se cerró)."""
        dialogo = Dialogo(self, tipo, titulo, mensaje, botones)
        self.wait_window(dialogo)
        return dialogo.resultado

    def toast(self, tipo, titulo, mensaje):
        """Notificación flotante que no interrumpe el trabajo."""
        if self.pantalla is None:
            return
        if self._toast is not None:
            try:
                self._toast.destroy()
            except tk.TclError:
                pass
        self._toast = Toast(self.pantalla, tipo, titulo, mensaje)

    def mostrar_error_sql(self, error):
        codigo = codigo_error(error)
        if codigo == "23505":
            detalle = getattr(getattr(error, "diag", None), "message_detail", None) or ""
            mensaje = ("Ya existe un registro con un dato que debe ser único "
                        "(código, teléfono o contraseña).\n\n" + detalle)
        elif codigo == "42P01":
            mensaje = ("La tabla no existe todavía. Créala primero desde pgAdmin 4 "
                        "con el nombre y las columnas que usa el programa.")
        elif codigo == "42703":
            mensaje = ("Alguna columna no existe en la tabla. Revisa que los nombres "
                        f"coincidan con el SQL del programa.\n\n{error}")
        elif codigo == "42501":
            mensaje = "Tu usuario de PostgreSQL no tiene permisos sobre esa tabla."
        elif codigo in ("23514", "22001", "22007", "22P02"):
            mensaje = f"Algún dato no cumple con las reglas de la tabla.\n\n{error}"
        else:
            mensaje = str(error)
        self.notificar("error", "Error de base de datos", mensaje)

    def confirmar_cerrar_sesion(self):
        if self.notificar("info", "Cerrar sesión",
                            f"¿Deseas cerrar la sesión de «{self.usuario}»?",
                            [("Cancelar", "contorno"), ("Cerrar sesión", "primario")]
                            ) == "Cerrar sesión":
            self.cerrar_sesion()

    def confirmar_salir(self):
        if self.notificar("advertencia", "Salir del sistema",
                            "¿Seguro que deseas cerrar el programa?",
                            [("Cancelar", "contorno"), ("Salir", "peligro")]) == "Salir":
            self.salir()

    # ---------------- pantalla: LOGIN ----------------
    def mostrar_login(self):
        self.limpiar()
        self.bind("<Return>", self.iniciar_sesion)
        self.bind("<Escape>", self.salir)

        pantalla = tk.Frame(self, bg=SUPERFICIE)
        pantalla.pack(fill="both", expand=True)
        self.pantalla = pantalla
        pantalla.columnconfigure(0, weight=1)
        pantalla.columnconfigure(1, weight=0, minsize=500)
        pantalla.rowconfigure(0, weight=1)

        hero = Hero(pantalla, kicker="SISTEMA DE GESTIÓN CLÍNICA",
                    titulo="Núcleo de Diagnóstico",
                    subtitulo="Citas, consultas y diagnósticos\nen un solo lugar.",
                    pie="Pacientes  ·  Médicos  ·  Citas  ·  Consultas  ·  Medicamentos")
        hero.grid(row=0, column=0, sticky="nsew")

        panel = tk.Frame(pantalla, bg=SUPERFICIE)
        panel.grid(row=0, column=1, sticky="nsew")

        centro = tk.Frame(panel, bg=SUPERFICIE, width=380)
        centro.place(relx=0.5, rely=0.5, anchor="center")

        marca = tk.Frame(centro, bg=SUPERFICIE)
        marca.pack(fill="x")
        Icono(marca, "mas", 40, BLANCO, SUPERFICIE, circulo=PRIMARIO).pack(side="left")
        tk.Label(marca, text="Núcleo de Diagnóstico", font=fuente(13, "bold"), fg=TEXTO,
                    bg=SUPERFICIE).pack(side="left", padx=12)

        tk.Label(centro, text="Iniciar sesión", font=fuente(26, "bold"), fg=TEXTO,
                    bg=SUPERFICIE, anchor="w").pack(fill="x", pady=(28, 0))
        tk.Label(centro, text="Ingresa con tu usuario de PostgreSQL para continuar.",
                    font=fuente(10), fg=TEXTO_SEC, bg=SUPERFICIE, anchor="w").pack(
            fill="x", pady=(2, 18))

        self.entrada_usuario = CampoFormulario(centro, "Usuario", ancho=34)
        self.entrada_usuario.pack(fill="x", pady=(0, 14))
        self.entrada_contrasena = CampoFormulario(centro, "Contraseña", "password", ancho=34)
        self.entrada_contrasena.pack(fill="x")

        ranura = tk.Frame(centro, bg=SUPERFICIE)       # aquí aparecen los avisos
        ranura.pack(fill="x")
        self.alerta_login = Alerta(ranura)
        self.alerta_login.pack(fill="x")

        self.boton_entrar = Boton(centro, "Iniciar sesión", self.iniciar_sesion,
                                    "primario", tam=12)
        self.boton_entrar.pack(fill="x", pady=(22, 8))
        Boton(centro, "Salir", self.salir, "fantasma").pack(fill="x")

        tk.Label(panel, text=f"Servidor: {HOST}:{PUERTO}  ·  Base de datos: {BASE_DE_DATOS}",
                    font=fuente(9), fg=TEXTO_SEC, bg=SUPERFICIE).pack(side="bottom", pady=(0, 8))
        tk.Label(panel, text="Enter: iniciar sesión   ·   F11: pantalla completa   ·   Esc: salir",
                    font=fuente(9), fg=TEXTO_TENUE, bg=SUPERFICIE).pack(side="bottom")

        self.entrada_usuario.enfocar()

    def iniciar_sesion(self, event=None):
        usuario = self.entrada_usuario.obtener().strip()
        contrasena = self.entrada_contrasena.obtener()
        self.alerta_login.ocultar()
        self.entrada_usuario.quitar_error()
        self.entrada_contrasena.quitar_error()

        if not usuario or not contrasena:
            if not usuario:
                self.entrada_usuario.marcar_error("Escribe tu usuario.")
            if not contrasena:
                self.entrada_contrasena.marcar_error("Escribe tu contraseña.")
            self.alerta_login.mostrar("advertencia", "Escribe tu usuario y tu contraseña.")
            return

        self.boton_entrar.set_texto("Conectando…")
        self.boton_entrar.habilitar(False)
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            # ---- Conexión con el servidor PostgreSQL ----
            conexion = pg.connect(host=HOST, port=PUERTO, dbname=BASE_DE_DATOS,
                                    user=usuario, password=contrasena,
                                    connect_timeout=5, application_name=NOMBRE_APP)
            conexion.autocommit = True
        except pg.OperationalError as error:
            texto = str(error)
            if "password authentication failed" in texto:
                mensaje = "Usuario o contraseña incorrectos."
            elif "does not exist" in texto:
                mensaje = f"La base de datos '{BASE_DE_DATOS}' o el usuario no existen."
            elif "refused" in texto or "timeout" in texto.lower():
                mensaje = "No se pudo conectar al servidor. ¿Está encendido PostgreSQL?"
            else:
                mensaje = texto
            self.config(cursor="")
            self.boton_entrar.set_texto("Iniciar sesión")
            self.boton_entrar.habilitar(True)
            self.alerta_login.mostrar("error", mensaje)
            self.entrada_contrasena.limpiar()
            self.entrada_contrasena.enfocar()
            return

        self.config(cursor="")
        self.conexion = conexion
        self.usuario = usuario
        self.mostrar_principal()
        self.toast("exito", "Sesión iniciada", f"Conectado como «{usuario}».")

    # ---------------- pantalla: PRINCIPAL ----------------
    def mostrar_principal(self):
        self.limpiar()
        self.unbind("<Return>")
        self.unbind("<Escape>")
        self.items_menu = {}

        pantalla = tk.Frame(self, bg=FONDO_APP)
        pantalla.pack(fill="both", expand=True)
        self.pantalla = pantalla

        # ---- Barra lateral ----
        lateral = tk.Frame(pantalla, bg=LATERAL, width=272)
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)

        marca = tk.Frame(lateral, bg=LATERAL)
        marca.pack(fill="x", padx=20, pady=(22, 18))
        Icono(marca, "mas", 42, BLANCO, LATERAL, circulo=SECUNDARIO).pack(side="left")
        textos = tk.Frame(marca, bg=LATERAL)
        textos.pack(side="left", padx=12)
        tk.Label(textos, text="Núcleo de Diagnóstico", font=fuente(12, "bold"),
                    fg=BLANCO, bg=LATERAL).pack(anchor="w")
        tk.Label(textos, text="Gestión clínica", font=fuente(9), fg=LATERAL_TENUE,
                    bg=LATERAL).pack(anchor="w")
        tk.Frame(lateral, bg=LATERAL_HOVER, height=1).pack(fill="x")

        def seccion(texto):
            tk.Label(lateral, text=texto, font=fuente(9, "bold"), fg=LATERAL_TENUE,
                        bg=LATERAL, anchor="w").pack(fill="x", padx=22, pady=(18, 6))

        def item(clave, texto, icono, comando):
            widget = ItemMenu(lateral, texto, icono, comando)
            widget.pack(fill="x")
            self.items_menu[clave] = widget

        seccion("GENERAL")
        item(("inicio",), "Inicio", "inicio", self.mostrar_inicio)
        for clave, ent in ENTIDADES.items():
            seccion(ent["plural"].upper())
            item((clave, "insertar"), f"Registrar {ent['singular']}", "mas",
                    lambda c=clave: self.mostrar_insertar(c))
            item((clave, "consulta"), "Consultas generales", "lista",
                    lambda c=clave: self.mostrar_consulta(c))

        # Pie de la barra lateral: usuario y sesión
        pie = tk.Frame(lateral, bg=LATERAL)
        pie.pack(side="bottom", fill="x")
        ItemMenu(pie, "Salir", "salida", self.confirmar_salir).pack(fill="x")
        ItemMenu(pie, "Cerrar sesión", "salida", self.confirmar_cerrar_sesion).pack(fill="x")
        tk.Frame(pie, bg=LATERAL_HOVER, height=1).pack(fill="x", pady=(8, 0))
        perfil = tk.Frame(pie, bg=LATERAL)
        perfil.pack(fill="x", padx=20, pady=14)
        avatar = tk.Canvas(perfil, width=40, height=40, bg=LATERAL, highlightthickness=0)
        avatar.create_oval(1, 1, 39, 39, fill=PRIMARIO, outline=PRIMARIO)
        avatar.create_text(20, 20, text=(self.usuario or "?")[:1].upper(), fill=BLANCO,
                            font=fuente(14, "bold"))
        avatar.pack(side="left")
        datos = tk.Frame(perfil, bg=LATERAL)
        datos.pack(side="left", padx=12)
        tk.Label(datos, text=self.usuario, font=fuente(11, "bold"), fg=BLANCO,
                    bg=LATERAL).pack(anchor="w")
        tk.Label(datos, text="Sesión activa", font=fuente(9), fg=ACENTO,
                    bg=LATERAL).pack(anchor="w")

        # ---- Zona derecha: barra superior + contenido ----
        derecha = tk.Frame(pantalla, bg=FONDO_APP)
        derecha.pack(side="left", fill="both", expand=True)

        barra = tk.Frame(derecha, bg=SUPERFICIE, height=70)
        barra.pack(fill="x")
        barra.pack_propagate(False)
        titulos = tk.Frame(barra, bg=SUPERFICIE)
        titulos.pack(side="left", padx=28)
        self.lbl_titulo = tk.Label(titulos, text="", font=fuente(17, "bold"), fg=TEXTO,
                                    bg=SUPERFICIE)
        self.lbl_titulo.pack(anchor="w", pady=(12, 0))
        self.lbl_ruta = tk.Label(titulos, text="", font=fuente(9), fg=TEXTO_SEC,
                                    bg=SUPERFICIE)
        self.lbl_ruta.pack(anchor="w")

        chip = tk.Frame(barra, bg=EXITO_SUAVE, highlightthickness=1,
                        highlightbackground=EXITO)
        chip.pack(side="right", padx=28)
        punto = tk.Canvas(chip, width=12, height=12, bg=EXITO_SUAVE, highlightthickness=0)
        punto.create_oval(2, 2, 10, 10, fill=EXITO, outline=EXITO)
        punto.pack(side="left", padx=(12, 6), pady=10)
        tk.Label(chip, text=f"Conectado · {BASE_DE_DATOS}", font=fuente(10, "bold"),
                    fg=EXITO_TEXTO, bg=EXITO_SUAVE).pack(side="left", padx=(0, 14))
        tk.Frame(derecha, bg=BORDE, height=1).pack(fill="x")

        self.contenido = tk.Frame(derecha, bg=FONDO_APP)
        self.contenido.pack(fill="both", expand=True, padx=28, pady=24)
        self.mostrar_inicio()

    def cerrar_sesion(self):
        self.cerrar_conexion()
        self.usuario = None
        self.mostrar_login()

    def vaciar_contenido(self):
        for widget in self.contenido.winfo_children():
            widget.destroy()

    def _preparar_vista(self, item, titulo, ruta):
        """Limpia el contenido, marca la opción activa y actualiza el encabezado."""
        self.vaciar_contenido()
        self._fila_hover = None
        for clave, widget in self.items_menu.items():
            widget.activar(clave == item)
        self.lbl_titulo.config(text=titulo)
        self.lbl_ruta.config(text=ruta)

    # ---- Inicio: imagen del núcleo de diagnóstico + tarjetas informativas ----
    def mostrar_inicio(self):
        self._preparar_vista(("inicio",), "Inicio", "Panel principal")

        Hero(self.contenido, kicker="SESIÓN INICIADA", titulo="Núcleo de Diagnóstico",
                subtitulo=f"Bienvenido(a), usuario: {self.usuario}",
                pie="", modo="banner", alto=230).pack(fill="x")

        fila = tk.Frame(self.contenido, bg=FONDO_APP)
        fila.pack(fill="x", pady=(20, 0))
        tarjetas = []
        for clave, ent in ENTIDADES.items():
            total = self.contar(clave)
            ok = total is not None
            tarjetas.append(TarjetaDato(
                fila, ent["plural"], total if ok else "—", ent["icono"],
                PRIMARIO, PRIMARIO_SUAVE,
                "Registrados en la base de datos" if ok else "Tabla no disponible",
                TEXTO_SEC if ok else AVISO_TEXTO))
        tarjetas.append(TarjetaDato(fila, "Usuario conectado", self.usuario, "usuario",
                                    SECUNDARIO, SECUNDARIO_SUAVE, "Sesión activa",
                                    EXITO_TEXTO, tam_valor=16))
        tarjetas.append(TarjetaDato(fila, "Base de datos", BASE_DE_DATOS, "base",
                                    PRIMARIO, PRIMARIO_SUAVE, f"{HOST}:{PUERTO}",
                                    tam_valor=14))
        for i, tarjeta_dato in enumerate(tarjetas):
            fila.columnconfigure(i, weight=1, uniform="datos")
            tarjeta_dato.grid(row=0, column=i, sticky="nsew",
                                padx=(0, 16 if i < len(tarjetas) - 1 else 0))

        rapidos = tarjeta(self.contenido)
        rapidos.pack(fill="x", pady=(20, 0))
        tk.Label(rapidos, text="Accesos rápidos", font=fuente(14, "bold"), fg=TEXTO,
                    bg=SUPERFICIE).pack(anchor="w", padx=24, pady=(18, 0))
        tk.Label(rapidos, text="Atajos a las acciones más frecuentes del sistema.",
                    font=fuente(10), fg=TEXTO_SEC, bg=SUPERFICIE).pack(anchor="w", padx=24)
        botones = tk.Frame(rapidos, bg=SUPERFICIE)
        botones.pack(anchor="w", padx=24, pady=(12, 20))
        for clave, ent in ENTIDADES.items():
            Boton(botones, f"Registrar {ent['singular']}",
                    lambda c=clave: self.mostrar_insertar(c), "primario").pack(
                side="left", padx=(0, 10))
            Boton(botones, f"Consultar {ent['plural'].lower()}",
                    lambda c=clave: self.mostrar_consulta(c), "contorno").pack(
                side="left", padx=(0, 10))

    # ---- Insertar (recepcionista / doctor) ----
    def mostrar_insertar(self, clave):
        ent = ENTIDADES[clave]
        primero = ent["campos"][0][0]
        self._preparar_vista((clave, "insertar"), f"Registrar {ent['singular']}",
                                f"{ent['plural']}  /  Registrar")

        tarj = tarjeta(self.contenido)
        tarj.pack(anchor="n")

        cabecera = tk.Frame(tarj, bg=SUPERFICIE)
        cabecera.pack(fill="x", padx=32, pady=(26, 18))
        Icono(cabecera, ent["icono"], 48, PRIMARIO, SUPERFICIE,
                circulo=PRIMARIO_SUAVE).pack(side="left", padx=(0, 16))
        textos = tk.Frame(cabecera, bg=SUPERFICIE)
        textos.pack(side="left")
        tk.Label(textos, text=f"Registrar {ent['singular']}", font=fuente(18, "bold"),
                    fg=TEXTO, bg=SUPERFICIE).pack(anchor="w")
        tk.Label(textos, text="Completa todos los datos. Los campos con error se marcarán en rojo.",
                    font=fuente(10), fg=TEXTO_SEC, bg=SUPERFICIE).pack(anchor="w")
        tk.Frame(tarj, bg=BORDE, height=1).pack(fill="x")

        cuerpo = tk.Frame(tarj, bg=SUPERFICIE)
        cuerpo.pack(fill="x", padx=32, pady=(22, 6))
        cuerpo.columnconfigure(0, weight=1, uniform="columna")
        cuerpo.columnconfigure(1, weight=1, uniform="columna")

        self.campos = {}
        for i, (columna, etiqueta, tipo, opciones) in enumerate(ent["campos"]):
            campo = CampoFormulario(cuerpo, etiqueta, tipo, opciones, ancho=30)
            campo.grid(row=i // 2, column=i % 2, sticky="new", pady=(0, 14),
                        padx=(0, 0) if i % 2 == 0 else (24, 0))
            self.campos[columna] = campo

        # Sugerir el siguiente código disponible (se puede cambiar)
        try:
            siguiente = self.ejecutar(ent["sql_siguiente"], consulta=True)[0][0]
            self.campos[primero].fijar(str(siguiente))
        except pg.Error:
            pass   # si la tabla no existe, el error se mostrará al guardar

        tk.Frame(tarj, bg=BORDE, height=1).pack(fill="x")
        pie = tk.Frame(tarj, bg=SUPERFICIE_ALT)
        pie.pack(fill="x")
        tk.Label(pie, text="Todos los campos son obligatorios.", font=fuente(10),
                    fg=TEXTO_SEC, bg=SUPERFICIE_ALT).pack(side="left", padx=32)
        self.boton_guardar = Boton(pie, "Guardar", lambda: self.guardar(clave), "primario")
        self.boton_guardar.pack(side="right", padx=(8, 32), pady=16)
        Boton(pie, "Limpiar", lambda: self.mostrar_insertar(clave), "contorno").pack(
            side="right", pady=16)

        self.campos[primero].enfocar()

    def guardar(self, clave):
        ent = ENTIDADES[clave]
        valores, con_error = [], []
        for columna, etiqueta, tipo, _ in ent["campos"]:
            campo = self.campos[columna]
            campo.quitar_error()
            texto = campo.obtener()
            if tipo != "password":
                texto = texto.strip()
            try:
                valores.append(convertir(tipo, texto, etiqueta))
            except ValueError as error:
                campo.marcar_error(str(error))
                con_error.append(columna)

        if con_error:
            self.campos[con_error[0]].enfocar()
            self.toast("advertencia", "Revisa el formulario",
                        f"Hay {len(con_error)} campo(s) con datos no válidos.")
            return

        self.boton_guardar.set_texto("Guardando…")
        self.boton_guardar.habilitar(False)
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            # ---- SQL empotrado: INSERT ----
            self.ejecutar(ent["sql_insertar"], valores)
        except pg.Error as error:
            self.config(cursor="")
            self.boton_guardar.set_texto("Guardar")
            self.boton_guardar.habilitar(True)
            self.mostrar_error_sql(error)
            return

        self.config(cursor="")
        self.mostrar_insertar(clave)   # formulario limpio con el siguiente código
        self.toast("exito", "Registro guardado",
                    f"Se insertó correctamente al {ent['singular']}: {valores[1]}")

    # ---- Consultas generales (recepcionista / doctor) ----
    def mostrar_consulta(self, clave):
        ent = ENTIDADES[clave]
        primero = ent["campos"][0][0]
        self._preparar_vista((clave, "consulta"), "Consultas generales",
                                f"{ent['plural']}  /  Consultas generales")

        # Encabezado: título, búsqueda y acciones
        cab = tarjeta(self.contenido)
        cab.pack(fill="x")
        interior = tk.Frame(cab, bg=SUPERFICIE)
        interior.pack(fill="x", padx=24, pady=16)
        izquierda = tk.Frame(interior, bg=SUPERFICIE)
        izquierda.pack(side="left")
        Icono(izquierda, ent["icono"], 46, PRIMARIO, SUPERFICIE,
                circulo=PRIMARIO_SUAVE).pack(side="left", padx=(0, 14))
        textos = tk.Frame(izquierda, bg=SUPERFICIE)
        textos.pack(side="left")
        tk.Label(textos, text=f"Consultas generales · {ent['plural']}",
                    font=fuente(16, "bold"), fg=TEXTO, bg=SUPERFICIE).pack(anchor="w")
        tk.Label(textos, text="Listado completo desde la base de datos.",
                    font=fuente(10), fg=TEXTO_SEC, bg=SUPERFICIE).pack(anchor="w")

        acciones = tk.Frame(interior, bg=SUPERFICIE)
        acciones.pack(side="right")
        Boton(acciones, f"Registrar {ent['singular']}",
                lambda: self.mostrar_insertar(clave), "primario").pack(side="right")
        Boton(acciones, "Actualizar", lambda: self.mostrar_consulta(clave),
                "contorno").pack(side="right", padx=10)
        busqueda = tk.Frame(acciones, bg=BLANCO, highlightthickness=1,
                            highlightbackground=BORDE)
        busqueda.pack(side="right", padx=(0, 4))
        Icono(busqueda, "buscar", 18, TEXTO_SEC, BLANCO).pack(side="left", padx=(10, 4))
        self.var_busqueda = tk.StringVar()
        entrada_busqueda = tk.Entry(busqueda, textvariable=self.var_busqueda,
                                    font=fuente(11), bg=BLANCO, fg=TEXTO, relief="flat",
                                    bd=0, highlightthickness=0, insertbackground=TEXTO,
                                    width=24)
        entrada_busqueda.pack(side="left", ipady=8, padx=(0, 10))
        entrada_busqueda.bind("<FocusIn>", lambda e: busqueda.configure(
            highlightbackground=PRIMARIO))
        entrada_busqueda.bind("<FocusOut>", lambda e: busqueda.configure(
            highlightbackground=BORDE))

        # Tabla
        tarj = tarjeta(self.contenido)
        tarj.pack(fill="both", expand=True, pady=(16, 0))
        pie = tk.Frame(tarj, bg=SUPERFICIE_ALT)
        pie.pack(side="bottom", fill="x")          # se empaca antes para no quedar tapado
        self.lbl_total = tk.Label(pie, text="", font=fuente(11, "bold"), fg=SECUNDARIO,
                                    bg=SUPERFICIE_ALT)
        self.lbl_total.pack(side="left", padx=20, pady=10)
        tk.Label(pie, text="Pasa el cursor sobre una fila para resaltarla.",
                    font=fuente(9), fg=TEXTO_SEC, bg=SUPERFICIE_ALT).pack(side="right", padx=20)

        marco = tk.Frame(tarj, bg=SUPERFICIE)
        marco.pack(fill="both", expand=True)
        marco.rowconfigure(0, weight=1)
        marco.columnconfigure(0, weight=1)

        columnas = [c[0] for c in ent["campos"]]
        tabla = ttk.Treeview(marco, columns=columnas, show="headings",
                                style="Nucleo.Treeview", selectmode="browse")
        barra_y = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview,
                                style="Nucleo.Vertical.TScrollbar")
        barra_x = ttk.Scrollbar(marco, orient="horizontal", command=tabla.xview,
                                style="Nucleo.Horizontal.TScrollbar")
        tabla.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        tabla.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")

        for columna, encabezado, ancho in zip(columnas, ent["encabezados"], ent["anchos"]):
            tabla.heading(columna, text=encabezado)
            tabla.column(columna, width=ancho, anchor="center" if columna == primero else "w")
        tabla.tag_configure("par", background=SUPERFICIE_ALT)
        tabla.tag_configure("impar", background=BLANCO)
        tabla.tag_configure("hover", background="#e8f1fb")
        tabla.bind("<Motion>", lambda e: self._hover_fila(tabla, e))
        tabla.bind("<Leave>", lambda e: self._quitar_hover(tabla))

        vacio = tk.Label(marco, text="", font=fuente(12), fg=TEXTO_SEC, bg=SUPERFICIE)

        error_sql = None
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            # ---- SQL empotrado: SELECT ----
            filas = self.ejecutar(ent["sql_consultar"], consulta=True)
        except pg.Error as error:
            filas, error_sql = [], error
        self.config(cursor="")
        filas = [[f"{v:.2f}" if isinstance(v, Decimal) else v for v in fila]
                    for fila in filas]

        def pintar(*_):
            filtro = self.var_busqueda.get().strip().casefold()
            for iid in tabla.get_children():
                tabla.delete(iid)
            self._fila_hover = None
            n = 0
            for fila in filas:
                if filtro and not any(filtro in str(v).casefold() for v in fila):
                    continue
                tabla.insert("", "end", values=fila,
                                tags=("par" if n % 2 == 0 else "impar",))
                n += 1
            self.lbl_total.config(text=f"Total = {len(filas)}" if not filtro
                                    else f"Mostrando {n} de {len(filas)}")
            if n == 0:
                vacio.config(text=("Sin resultados para la búsqueda." if filas else
                                    f"Aún no hay {ent['plural'].lower()} registrados."))
                vacio.place(relx=0.5, rely=0.5, anchor="center")
            else:
                vacio.place_forget()

        self.var_busqueda.trace_add("write", pintar)
        pintar()

        if error_sql is not None:
            self.mostrar_error_sql(error_sql)

    def _hover_fila(self, tabla, evento):
        """Resalta la fila bajo el cursor."""
        iid = tabla.identify_row(evento.y)
        if iid == self._fila_hover:
            return
        self._quitar_hover(tabla)
        if iid:
            tabla.item(iid, tags=("hover",))
            self._fila_hover = iid

    def _quitar_hover(self, tabla):
        iid, self._fila_hover = self._fila_hover, None
        if iid and tabla.exists(iid):
            tabla.item(iid, tags=("par" if tabla.index(iid) % 2 == 0 else "impar",))


if __name__ == "__main__":
    App().mainloop()