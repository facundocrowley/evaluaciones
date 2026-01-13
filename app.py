from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pyodbc
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Cambiar por una clave más segura

# PIN para usuario avanzado
ADMIN_PIN = "15953261"  # Cambiar según necesites

# Configuración de la base de datos
DB_CONFIG = {
    'server': 's3.tecnolar.tech',
    'database': 'TecnolarWeb',
    'username': 'shs',
    'password': '',
    'driver': 'SQL Server'
}

def get_db_connection():
    """Crear conexión a la base de datos"""
    EntornoPrueba=1
    
    try:
        
        conn_str = (
            f"DRIVER={{{DB_CONFIG['driver']}}};"
            f"SERVER={DB_CONFIG['server']};"
            f"DATABASE={DB_CONFIG['database']};"
            f"UID={DB_CONFIG['username']};"
            f"PWD={DB_CONFIG['password']};"
            
        )
        if EntornoPrueba==0:
            conn_str =+ "Encrypt=yes;TrustServerCertificate=yes;"
            print(conn_str)
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None

@app.route('/')
def index():
    """Página principal - redirige al login"""
    if 'user_id' in session:
        return redirect(url_for('menu'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT Codigo, Usuario FROM Usuarios WHERE Usuario = ? AND Password = ?", (usuario, password))
                user = cursor.fetchone()
                
                if user:
                    session['user_id'] = user[0]
                    session['username'] = user[1]
                    return redirect(url_for('menu'))
                else:
                    flash('Usuario o contraseña incorrectos')
            except Exception as e:
                flash(f'Error en la consulta: {e}')
            finally:
                conn.close()
        else:
            flash('Error de conexión a la base de datos')
    
    return render_template('login.html')

@app.route('/perfil')
def perfil():
    """Perfil del usuario con sus evaluaciones"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    evaluaciones = []
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Obtener evaluaciones del usuario
            cursor.execute("""
                SELECT 
                    e.Codigo,
                    te.Descripcion as Tema,
                    e.Fecha,
                    e.Nota,
                    e.NotaAprobado,
                    e.Observacion,
                    (SELECT COUNT(*) FROM Respuestas WHERE Evaluacion = e.Codigo) as TotalRespuestas,
                    (SELECT COUNT(*) FROM Respuestas r 
                     INNER JOIN PreguntasRespuestas pr ON r.Respuesta = pr.ID 
                     WHERE r.Evaluacion = e.Codigo AND pr.orden = 
                        (SELECT MAX(orden) FROM PreguntasRespuestas WHERE Pregunta = r.Pregunta)) as RespuestasCorrectas
                FROM Evaluaciones e
                INNER JOIN TemasEvaluaciones te ON e.Tema = te.Codigo
                WHERE e.Usuario = ?
                ORDER BY e.Fecha DESC
            """, (session['user_id'],))
            evaluaciones = cursor.fetchall()
            
        except Exception as e:
            flash(f'Error cargando evaluaciones: {e}')
        finally:
            conn.close()
    
    return render_template('perfil.html', evaluaciones=evaluaciones)

@app.route('/ver_mis_respuestas/<int:evaluacion_id>')
def ver_mis_respuestas(evaluacion_id):
    """Ver las respuestas propias de una evaluación"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    respuestas = []
    evaluacion_info = None
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Verificar que la evaluación pertenece al usuario
            cursor.execute("""
                SELECT e.Codigo, te.Descripcion, e.Fecha, e.Nota, e.NotaAprobado, e.Observacion
                FROM Evaluaciones e
                INNER JOIN TemasEvaluaciones te ON e.Tema = te.Codigo
                WHERE e.Codigo = ? AND e.Usuario = ?
            """, (evaluacion_id, session['user_id']))
            evaluacion_info = cursor.fetchone()
            
            if not evaluacion_info:
                flash('No tienes acceso a esta evaluación')
                return redirect(url_for('perfil'))
            
            # Obtener respuestas
            cursor.execute("""
                SELECT 
                    p.Detalle as Pregunta,
                    pr.Respuesta as OpcionElegida,
                    r.Detalle as ComentarioUsuario,
                    (SELECT MAX(orden) FROM PreguntasRespuestas WHERE Pregunta = p.ID) as OrdenCorrecto,
                    pr.orden as OrdenElegido
                FROM Respuestas r
                INNER JOIN Preguntas p ON r.Pregunta = p.ID
                LEFT JOIN PreguntasRespuestas pr ON r.Respuesta = pr.ID
                WHERE r.Evaluacion = ?
                ORDER BY r.ID
            """, (evaluacion_id,))
            respuestas = cursor.fetchall()
            
        except Exception as e:
            flash(f'Error cargando respuestas: {e}')
        finally:
            conn.close()
    
    return render_template('ver_mis_respuestas.html', respuestas=respuestas, evaluacion=evaluacion_info)

@app.route('/menu')
def menu():
    """Menú principal después del login"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    temas = []
    
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Codigo, Descripcion, 
                       ISNULL(Habilitado, '') as Habilitado
                FROM TemasEvaluaciones 
                ORDER BY Descripcion
            """)
            temas_raw = cursor.fetchall()
            
            # Procesar cada tema para verificar si el usuario está habilitado
            user_id_str = str(session['user_id'])
            
            for tema in temas_raw:
                tema_id = tema[0]
                tema_descripcion = tema[1]
                habilitados = tema[2] if tema[2] else ''
                
                # Verificar si el usuario está en la lista de habilitados
                usuarios_habilitados = [u.strip() for u in habilitados.split(',') if u.strip()]
                esta_habilitado = user_id_str in usuarios_habilitados
                
                # Verificar si ya realizó esta evaluación
                cursor.execute("""
                    SELECT COUNT(*) FROM Evaluaciones 
                    WHERE Usuario = ? AND Tema = ?
                """, (session['user_id'], tema_id))
                ya_realizo = cursor.fetchone()[0] > 0
                
                temas.append({
                    'codigo': tema_id,
                    'descripcion': tema_descripcion,
                    'habilitado': esta_habilitado,
                    'ya_realizo': ya_realizo
                })
                
        except Exception as e:
            flash(f'Error cargando temas: {e}')
        finally:
            conn.close()
    
    return render_template('menu.html', temas=temas)

@app.route('/evaluacion/<int:tema_id>')
def evaluacion(tema_id):
    """Página de evaluación para un tema específico"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    preguntas = []
    tema_info = None
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Verificar si el usuario está habilitado para este tema
            cursor.execute("""
                SELECT Descripcion, ISNULL(Habilitado, '') as Habilitado 
                FROM TemasEvaluaciones WHERE Codigo = ?
            """, (tema_id,))
            tema_data = cursor.fetchone()
            
            if not tema_data:
                flash('Tema no encontrado')
                return redirect(url_for('menu'))
            
            tema_info = tema_data[0]
            habilitados = tema_data[1] if tema_data[1] else ''
            
            # Verificar si el usuario está en la lista de habilitados
            user_id_str = str(session['user_id'])
            usuarios_habilitados = [u.strip() for u in habilitados.split(',') if u.strip()]
            
            if user_id_str not in usuarios_habilitados:
                flash('No tienes permisos para acceder a esta evaluación')
                return redirect(url_for('menu'))
            
            # Verificar si ya realizó esta evaluación
            cursor.execute("""
                SELECT COUNT(*) FROM Evaluaciones 
                WHERE Usuario = ? AND Tema = ?
            """, (session['user_id'], tema_id))
            ya_realizo = cursor.fetchone()[0] > 0
            
            if ya_realizo:
                flash('Ya has realizado esta evaluación anteriormente')
                return redirect(url_for('menu'))
            
            # Obtener preguntas del tema
            cursor.execute("SELECT ID, Detalle FROM Preguntas WHERE Tema = ? ORDER BY ID", (tema_id,))
            preguntas_raw = cursor.fetchall()
            
            # Para cada pregunta, obtener sus respuestas
            for pregunta in preguntas_raw:
                cursor.execute("""
                    SELECT ID, Respuesta, orden 
                    FROM PreguntasRespuestas 
                    WHERE Pregunta = ? 
                    ORDER BY orden
                """, (pregunta[0],))
                respuestas = cursor.fetchall()
                
                # Mezclar las respuestas aleatoriamente
                respuestas_list = list(respuestas)
                random.shuffle(respuestas_list)
                
                preguntas.append({
                    'id': pregunta[0],
                    'detalle': pregunta[1],
                    'respuestas': respuestas_list
                })
            
        except Exception as e:
            flash(f'Error cargando evaluación: {e}')
            return redirect(url_for('menu'))
        finally:
            conn.close()
    
    session['tema_actual'] = tema_id
    return render_template('evaluacion.html', preguntas=preguntas, tema=tema_info)

@app.route('/guardar_evaluacion', methods=['POST'])
def guardar_evaluacion():
    """Guardar las respuestas de la evaluación"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    respuestas_vacias = []
    conn = get_db_connection()
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Verificar respuestas vacías
            for key in request.form:
                if key.startswith('pregunta_'):
                    pregunta_id = key.split('_')[1]
                    if not request.form[key]:
                        # Obtener el detalle de la pregunta para mostrar al usuario
                        cursor.execute("SELECT Detalle FROM Preguntas WHERE ID = ?", (pregunta_id,))
                        pregunta_detalle = cursor.fetchone()
                        if pregunta_detalle:
                            respuestas_vacias.append(pregunta_detalle[0])
            
            # Si hay respuestas vacías y no se confirmó
            if respuestas_vacias and request.form.get('confirmacion') != 'Confirmar':
                return render_template('confirmar_evaluacion.html', 
                                     respuestas_vacias=respuestas_vacias, 
                                     form_data=request.form)
            
            # Obtener el tema de la evaluación actual
            tema_id = session.get('tema_actual')
            if not tema_id:
                flash('Error: No se pudo determinar el tema de la evaluación')
                return redirect(url_for('menu'))
            
            # Obtener NotaAprobado del tema
            cursor.execute("SELECT NotaAprueba FROM TemasEvaluaciones WHERE Codigo = ?", (tema_id,))
            nota_aprueba_result = cursor.fetchone()
            nota_aprueba = nota_aprueba_result[0] if nota_aprueba_result else 7.0
            
            # Crear registro en tabla Evaluaciones
            cursor.execute("""
                INSERT INTO Evaluaciones (Fecha, Usuario, Tema, FechaCarga, UsuarioCarga, Nota, NotaAprobado, Observacion)
                VALUES (GETDATE(), ?, ?, GETDATE(), ?, 0, ?, '')
            """, (session['user_id'], tema_id, session['user_id'], nota_aprueba))
            
            # Obtener el ID de la evaluación recién creada
            cursor.execute("SELECT @@IDENTITY")
            evaluacion_id = cursor.fetchone()[0]
            
            # Guardar respuestas asociadas a la evaluación
            for key in request.form:
                if key.startswith('pregunta_'):
                    pregunta_id = int(key.split('_')[1])
                    respuesta_id = int(request.form[key]) if request.form[key] else 0
                    detalle = request.form.get(f'detalle_{pregunta_id}', '')
                    
                    cursor.execute("""
                        INSERT INTO Respuestas (Evaluacion, Respuesta, Usuario, Detalle, Pregunta)
                        VALUES (?, ?, ?, ?, ?)
                    """, (evaluacion_id, respuesta_id, session['user_id'], detalle, pregunta_id))
            
            conn.commit()
            flash('Evaluación guardada correctamente')
            
        except Exception as e:
            flash(f'Error guardando evaluación: {e}')
        finally:
            conn.close()
    
    return redirect(url_for('menu'))

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    """Login para usuario administrador"""
    if request.method == 'POST':
        pin = request.form['pin']
        if pin == ADMIN_PIN:
            session['is_admin'] = True
            return redirect(url_for('admin_panel'))
        else:
            flash('PIN incorrecto')
    
    return render_template('admin_login.html')

@app.route('/admin_panel')
def admin_panel():
    """Panel de administración"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    evaluaciones = []
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Obtener evaluaciones con sus calificaciones calculadas
            cursor.execute("""
                SELECT 
                    e.Codigo as EvaluacionID,
                    u.Codigo as UsuarioID,
                    u.Usuario as UsuarioNombre,
                    e.Tema as TemaID,
                    te.Descripcion as TemaNombre,
                    e.Fecha,
                    e.Nota,
                    e.NotaAprobado,
                    e.Observacion,
                    (SELECT COUNT(*) FROM Preguntas WHERE Tema = e.Tema) as TotalPreguntas,
                    (SELECT COUNT(*)
                     FROM Respuestas r
                     INNER JOIN PreguntasRespuestas pr ON r.Respuesta = pr.ID
                     INNER JOIN Preguntas p ON pr.Pregunta = p.ID
                     WHERE r.Evaluacion = e.Codigo 
                     AND pr.orden = (SELECT MAX(orden) FROM PreguntasRespuestas WHERE Pregunta = p.ID)
                    ) as RespuestasCorrectas
                FROM Evaluaciones e
                INNER JOIN Usuarios u ON e.Usuario = u.Codigo
                INNER JOIN TemasEvaluaciones te ON e.Tema = te.Codigo
                ORDER BY u.Usuario, te.Descripcion, e.Fecha DESC
            """)
            evaluaciones_raw = cursor.fetchall()
            
            # Procesar y actualizar calificaciones
            for eval_data in evaluaciones_raw:
                evaluacion_id = eval_data[0]
                total_preguntas = eval_data[9]
                respuestas_correctas = eval_data[10]
                nota_aprobado = float(eval_data[7])  # Convertir decimal a float
                
                # Calcular nueva calificación
                if total_preguntas > 0:
                    nueva_calificacion = round((10.0 * respuestas_correctas) / total_preguntas, 2)
                else:
                    nueva_calificacion = 0.0
                
                # Actualizar la calificación en la base de datos si ha cambiado
                if float(eval_data[6]) != nueva_calificacion:  # Convertir decimal a float
                    cursor.execute("UPDATE Evaluaciones SET Nota = ? WHERE Codigo = ?", 
                                 (nueva_calificacion, evaluacion_id))
                
                evaluaciones.append((
                    evaluacion_id,          # 0 - EvaluacionID
                    eval_data[1],          # 1 - UsuarioID
                    eval_data[2],          # 2 - UsuarioNombre
                    eval_data[3],          # 3 - TemaID
                    eval_data[4],          # 4 - TemaNombre
                    eval_data[5],          # 5 - Fecha
                    nueva_calificacion,    # 6 - Nota (calculada)
                    nota_aprobado,         # 7 - NotaAprobado (convertida a float)
                    eval_data[8],          # 8 - Observacion
                    total_preguntas,       # 9 - TotalPreguntas
                    respuestas_correctas   # 10 - RespuestasCorrectas
                ))
            
            conn.commit()
            
        except Exception as e:
            flash(f'Error cargando datos: {e}')
        finally:
            conn.close()
    
    return render_template('admin_panel.html', evaluaciones=evaluaciones)

@app.route('/admin_ver_respuestas/<int:evaluacion_id>')
def admin_ver_respuestas(evaluacion_id):
    """Ver respuestas de una evaluación específica"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    respuestas = []
    evaluacion_info = None
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Información de la evaluación
            cursor.execute("""
                SELECT e.Codigo, u.Usuario, te.Descripcion, e.Fecha, e.Nota, e.NotaAprobado, e.Observacion
                FROM Evaluaciones e
                INNER JOIN Usuarios u ON e.Usuario = u.Codigo
                INNER JOIN TemasEvaluaciones te ON e.Tema = te.Codigo
                WHERE e.Codigo = ?
            """, (evaluacion_id,))
            evaluacion_info = cursor.fetchone()
            
            # Obtener todas las respuestas de esta evaluación con JOIN directo
            cursor.execute("""
                SELECT 
                    r.ID,
                    p.Detalle as Pregunta,
                    pr.Respuesta as OpcionElegida,
                    r.Detalle as ComentarioUsuario,
                    p.ID as PreguntaID,
                    (SELECT MAX(orden) FROM PreguntasRespuestas WHERE Pregunta = p.ID) as OrdenCorrecto,
                    pr.orden as OrdenElegido
                FROM Respuestas r
                INNER JOIN Preguntas p ON r.Pregunta = p.ID
                LEFT JOIN PreguntasRespuestas pr ON r.Respuesta = pr.ID
                WHERE r.Evaluacion = ?
                ORDER BY r.ID
            """, (evaluacion_id,))
            respuestas = cursor.fetchall()
            
        except Exception as e:
            flash(f'Error cargando respuestas: {e}')
        finally:
            conn.close()
    
    return render_template('admin_respuestas.html', respuestas=respuestas, evaluacion=evaluacion_info)

@app.route('/admin_actualizar_observacion', methods=['POST'])
def admin_actualizar_observacion():
    """Actualizar observación de una evaluación"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    evaluacion_id = request.form['evaluacion_id']
    observacion = request.form['observacion']
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE Evaluaciones SET Observacion = ? WHERE Codigo = ?", 
                         (observacion, evaluacion_id))
            conn.commit()
            flash('Observación actualizada correctamente')
        except Exception as e:
            flash(f'Error actualizando observación: {e}')
        finally:
            conn.close()
    
    return redirect(url_for('admin_panel'))

@app.route('/admin_preguntas')
def admin_preguntas():
    """Panel de gestión de preguntas para administrador"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    preguntas = []
    temas = []
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Obtener todas las preguntas con información del tema
            cursor.execute("""
                SELECT p.ID, p.Detalle, t.Descripcion, p.Tema,
                       (SELECT COUNT(*) FROM PreguntasRespuestas WHERE Pregunta = p.ID) as CantRespuestas
                FROM Preguntas p
                INNER JOIN TemasEvaluaciones t ON p.Tema = t.Codigo
                ORDER BY t.Descripcion, p.ID
            """)
            preguntas = cursor.fetchall()
            
            # Obtener todos los temas para el formulario
            cursor.execute("SELECT Codigo, Descripcion FROM TemasEvaluaciones ORDER BY Descripcion")
            temas = cursor.fetchall()
            
        except Exception as e:
            flash(f'Error cargando preguntas: {e}')
        finally:
            conn.close()
    
    return render_template('admin_preguntas.html', preguntas=preguntas, temas=temas)

@app.route('/admin_nueva_pregunta', methods=['GET', 'POST'])
def admin_nueva_pregunta():
    """Crear nueva pregunta"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        tema_id = request.form['tema']
        detalle = request.form['detalle']
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Preguntas (Tema, Detalle) VALUES (?, ?)", (tema_id, detalle))
                conn.commit()
                flash('Pregunta creada correctamente')
                return redirect(url_for('admin_preguntas'))
            except Exception as e:
                flash(f'Error creando pregunta: {e}')
            finally:
                conn.close()
    
    # GET - mostrar formulario
    conn = get_db_connection()
    temas = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT Codigo, Descripcion FROM TemasEvaluaciones ORDER BY Descripcion")
            temas = cursor.fetchall()
        except Exception as e:
            flash(f'Error cargando temas: {e}')
        finally:
            conn.close()
    
    return render_template('admin_nueva_pregunta.html', temas=temas)

@app.route('/admin_editar_pregunta/<int:pregunta_id>', methods=['GET', 'POST'])
def admin_editar_pregunta(pregunta_id):
    """Editar pregunta existente"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        tema_id = request.form['tema']
        detalle = request.form['detalle']
        
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE Preguntas SET Tema = ?, Detalle = ? WHERE ID = ?", 
                             (tema_id, detalle, pregunta_id))
                conn.commit()
                flash('Pregunta actualizada correctamente')
                return redirect(url_for('admin_preguntas'))
            except Exception as e:
                flash(f'Error actualizando pregunta: {e}')
            finally:
                conn.close()
    
    # GET - mostrar formulario con datos actuales
    pregunta = None
    temas = []
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Obtener datos de la pregunta
            cursor.execute("SELECT ID, Tema, Detalle FROM Preguntas WHERE ID = ?", (pregunta_id,))
            pregunta = cursor.fetchone()
            
            # Obtener todos los temas
            cursor.execute("SELECT Codigo, Descripcion FROM TemasEvaluaciones ORDER BY Descripcion")
            temas = cursor.fetchall()
            
        except Exception as e:
            flash(f'Error cargando datos: {e}')
        finally:
            conn.close()
    
    if not pregunta:
        flash('Pregunta no encontrada')
        return redirect(url_for('admin_preguntas'))
    
    return render_template('admin_editar_pregunta.html', pregunta=pregunta, temas=temas)

