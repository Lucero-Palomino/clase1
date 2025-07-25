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


# Configurar Gemini API Key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

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

def evaluar_respuesta_y_dar_feedback(ejercicio, respuesta_estudiante):
    """Evalúa la respuesta de un estudiante a un ejercicio y proporciona retroalimentación."""
    prompt = f"""Eres un tutor de Arquitectura de Redes. Tu tarea es evaluar la respuesta de un estudiante a un problema y proporcionar retroalimentación detallada.
    Problema: {ejercicio}
    Respuesta del estudiante: {respuesta_estudiante}
    Por favor, sigue estos pasos:
    1. Primero, indica si la respuesta del estudiante es correcta o incorrecta.
    2. Si es incorrecta, explica *por qué* es incorrecta, señalando los errores conceptuales o de cálculo.
    3. Luego, proporciona la solución *completa y detallada* paso a paso del ejercicio original.
    4. Usa formato Markdown para una mejor lectura (por ejemplo, listas numeradas para pasos).
    """
    response = model.generate_content(prompt)
    return response.text

def generar_pregunta_multiple_choice(tema, nivel):
    """
    Crea una pregunta de opción múltiple con 4 opciones, una correcta y una explicación.
    Se enfatiza la originalidad para evitar repeticiones.
    """
    prompt = f"""Eres un experto en Arquitectura de Redes. Crea una **pregunta nueva y original, diferente a las anteriores, y variada** de opción múltiple sobre **"{tema}"** para un estudiante de nivel **"{nivel}"**. La pregunta debe tener 4 opciones de respuesta (A, B, C, D), de las cuales solo una es correcta.
    Formatea la salida estrictamente de la siguiente manera, sin texto adicional antes o después de este formato:

    Pregunta: [Tu pregunta aquí]
    A) [Opción A]
    B) [Opción B]
    C) [Opción C]
    D) [Opción D]
    Respuesta Correcta: [Letra de la opción correcta, por ejemplo, A]
    Explicación: [Breve explicación de por qué la respuesta es correcta]
    """
    response = model.generate_content(prompt)
    return response.text

def parse_multiple_choice_question(raw_data):
    """
    Parsea la cadena de texto de la pregunta de opción múltiple generada por Gemini.
    Retorna un diccionario con la pregunta, opciones, respuesta correcta y explicación,
    o None si el parseo falla o los datos son incompletos.
    """
    question_text = ""
    options_raw = []
    correct_answer_char = ""
    explanation = ""

    lines = raw_data.split('\n')
    line_type = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("Pregunta:"):
            question_text = line.replace("Pregunta:", "").strip()
            line_type = "question"
        elif re.match(r"^[A-D]\)", line):
            options_raw.append(line)
            line_type = "option"
        elif line.startswith("Respuesta Correcta:"):
            correct_answer_match = re.search(r"Respuesta Correcta:\s*([A-D])", line)
            if correct_answer_match:
                correct_answer_char = correct_answer_match.group(1).strip()
            line_type = "correct_answer"
        elif line.startswith("Explicación:"):
            explanation = line.replace("Explicación:", "").strip()
            line_type = "explanation"
        elif line_type == "explanation":
            explanation += " " + line # Para explicaciones multilinea

    # Validar que hemos encontrado todos los componentes esenciales
    if not (question_text and len(options_raw) == 4 and correct_answer_char and explanation):
        return None

    # Barajar las opciones y mapear la respuesta correcta a la nueva letra
    shuffled_options_with_correct = []
    original_option_map = {}
    for opt_raw in options_raw:
        char = opt_raw[0]
        original_option_map[opt_raw] = (char == correct_answer_char)
        shuffled_options_with_correct.append(opt_raw)

    random.shuffle(shuffled_options_with_correct)

    new_correct_char = ''
    new_options_display = []
    for i, opt_display in enumerate(shuffled_options_with_correct):
        char_label = chr(65 + i) # Genera A, B, C, D
        option_text = opt_display[3:].strip() if opt_display.startswith(tuple("ABCD)")) else opt_display.strip()
        new_options_display.append(f"{char_label}) {option_text}")

        if original_option_map.get(opt_display):
            new_correct_char = char_label

    if not new_correct_char:
        return None

    return {
        'question': question_text,
        'options': new_options_display,
        'correct_answer_char': new_correct_char,
        'explanation': explanation,
        'original_correct_option_text': next((opt[3:].strip() for opt in options_raw if opt.startswith(correct_answer_char + ')')), "")
    }


