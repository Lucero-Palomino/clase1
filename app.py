import streamlit as st
import google.generativeai as genai
import os
import random
import re # Importar para usar expresiones regulares

# Configurar Gemini API Key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# Funciones del core
def explicar_concepto(tema):
    prompt = f"""Eres un tutor de Arquitectura de Redes. Explica el concepto de {tema} de forma clara, concisa y paso a paso, como si se lo explicaras a un estudiante universitario. Incluye ejemplos si es pertinente."""
    response = model.generate_content(prompt)
    return response.text

def generar_ejercicio(tema, nivel):
    prompt = f"""Eres un tutor de Arquitectura de Redes. Crea un problema nuevo y original sobre {tema} para un estudiante de nivel {nivel}. Asegúrate de que el problema sea relevante para el tema y el nivel de dificultad. No incluyas la solución."""
    response = model.generate_content(prompt)
    return response.text

def evaluar_respuesta_y_dar_feedback(ejercicio, respuesta_estudiante):
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
    prompt = f"""Eres un experto en Arquitectura de Redes. Crea una pregunta de opción múltiple sobre {tema} para un estudiante de nivel {nivel}. La pregunta debe tener 4 opciones de respuesta (A, B, C, D), de las cuales solo una es correcta.
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
    o None si el parseo falla.
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
        # Si la línea no coincide con un patrón conocido, pero estamos en un tipo de línea
        # específico, podríamos intentar adjuntarla (ej. explicación multilinea)
        elif line_type == "explanation":
            explanation += " " + line # Para explicaciones que continúan en varias líneas
        # Podríamos agregar lógica similar para preguntas u opciones multilinea si fuera necesario

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

def main():
    st.title("👨‍🏫 Chatbot de ARQUITECTURA DE REDES para Universitarios")
    st.markdown("¡Bienvenido! Estoy aquí para ayudarte con tus dudas de Arquitectura de Redes.")

    # Selectores para Tema y Nivel
    temas = ["Redes LAN", "Protocolos de Red", "Modelos OSI/TCP-IP", "Seguridad de Red", "Dispositivos de Red", "Direccionamiento IP", "Enrutamiento", "Conmutación", "Subredes", "Capa Física"]
    nivel_estudiante = st.selectbox("Selecciona tu nivel actual:", ["Básico", "Intermedio", "Avanzado"])
    tema_seleccionado = st.selectbox("Selecciona un tema:", temas)

    # Opciones del chatbot
    opcion = st.radio("¿Qué quieres hacer hoy?", ("Explicar un Concepto", "Proponer un Ejercicio", "Evaluar mi Respuesta a un Ejercicio", "Tomar un Examen"))

    if opcion == "Explicar un Concepto":
        st.header(f"Explicación de {tema_seleccionado}")
        if st.button("Obtener Explicación"):
            with st.spinner("Generando explicación..."):
                explicacion = explicar_concepto(tema_seleccionado)
                st.write(explicacion)

    elif opcion == "Proponer un Ejercicio":
        st.header(f"Ejercicio de {tema_seleccionado} (Nivel {nivel_estudiante})")
        if st.button("Generar Ejercicio"):
            with st.spinner("Generando ejercicio..."):
                ejercicio = generar_ejercicio(tema_seleccionado, nivel_estudiante)
                st.session_state['current_exercise'] = ejercicio # Guardar el ejercicio para evaluación
                st.write(ejercicio)
            st.info("Ahora puedes ir a 'Evaluar mi Respuesta' para obtener retroalimentación.")

    elif opcion == "Evaluar mi Respuesta a un Ejercicio":
        st.header("Evaluar mi Respuesta")
        if 'current_exercise' in st.session_state and st.session_state['current_exercise']:
            st.write("**Ejercicio Actual:**")
            st.write(st.session_state['current_exercise'])
            respuesta_estudiante = st.text_area("Escribe aquí tu respuesta:")
            if st.button("Evaluar"):
                if respuesta_estudiante:
                    with st.spinner("Evaluando y generando feedback..."):
                        feedback = evaluar_respuesta_y_dar_feedback(st.session_state['current_exercise'], respuesta_estudiante)
                        st.write(feedback)
                else:
                    st.warning("Por favor, escribe tu respuesta para evaluar.")
        else:
            st.info("Primero genera un ejercicio en la sección 'Proponer un Ejercicio'.")

    elif opcion == "Tomar un Examen":
        st.header("Examen de Arquitectura de Redes")
        st.markdown("Presiona 'Comenzar Ahora' para iniciar el examen de 10 preguntas.")

        # Inicialización del estado del examen
        if 'exam_started' not in st.session_state:
            st.session_state['exam_started'] = False
            st.session_state['current_question_index'] = 0
            st.session_state['score'] = 0
            st.session_state['questions'] = []
            st.session_state['user_answers'] = []
            st.session_state['exam_finished'] = False

        if not st.session_state['exam_started']:
            if st.button("Comenzar Ahora"):
                st.session_state['exam_started'] = True
                st.session_state['current_question_index'] = 0
                st.session_state['score'] = 0
                st.session_state['questions'] = []
                st.session_state['user_answers'] = []
                st.session_state['exam_finished'] = False
                with st.spinner("Generando preguntas del examen..."):
                    while len(st.session_state['questions']) < 10:
                        question_data_raw = generar_pregunta_multiple_choice(tema_seleccionado, nivel_estudiante)
                        parsed_question = parse_multiple_choice_question(question_data_raw)
                        if parsed_question:
                            st.session_state['questions'].append(parsed_question)
                        else:
                            st.warning(f"No se pudo parsear una pregunta. Reintentando... Datos crudos: {question_data_raw[:200]}...") # Mostrar un fragmento
                            # El bucle while se encarga de reintentar hasta obtener 10 preguntas válidas
                st.experimental_rerun() # Rerun para mostrar la primera pregunta

        if st.session_state['exam_started'] and not st.session_state['exam_finished']:
            if st.session_state['current_question_index'] < len(st.session_state['questions']):
                current_question = st.session_state['questions'][st.session_state['current_question_index']]
                st.subheader(f"Pregunta {st.session_state['current_question_index'] + 1} de {len(st.session_state['questions'])}")
                st.write(current_question['question'])

                selected_option_label = st.radio("Elige una opción:", current_question['options'], key=f"q_{st.session_state['current_question_index']}")

                if st.button("Siguiente Pregunta" if st.session_state['current_question_index'] < len(st.session_state['questions']) - 1 else "Terminar Examen"):
                    if selected_option_label:
                        user_answer_char = selected_option_label[0] # Get A, B, C, or D
                        st.session_state['user_answers'].append({
                            'question_index': st.session_state['current_question_index'],
                            'user_choice_char': user_answer_char,
                            'correct_char': current_question['correct_answer_char']
                        })

                        if user_answer_char == current_question['correct_answer_char']:
                            st.session_state['score'] += 1

                        st.session_state['current_question_index'] += 1
                        if st.session_state['current_question_index'] >= len(st.session_state['questions']):
                            st.session_state['exam_finished'] = True
                            st.experimental_rerun() # Rerun to show results
                        else:
                            st.experimental_rerun() # Rerun to show next question
                    else:
                        st.warning("Por favor, selecciona una opción antes de continuar.")
            else: # Esto maneja el caso donde el índice va más allá de las preguntas (debería ser cubierto por el if anterior)
                st.session_state['exam_finished'] = True
                st.experimental_rerun()

        if st.session_state['exam_finished']:
            st.success(f"¡Examen Terminado! Has respondido correctamente a {st.session_state['score']} de {len(st.session_state['questions'])} preguntas.")
            st.subheader("Resultados Detallados:")
            for i, user_ans in enumerate(st.session_state['user_answers']):
                question_info = st.session_state['questions'][user_ans['question_index']]
                st.markdown(f"---")
                st.markdown(f"**Pregunta {i + 1}:** {question_info['question']}")
                st.markdown(f"Tu respuesta: **{user_ans['user_choice_char']}**")
                st.markdown(f"Respuesta correcta: **{user_ans['correct_char']}**")
                if user_ans['user_choice_char'] == user_ans['correct_char']:
                    st.success("¡Correcto!")
                else:
                    st.error("Incorrecto.")
                st.markdown(f"**Explicación:** {question_info['explanation']}")

            if st.button("Reiniciar Examen"):
                # Limpiar el estado de la sesión para reiniciar el examen
                for key in ['exam_started', 'current_question_index', 'score', 'questions', 'user_answers', 'exam_finished']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.experimental_rerun()

if __name__ == "__main__":
    main()
