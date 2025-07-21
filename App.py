
import streamlit as st
import google.generativeai as genai
import os

# Configurar clave API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# Variables de estado para contar respuestas
if "preguntas_correctas" not in st.session_state:
    st.session_state["preguntas_correctas"] = 0
if "preguntas_incorrectas" not in st.session_state:
    st.session_state["preguntas_incorrectas"] = 0

# FUNCIONES

def explicar_concepto(tema):
    prompt = f"Eres un tutor universitario experto en Arquitectura de Redes. Explica el concepto de {tema} de forma clara, concisa y paso a paso. Incluye ejemplos si es pertinente."
    response = model.generate_content(prompt)
    return response.text

def generar_ejercicio(tema, nivel):
    prompt = f"Eres un tutor de Arquitectura de Redes. Crea un problema nuevo y original sobre {tema} para un estudiante de nivel {nivel}. No des la solución, solo el enunciado."
    response = model.generate_content(prompt)
    return response.text

def evaluar_respuesta_y_dar_feedback(ejercicio, respuesta_estudiante):
    prompt = f"""Eres un tutor de Arquitectura de Redes. Tu tarea es evaluar la respuesta de un estudiante a un problema y proporcionar retroalimentación detallada.
    Problema:
    {ejercicio}

    Respuesta del estudiante:
    {respuesta_estudiante}

    Por favor, sigue estos pasos:
    1. Indica si la respuesta del estudiante es correcta o incorrecta.
    2. Si es incorrecta, explica por qué.
    3. Da la solución completa paso a paso.
    4. Usa formato Markdown.
    """
    response = model.generate_content(prompt)
    return response.text

def generar_pregunta_opcion_multiple(tema):
    prompt = f"""Eres un profesor de Arquitectura de Redes. Crea una pregunta de opción múltiple sobre el tema "{tema}".
- Incluye 4 alternativas (A, B, C, D).
- Indica claramente cuál es la respuesta correcta.
- Luego proporciona una breve justificación.

Formato:
Pregunta: ...
A) ...
B) ...
C) ...
D) ...
Respuesta correcta: ...
Justificación: ...
"""
    response = model.generate_content(prompt)
    return response.text

# INTERFAZ PRINCIPAL