@app.route('/admin_eliminar_pregunta/<int:pregunta_id>', methods=['POST'])
def admin_eliminar_pregunta(pregunta_id):
    """Eliminar pregunta y todas sus respuestas"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Primero eliminar las respuestas de usuarios relacionadas
            cursor.execute("""
                DELETE FROM Respuestas 
                WHERE Respuesta IN (
                    SELECT ID FROM PreguntasRespuestas WHERE Pregunta = ?
                )
            """, (pregunta_id,))
            
            # Luego eliminar las opciones de respuesta
            cursor.execute("DELETE FROM PreguntasRespuestas WHERE Pregunta = ?", (pregunta_id,))
            
            # Finalmente eliminar la pregunta
            cursor.execute("DELETE FROM Preguntas WHERE ID = ?", (pregunta_id,))
            
            conn.commit()
            flash('Pregunta eliminada correctamente')
            
        except Exception as e:
            flash(f'Error eliminando pregunta: {e}')
        finally:
            conn.close()
    
    return redirect(url_for('admin_preguntas'))

@app.route('/admin_respuestas_pregunta/<int:pregunta_id>')
def admin_respuestas_pregunta(pregunta_id):
    """Gestionar respuestas de una pregunta específica"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    pregunta_info = None
    respuestas = []
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Información de la pregunta
            cursor.execute("""
                SELECT p.ID, p.Detalle, t.Descripcion 
                FROM Preguntas p 
                INNER JOIN TemasEvaluaciones t ON p.Tema = t.Codigo 
                WHERE p.ID = ?
            """, (pregunta_id,))
            pregunta_info = cursor.fetchone()
            
            # Respuestas de la pregunta ordenadas por orden
            cursor.execute("""
                SELECT ID, Respuesta, orden 
                FROM PreguntasRespuestas 
                WHERE Pregunta = ? 
                ORDER BY orden
            """, (pregunta_id,))
            respuestas = cursor.fetchall()
            
        except Exception as e:
            flash(f'Error cargando datos: {e}')
        finally:
            conn.close()
    
    if not pregunta_info:
        flash('Pregunta no encontrada')
        return redirect(url_for('admin_preguntas'))
    
    return render_template('admin_respuestas_pregunta.html', 
                         pregunta=pregunta_info, respuestas=respuestas)

