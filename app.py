
import streamlit as st
import google.generativeai as genai
import os
import random
import re
import time
from datetime import datetime
import pytz # Para manejar zonas horarias

# --- Importaciones para PDF ---
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT # Importar TA_RIGHT
import io
import base64
# --- Fin Importaciones para PDF ---

# --- Importaciones para Firestore ---
import streamlit.connections as st_connections
from google.cloud import firestore
# --- Fin Importaciones para Firestore ---

# Configurar Gemini API Key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# --- Inicializa la conexión a Firestore usando Streamlit Secrets ---
db = None # Inicializamos db como None por defecto
try:
    # 'firestore' aquí debe coincidir con el nombre de la sección en tu secrets.toml ([connections.firestore])
    db = st_connections.get_connection("firestore")
    st.success("Conexión a Firestore establecida.")
except Exception as e:
    st.error(f"⚠️ No se pudo conectar a Firestore. Asegúrate de que tus secretos (.streamlit/secrets.toml) estén configurados correctamente. Error: {e}")
    st.info("Revisa la sección `[connections.firestore]` en tus `secrets.toml` o en los secretos de Streamlit Cloud.")
# --- Fin Inicialización Firestore ---


# --- Funciones Core del Chatbot ---

def explicar_concepto(tema):
    """Genera una explicación detallada de un concepto de red."""
    prompt = f"""Eres un tutor de Arquitectura de Redes. Explica el concepto de {tema} de forma clara, concisa y paso a paso, como si se lo explicaras a un estudiante universitario. Incluye ejemplos si es pertinente."""
    response = model.generate_content(prompt)
    return response.text

def generar_ejercicio(tema, nivel):
    """Crea un problema nuevo y original sobre un tema específico para un nivel dado."""
    prompt = f"""Eres un tutor de Arquitectura de Redes. Crea un problema nuevo y original sobre {tema} para un estudiante de nivel {nivel}. Asegúrate de que el problema sea relevante para el tema y el nivel de dificultad. No incluyas la solución."""
    response = model.generate_content(prompt)
    return response.text

def generar_preguntas_examen(tema, nivel, num_preguntas=5):
    """Genera preguntas de opción múltiple con una única respuesta correcta."""
    prompt = f"""
    Eres un experto en Arquitectura de Redes y un creador de exámenes.
    Genera {num_preguntas} preguntas de opción múltiple sobre el tema de "{tema}" para un estudiante de nivel "{nivel}".

    Para cada pregunta, sigue este formato estricto:

    **Pregunta {numero}:** [Texto de la pregunta]
    A) [Opción A]
    B) [Opción B]
    C) [Opción C]
    D) [Opción D]
    **Respuesta Correcta:** [Letra de la opción correcta, ej. "A"]
    **Explicación:** [Breve explicación de por qué esa es la respuesta correcta y las otras no]

    Asegúrate de que cada pregunta sea diferente y original. No repitas preguntas o explicaciones. Las opciones deben ser plausibles.
    """
    response = model.generate_content(prompt)
    return response.text

def parsear_preguntas_examen(raw_text):
    """Parsea el texto crudo del examen en una lista de diccionarios."""
    questions_parsed = []
    # Usar expresiones regulares para encontrar bloques de preguntas
    # Se ajusta para capturar hasta la siguiente "Pregunta X:" o el final del texto
    question_blocks = re.split(r'\*\*Pregunta \d+:\*\*', raw_text)[1:] # Ignorar el primer split si está vacío

    for i, block in enumerate(question_blocks):
        lines = block.strip().split('\n')
        if not lines:
            continue

        # La primera línea es el texto de la pregunta
        question_text = lines[0].strip()
        options = []
        correct_answer_char = ''
        explanation = ''
        original_correct_option_text = '' # Para guardar el texto completo de la respuesta correcta original

        in_options = False
        in_explanation = False

        for line in lines[1:]: # Empezar desde la segunda línea
            line = line.strip()
            if not line:
                continue

            if line.startswith('A)') or line.startswith('B)') or line.startswith('C)') or line.startswith('D)'):
                options.append(line)
                in_options = True
                in_explanation = False # Salir del modo explicación si volvemos a opciones
            elif line.startswith('**Respuesta Correcta:**'):
                correct_answer_char = line.split(':')[-1].strip().upper()
                in_options = False # Ya no estamos en opciones
                # Intentar extraer el texto completo de la opción correcta
                for opt in options:
                    if opt.startswith(correct_answer_char + ')'):
                        original_correct_option_text = opt
                        break
            elif line.startswith('**Explicación:**'):
                explanation = line.replace('**Explicación:**', '').strip()
                in_explanation = True
                in_options = False # Salir del modo opciones
            elif in_explanation: # Si estamos en modo explicación y la línea no es una nueva sección
                explanation += " " + line # Concatenar líneas adicionales a la explicación

        # Asegurarse de que tenemos un mínimo de datos para una pregunta válida
        if question_text and options and correct_answer_char and explanation:
            questions_parsed.append({
                'question_index': i, # Añadir índice para referencia
                'question': question_text,
                'options': options,
                'correct_char': correct_answer_char,
                'original_correct_option_text': original_correct_option_text,
                'explanation': explanation
            })
    return questions_parsed


