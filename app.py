"""
Núcleo de Diagnóstico - Sistema (Avance 2)
Interfaz gráfica en Tkinter conectada a PostgreSQL (el mismo servidor de pgAdmin 4).

Flujo del programa:
    1. Login (usuario y contraseña de un rol de PostgreSQL).
    2. Ventana principal con imagen del núcleo de diagnóstico y el usuario logueado.
    3. Menú EMPLEADOS  -> Insertar empleado / Consultas generales
    4. Menú DOCTORES   -> Insertar doctor   / Consultas generales

Requisitos:   pip install psycopg2-binary pillow
Imagen:       guarda tu foto junto a este archivo como imagen_nucleo.jpg (o .jpeg/.png).
                Si no hay imagen, se dibuja una ilustración de respaldo.
Teclas:       Enter = iniciar sesión | F11 = pantalla completa | Esc = salir (en el login)
"""
import os
import tkinter as tk
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

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

# --------------------------------------------------------------------
# Datos del servidor (los mismos que ves en pgAdmin 4)
# --------------------------------------------------------------------
HOST = "localhost"
PUERTO = 5432
BASE_DE_DATOS = "Nucleo_De_Diagnostico"
NOMBRE_APP = "Nucleo_Diagnostico_GUI"   # aparece en pg_stat_activity (sirve para comprobar el login)

# --------------------------------------------------------------------
# Colores y fuente
# --------------------------------------------------------------------
AZUL_OSCURO = "#0b2545"
TURQUESA = "#14b8a6"
TURQUESA_OSCURO = "#0f766e"
BLANCO = "#ffffff"
FONDO = "#f4f8fb"
CAMPO = "#f1f5f9"
BORDE = "#cbd5e1"
TEXTO = "#0f172a"
GRIS = "#64748b"
FUENTE = "Segoe UI"

# --------------------------------------------------------------------
# Imagen principal
# --------------------------------------------------------------------
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

# --------------------------------------------------------------------
# Definición de las entidades (tablas) y SU SQL EMPOTRADO
#   campos: (columna, etiqueta del formulario, tipo, opciones)
# --------------------------------------------------------------------
SEXOS = ["FEMENINO", "MASCULINO"]
TURNOS = ["MATUTINO", "VESPERTINO", "NOCTURNO"]