@app.route('/admin_nueva_respuesta/<int:pregunta_id>', methods=['POST'])
def admin_nueva_respuesta(pregunta_id):
    """Agregar nueva respuesta a una pregunta"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    respuesta = request.form['respuesta']
    es_correcta = request.form.get('es_correcta') == 'on'
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Obtener el próximo orden
            cursor.execute("SELECT ISNULL(MAX(orden), 0) + 1 FROM PreguntasRespuestas WHERE Pregunta = ?", (pregunta_id,))
            nuevo_orden = cursor.fetchone()[0]
            
            # Si es correcta, ajustar los órdenes existentes
            if es_correcta:
                # Decrementar orden de todas las respuestas existentes
                cursor.execute("UPDATE PreguntasRespuestas SET orden = orden - 1 WHERE Pregunta = ?", (pregunta_id,))
                # La nueva respuesta correcta tendrá el orden máximo
                cursor.execute("SELECT MAX(orden) FROM PreguntasRespuestas WHERE Pregunta = ?", (pregunta_id,))
                max_orden_result = cursor.fetchone()
                nuevo_orden = (max_orden_result[0] if max_orden_result[0] else 0) + 1
            
            # Insertar la nueva respuesta
            cursor.execute("""
                INSERT INTO PreguntasRespuestas (Pregunta, Respuesta, orden) 
                VALUES (?, ?, ?)
            """, (pregunta_id, respuesta, nuevo_orden))
            
            conn.commit()
            flash('Respuesta agregada correctamente')
            
        except Exception as e:
            flash(f'Error agregando respuesta: {e}')
        finally:
            conn.close()
    
    return redirect(url_for('admin_respuestas_pregunta', pregunta_id=pregunta_id))

@app.route('/admin_editar_respuesta/<int:respuesta_id>', methods=['POST'])
def admin_editar_respuesta(respuesta_id):
    """Editar respuesta existente"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    nueva_respuesta = request.form['respuesta']
    es_correcta = request.form.get('es_correcta') == 'on'
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Obtener información actual
            cursor.execute("SELECT Pregunta, orden FROM PreguntasRespuestas WHERE ID = ?", (respuesta_id,))
            info_actual = cursor.fetchone()
            pregunta_id = info_actual[0]
            
            # Actualizar texto de la respuesta
            cursor.execute("UPDATE PreguntasRespuestas SET Respuesta = ? WHERE ID = ?", 
                         (nueva_respuesta, respuesta_id))
            
            # Manejar cambio de correcta/incorrecta
            if es_correcta:
                # Hacer esta respuesta la correcta (orden máximo)
                cursor.execute("SELECT MAX(orden) FROM PreguntasRespuestas WHERE Pregunta = ?", (pregunta_id,))
                max_orden = cursor.fetchone()[0] + 1
                cursor.execute("UPDATE PreguntasRespuestas SET orden = ? WHERE ID = ?", 
                             (max_orden, respuesta_id))
            
            conn.commit()
            flash('Respuesta actualizada correctamente')
            
        except Exception as e:
            flash(f'Error actualizando respuesta: {e}')
        finally:
            conn.close()
    
    return redirect(url_for('admin_respuestas_pregunta', pregunta_id=pregunta_id))

