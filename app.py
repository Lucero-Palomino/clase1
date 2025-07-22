import streamlit as st
import google.generativeai as genai
import os
import random
import re

# Configurar Gemini API Key
# Asegúrate de tener una variable de entorno GEMINI_API_KEY configurada
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
        # Almacenar la opción cruda y si es la correcta
        original_option_map[opt_raw] = (char == correct_answer_char)
        shuffled_options_with_correct.append(opt_raw)

    random.shuffle(shuffled_options_with_correct)

    new_correct_char = ''
    new_options_display = []
    for i, opt_display in enumerate(shuffled_options_with_correct):
        char_label = chr(65 + i) # Genera A, B, C, D
        # Eliminar el prefijo original (ej. "A)") para mostrar solo el texto de la opción
        option_text = opt_display[3:].strip() if opt_display.startswith(tuple("ABCD)")) else opt_display.strip()
        new_options_display.append(f"{char_label}) {option_text}")

        if original_option_map.get(opt_display):
            new_correct_char = char_label

    if not new_correct_char: # Si por alguna razón no se encontró la respuesta correcta después de barajar
        return None

    return {
        'question': question_text,
        'options': new_options_display,
        'correct_answer_char': new_correct_char,
        'explanation': explanation
    }

# --- Función Principal de Streamlit ---