def evaluar_respuesta(user_response_char, correct_answer_char):
    """Compara la respuesta del usuario con la respuesta correcta."""
    return user_response_char.strip().upper() == correct_answer_char.strip().upper()

# --- Fin Funciones Core del Chatbot ---


# --- Función para guardar resultados en Firestore ---
def save_exam_results_to_firestore(db, user_name, user_email, level, topic, score, total_questions, user_answers_data, all_questions_data):
    if not db:
        st.error("No se pudo guardar los resultados: la conexión a Firestore no está disponible.")
        return

    # Prepara los datos de las respuestas para que sean fáciles de guardar
    simplified_answers = []
    for ans in user_answers_data:
        q_idx = ans['question_index']
        # Accede a la información completa de la pregunta
        question_info = all_questions_data[q_idx]

        simplified_answers.append({
            'question_text': question_info['question'],
            'options': question_info['options'], # Guardar todas las opciones
            'user_choice_char': ans['user_choice_char'],
            'user_choice_full_text': ans['user_choice_full_text'],
            'correct_char': ans['correct_char'],
            'correct_option_text': question_info.get('original_correct_option_text', 'N/A'), # Usar .get para evitar errores si la clave no existe
            'explanation': question_info['explanation'],
            'is_correct': (ans['user_choice_char'] == ans['correct_char'])
        })

    exam_data = {
        "student_name": user_name,
        "student_email": user_email,
        "level": level,
        "topic": topic,
        "score": score,
        "total_questions": total_questions,
        "exam_date": firestore.SERVER_TIMESTAMP, # Marca de tiempo del servidor
        "user_answers": simplified_answers,
        "raw_questions_used": all_questions_data # Opcional: guardar las preguntas completas tal como se presentaron
    }

    try:
        # Crea un nuevo documento en la colección 'exam_results'
        # El ID del documento puede ser automático o puedes generarlo con una marca de tiempo
        doc_ref = db.collection('exam_results').document(f"{user_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        doc_ref.set(exam_data)
        st.success(f"Resultados del examen guardados en Firestore con ID: {doc_ref.id}")
    except Exception as e:
        st.error(f"Error al guardar resultados en Firestore: {e}")
# --- Fin Función para guardar resultados en Firestore ---


# --- Funciones para Generar PDF ---
def generate_exam_pdf(name, email, level, topic, score, total_questions, user_answers, questions_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Estilos personalizados
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['h1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=14
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['h2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.leading = 12 # Espaciado entre líneas

    question_style = ParagraphStyle(
        'QuestionStyle',
        parent=styles['h3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        spaceAfter=6,
        leading=13
    )
    answer_option_style = ParagraphStyle(
        'AnswerOptionStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        spaceBefore=2,
        spaceAfter=2,
        leftIndent=0.3 * inch
    )
    correct_feedback_style = ParagraphStyle(
        'CorrectFeedbackStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        textColor='#28a745', # Verde Bootstrap
        fontSize=10,
        spaceBefore=4,
        spaceAfter=4
    )
    incorrect_feedback_style = ParagraphStyle(
        'IncorrectFeedbackStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        textColor='#dc3545', # Rojo Bootstrap
        fontSize=10,
        spaceBefore=4,
        spaceAfter=4
    )
    explanation_style = ParagraphStyle(
        'ExplanationStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        spaceBefore=4,
        spaceAfter=8,
        leftIndent=0.2 * inch,
        backColor='#f8f9fa', # Gris claro para el fondo
        borderColor='#e2e6ea',
        borderWidth=0.5,
        borderPadding=5
    )
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        alignment=TA_RIGHT,
        spaceAfter=10
    )
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        alignment=TA_CENTER,
        spaceBefore=12
    )
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=normal_style,
        spaceAfter=6
    )

    story = []

    # Encabezado (con fecha actual)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Fecha: {now}", header_style))
    story.append(Spacer(1, 0.1 * inch))

    # Título y Subtítulo
    story.append(Paragraph("Reporte de Examen de Arquitectura de Redes", title_style))
    story.append(Paragraph(f"Tema: {topic} | Nivel: {level}", subtitle_style))
    story.append(Spacer(1, 0.2 * inch))

    # Información del Estudiante
    story.append(Paragraph(f"**Nombre del Estudiante:** {name}", info_style))
    story.append(Paragraph(f"**Correo Electrónico:** {email}", info_style))
    story.append(Spacer(1, 0.1 * inch))

    # Resultados
    story.append(Paragraph(f"**Puntuación Final:** {score} / {total_questions}", subtitle_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("--- Detalles de las Respuestas ---", styles['h3']))
    story.append(Spacer(1, 0.1 * inch))


    # Recorrer preguntas y respuestas del usuario
    for user_ans in user_answers:
        q_idx = user_ans['question_index']
        question_info = questions_data[q_idx]

        story.append(Paragraph(f"**Pregunta {q_idx + 1}:** {question_info['question']}", question_style))
        story.append(Spacer(1, 0.05 * inch))

        # Opciones
        for option_text in question_info['options']:
            story.append(Paragraph(option_text, answer_option_style))
        story.append(Spacer(1, 0.1 * inch))

        # Respuesta del usuario
        story.append(Paragraph(f"Tu respuesta: **{user_ans['user_choice_full_text']}**", normal_style))

        # Respuesta correcta
        correct_option_full_text_display = ""
        for option in question_info['options']:
            if option.startswith(user_ans['correct_char'] + ')'):
                correct_option_full_text_display = option
                break
        story.append(Paragraph(f"Respuesta correcta: **{correct_option_full_text_display}**", normal_style))

        # Feedback
        if user_ans['user_choice_char'] == user_ans['correct_char']:
            story.append(Paragraph("✅ ¡Correcto!", correct_feedback_style))
        else:
            story.append(Paragraph("❌ Incorrecto.", incorrect_feedback_style))
            story.append(Paragraph(f"**Explicación:** {question_info['explanation']}", explanation_style))

        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("<hr/>", normal_style)) # Línea separadora
        story.append(Spacer(1, 0.2 * inch))


    doc.build(story)
    buffer.seek(0)
    return buffer

# --- Fin Funciones para Generar PDF ---


# --- Función Principal de Streamlit ---
def main():
    st.set_page_config(layout="centered", page_title="Tutor de Arquitectura de Redes", page_icon="🌐")

    # Cargar estilos CSS
    # Asume que style.css está en el mismo directorio. Si no, ajusta la ruta o incrusta el CSS directamente.
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("No se encontró 'style.css'. La aplicación se mostrará con el estilo por defecto.")


    st.sidebar.title("Tutor de Arquitectura de Redes")
    st.sidebar.write("Tu asistente personal para aprender y practicar sobre redes.")

    # Inicializar session_state
    if 'exam_started' not in st.session_state:
        st.session_state['exam_started'] = False
        st.session_state['current_question_index'] = 0
        st.session_state['score'] = 0
        st.session_state['questions'] = []
        st.session_state['user_answers'] = []
        st.session_state['exam_finished'] = False
        st.session_state['exam_active_session'] = False
        st.session_state['current_progress'] = 0
        st.session_state['total_questions'] = 0
        st.session_state['name_entered_for_exam'] = False
        st.session_state['user_name'] = ""
        st.session_state['user_email'] = "" # Inicializar user_email
        st.session_state['exam_level'] = "" # Inicializar
        st.session_state['exam_topic'] = "" # Inicializar


    # Sección de navegación en la barra lateral
    menu_selection = st.sidebar.radio("Elige una opción:", ("Explicar Concepto", "Generar Ejercicio", "Generar Examen", "Sobre el Tutor"))

    if menu_selection == "Explicar Concepto":
        st.title("📚 Explicar Concepto de Redes")
        tema = st.text_input("Ingresa el concepto de red que deseas entender:", key="concepto_input")
        if st.button("Explicar", key="explicar_button"):
            if tema:
                with st.spinner("Generando explicación..."):
                    explicacion = explicar_concepto(tema)
                st.markdown(explicacion)
            else:
                st.warning("Por favor, ingresa un concepto para explicar.")

    elif menu_selection == "Generar Ejercicio":
        st.title("📝 Generar Ejercicio de Redes")
        ejercicio_tema = st.text_input("Ingresa el tema del ejercicio (ej. 'Subneteo', 'OSPF'):", key="ejercicio_tema_input")
        ejercicio_nivel = st.selectbox("Selecciona el nivel de dificultad:", ["Básico", "Intermedio", "Avanzado"], key="ejercicio_nivel_select")
        if st.button("Generar Ejercicio", key="generar_ejercicio_button"):
            if ejercicio_tema:
                with st.spinner("Generando ejercicio..."):
                    ejercicio = generar_ejercicio(ejercicio_tema, ejercicio_nivel)
                st.markdown(ejercicio)
            else:
                st.warning("Por favor, ingresa un tema para el ejercicio.")

    elif menu_selection == "Generar Examen":
        st.title("🎓 Generar Examen de Arquitectura de Redes")

        # Formulario de inicio de examen
        if not st.session_state['name_entered_for_exam'] and not st.session_state['exam_active_session']:
            with st.form("exam_start_form"):
                st.session_state['user_name'] = st.text_input("Ingresa tu Nombre Completo para el Examen:", value=st.session_state.get('user_name', ''), key="user_name_input_form")
                st.session_state['user_email'] = st.text_input("Ingresa tu Correo Electrónico:", value=st.session_state.get('user_email', ''), key="user_email_input_form")
                st.session_state['exam_topic'] = st.text_input("Tema del examen (ej. 'Routing', 'VLANs'):", value=st.session_state.get('exam_topic', ''), key="exam_topic_input_form")

                # --- INICIO DE LA MODIFICACIÓN PARA EL ERROR ValueError ---
                options_level = ["Básico", "Intermedio", "Avanzado"]
                initial_exam_level_value = st.session_state.get('exam_level', 'Básico') # Obtener el valor actual o el predeterminado

                # Encontrar el índice del valor predeterminado, con un manejo de error robusto
                try:
                    initial_exam_level_index = options_level.index(initial_exam_level_value)
                except ValueError:
                    # Si por alguna razón el valor inicial no está en la lista (ej. si fue ''), usa 0 (para 'Básico')
                    initial_exam_level_index = 0

                st.session_state['exam_level'] = st.selectbox(
                    "Nivel de dificultad del examen:",
                    options_level,
                    index=initial_exam_level_index, # Usa el índice seguro
                    key="exam_level_select_form"
                )
                # --- FIN DE LA MODIFICACIÓN ---

                num_preguntas = st.slider("Número de preguntas:", min_value=3, max_value=10, value=5, key="num_preguntas_slider_form")

                submitted = st.form_submit_button("Iniciar Examen")
                if submitted:
                    if st.session_state['user_name'] and st.session_state['user_email'] and st.session_state['exam_topic']:
                        st.session_state['name_entered_for_exam'] = True
                        st.session_state['exam_active_session'] = True
                        st.session_state['total_questions'] = num_preguntas
                        st.session_state['current_question_index'] = 0
                        st.session_state['score'] = 0
                        st.session_state['user_answers'] = []
                        st.session_state['exam_finished'] = False
                        st.session_state['current_progress'] = 0

                        with st.spinner("Generando tu examen... Esto puede tomar un momento."):
                            raw_questions = generar_preguntas_examen(st.session_state['exam_topic'], st.session_state['exam_level'], num_preguntas)
                            parsed_questions = parsear_preguntas_examen(raw_questions)

                            if not parsed_questions or len(parsed_questions) != num_preguntas:
                                st.error("No se pudieron generar las preguntas. Por favor, intenta de nuevo o con un tema diferente.")
                                # Resetear estado si las preguntas no se generan correctamente
                                for key in ['exam_started', 'current_question_index', 'score', 'questions', 'user_answers', 'exam_finished', 'exam_active_session', 'current_progress', 'total_questions', 'name_entered_for_exam', 'exam_level', 'exam_topic', 'user_name', 'user_email']:
                                    if key in st.session_state:
                                        del st.session_state[key]
                                st.rerun() # Recargar la página para limpiar el formulario
                                return

                            st.session_state['questions'] = parsed_questions
                            st.session_state['exam_started'] = True
                            st.session_state['exam_finished'] = False
                            st.rerun()
                    else:
                        st.warning("Por favor, completa todos los campos (Nombre, Correo y Tema) para iniciar el examen.")

        # Sección del examen activo
        if st.session_state['exam_started'] and not st.session_state['exam_finished']:
            current_q_index = st.session_state['current_question_index']
            questions = st.session_state['questions']
            total_questions = st.session_state['total_questions']

            # Barra de progreso
            st.session_state['current_progress'] = (current_q_index / total_questions) * 100
            st.progress(st.session_state['current_progress'], text=f"Pregunta {current_q_index + 1} de {total_questions}")

            if current_q_index < total_questions:
                question_data = questions[current_q_index]
                st.markdown(f"**Pregunta {current_q_index + 1}:** {question_data['question']}")

                # Crear un formulario para cada pregunta para manejar la selección y navegación
                with st.form(key=f"question_form_{current_q_index}"):
                    selected_option = st.radio(
                        "Selecciona tu respuesta:",
                        options=question_data['options'],
                        key=f"radio_{current_q_index}"
                    )
                    st.session_state['user_selected_option_for_current_q'] = selected_option # Almacenar la selección

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.form_submit_button("Siguiente Pregunta"):
                            # Guardar la respuesta del usuario
                            user_choice_char = selected_option[0] # La letra de la opción (A, B, C, D)
                            correct_char = question_data['correct_char']
                            is_correct = evaluar_respuesta(user_choice_char, correct_char)

                            # Guardar la información completa de la respuesta del usuario
                            st.session_state['user_answers'].append({
                                'question_index': current_q_index,
                                'user_choice_char': user_choice_char,
                                'user_choice_full_text': selected_option, # Guardar el texto completo de la opción seleccionada
                                'correct_char': correct_char
                            })

                            if is_correct:
                                st.session_state['score'] += 1

                            st.session_state['current_question_index'] += 1
                            if st.session_state['current_question_index'] >= total_questions:
                                st.session_state['exam_finished'] = True # Marcar el examen como terminado
                                st.session_state['exam_active_session'] = False # Desactivar la sesión de examen
                            st.rerun()

                    with col2:
                        # Botón para salir del examen en cualquier momento
                        if st.form_submit_button("Salir del Examen :x:"):
                            for key in ['exam_started', 'current_question_index', 'score', 'questions', 'user_answers', 'exam_finished', 'exam_active_session', 'current_progress', 'total_questions', 'name_entered_for_exam', 'exam_level', 'exam_topic']:# 'user_name', 'user_email'
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.session_state['user_name'] = "" # Limpiar el nombre al salir
                            st.session_state['user_email'] = "" # Limpiar el email al salir
                            st.rerun()

            else: # Cuando todas las preguntas han sido respondidas (debería ser manejado por exam_finished)
                st.session_state['exam_finished'] = True
                st.session_state['exam_active_session'] = False
                st.rerun()


        # Sección de resultados finales
        if st.session_state['exam_finished']:
            st.markdown("---")
            st.header("🎉 Examen Terminado 🎉")
            st.subheader(f"Resultados para {st.session_state['user_name']}")
            st.write(f"Tu puntuación final es: **{st.session_state['score']}** de **{st.session_state['total_questions']}**")

            # Botón para descargar PDF
            if st.session_state['score'] is not None: # Asegurarse de que el score se haya calculado
                pdf_buffer = generate_exam_pdf(
                    st.session_state['user_name'],
                    st.session_state['user_email'],
                    st.session_state.get('exam_level', 'N/A'),
                    st.session_state.get('exam_topic', 'N/A'),
                    st.session_state['score'],
                    st.session_state['total_questions'],
                    st.session_state['user_answers'],
                    st.session_state['questions']
                )
                st.download_button(
                    label="Descargar Informe PDF",
                    data=pdf_buffer,
                    file_name=f"Informe_Examen_{st.session_state['user_name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf",
                    mime="application/pdf"
                )

            # --- Llamar a la función para guardar resultados en Firestore ---
            # Asegúrate de que la variable global 'db' es accesible y la conexión fue exitosa
            global db # Declarar db como global para asegurar acceso si no fue inicializada en el mismo ámbito
            if db:
                save_exam_results_to_firestore(
                    db,
                    st.session_state['user_name'],
                    st.session_state['user_email'],
                    st.session_state.get('exam_level', 'N/A'),
                    st.session_state.get('exam_topic', 'N/A'),
                    st.session_state['score'],
                    st.session_state['total_questions'],
                    st.session_state['user_answers'],
                    st.session_state['questions'] # Pasar todas las preguntas para guardarlas también
                )
            else:
                st.warning("No se pudieron guardar los resultados del examen en Firestore debido a un problema de conexión.")
            # --- Fin Llamada a Firestore ---

            st.subheader("Revisión de tus respuestas:")
            # Mostrar la revisión de las respuestas
            for i, user_ans in enumerate(st.session_state['user_answers']):
                question_info = st.session_state['questions'][user_ans['question_index']]
                st.markdown(f"**Pregunta {i + 1}:** {question_info['question']}")
                st.markdown(f"Tu respuesta: **{user_ans['user_choice_full_text']}**")

                # Obtener el texto completo de la respuesta correcta para mostrarlo en Streamlit
                correct_option_full_text_display = ""
                for option in question_info['options']:
                    if option.startswith(user_ans['correct_char'] + ')'):
                        correct_option_full_text_display = option
                        break
                st.markdown(f"Respuesta correcta: **{correct_option_full_text_display}**")


                if user_ans['user_choice_char'] == user_ans['correct_char']:
                    st.success("✅ ¡Correcto!")
                else:
                    st.error("❌ Incorrecto.")
                    st.markdown(f"**Explicación:** {question_info['explanation']}")

            st.markdown("---")

            if st.button("Reiniciar Examen :repeat:", key="reset_exam_button_final"):
                for key in ['exam_started', 'current_question_index', 'score', 'questions', 'user_answers', 'exam_finished', 'exam_active_session', 'current_progress', 'total_questions', 'name_entered_for_exam', 'exam_level', 'exam_topic']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state['user_name'] = "" # Limpiar el nombre al reiniciar examen
                st.session_state['user_email'] = "" # Limpiar el email al reiniciar examen
                st.rerun()

    elif menu_selection == "Sobre el Tutor":
        st.title("ℹ️ Sobre el Tutor de Arquitectura de Redes")
        st.write("Este tutor está diseñado para ayudarte a aprender y practicar conceptos de arquitectura de redes de manera interactiva.")
        st.write("Puedes:")
        st.markdown("- **Explicar Concepto:** Obtener explicaciones detalladas sobre cualquier término o concepto de redes.")
        st.markdown("- **Generar Ejercicio:** Recibir problemas prácticos para resolver y aplicar tus conocimientos.")
        st.markdown("- **Generar Examen:** Poner a prueba tus conocimientos con exámenes de opción múltiple personalizados por tema y nivel.")
        st.markdown("\n¡Espero que sea una herramienta útil en tu aprendizaje!")


# --- Punto de Entrada de la Aplicación ---
if __name__ == "__main__":
    main()
