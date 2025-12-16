# Sistema de Evaluaciones Flask

Sistema de evaluaciones con múltiples opciones desarrollado en Flask para conectar a SQL Server.

## Características

- Login simple de usuarios desde base de datos
- Evaluaciones con preguntas de opción múltiple
- Respuestas aleatorias para cada pregunta
- Campo de comentarios opcional por pregunta
- Validación de respuestas vacías con confirmación
- Panel de administración con PIN
- Modificación de respuestas por parte del administrador

## Instalación

1. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

2. Asegúrate de tener instalado el driver ODBC para SQL Server en tu sistema.

## Configuración

### Base de Datos
- Servidor: s3.tecnolar.tech
- Base de datos: TecnolarWeb
- Usuario: shs
- Contraseña: (vacía)

### PIN de Administrador
El PIN por defecto es "1234". Puedes cambiarlo en la variable `ADMIN_PIN` en `app.py`.

## Estructura de la Base de Datos

### Tablas principales:
- **Usuarios**: Almacena usuarios y contraseñas
- **TemasEvaluaciones**: Temas disponibles para evaluar
- **Preguntas**: Preguntas por tema
- **PreguntasRespuestas**: Opciones de respuesta (la de mayor orden es la correcta)
- **Respuestas**: Respuestas de los usuarios

### Tablas adicionales para administración:
- **Evaluaciones**: Registro de evaluaciones completadas
- **TemasEvaluaciones**: Información completa de temas

## Uso

### Para ejecutar la aplicación:
```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

### Flujo de Usuario Normal:
1. Login con usuario/contraseña de la BD
2. Seleccionar tema de evaluación
3. Responder preguntas (opciones aleatorias)
4. Confirmar envío (si hay respuestas vacías)
5. Evaluación guardada

### Flujo de Administrador:
1. Acceso con PIN desde la pantalla de login
2. Ver lista de usuarios con evaluaciones
3. Revisar respuestas de cada usuario
4. Modificar respuestas (correcta/incorrecta)

## Funcionalidades Especiales

- **Respuestas aleatorias**: Las opciones se mezclan automáticamente
- **Respuesta correcta oculta**: Se identifica por el campo "orden" máximo
- **Confirmación de vacías**: Si faltan respuestas, requiere escribir "Confirmar"
- **Sin mostrar correctas**: No se muestran las respuestas correctas al finalizar
- **Sesiones guardadas**: Los datos de sesión se mantienen durante el uso

## Estructura de Archivos

```
/
├── app.py                          # Aplicación principal Flask
├── requirements.txt                # Dependencias
├── README.md                      # Este archivo
└── templates/                     # Plantillas HTML
    ├── base.html                  # Plantilla base
    ├── login.html                 # Login normal
    ├── menu.html                  # Menú de temas
    ├── evaluacion.html            # Formulario de evaluación
    ├── confirmar_evaluacion.html  # Confirmación respuestas vacías
    ├── admin_login.html           # Login administrador
    ├── admin_panel.html           # Panel principal admin
    └── admin_respuestas.html      # Ver/modificar respuestas
```

## Notas Importantes

- Las respuestas vacías se guardan como Respuesta=0 en la BD
- La respuesta correcta siempre es la de mayor valor en el campo "orden"
- El sistema mantiene sesiones activas hasta logout manual
- Bootstrap 5.1.3 se carga desde CDN para el diseño