ENTIDADES = {
    "Recepcionista": {
        "singular": "Recepcionista",
        "plural": "Recepcionistas",
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
    "Doctor": {
        "singular": "Doctor",
        "plural": "Doctores",
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
}

# --------------------------------------------------------------------
# Validación y conversión de los datos del formulario
# --------------------------------------------------------------------
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


def puntos_ecg(ancho, y0, k):
    """Puntos de una línea de electrocardiograma que cruza todo el ancho."""
    latido = [(0, 0), (30, 0), (42, -14), (54, 0), (80, 0), (90, 12),
            (102, -80), (114, 46), (124, 0), (150, 0), (168, -20),
            (186, 0), (230, 0)]
    puntos = []
    x0 = 0
    while x0 < ancho:
        for x, y in latido:
            puntos += [x0 + x * k, y0 + y * k]
        x0 += 230 * k
    return puntos


# --------------------------------------------------------------------
# Panel con la imagen del núcleo de diagnóstico
# --------------------------------------------------------------------
class Hero(tk.Canvas):
    """Imagen a todo el panel (foto o ilustración de respaldo) con texto encima."""

    def __init__(self, padre, kicker, titulo, subtitulo, pie):
        super().__init__(padre, highlightthickness=0, bg=AZUL_OSCURO)
        self.kicker, self.titulo, self.subtitulo, self.pie = kicker, titulo, subtitulo, pie
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

    def _ilustracion(self, w, h):
        """Respaldo: degradado + cruz médica + electrocardiograma."""
        pasos = 50
        for i in range(pasos):
            color = mezclar((11, 37, 69), (15, 118, 110), i / pasos)
            self.create_rectangle(0, h * i / pasos, w, h * (i + 1) / pasos + 1,
                                fill=color, outline=color)
        cx, cy = w * 0.5, h * 0.21
        r = min(w, h) * 0.11
        self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=TURQUESA, width=3)
        brazo, grosor = r * 0.55, r * 0.17
        self.create_rectangle(cx - grosor, cy - brazo, cx + grosor, cy + brazo,
                            fill=BLANCO, outline=BLANCO)
        self.create_rectangle(cx - brazo, cy - grosor, cx + brazo, cy + grosor,
                            fill=BLANCO, outline=BLANCO)
        k = max(0.9, h / 700)
        puntos = puntos_ecg(w, h * 0.43, k)
        self.create_line(*puntos, fill=TURQUESA_OSCURO, width=9, joinstyle="round")
        self.create_line(*puntos, fill=TURQUESA, width=3, joinstyle="round")

    def _dibujar(self):
        self._tarea = None
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50 or h < 50:
            return
        self.delete("all")

        if IMAGEN_ORIGINAL is not None:
            img = ImageOps.fit(IMAGEN_ORIGINAL, (w, h), Image.LANCZOS)
            capa = Image.new("RGB", (w, h), AZUL_OSCURO)
            img = Image.blend(img, capa, 0.55)   # oscurece para que el texto se lea
            self.foto = ImageTk.PhotoImage(img)
            self.create_image(0, 0, image=self.foto, anchor="nw")
        else:
            self._ilustracion(w, h)

        x = w * 0.08
        t_titulo = max(26, min(54, w // 18))
        t_sub = max(12, min(20, w // 70))
        t_peq = max(10, min(14, w // 90))
        self.create_text(x, h * 0.58, anchor="w", fill=TURQUESA, text=self.kicker,
                        font=(FUENTE, t_peq, "bold"))
        self.create_text(x, h * 0.67, anchor="w", fill=BLANCO, text=self.titulo,
                        font=(FUENTE, t_titulo, "bold"))
        self.create_text(x, h * 0.77, anchor="w", fill="#d7e3ee", text=self.subtitulo,
                        font=(FUENTE, t_sub))
        self.create_text(x, h * 0.92, anchor="w", fill="#9fb4c8", text=self.pie,
                        font=(FUENTE, t_peq))


def crear_campo(padre, texto, **opciones):
    """Etiqueta + caja de texto con el estilo del login."""
    tk.Label(padre, text=texto, font=(FUENTE, 10, "bold"), bg=BLANCO,
            fg=TEXTO, anchor="w").pack(fill="x", pady=(14, 4))
    campo = tk.Entry(padre, font=(FUENTE, 12), bg=CAMPO, fg=TEXTO,
                    relief="flat", insertbackground=TEXTO,
                    highlightthickness=1, highlightbackground=BORDE,
                     highlightcolor=TURQUESA, **opciones)
    campo.pack(fill="x", ipady=9)
    return campo


# --------------------------------------------------------------------
# Aplicación
# --------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Núcleo de Diagnóstico")
        self.configure(bg=BLANCO)
        self.attributes("-fullscreen", True)
        self.minsize(900, 600)
        self.protocol("WM_DELETE_WINDOW", self.salir)

        self.conexion = None
        self.usuario = None
        self.pantalla = None
        self.contenido = None
        self.campos = {}

        self._configurar_estilos()
        self.bind("<F11>", self.alternar_pantalla_completa)
        self.mostrar_login()

    # ---------------- utilidades ----------------
    def _configurar_estilos(self):
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("Nucleo.Treeview", rowheight=34, font=(FUENTE, 11),
                        background=BLANCO, fieldbackground=BLANCO,
                        foreground=TEXTO, bordercolor=BORDE)
        estilo.configure("Nucleo.Treeview.Heading", font=(FUENTE, 10, "bold"),
                        background=AZUL_OSCURO, foreground=BLANCO,
                        relief="flat", padding=8)
        estilo.map("Nucleo.Treeview.Heading", background=[("active", TURQUESA_OSCURO)])
        estilo.map("Nucleo.Treeview",
                background=[("selected", TURQUESA)],
                foreground=[("selected", BLANCO)])

    def alternar_pantalla_completa(self, event=None):
        self.attributes("-fullscreen", not self.attributes("-fullscreen"))
        return "break"

    def limpiar(self):
        if self.pantalla is not None:
            self.pantalla.destroy()
            self.pantalla = None

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

    def mostrar_error_sql(self, error):
        codigo = codigo_error(error)
        if codigo == "23505":
            mensaje = "Ya existe un registro con ese CÓDIGO. Usa uno diferente."
        elif codigo == "42P01":
            mensaje = ("La tabla no existe todavía. Créala primero desde pgAdmin 4 "
                    "(script avance2_pgadmin.sql, pasos 1 y 5).")
        elif codigo == "42501":
            mensaje = "Tu usuario de PostgreSQL no tiene permisos sobre esa tabla."
        elif codigo in ("23514", "22001", "22007", "22P02"):
            mensaje = f"Algún dato no cumple con las reglas de la tabla.\n\n{error}"
        else:
            mensaje = str(error)
        messagebox.showerror("Error de base de datos", mensaje, parent=self)

    # ---------------- pantalla: LOGIN ----------------
    def mostrar_login(self):
        self.limpiar()
        self.bind("<Return>", self.iniciar_sesion)
        self.bind("<Escape>", self.salir)

        pantalla = tk.Frame(self, bg=BLANCO)
        pantalla.pack(fill="both", expand=True)
        self.pantalla = pantalla
        pantalla.columnconfigure(0, weight=1)
        pantalla.columnconfigure(1, weight=0, minsize=480)
        pantalla.rowconfigure(0, weight=1)

        hero = Hero(pantalla, kicker="SISTEMA DE GESTIÓN CLÍNICA",
                    titulo="Núcleo de Diagnóstico",
                    subtitulo="Citas, consultas y diagnósticos\nen un solo lugar.",
                    pie="Pacientes  ·  Médicos  ·  Citas  ·  Consultas  ·  Medicamentos")
        hero.grid(row=0, column=0, sticky="nsew")

        panel = tk.Frame(pantalla, bg=BLANCO)
        panel.grid(row=0, column=1, sticky="nsew")

        tarjeta = tk.Frame(panel, bg=BLANCO, width=360)
        tarjeta.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(tarjeta, text="BIENVENIDO", font=(FUENTE, 10, "bold"),
                bg=BLANCO, fg=TURQUESA_OSCURO, anchor="w").pack(fill="x")
        tk.Label(tarjeta, text="Inicia sesión", font=(FUENTE, 26, "bold"),
                bg=BLANCO, fg=TEXTO, anchor="w").pack(fill="x", pady=(2, 0))
        tk.Label(tarjeta, text="Ingresa con tu usuario de PostgreSQL",
                font=(FUENTE, 10), bg=BLANCO, fg=GRIS, anchor="w").pack(fill="x", pady=(2, 8))

        self.entrada_usuario = crear_campo(tarjeta, "Usuario", width=32)
        self.entrada_contrasena = crear_campo(tarjeta, "Contraseña", width=32, show="*")

        self.ver_contrasena = tk.BooleanVar(value=False)
        tk.Checkbutton(tarjeta, text="Mostrar contraseña", variable=self.ver_contrasena,
                    command=lambda: self.entrada_contrasena.config(
                        show="" if self.ver_contrasena.get() else "*"),
                    font=(FUENTE, 9), bg=BLANCO, fg=GRIS, activebackground=BLANCO,
                    activeforeground=TEXTO, selectcolor=BLANCO, bd=0,
                    highlightthickness=0, cursor="hand2").pack(anchor="w", pady=(8, 0))

        entrar = tk.Button(tarjeta, text="Iniciar sesión", command=self.iniciar_sesion,
                        font=(FUENTE, 12, "bold"), bg=TURQUESA_OSCURO, fg=BLANCO,
                        activebackground=AZUL_OSCURO, activeforeground=BLANCO,
                        relief="flat", bd=0, cursor="hand2")
        entrar.pack(fill="x", ipady=10, pady=(22, 8))
        entrar.bind("<Enter>", lambda e: entrar.config(bg=AZUL_OSCURO))
        entrar.bind("<Leave>", lambda e: entrar.config(bg=TURQUESA_OSCURO))

        tk.Button(tarjeta, text="Salir", command=self.salir, font=(FUENTE, 10),
                bg=BLANCO, fg=GRIS, activebackground=CAMPO, activeforeground=TEXTO,
                relief="flat", bd=0, cursor="hand2").pack(fill="x", ipady=6)

        tk.Label(panel, text=f"Servidor: {HOST}:{PUERTO}  ·  Base de datos: {BASE_DE_DATOS}",
                font=(FUENTE, 8), bg=BLANCO, fg=GRIS).pack(side="bottom", pady=(0, 6))
        tk.Label(panel, text="F11: pantalla completa   ·   Esc: salir",
                font=(FUENTE, 8), bg=BLANCO, fg=BORDE).pack(side="bottom")

        self.entrada_usuario.focus()

    def iniciar_sesion(self, event=None):
        usuario = self.entrada_usuario.get().strip()
        contrasena = self.entrada_contrasena.get()

        if not usuario or not contrasena:
            messagebox.showwarning("Datos incompletos",
                                "Escribe tu usuario y tu contraseña.", parent=self)
            return

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
            messagebox.showerror("Error de conexión", mensaje, parent=self)
            self.entrada_contrasena.delete(0, tk.END)
            self.entrada_contrasena.focus()
            return

        self.conexion = conexion
        self.usuario = usuario
        self.mostrar_principal()

    # ---------------- pantalla: PRINCIPAL ----------------
    def mostrar_principal(self):
        self.limpiar()
        self.unbind("<Return>")
        self.unbind("<Escape>")

        pantalla = tk.Frame(self, bg=FONDO)
        pantalla.pack(fill="both", expand=True)
        self.pantalla = pantalla

        # Barra superior (como el menú de una página web)
        barra = tk.Frame(pantalla, bg=AZUL_OSCURO)
        barra.pack(fill="x")
        tk.Label(barra, text="Núcleo de Diagnóstico", font=(FUENTE, 15, "bold"),
                bg=AZUL_OSCURO, fg=BLANCO).pack(side="left", padx=(24, 30), pady=12)

        def boton_barra(texto, comando, lado="left"):
            b = tk.Button(barra, text=texto, command=comando, font=(FUENTE, 10, "bold"),
                        bg=AZUL_OSCURO, fg=BLANCO, activebackground=TURQUESA_OSCURO,
                        activeforeground=BLANCO, relief="flat", bd=0,
                        padx=16, pady=14, cursor="hand2")
            b.pack(side=lado)
            return b

        boton_barra("INICIO", self.mostrar_inicio)

        for clave, ent in ENTIDADES.items():
            menu_boton = tk.Menubutton(barra, text=f"{ent['plural'].upper()}  ▾",
                                    font=(FUENTE, 10, "bold"), bg=AZUL_OSCURO,
                                    fg=BLANCO, activebackground=TURQUESA_OSCURO,
                                    activeforeground=BLANCO, relief="flat", bd=0,
                                    indicatoron=False, padx=16, pady=14,
                                    cursor="hand2")
            menu = tk.Menu(menu_boton, tearoff=0, font=(FUENTE, 11), bg=BLANCO,
                        fg=TEXTO, activebackground=TURQUESA_OSCURO,
                        activeforeground=BLANCO, bd=0)
            menu.add_command(label=f"Insertar {ent['singular']}",
                            command=lambda c=clave: self.mostrar_insertar(c))
            menu.add_command(label="Consultas generales",
                            command=lambda c=clave: self.mostrar_consulta(c))
            menu_boton.config(menu=menu)
            menu_boton.pack(side="left")

        boton_barra("Salir", self.salir, lado="right")
        boton_barra("Cerrar sesión", self.cerrar_sesion, lado="right")
        tk.Label(barra, text=f"Usuario: {self.usuario}", font=(FUENTE, 10),
                bg=AZUL_OSCURO, fg="#9fe7de").pack(side="right", padx=16)

        self.contenido = tk.Frame(pantalla, bg=FONDO)
        self.contenido.pack(fill="both", expand=True)
        self.mostrar_inicio()

    def cerrar_sesion(self):
        self.cerrar_conexion()
        self.usuario = None
        self.mostrar_login()

    def vaciar_contenido(self):
        for widget in self.contenido.winfo_children():
            widget.destroy()

    # ---- Inicio: imagen del núcleo de diagnóstico + usuario logueado ----
    def mostrar_inicio(self):
        self.vaciar_contenido()
        hero = Hero(self.contenido, kicker="SESIÓN INICIADA",
                    titulo="Núcleo de Diagnóstico",
                    subtitulo=f"Bienvenido(a), usuario: {self.usuario}",
                    pie="Usa los menús EMPLEADOS y DOCTORES de la barra superior")
        hero.pack(fill="both", expand=True)

    # ---- Insertar (empleado / doctor) ----
    def mostrar_insertar(self, clave):
        ent = ENTIDADES[clave]
        self.vaciar_contenido()

        fondo = tk.Frame(self.contenido, bg=FONDO)
        fondo.pack(fill="both", expand=True)
        tarjeta = tk.Frame(fondo, bg=BLANCO, padx=40, pady=28,
                        highlightthickness=1, highlightbackground=BORDE)
        tarjeta.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(tarjeta, text=f"Insertar {ent['singular']}", font=(FUENTE, 20, "bold"),
                bg=BLANCO, fg=TEXTO).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(tarjeta, text="Llena todos los datos y presiona Guardar.",
                font=(FUENTE, 10), bg=BLANCO, fg=GRIS).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.campos = {}
        for i, (columna, etiqueta, tipo, opciones) in enumerate(ent["campos"]):
            fila, col = divmod(i, 2)
            celda = tk.Frame(tarjeta, bg=BLANCO)
            celda.grid(row=fila + 2, column=col, sticky="ew", pady=6,
                    padx=(0, 0) if col == 0 else (24, 0))
            tk.Label(celda, text=etiqueta, font=(FUENTE, 10, "bold"),
                    bg=BLANCO, fg=TEXTO, anchor="w").pack(fill="x", pady=(0, 3))
            if tipo == "lista":
                widget = ttk.Combobox(celda, values=opciones, state="readonly",
                                    font=(FUENTE, 11), width=32)
            else:
                widget = tk.Entry(celda, font=(FUENTE, 11), bg=CAMPO, fg=TEXTO,
                                relief="flat", insertbackground=TEXTO, width=34,
                                highlightthickness=1, highlightbackground=BORDE,
                                highlightcolor=TURQUESA,
                                show="*" if tipo == "password" else "")
            widget.pack(fill="x", ipady=6)
            self.campos[columna] = widget

        # Sugerir el siguiente código disponible (se puede cambiar)
        try:
            siguiente = self.ejecutar(ent["sql_siguiente"], consulta=True)[0][0]
            self.campos["codigo"].insert(0, str(siguiente))
        except pg.Error:
            pass   # si la tabla no existe, el error se mostrará al guardar

        fila_final = len(ent["campos"]) // 2 + 3
        self.ver_pass = tk.BooleanVar(value=False)
        tk.Checkbutton(tarjeta, text="Mostrar contraseña", variable=self.ver_pass,
                    command=lambda: self.campos["contrasena"].config(
                        show="" if self.ver_pass.get() else "*"),
                    font=(FUENTE, 9), bg=BLANCO, fg=GRIS, activebackground=BLANCO,
                    selectcolor=BLANCO, bd=0, highlightthickness=0,
                    cursor="hand2").grid(row=fila_final, column=0, sticky="w", pady=(6, 0))

        botones = tk.Frame(tarjeta, bg=BLANCO)
        botones.grid(row=fila_final + 1, column=0, columnspan=2, sticky="e", pady=(18, 0))
        tk.Button(botones, text="Limpiar", command=lambda: self.mostrar_insertar(clave),
                font=(FUENTE, 11), bg=CAMPO, fg=TEXTO, activebackground=BORDE,
                relief="flat", bd=0, padx=22, pady=9, cursor="hand2").pack(side="left", padx=8)
        tk.Button(botones, text="Guardar", command=lambda: self.guardar(clave),
                font=(FUENTE, 11, "bold"), bg=TURQUESA_OSCURO, fg=BLANCO,
                activebackground=AZUL_OSCURO, activeforeground=BLANCO,
                relief="flat", bd=0, padx=26, pady=9, cursor="hand2").pack(side="left")

        self.campos["codigo"].focus()

    def guardar(self, clave):
        ent = ENTIDADES[clave]
        valores = []
        for columna, etiqueta, tipo, _ in ent["campos"]:
            texto = self.campos[columna].get()
            if tipo != "password":
                texto = texto.strip()
            try:
                valores.append(convertir(tipo, texto, etiqueta))
            except ValueError as error:
                messagebox.showwarning("Dato no válido", str(error), parent=self)
                self.campos[columna].focus()
                return

        try:
            # ---- SQL empotrado: INSERT ----
            self.ejecutar(ent["sql_insertar"], valores)
        except pg.Error as error:
            self.mostrar_error_sql(error)
            return

        messagebox.showinfo("Registro guardado",
                            f"Se insertó correctamente al {ent['singular']}:\n{valores[1]}",
                            parent=self)
        self.mostrar_insertar(clave)   # formulario limpio con el siguiente código

    # ---- Consultas generales (empleado / doctor) ----
    def mostrar_consulta(self, clave):
        ent = ENTIDADES[clave]
        self.vaciar_contenido()

        fondo = tk.Frame(self.contenido, bg=FONDO)
        fondo.pack(fill="both", expand=True)

        cabecera = tk.Frame(fondo, bg=FONDO)
        cabecera.pack(fill="x", padx=40, pady=(28, 12))
        tk.Label(cabecera, text=f"Consultas generales · {ent['plural']}",
                font=(FUENTE, 20, "bold"), bg=FONDO, fg=TEXTO).pack(side="left")
        tk.Button(cabecera, text="Actualizar", command=lambda: self.mostrar_consulta(clave),
                font=(FUENTE, 10, "bold"), bg=TURQUESA_OSCURO, fg=BLANCO,
                activebackground=AZUL_OSCURO, activeforeground=BLANCO,
                relief="flat", bd=0, padx=18, pady=8, cursor="hand2").pack(side="right")

        marco = tk.Frame(fondo, bg=FONDO)
        marco.pack(fill="both", expand=True, padx=40)
        marco.rowconfigure(0, weight=1)
        marco.columnconfigure(0, weight=1)

        columnas = [c[0] for c in ent["campos"]]
        tabla = ttk.Treeview(marco, columns=columnas, show="headings",
                            style="Nucleo.Treeview")
        barra_y = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
        barra_x = ttk.Scrollbar(marco, orient="horizontal", command=tabla.xview)
        tabla.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        tabla.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")

        for columna, encabezado, ancho in zip(columnas, ent["encabezados"], ent["anchos"]):
            tabla.heading(columna, text=encabezado)
            tabla.column(columna, width=ancho, anchor="center" if columna == "codigo" else "w")
        tabla.tag_configure("par", background="#eef6f9")
        tabla.tag_configure("impar", background=BLANCO)

        try:
            # ---- SQL empotrado: SELECT ----
            filas = self.ejecutar(ent["sql_consultar"], consulta=True)
        except pg.Error as error:
            filas = []
            self.mostrar_error_sql(error)

        for i, fila in enumerate(filas):
            fila = [f"{v:.2f}" if isinstance(v, Decimal) else v for v in fila]
            tabla.insert("", "end", values=fila, tags=("par" if i % 2 == 0 else "impar",))

        tk.Label(fondo, text=f"Total = {len(filas)}", font=(FUENTE, 12, "bold"),
                bg=FONDO, fg=TURQUESA_OSCURO).pack(anchor="w", padx=40, pady=(10, 20))


if __name__ == "__main__":
    App().mainloop()