@app.route('/admin_eliminar_respuesta/<int:respuesta_id>', methods=['POST'])
def admin_eliminar_respuesta(respuesta_id):
    """Eliminar respuesta"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    pregunta_id = None
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Obtener pregunta_id antes de eliminar
            cursor.execute("SELECT Pregunta FROM PreguntasRespuestas WHERE ID = ?", (respuesta_id,))
            resultado = cursor.fetchone()
            if resultado:
                pregunta_id = resultado[0]
            
            # Eliminar respuestas de usuarios relacionadas
            cursor.execute("DELETE FROM Respuestas WHERE Respuesta = ?", (respuesta_id,))
            
            # Eliminar la respuesta
            cursor.execute("DELETE FROM PreguntasRespuestas WHERE ID = ?", (respuesta_id,))
            
            conn.commit()
            flash('Respuesta eliminada correctamente')
            
        except Exception as e:
            flash(f'Error eliminando respuesta: {e}')
        finally:
            conn.close()
    
    if pregunta_id:
        return redirect(url_for('admin_respuestas_pregunta', pregunta_id=pregunta_id))
    else:
        return redirect(url_for('admin_preguntas'))

@app.route('/admin_cambiar_respuesta', methods=['POST'])
def admin_cambiar_respuesta():
    """Cambiar respuesta de un usuario"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    respuesta_id = request.form['respuesta_id']
    accion = request.form['accion']  # 'correcta' o 'incorrecta'
    
    conn = get_db_connection()
    
    if conn:
        try:
            cursor = conn.cursor()
            
            if accion == 'incorrecta':
                # Marcar como incorrecta
                cursor.execute("UPDATE Respuestas SET Respuesta = 0 WHERE ID = ?", (respuesta_id,))
            else:
                # Marcar como correcta - obtener el ID de respuesta correcta
                cursor.execute("""
                    SELECT pr.ID
                    FROM Respuestas r
                    INNER JOIN PreguntasRespuestas pr_actual ON r.Respuesta = pr_actual.ID
                    INNER JOIN PreguntasRespuestas pr ON pr_actual.Pregunta = pr.Pregunta
                    WHERE r.ID = ? AND pr.orden = (
                        SELECT MAX(orden) FROM PreguntasRespuestas WHERE Pregunta = pr_actual.Pregunta
                    )
                """, (respuesta_id,))
                respuesta_correcta = cursor.fetchone()
                
                if respuesta_correcta:
                    cursor.execute("UPDATE Respuestas SET Respuesta = ? WHERE ID = ?", 
                                 (respuesta_correcta[0], respuesta_id))
            
            conn.commit()
            flash('Respuesta actualizada correctamente')
            
        except Exception as e:
            flash(f'Error actualizando respuesta: {e}')
        finally:
            conn.close()
    
    return redirect(request.referrer or url_for('admin_panel'))

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)