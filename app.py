import streamlit as st
import google.generativeai as genai
import os
import random # Importar para barajar las opciones


# Configurar Gemini API Key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# Funciones del core (las que definiste en el Paso 2)
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
    prompt = f"""Eres un experto en Arquitectura de Redes. Crea una pregunta de opción múltiple sobre {tema} para un estudiante de nivel {nivel}. La pregunta debe tener 4 opciones de respuesta (A, B, C, D), de las cuales solo una es correcta. Formatea la salida de la siguiente manera:

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
                    for _ in range(10): # Generar 10 preguntas
                        question_data_raw = generar_pregunta_multiple_choice(tema_seleccionado, nivel_estudiante)
                        # Intentar parsear la pregunta
                        try:
                            question_parts = question_data_raw.split('\n')
                            question_text = question_parts[0].replace('Pregunta: ', '').strip()
                            options = [q.strip() for q in question_parts[1:5]]
                            correct_answer_line = [q for q in question_parts if 'Respuesta Correcta:' in q][0]
                            correct_answer_char = correct_answer_line.split(':')[1].strip()
                            explanation_line = [q for q in question_parts if 'Explicación:' in q][0]
                            explanation = explanation_line.split(':', 1)[1].strip()

                            # Shuffle options to make sure the correct answer isn't always in the same spot
                            shuffled_options_with_correct = []
                            original_option_map = {}
                            for opt in options:
                                char = opt[0]
                                if char == correct_answer_char:
                                    original_option_map[opt] = True # Mark as correct
                                else:
                                    original_option_map[opt] = False # Mark as incorrect
                                shuffled_options_with_correct.append(opt)

                            random.shuffle(shuffled_options_with_correct)

                            # Find the new position of the correct answer after shuffling
                            new_correct_char = ''
                            new_options_display = []
                            for i, opt_display in enumerate(shuffled_options_with_correct):
                                char_label = chr(65 + i) # A, B, C, D
                                new_options_display.append(f"{char_label}) {opt_display[3:]}") # Remove original A) B) C) D)

                                if original_option_map.get(opt_display):
                                    new_correct_char = char_label


                            st.session_state['questions'].append({
                                'question': question_text,
                                'options': new_options_display,
                                'correct_answer_char': new_correct_char,
                                'explanation': explanation
                            })
                        except Exception as e:
                            st.warning(f"No se pudo parsear la pregunta. Saltando esta pregunta. Error: {e}\nRaw data: {question_data_raw}")
                            # Si falla, genera otra pregunta para asegurar 10
                            pass # allow loop to continue, next iteration will generate a new question if len < 10

                    # Ensure we have 10 questions, regenerate if parsing failed for some
                    while len(st.session_state['questions']) < 10:
                        question_data_raw = generar_pregunta_multiple_choice(tema_seleccionado, nivel_estudiante)
                        try:
                            question_parts = question_data_raw.split('\n')
                            question_text = question_parts[0].replace('Pregunta: ', '').strip()
                            options_raw = [q.strip() for q in question_parts[1:5]]
                            correct_answer_line = [q for q in question_parts if 'Respuesta Correcta:' in q][0]
                            correct_answer_char = correct_answer_line.split(':')[1].strip()
                            explanation_line = [q for q in question_parts if 'Explicación:' in q][0]
                            explanation = explanation_line.split(':', 1)[1].strip()

                            shuffled_options_with_correct = []
                            original_option_map = {}
                            for opt in options_raw:
                                char = opt[0]
                                if char == correct_answer_char:
                                    original_option_map[opt] = True
                                else:
                                    original_option_map[opt] = False
                                shuffled_options_with_correct.append(opt)

                            random.shuffle(shuffled_options_with_correct)

                            new_correct_char = ''
                            new_options_display = []
                            for i, opt_display in enumerate(shuffled_options_with_correct):
                                char_label = chr(65 + i)
                                new_options_display.append(f"{char_label}) {opt_display[3:]}")

                                if original_option_map.get(opt_display):
                                    new_correct_char = char_label

                            st.session_state['questions'].append({
                                'question': question_text,
                                'options': new_options_display,
                                'correct_answer_char': new_correct_char,
                                'explanation': explanation
                            })
                        except Exception as e:
                            st.warning(f"Re-generación: No se pudo parsear la pregunta. Saltando esta pregunta. Error: {e}\nRaw data: {question_data_raw}")


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
            else:
                st.session_state['exam_finished'] = True
                st.experimental_rerun() # In case somehow index goes out of bound

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
                del st.session_state['exam_started']
                del st.session_state['current_question_index']
                del st.session_state['score']
                del st.session_state['questions']
                del st.session_state['user_answers']
                del st.session_state['exam_finished']
                st.experimental_rerun()


if __name__ == "__main__":
    main()