def main():
    # --- Cargar estilos CSS externos ---
    # Asegúrate de que style.css esté en la misma carpeta que app.py
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("Error: El archivo 'style.css' no se encontró. Asegúrate de que esté en la misma carpeta que 'app.py'.")

    st.title("👨‍🏫 Chatbot de ARQUITECTURA DE REDES para Universitarios 🌐")
    st.markdown("---")
    st.markdown("¡Bienvenido! Estoy aquí para ayudarte a **dominar** la Arquitectura de Redes. Selecciona una opción para comenzar tu aprendizaje o desafiarte con un examen. ✨")

    # Definimos los temas principales para los selectores de explicación/ejercicio
    temas_principales = ["Redes LAN", "Protocolos de Red", "Modelos OSI/TCP-IP", "Seguridad de Red", "Dispositivos de Red", "Direccionamiento IP", "Enrutamiento", "Conmutación", "Subredes", "Capa Física"]

    # Definimos una lista más granular de sub-temas para la generación de preguntas del examen
    # Esto es clave para la variedad y evitar repeticiones.
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


    # Uso de columnas para organizar los selectores de nivel y tema
    col_level, col_topic = st.columns(2)
    with col_level:
        nivel_estudiante = st.selectbox("Selecciona tu nivel actual:", ["Básico", "Intermedio", "Avanzado"], key="nivel_select")
    with col_topic:
        tema_seleccionado = st.selectbox("Selecciona un tema general:", temas_principales, key="tema_select")

    st.markdown("---")

    # Uso de pestañas para organizar las diferentes funcionalidades
    tab1, tab2, tab3, tab4 = st.tabs([":bulb: Explicar Concepto", ":pencil: Proponer Ejercicio", ":clipboard: Evaluar Respuesta", ":test_tube: Tomar Examen"])

    with tab1:
        st.header(f"Explicación de {tema_seleccionado}")
        st.markdown("Aquí puedes obtener explicaciones detalladas sobre cualquier concepto.")
        if st.button("Obtener Explicación :mag:", key="get_explanation_button"):
            with st.spinner("Generando explicación..."):
                explicacion = explicar_concepto(tema_seleccionado)
                st.info(explicacion)

    with tab2:
        st.header(f"Ejercicio de {tema_seleccionado} (Nivel {nivel_estudiante})")
        st.markdown("¡Pon a prueba tus conocimientos con un problema nuevo!")
        if st.button("Generar Ejercicio :brain:", key="generate_exercise_button"):
            with st.spinner("Generando ejercicio..."):
                ejercicio = generar_ejercicio(tema_seleccionado, nivel_estudiante)
            st.session_state['current_exercise'] = ejercicio
            st.success(ejercicio)
            st.info("Ahora puedes ir a 'Evaluar mi Respuesta' para obtener retroalimentación.")

    with tab3:
        st.header("Evaluar mi Respuesta")
        st.markdown("Recibe retroalimentación detallada sobre tus soluciones a los ejercicios.")
        if 'current_exercise' in st.session_state and st.session_state['current_exercise']:
            st.info("**Ejercicio Actual:**")
            st.markdown(st.session_state['current_exercise'])
            respuesta_estudiante = st.text_area("Escribe aquí tu respuesta:", key="student_response_area")
            if st.button("Evaluar :chart_with_upwards_trend:", key="evaluate_button"):
                if respuesta_estudiante:
                    with st.spinner("Evaluando y generando feedback..."):
                        feedback = evaluar_respuesta_y_dar_feedback(st.session_state['current_exercise'], respuesta_estudiante)
                    st.markdown(feedback)
                else:
                    st.warning("Por favor, escribe tu respuesta para evaluar.")
        else:
            st.info("Primero genera un ejercicio en la sección 'Proponer un Ejercicio'.")

    with tab4:
        st.header("Examen de Arquitectura de Redes :book:")
        st.markdown("¿Listo para un desafío? Responde 10 preguntas de opción múltiple. ¡Buena suerte!")

        # Inicialización del estado del examen
        if 'exam_started' not in st.session_state:
            st.session_state['exam_started'] = False
            st.session_state['current_question_index'] = 0
            st.session_state['score'] = 0
            st.session_state['questions'] = []
            st.session_state['user_answers'] = []
            st.session_state['exam_finished'] = False
            st.session_state['exam_active_session'] = False # Nueva bandera para controlar la sesión activa

        if not st.session_state['exam_started']:
            if st.button("Comenzar Examen Ahora :rocket:", key="start_exam_button"):
                st.session_state['exam_started'] = True
                st.session_state['current_question_index'] = 0
                st.session_state['score'] = 0
                st.session_state['questions'] = []
                st.session_state['user_answers'] = []
                st.session_state['exam_finished'] = False
                st.session_state['exam_active_session'] = True # Activar sesión de examen

                with st.spinner("Generando las 10 preguntas del examen..."):
                    generated_themes = set() # Para llevar un registro de los temas ya usados en este examen
                    while len(st.session_state['questions']) < 10:
                        # Selecciona un sub-tema aleatorio que no se haya usado todavía en este examen
                        available_themes = [t for t in posibles_sub_temas_para_examen if t not in generated_themes]
                        if not available_themes: # Si ya se usaron todos los temas, reinicia la lista
                            st.warning("Se han utilizado todos los sub-temas posibles. Reutilizando temas para completar el examen.")
                            available_themes = list(posibles_sub_temas_para_examen)
                            generated_themes.clear() # Limpiar para empezar a reutilizar

                        current_sub_tema = random.choice(available_themes)
                        
                        question_data_raw = generar_pregunta_multiple_choice(current_sub_tema, nivel_estudiante)
                        parsed_question = parse_multiple_choice_question(question_data_raw)
                        
                        if parsed_question:
                            st.session_state['questions'].append(parsed_question)
                            generated_themes.add(current_sub_tema) # Añadir el tema al conjunto de usados
                        else:
                            st.warning(f"⚠️ No se pudo parsear una pregunta. Reintentando... Posible formato inesperado de Gemini para: '{current_sub_tema}'.")
                # Streamlit detectará los cambios en session_state y re-ejecutará automáticamente.

        # Lógica para mostrar preguntas y manejar la navegación durante el examen
        if st.session_state.get('exam_active_session', False) and not st.session_state['exam_finished']:
            if st.session_state['current_question_index'] < len(st.session_state['questions']):
                current_question = st.session_state['questions'][st.session_state['current_question_index']]
                st.subheader(f"Pregunta {st.session_state['current_question_index'] + 1} de {len(st.session_state['questions'])}")

                # Intentar mostrar el sub-tema si es posible extraerlo del prompt original de Gemini
                try:
                    # Intenta encontrar el tema entre comillas dobles, o después de "sobre"
                    match = re.search(r'sobre "([^"]+)"', current_question['question'])
                    if match:
                        display_topic = match.group(1)
                    else:
                        # Fallback si no está entre comillas dobles
                        display_topic = current_question['question'].split(':', 1)[0].split(' sobre ')[0].replace('¿Qué es el concepto de ', '').replace('Pregunta sobre ', '').strip()
                        if display_topic == current_question['question']: # Si no se pudo limpiar, muestra el tema general
                             display_topic = tema_seleccionado
                except Exception:
                    display_topic = tema_seleccionado # Si falla la extracción, usa el tema general

                st.markdown(f"**Tema cubierto:** *{display_topic}*")
                st.write(current_question['question'])

                # Usar una clave única para el radio button de cada pregunta
                selected_option_label = st.radio(
                    "Elige una opción:",
                    current_question['options'],
                    key=f"q_radio_{st.session_state['current_question_index']}"
                )

                if st.button("Siguiente Pregunta :arrow_right:" if st.session_state['current_question_index'] < len(st.session_state['questions']) - 1 else "Terminar Examen :checkered_flag:", key=f"next_q_button_{st.session_state['current_question_index']}"):
                    if selected_option_label:
                        user_answer_char = selected_option_label[0] # Obtener la letra (A, B, C, D)
                        st.session_state['user_answers'].append({
                            'question_index': st.session_state['current_question_index'],
                            'user_choice_char': user_answer_char,
                            'correct_char': current_question['correct_answer_char']
                        })

                        if user_answer_char == current_question['correct_answer_char']:
                            st.session_state['score'] += 1

                        st.session_state['current_question_index'] += 1
                        # Si es la última pregunta o se pasa del límite, marca el examen como terminado
                        if st.session_state['current_question_index'] >= len(st.session_state['questions']):
                            st.session_state['exam_finished'] = True
                            st.session_state['exam_active_session'] = False # Desactivar sesión de examen
                        # No se necesita st.experimental_rerun() aquí, Streamlit maneja el estado
                    else:
                        st.warning("Por favor, selecciona una opción antes de continuar.")
            else: # Esto maneja el caso donde el índice se sale del rango (si no se manejó en el botón anterior)
                st.session_state['exam_finished'] = True
                st.session_state['exam_active_session'] = False

        # Lógica para mostrar los resultados finales del examen
        if st.session_state['exam_finished']:
            st.balloons() # ¡Animación de celebración!
            st.success(f"🎉 ¡Examen Terminado! Has respondido correctamente a **{st.session_state['score']}** de **{len(st.session_state['questions'])}** preguntas. ¡Felicidades! 🎉")
            st.markdown("---")
            st.subheader("Resultados Detallados:")
            for i, user_ans in enumerate(st.session_state['user_answers']):
                question_info = st.session_state['questions'][user_ans['question_index']]
                st.markdown(f"---")
                st.markdown(f"**Pregunta {i + 1}:** {question_info['question']}")
                st.markdown(f"Tu respuesta: **{user_ans['user_choice_char']}**")
                st.markdown(f"Respuesta correcta: **{user_ans['correct_char']}**")
                
                if user_ans['user_choice_char'] == user_ans['correct_char']:
                    st.success("✅ ¡Correcto!")
                else:
                    st.error("❌ Incorrecto.")
                    # --- AQUÍ ES DONDE DEBES COLOCAR LOS VIDEOS O IMÁGENES ---
                    st.markdown(f"**Explicación:** {question_info['explanation']}")

                    # EJEMPLOS: Usa condiciones para mostrar el multimedia adecuado
                    # Convierte la pregunta a minúsculas para una comparación insensible a mayúsculas
                    q_lower = question_info['question'].lower()

                    if "capa física" in q_lower or "codificación" in q_lower:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Modem_diagram.svg/300px-Modem_diagram.svg.png",
                                 caption="Ejemplo de Codificación en Capa Física",
                                 width=300)
                        st.markdown("_Este diagrama ilustra cómo se transforman los datos en señales físicas._")

                    elif "capa de presentación" in q_lower or "cifrado" in q_lower:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Cipher_block_chaining_decryption.svg/300px-Cipher_block_chaining_decryption.svg.png",
                                 caption="Proceso de Cifrado/Descifrado (Capa de Presentación)",
                                 width=300)
                        st.markdown("_La capa de presentación maneja la compresión y el cifrado._")

                    elif "conmutación de paquetes" in q_lower:
                        st.video("https://www.youtube.com/watch?v=yW6hI1F8K-0") # Reemplaza con un URL de video real y relevante
                        st.markdown("_Video: ¿Cómo funciona la conmutación de paquetes?_")

                    elif "ripv1" in q_lower or "enrutamiento" in q_lower:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Router_distance_vector_protocol_RIP.png/400px-Router_distance_vector_protocol_RIP.png",
                                 caption="Métrica de Saltos en RIP",
                                 width=400)
                        st.markdown("_RIP se basa solo en el conteo de saltos._")

                    elif "dhcp" in q_lower:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/DHCP_Process.svg/400px-DHCP_Process.svg.png",
                                 caption="Proceso DORA de DHCP",
                                 width=400)
                        st.markdown("_El cliente puede recibir múltiples ofertas antes de elegir._")
                    
                    elif "conmutación de circuitos" in q_lower:
                        st.video("https://www.youtube.com/watch?v=JmUa6s_t-6s") # Otro ejemplo de URL de video
                        st.markdown("_Video: Conmutación de Circuitos vs Paquetes._")

                    elif "dns" in q_lower:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/DNS_query_example.svg/450px-DNS_query_example.svg.png",
                                 caption="Funcionamiento de DNS",
                                 width=450)
                        st.markdown("_El proceso de resolución de DNS inicia con la consulta al servidor recursivo._")
                    
                    elif "tcp" in q_lower or "udp" in q_lower:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/TCP_UDP.svg/350px-TCP_UDP.svg.png",
                                 caption="Comparación TCP vs UDP",
                                 width=350)
                        st.markdown("_TCP garantiza fiabilidad, UDP se enfoca en la velocidad._")

                    elif "topología de malla" in q_lower:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Mesh_topology.svg/400px-Mesh_topology.svg.png",
                                 caption="Topología de Malla Completa",
                                 width=400)
                        st.markdown("_Las mallas completas requieren muchos cables, elevando el coste._")

                    elif "csma/ca" in q_lower:
                        st.video("https://www.youtube.com/watch?v=F07X648C-x0") # Un video corto sobre CSMA/CA
                        st.markdown("_Video: Entendiendo CSMA/CA y su ventana de contención._")
                    
                    # Puedes añadir más `elif` o `if` con diferentes palabras clave y sus respectivos medios.
                    # Asegúrate de reemplazar los URLs de ejemplo con URLs de imágenes y videos reales que hayas seleccionado.

                st.markdown("---") # Separador para cada pregunta en los resultados

            st.markdown("---")
            if st.button("Reiniciar Examen :repeat:", key="reset_exam_button_final"):
                # Limpiar el estado de la sesión para reiniciar el examen
                for key in ['exam_started', 'current_question_index', 'score', 'questions', 'user_answers', 'exam_finished', 'exam_active_session']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.experimental_rerun() # Forzar un re-render para volver al estado inicial

# --- Punto de Entrada de la Aplicación ---
if __name__ == "__main__":
    main()