def main():
    st.title("🌐 Chatbot de Arquitectura de Redes")
    st.markdown("¡Bienvenido! Soy tu asistente virtual para ayudarte con tus dudas de Arquitectura de Redes.")

    temas = ["Modelo OSI", "TCP/IP", "Dispositivos de red", "Direcciones IP", "Switching y Routing",
             "Protocolos de comunicación", "Redes LAN y WAN", "WiFi y redes inalámbricas", "Seguridad de red"]
    nivel_estudiante = st.selectbox("Selecciona tu nivel actual:", ["Básico", "Intermedio", "Avanzado"])
    tema_seleccionado = st.selectbox("Selecciona un tema:", temas)

    opcion = st.radio("¿Qué quieres hacer hoy?",
                      ("Explicar un Concepto", "Proponer un Ejercicio", "Evaluar mi Respuesta a un Ejercicio", "📝 Examen de opción múltiple"))

    if opcion == "Explicar un Concepto":
        st.header(f"📖 Explicación de {tema_seleccionado}")
        if st.button("🔍 Obtener Explicación"):
            with st.spinner("Generando explicación..."):
                st.markdown(explicar_concepto(tema_seleccionado), unsafe_allow_html=True)

    elif opcion == "Proponer un Ejercicio":
        st.header(f"🧠 Ejercicio de {tema_seleccionado} (Nivel {nivel_estudiante})")
        if st.button("🎲 Generar Ejercicio"):
            with st.spinner("Generando ejercicio..."):
                ejercicio = generar_ejercicio(tema_seleccionado, nivel_estudiante)
                st.session_state['current_exercise'] = ejercicio
                st.markdown(ejercicio)
                st.info("Ahora puedes ir a 'Evaluar mi Respuesta' para obtener retroalimentación.")

    elif opcion == "Evaluar mi Respuesta a un Ejercicio":
        st.header("✅ Evaluar mi Respuesta")
        if 'current_exercise' in st.session_state:
            st.markdown("**Ejercicio Actual:**")
            st.markdown(st.session_state['current_exercise'])
            respuesta_estudiante = st.text_area("✏️ Escribe aquí tu respuesta:")
            if st.button("📋 Evaluar"):
                if respuesta_estudiante:
                    with st.spinner("Evaluando..."):
                        feedback = evaluar_respuesta_y_dar_feedback(st.session_state['current_exercise'], respuesta_estudiante)
                        st.markdown(feedback, unsafe_allow_html=True)
                else:
                    st.warning("Por favor, escribe tu respuesta para evaluar.")
        else:
            st.info("Primero genera un ejercicio en la sección 'Proponer un Ejercicio'.")

    elif opcion == "📝 Examen de opción múltiple":
        st.header("📝 Examen de opción múltiple sobre Arquitectura de Redes")

        if "preguntas_lista" not in st.session_state:
            st.session_state["preguntas_lista"] = []
            st.session_state["respuestas_usuario"] = {}
            st.session_state["preguntas_mostradas"] = False

        if st.button("🧩 Generar 10 preguntas"):
            st.session_state["preguntas_lista"] = []
            st.session_state["respuestas_usuario"] = {}
            st.session_state["preguntas_mostradas"] = False
            with st.spinner("Generando preguntas..."):
                for _ in range(10):
                    pregunta_bruta = generar_pregunta_opcion_multiple(tema_seleccionado)
                    st.session_state["preguntas_lista"].append(pregunta_bruta)
            st.session_state["preguntas_mostradas"] = True

        if st.session_state.get("preguntas_mostradas", False):
            st.subheader("🧪 Responde a las siguientes preguntas:")

            for idx, pregunta_texto in enumerate(st.session_state["preguntas_lista"]):
                try:
                    lineas = pregunta_texto.split("\n")
                    pregunta = next(l for l in lineas if l.startswith("Pregunta:")).split(":", 1)[1].strip()
                    opciones = [l for l in lineas if l.startswith(("A)", "B)", "C)", "D)"))]
                    respuesta_correcta = next(l for l in lineas if "Respuesta correcta:" in l).split(":")[1].strip()
                    justificacion = next(l for l in lineas if "Justificación:" in l).split(":", 1)[1].strip()

                    st.markdown(f"**{idx+1}. {pregunta}**")
                    seleccion = st.radio("Elige una opción:", opciones, key=f"preg_{idx}")

                    if st.button(f"✔️ Verificar pregunta {idx+1}"):
                        eleccion_usuario = st.session_state[f"preg_{idx}"][0]
                        ya_respondida = f"resp_{idx}" in st.session_state["respuestas_usuario"]

                        if not ya_respondida:
                            if eleccion_usuario == respuesta_correcta:
                                st.success("✅ ¡Correcto!")
                                st.session_state["preguntas_correctas"] += 1
                            else:
                                st.error(f"❌ Incorrecto. La respuesta correcta era: {respuesta_correcta}")
                                st.info(f"📘 Justificación: {justificacion}")
                                st.session_state["preguntas_incorrectas"] += 1

                            st.session_state["respuestas_usuario"][f"resp_{idx}"] = eleccion_usuario

                        st.markdown("---")
                except Exception as e:
                    st.warning(f"Ocurrió un error en la pregunta {idx+1}.")
                    st.text_area(f"Texto de la pregunta {idx+1}:", pregunta_texto)

            if len(st.session_state["respuestas_usuario"]) == 10:
                st.success("🎉 Has respondido todas las preguntas.")
                st.write(f"✅ Correctas: {st.session_state['preguntas_correctas']}")
                st.write(f"❌ Incorrectas: {st.session_state['preguntas_incorrectas']}")

if __name__ == "__main__":
    main()