# --- FUNCIÓN PARA GENERAR PDF ---
def generate_exam_pdf(score, total_questions, user_answers, all_questions, user_name="Estudiante", level="N/A", topic="N/A"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()

    # Estilos personalizados para el PDF
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=20, leading=24,
                               alignment=TA_CENTER, spaceAfter=20))
    # --- MODIFICACIONES AQUÍ para la información del estudiante/examen ---
    styles.add(ParagraphStyle(name='StudentInfoStyle', fontSize=9, leading=10, # Más pequeño
                               alignment=TA_LEFT, spaceAfter=2)) # Alineado a la derecha y más junto
    styles.add(ParagraphStyle(name='HeaderStyle', fontSize=12, leading=16,
                               alignment=TA_RIGHT, spaceAfter=10, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='NormalStyle', fontSize=10, leading=12,
                               alignment=TA_RIGHT, spaceAfter=8, leftIndent=10))
    styles.add(ParagraphStyle(name='OptionStyle', fontSize=9, leading=11,
                               alignment=TA_RIGHT, spaceAfter=4, leftIndent=30))
    styles.add(ParagraphStyle(name='CorrectAnswerStyle', fontSize=10, leading=12,
                               alignment=TA_RIGHT, spaceAfter=8, textColor='green', fontName='Helvetica-Bold', leftIndent=10))
    styles.add(ParagraphStyle(name='IncorrectAnswerStyle', fontSize=10, leading=12,
                               alignment=TA_RIGHT, spaceAfter=8, textColor='red', fontName='Helvetica-Bold', leftIndent=10))
    styles.add(ParagraphStyle(name='ExplanationStyle', fontSize=9, leading=11,
                               alignment=TA_RIGHT, spaceBefore=5, spaceAfter=10, textColor='gray', leftIndent=20))


    story = []

    # Obtener la hora actual en la zona horaria de Puno, Perú
    peru_tz = pytz.timezone('America/Lima') # Lima es la zona horaria para Puno, Perú
    current_time_peru = datetime.now(peru_tz).strftime('%Y-%m-%d %H:%M:%S')

    # Título principal del examen
    story.append(Paragraph("Resultados del Examen de Arquitectura de Redes", styles['TitleStyle']))
    story.append(Spacer(1, 0.2 * inch)) # Espacio después del título principal

    # --- INFORMACIÓN DEL ESTUDIANTE/EXAMEN (MOVIDO Y AJUSTADO) ---
    # Usamos un Frame o una tabla para controlar mejor la posición
    # Para simplicidad sin usar Frames complejos, podemos usar Paragraphs con TA_RIGHT
    # y control de espaciado.
    story.append(Paragraph(f"Estudiante: {user_name}", styles['StudentInfoStyle']))
    story.append(Paragraph(f"Nivel: {level}", styles['StudentInfoStyle']))
    story.append(Paragraph(f"Tema General: {topic}", styles['StudentInfoStyle']))
    story.append(Paragraph(f"Fecha y Hora: {current_time_peru}", styles['StudentInfoStyle']))
    story.append(Spacer(1, 0.3 * inch)) # Espacio después de la información del estudiante

    # Resumen de puntuación
    story.append(Paragraph(f"Puntuación Final: {score} / {total_questions}", styles['HeaderStyle']))
    story.append(Spacer(1, 0.2 * inch))

    # Detalles de cada pregunta
    for i, user_ans_data in enumerate(user_answers):
        question_info = all_questions[user_ans_data['question_index']]
        story.append(Paragraph(f"**{i + 1})** {question_info['question']}", styles['NormalStyle']))
        story.append(Spacer(1, 0.1 * inch))

        # Mostrar todas las opciones de la pregunta
        story.append(Paragraph("Opciones:", styles['NormalStyle']))
        for option_text in question_info['options']:
            story.append(Paragraph(option_text, styles['OptionStyle']))
        story.append(Spacer(1, 0.1 * inch))


        # Mostrar la respuesta del usuario de forma completa
        story.append(Paragraph(f"Tu respuesta: **{user_ans_data['user_choice_full_text']}**", styles['NormalStyle']))

        # Mostrar la respuesta correcta de forma completa
        correct_option_full_text = ""
        for option in question_info['options']:
            if option.startswith(user_ans_data['correct_char'] + ')'):
                correct_option_full_text = option
                break
        story.append(Paragraph(f"Respuesta correcta: **{correct_option_full_text}**", styles['NormalStyle']))


        if user_ans_data['user_choice_char'] == user_ans_data['correct_char']:
            story.append(Paragraph("Estado: Correcto ✅", styles['CorrectAnswerStyle']))
        else:
            story.append(Paragraph("Estado: Incorrecto ❌", styles['IncorrectAnswerStyle']))
            story.append(Paragraph(f"**Explicación:** {question_info['explanation']}", styles['ExplanationStyle']))

        story.append(Spacer(1, 0.2 * inch))
        if (i + 1) % 3 == 0 and (i + 1) != total_questions: # Añade un salto de página cada 3 preguntas
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer

# --- Función Principal de Streamlit ---

def main():
    # --- Cargar estilos CSS externos ---
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("Error: El archivo 'style.css' no se encontró. Asegúrate de que esté en la misma carpeta que 'app.py'.")

    st.title("   ARQUITECTURA DE REDES    ")
    st.markdown("---")
    st.markdown("¡Bienvenido! Estoy aquí para ayudarte a **dominar** la Arquitectura de Redes. Selecciona una opción para comenzar tu aprendizaje o desafiarte con un examen. ✨")

    temas_principales = ["Redes LAN", "Protocolos de Red", "Modelos OSI/TCP-IP", "Seguridad de Red", "Dispositivos de Red", "Direccionamiento IP", "Enrutamiento", "Conmutación", "Subredes", "Capa Física"]

    posibles_sub_temas_para_examen = [
        "Capa Física del Modelo OSI", "Capa de Enlace de Datos del Modelo OSI",
        "Capa de Red del Modelo OSI", "Capa de Transporte del Modelo OSI",
        "Capa de Sesión del Modelo OSI", "Capa de Presentación del Modelo OSI",
        "Capa de Aplicación del Modelo OSI", "Comparación OSI vs TCP/IP",
        "Protocolo IP (Internet Protocol)", "Protocolo TCP (Transmission Control Protocol)",
        "Protocolo UDP (User Datagram Protocol)", "Direccionamiento IPv4 y Clases",
        "Direccionamiento IPv4 Privado", "Direccionamiento IPv6", "Máscaras de subred y cálculo", "VLSM",
        "Concepto de Gateway", "Funcionamiento de un Switch", "Funcionamiento de un Router",
        "Concepto de Hub", "Firewall de Filtrado de Paquetes", "Firewall de Estado",
        "VPNs (Virtual Private Networks) funcionamiento", "Tipos de VPN",
        "Protocolos de enrutamiento estático", "Protocolos de enrutamiento dinámico (RIP)",
        "Protocolos de enrutamiento dinámico (OSPF)", "Protocolos de enrutamiento dinámico (EIGRP)",
        "DNS (Domain Name System) funcionamiento", "DHCP (Dynamic Host Configuration Protocol) funcionamiento",
        "ARP (Address Resolution Protocol) funcionamiento", "ICMP (Internet Control Message Protocol)",
        "Protocolos de Capa de Aplicación (HTTP, HTTPS, FTP, SMTP, POP3, IMAP)",
        "Topología de Estrella", "Topología de Anillo", "Topología de Bus", "Topología de Malla",
        "Concepto de Dominio de Colisión", "Concepto de Dominio de Broadcast",
        "CSMA/CD", "CSMA/CA", "Ethernet y sus estándares (802.3)", "Wi-Fi (802.11)",
        "Seguridad WEP/WPA/WPA2/WPA3", "SSID", "Concepto de MAC Address",
        "Conmutación de Paquetes", "Conmutación de Circuitos", "Redes SDN (Software-Defined Networking)",
        "NAT (Network Address Translation)", "Port Forwarding", "VLANs (Virtual LANs)"
    ]

    col_level, col_topic = st.columns(2)
    with col_level:
        nivel_estudiante = st.selectbox("Selecciona tu nivel actual:", ["Básico", "Intermedio", "Avanzado"], key="nivel_select")
    with col_topic:
        tema_seleccionado = st.selectbox("Selecciona un tema general:", temas_principales, key="tema_select")

    st.markdown("---")

    # --- Implementación de los "Cuadros Grandes" con botones y gestión de estado ---

    st.subheader("¿Qué quieres hacer hoy?")

    # Inicializar el estado de la actividad si no existe
    if 'current_activity' not in st.session_state:
        st.session_state['current_activity'] = None
    if 'user_name' not in st.session_state: # Asegurarse de que 'user_name' siempre exista
        st.session_state['user_name'] = ""

    # Crear las columnas para los botones de "cuadros grandes"
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        if st.button("Explicar un concepto", key="btn_explicar_concepto", use_container_width=True):
            st.session_state['current_activity'] = 'explicar'
            # Resetear estado del examen si se cambia de actividad
            for key in ['exam_started', 'current_question_index', 'score', 'questions', 'user_answers', 'exam_finished', 'exam_active_session', 'current_progress', 'total_questions', 'name_entered_for_exam']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state['user_name'] = "" # Limpiar el nombre al cambiar de actividad
    with col2:
        if st.button("Proponer un ejercicio", key="btn_proponer_ejercicio", use_container_width=True):
            st.session_state['current_activity'] = 'proponer'
            # Resetear estado del examen si se cambia de actividad
            for key in ['exam_started', 'current_question_index', 'score', 'questions', 'user_answers', 'exam_finished', 'exam_active_session', 'current_progress', 'total_questions', 'name_entered_for_exam']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state['user_name'] = "" # Limpiar el nombre al cambiar de actividad
    with col3:
        if st.button("Evaluar mi respuesta al ejercicio", key="btn_evaluar_respuesta", use_container_width=True):
            st.session_state['current_activity'] = 'evaluar'
            # Resetear estado del examen si se cambia de actividad
            for key in ['exam_started', 'current_question_index', 'score', 'questions', 'user_answers', 'exam_finished', 'exam_active_session', 'current_progress', 'total_questions', 'name_entered_for_exam']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state['user_name'] = "" # Limpiar el nombre al cambiar de actividad
    with col4:
        if st.button("Tomar examen", key="btn_tomar_examen", use_container_width=True):
            st.session_state['current_activity'] = 'examen'
            # Siempre se reinicia el estado del examen al hacer clic en "Tomar examen"
            for key in ['exam_started', 'current_question_index', 'score', 'questions', 'user_answers', 'exam_finished', 'exam_active_session', 'current_progress', 'total_questions', 'name_entered_for_exam']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state['exam_started'] = False
            st.session_state['exam_active_session'] = False
            st.session_state['name_entered_for_exam'] = False # NUEVO: Flag para controlar si ya se preguntó el nombre
            st.session_state['user_name'] = "" # Asegurar que el nombre esté vacío al inicio del flujo del examen

    st.markdown("---") # Separador después de los botones principales

    # Mostrar contenido según la actividad seleccionada
    if st.session_state['current_activity'] == 'explicar':
        st.header(f"Explicación de {tema_seleccionado}")
        st.markdown("Aquí puedes obtener explicaciones detalladas sobre cualquier concepto.")
        if st.button("Obtener Explicación :mag:", key="get_explanation_button"):
            with st.spinner("Generando explicación..."):
                explicacion = explicar_concepto(tema_seleccionado)
                st.info(explicacion)

            st.markdown("### 📚 Recursos Adicionales para Profundizar")
            st.markdown("Aquí te dejo enlaces a papers, documentos y videos clave para este tema:")

            recursos_por_tema = {
                "Redes LAN": [
                    {"tipo": "Referencia", "titulo": "¿Qué es una LAN?", "url": "https://www-cisco-com.translate.goog/c/en/us/products/switches/what-is-a-lan-local-area-network.html?_x_tr_sl=en&_x_tr_tl=es&_x_tr_hl=es&_x_tr_pto=tc"},
                    {"tipo": "Referencia", "titulo": "Red LAN", "url": "https://www.godaddy.com/resources/latam/tecnologia/que-es-una-red-lan"},
                    {"tipo": "video", "titulo": "Fundamentos de Redes LAN (YouTube)", "url": "https://www.youtube.com/watch?v=VD5k_0q_fus"}
                ],
                "Protocolos de Red": [
                    {"tipo": "Referencia", "titulo": "Definición", "url": "https://www.cloudflare.com/es-es/learning/network-layer/what-is-a-protocol/"},
                    {"tipo": "Referencia", "titulo": "(IBM)", "url": "https://www.ibm.com/docs/es/aix/7.2.0?topic=protocols-internet-network-level"},
                    {"tipo": "video", "titulo": "Qué son los protocolos de red", "url": "https://www.youtube.com/watch?v=hJqu97N_zhA&pp=ygURUHJvdG9jb2xvcyBkZSBSZWQ%3D"}
                ],
                "Modelos OSI/TCP-IP": [
                    {"tipo": "Referencia", "titulo": "ISO/IEC 7498 (OSI Model)", "url": "https://www.iso.org/standard/14299.html"},
                    {"tipo": "documento", "titulo": "Comparación OSI y TCP/IP (Microsoft)", "url": "https://learn.microsoft.com/es-es/troubleshoot/windows-server/networking/tcpip-layer-model-vs-osi-layer-model"},
                    {"tipo": "video", "titulo": "Modelo OSI Explicado (YouTube)", "url": "https://www.youtube.com/watch?v=MqpIJLmMny8&pp=ygUSTW9kZWxvcyBPU0kvVENQLUlQ"}
                ],
                "Seguridad de Red": [
                    {"tipo": "Referencia", "titulo": "NIST SP 800-12 (Introduction to Computer Security)", "url": "https://csrc.nist.gov/publications/detail/sp/800-12/rev-1/archive/1995-10-01"},
                    {"tipo": "documento", "titulo": "Conceptos Básicos de Ciberseguridad (CISCO)", "url": "https://www.cisco.com/c/es_mx/training-events/getting-started-with-networking/cybersecurity-fundamentals.html"},
                    {"tipo": "video", "titulo": "Fundamentos de Ciberseguridad (YouTube)", "url": "https://www.youtube.com/watch?v=Vl3rKqM9wI0"}
                ],
                "Dispositivos de Red": [
                    {"tipo": "Referencia", "titulo": "Conceptos de Switching (CCNA - Cisco)", "url": "https://www.cisco.com/c/es_mx/training-events/getting-started-with-networking/switching-fundamentals.html"},
                    {"tipo": "video", "titulo": "Tipos de Dispositivos de Red (YouTube)", "url": "https://www.youtube.com/watch?v=oCzPbiN5wao&pp=ygUTRGlzcG9zaXRpdm9zIGRlIFJlZA%3D%3D"}
                ],
                "Direccionamiento IP": [
                    {"tipo": "Referencia", "titulo": "RFC 791 (Internet Protocol)", "url": "https://datatracker.ietf.org/doc/html/rfc791"},
                    {"tipo": "documento", "titulo": "Direccionamiento IP (UNAM)", "url": "http://www.dgsca.unam.mx/publicaciones/curso/ip/ip-2.html"},
                    {"tipo": "video", "titulo": "Qué es una Dirección IP y cómo funciona (YouTube)", "url": "https://www.youtube.com/watch?v=801xu7tGEfA&pp=ygUUIkRpcmVjY2lvbmFtaWVudG8gSVA%3D"}
                ],
                "Enrutamiento": [
                    {"tipo": "Referencia", "titulo": "RFC 1058 (RIP Version 1)", "url": "https://datatracker.ietf.org/doc/html/rfc1058"},
                    {"tipo": "documento", "titulo": "Introducción al Enrutamiento (Cisco)", "url": "https://www.cisco.com/c/es_mx/training-events/getting-started-with-networking/routing-fundamentals.html"},
                    {"tipo": "video", "titulo": "Enrutamiento Estático y Dinámico (YouTube)", "url": "https://www.youtube.com/watch?v=nuHUTToftoQ&pp=ygUMRW5ydXRhbWllbnRv"}
                ],
                "Conmutación": [
                    {"tipo": "Referencia", "titulo": "Conceptos de Switching (CCNA - Cisco)", "url": "https://www.cisco.com/c/es_mx/training-events/getting-started-with-networking/switching-fundamentals.html"},
                    {"tipo": "video", "titulo": "Switches: ¿Qué son y cómo funcionan? (YouTube)", "url": "https://www.youtube.com/watch?v=u8-hJv3f-9k"}
                ],
                "Subredes": [
                    {"tipo": "Referencia", "titulo": "Subnetting (Wikipedia)", "url": "https://es.wikipedia.org/wiki/Subred"},
                    {"tipo": "video", "titulo": "Tutorial de Subnetting paso a paso (YouTube)", "url": "https://www.youtube.com/watch?v=eE7yG0XzFqc"}
                ],
                "Capa Física": [
                    {"tipo": "Referencia", "titulo": "Capa Física del Modelo OSI (Wikipedia)", "url": "https://es.wikipedia.org/wiki/Capa_f%C3%ADsica"},
                    {"tipo": "video", "titulo": "La capa física del modelo OSI (YouTube)", "url": "https://www.youtube.com/watch?v=wfmExYHthbA&pp=ygUMQ2FwYSBGw61zaWNh0gcJCccJAYcqIYzv"}
                ],
            }

            if tema_seleccionado in recursos_por_tema:
                for recurso in recursos_por_tema[tema_seleccionado]:
                    if recurso["tipo"] == "paper":
                        st.markdown(f"- 📄 **Paper:** [{recurso['titulo']}]({recurso['url']})")
                    elif recurso["tipo"] == "documento":
                        st.markdown(f"- 📝 **Documento:** [{recurso['titulo']}]({recurso['url']})")
                    elif recurso["tipo"] == "video":
                        st.markdown(f"- ▶️ **Video:** [{recurso['titulo']}]({recurso['url']})")
            else:
                st.info("Actualmente no hay recursos adicionales específicos para este tema. ¡Pero la explicación de Gemini te ayudará mucho!")

    elif st.session_state['current_activity'] == 'proponer':
        st.header(f"Ejercicio de {tema_seleccionado} (Nivel {nivel_estudiante})")
        st.markdown("¡Pon a prueba tus conocimientos con un problema nuevo!")
        if st.button("Generar Ejercicio :brain:", key="generate_exercise_button_prop"):
            with st.spinner("Generando ejercicio..."):
                ejercicio = generar_ejercicio(tema_seleccionado, nivel_estudiante)
            st.session_state['current_exercise'] = ejercicio
            st.success(ejercicio)
            st.info("Ahora puedes ir a 'Evaluar mi Respuesta' para obtener retroalimentación.")

    elif st.session_state['current_activity'] == 'evaluar':
        st.header("Evaluar mi Respuesta")
        st.markdown("Recibe retroalimentación detallada sobre tus soluciones a los ejercicios.")
        if 'current_exercise' in st.session_state and st.session_state['current_exercise']:
            st.info("**Ejercicio Actual:**")
            st.markdown(st.session_state['current_exercise'])
            respuesta_estudiante = st.text_area("Escribe aquí tu respuesta:", key="student_response_area")
            if st.button("Evaluar :chart_with_upwards_trend:", key="evaluate_button_eval"):
                if respuesta_estudiante:
                    with st.spinner("Evaluando y generando feedback..."):
                        feedback = evaluar_respuesta_y_dar_feedback(st.session_state['current_exercise'], respuesta_estudiante)
                    st.markdown(feedback)
                else:
                    st.warning("Por favor, escribe tu respuesta para evaluar.")
        else:
            st.info("Primero genera un ejercicio en la sección 'Proponer un Ejercicio'.")

    elif st.session_state['current_activity'] == 'examen':
        st.header("Examen de Arquitectura de Redes :book:")
        st.markdown("¿Listo para un desafío? Responde 10 preguntas de opción múltiple. ¡Buena suerte!")

        # --- INICIALIZACIÓN ROBUSTA DEL ESTADO DEL EXAMEN ---
        # Asegurarse de que todas las claves existan antes de usarlas
        if 'exam_started' not in st.session_state:
            st.session_state['exam_started'] = False
        if 'current_question_index' not in st.session_state:
            st.session_state['current_question_index'] = 0
        if 'score' not in st.session_state:
            st.session_state['score'] = 0
        if 'questions' not in st.session_state:
            st.session_state['questions'] = []
        if 'user_answers' not in st.session_state:
            st.session_state['user_answers'] = []
        if 'exam_finished' not in st.session_state:
            st.session_state['exam_finished'] = False
        if 'exam_active_session' not in st.session_state:
            st.session_state['exam_active_session'] = False
        if 'current_progress' not in st.session_state:
            st.session_state['current_progress'] = 0.0
        if 'total_questions' not in st.session_state:
            st.session_state['total_questions'] = 10
        if 'name_entered_for_exam' not in st.session_state: # NUEVO: Inicializar el flag del nombre
            st.session_state['name_entered_for_exam'] = False
        if 'user_name' not in st.session_state: # Asegurar que 'user_name' exista
            st.session_state['user_name'] = ""
        # Guardar nivel y tema seleccionados para el PDF
        st.session_state['exam_level'] = nivel_estudiante
        st.session_state['exam_topic'] = tema_seleccionado


        # --- Flujo para pedir el nombre solo si se presiona "Tomar examen" ---
        if not st.session_state['name_entered_for_exam']:
            st.session_state['user_name'] = st.text_input("Ingresa tu nombre para el examen:", value=st.session_state['user_name'], key="user_name_input_exam_flow")
            if st.button("Confirmar Nombre y Continuar", key="confirm_name_button"):
                if st.session_state['user_name']:
                    st.session_state['name_entered_for_exam'] = True
                    st.rerun() # Volver a ejecutar para ocultar el campo de nombre y mostrar el botón de inicio de examen
                else:
                    st.warning("Por favor, ingresa tu nombre para continuar.")
        elif not st.session_state['exam_started']:
            if st.button("Comenzar Examen Ahora :rocket:", key="start_exam_button"):
                # No necesitamos validar el nombre aquí de nuevo, ya lo hicimos arriba.
                st.session_state['exam_started'] = True
                st.session_state['current_question_index'] = 0
                st.session_state['score'] = 0
                st.session_state['questions'] = []
                st.session_state['user_answers'] = []
                st.session_state['exam_finished'] = False
                st.session_state['exam_active_session'] = True
                st.session_state['current_progress'] = 0.0
                st.session_state['total_questions'] = 10

                with st.spinner("Generando las 10 preguntas del examen..."):
                    generated_themes = set()
                    while len(st.session_state['questions']) < st.session_state['total_questions']:
                        available_themes = [t for t in posibles_sub_temas_para_examen if t not in generated_themes]
                        if not available_themes:
                            st.warning("Se han utilizado todos los sub-temas posibles. Reutilizando temas para completar el examen.")
                            available_themes = list(posibles_sub_temas_para_examen)
                            generated_themes.clear()

                        current_sub_tema = random.choice(available_themes)
                        try:
                            question_data_raw = generar_pregunta_multiple_choice(current_sub_tema, nivel_estudiante)
                            parsed_question = parse_multiple_choice_question(question_data_raw)

                            if parsed_question:
                                st.session_state['questions'].append(parsed_question)
                                generated_themes.add(current_sub_tema)
                            else:
                                st.warning(f"⚠️ No se pudo parsear una pregunta. Reintentando... Posible formato inesperado de Gemini para: '{current_sub_tema}'.")

                            # --- Añadir un pequeño retraso aquí ---
                            time.sleep(1.5) # Espera 1.5 segundos entre cada llamada a la API
                            # Puedes ajustar este valor. Si el error persiste, auméntalo.

                        except Exception as e:
                            st.error(f"Error al generar pregunta para '{current_sub_tema}': {e}. Es posible que hayas excedido la cuota de la API. Por favor, inténtalo de nuevo en unos minutos o revisa tus cuotas en Google Cloud Console.")
                            # Detener el proceso de generación de preguntas si hay un error de API
                            st.session_state['exam_started'] = False
                            st.session_state['exam_active_session'] = False
                            st.session_state['exam_finished'] = False
                            break # Salir del bucle while

                if len(st.session_state['questions']) == st.session_state['total_questions']:
                     st.session_state['current_progress'] = (st.session_state['current_question_index'] / st.session_state['total_questions']) * 100

        # Lógica para mostrar preguntas y manejar la navegación durante el examen
        if st.session_state.get('exam_active_session', False) and not st.session_state['exam_finished']:
            if st.session_state['current_question_index'] < st.session_state['total_questions']:
                # Barra de progreso al estilo Duolingo
                progress_percentage = (st.session_state['current_question_index'] / st.session_state['total_questions']) * 100
                st.progress(progress_percentage / 100, text=f"Progreso: {int(progress_percentage)}%")
                st.write(f"Pregunta {st.session_state['current_question_index'] + 1} de {st.session_state['total_questions']}")

                current_question = st.session_state['questions'][st.session_state['current_question_index']]

                try:
                    match = re.search(r'sobre "([^"]+)"', current_question['question'])
                    if match:
                        display_topic = match.group(1)
                    else:
                        display_topic = tema_seleccionado
                except Exception:
                    display_topic = tema_seleccionado

                st.markdown(f"**Tema cubierto:** *{display_topic}*")
                st.write(current_question['question'])

                selected_option_label = st.radio(
                    "Elige una opción:",
                    current_question['options'],
                    key=f"q_radio_{st.session_state['current_question_index']}"
                )

                if st.button("Comprobar :white_check_mark:", key=f"check_answer_button_{st.session_state['current_question_index']}"):
                    if selected_option_label:
                        user_answer_char = selected_option_label[0] # Solo la letra (A, B, C, D)

                        # Almacenar la respuesta del usuario para revisión posterior, incluyendo el texto completo
                        st.session_state['user_answers'].append({
                            'question_index': st.session_state['current_question_index'],
                            'user_choice_char': user_answer_char,
                            'user_choice_full_text': selected_option_label, # Guardamos el texto completo aquí
                            'correct_char': current_question['correct_answer_char'],
                            'question_text': current_question['question'],
                            'explanation': current_question['explanation']
                        })

                        if user_answer_char == current_question['correct_answer_char']:
                            st.session_state['score'] += 1
                            # Feedback visual de éxito
                            st.success("🎉 ¡Correcto! ¡Sigue así! 🎉")
                            st.balloons()
                            # time.sleep(1)
                        else:
                            # Feedback visual de error
                            st.error(f"❌ Incorrecto. La respuesta correcta era **{current_question['correct_answer_char']}**.")
                            st.markdown(f"**Explicación:** {current_question['explanation']}")

                            q_lower = current_question['question'].lower()
                            if "capa física" in q_lower or "codificación" in q_lower:
                                st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Modem_diagram.svg/400px-Modem_diagram.svg.png",
                                         caption="Ejemplo de Codificación en Capa Física")
                                st.markdown("_Este diagrama ilustra cómo se transforman los datos en señales físicas._")
                            elif "conmutación de paquetes" in q_lower:
                                st.video("https://www.youtube.com/watch?v=yW6hI1F8K-0")
                                st.markdown("_Video: ¿Cómo funciona la conmutación de paquetes?_")

                        # Mover a la siguiente pregunta
                        st.session_state['current_question_index'] += 1
                        st.session_state['current_progress'] = (st.session_state['current_question_index'] / st.session_state['total_questions']) * 100

                        # Si se terminó el examen
                        if st.session_state['current_question_index'] >= st.session_state['total_questions']:
                            st.session_state['exam_finished'] = True
                            st.session_state['exam_active_session'] = False
                        else:
                            st.rerun()
                    else:
                        st.warning("Por favor, selecciona una opción antes de comprobar.")
            else:
                st.session_state['exam_finished'] = True
                st.session_state['exam_active_session'] = False

        # Lógica para mostrar los resultados finales del examen
        if st.session_state['exam_finished']:
            st.balloons()
            st.success(f"🎉 ¡Examen Terminado! Has respondido correctamente a **{st.session_state['score']}** de **{st.session_state['total_questions']}** preguntas. ¡Felicidades, {st.session_state['user_name']}! 🎉")
            st.markdown("---")
            st.subheader("Resultados Detallados:")

            st.markdown(f"**Puntos obtenidos en este examen:** {st.session_state['score'] * 10} XP (por ejemplo)")

            # Usar user_answers y questions para el PDF
            pdf_user_name = st.session_state['user_name'] if st.session_state['user_name'] else "Estudiante"
            pdf_buffer = generate_exam_pdf(
                st.session_state['score'],
                st.session_state['total_questions'],
                st.session_state['user_answers'],
                st.session_state['questions'],
                user_name=pdf_user_name,
                level=st.session_state.get('exam_level', 'N/A'), # Pasa el nivel
                topic=st.session_state.get('exam_topic', 'N/A')   # Pasa el tema
            )
            st.download_button(
                label="Descargar Resultados del Examen como PDF 📄",
                data=pdf_buffer,
                file_name=f"Resultados_Examen_Redes_{pdf_user_name.replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                key="download_pdf_button"
            )

            for i, user_ans in enumerate(st.session_state['user_answers']):
                question_info = st.session_state['questions'][user_ans['question_index']]
                st.markdown(f"---")
                st.markdown(f"**Pregunta {i + 1}:** {question_info['question']}") # Aquí mantengo "Pregunta X:" para el display en web

                st.markdown("**Opciones:**")
                for option_text in question_info['options']:
                    st.markdown(f"- {option_text}")

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
                st.rerun()

# --- Punto de Entrada de la Aplicación ---
if __name__ == "__main__":
    main()
