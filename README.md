# Núcleo de Diagnóstico

Aplicación de escritorio desarrollada en Python con Tkinter y PostgreSQL, como proyecto académico de gestión y diagnóstico.

## Tecnologías utilizadas

- Python
- Tkinter y ttk
- PostgreSQL
- psycopg2
- Pillow

## Requisitos

- Python instalado.
- PostgreSQL instalado y configurado.
- Base de datos `Nucleo_De_Diagnostico`.
- Dependencias de Python indicadas en `requirements.txt`.

## Instalación

1. Clonar el repositorio:

   ```bash
   git clone URL_DEL_REPOSITORIO
   ```

2. Entrar en la carpeta:

   ```bash
   cd nucleo-diagnostico
   ```

3. Crear un entorno virtual:

   ```bash
   python -m venv .venv
   ```

4. Activarlo en Windows:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

5. Instalar las dependencias:

   ```bash
   python -m pip install -r requirements.txt
   ```

## Configuración de PostgreSQL

Cada integrante debe contar con su propia instalación de PostgreSQL y una base de datos compatible con la aplicación.

Actualmente, la configuración de conexión se encuentra en `app.py`:

- Host: `localhost`
- Puerto: `5432`
- Base de datos: `Nucleo_De_Diagnostico`

Los parámetros deberán ajustarse si la configuración local de PostgreSQL es diferente.

## Ejecutar la aplicación

```bash
python app.py
```

## Trabajo colaborativo

El proyecto utiliza Git y GitHub para compartir el código y coordinar el desarrollo entre los integrantes del equipo.

Se recomienda trabajar en ramas independientes y utilizar Pull Requests para integrar cambios en la rama principal `main`.