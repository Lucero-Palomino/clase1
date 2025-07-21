
import streamlit as st
import google.generativeai as genai
import os

# Configurar clave API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# Inicializar estados
if "preguntas_correctas" not in st.session_state:
    st.session_state["preguntas_correctas"] = 0
if "preguntas_incorrectas" not in st.session_state:
    st.session_state["preguntas_incorrectas"] = 0
if "preguntas_lista" not in st.session_state:
    st.session_state["preguntas_lista"] = []
if "indice_pregunta_actual" not in st.session_state:
    st.session_state["indice_pregunta_actual"] = 0
if "respondiendo_examen" not in st.session_state:
    st.session_state["respondiendo_examen"] = False
if "respuesta_enviada" not in st.session_state:
    st.session_state["respuesta_enviada"] = False

# FUNCIONES

def explicar_concepto(tema):
    prompt = f"Eres un tutor universitario experto en Arquitectura de Redes. Explica el concepto de {tema} de forma clara, concisa y paso a paso."
    response = model.generate_content(prompt)
    return response.text

def generar_ejercicio(tema, nivel):
    prompt = f"Eres un tutor de Arquitectura de Redes. Crea un problema original sobre {tema} para nivel {nivel}. No des la solución."
    response = model.generate_content(prompt)
    return response.text

def evaluar_respuesta_y_dar_feedback(ejercicio, respuesta_estudiante):
    prompt = f"""Eres un tutor de Arquitectura de Redes. Evalúa la siguiente respuesta:
Problema:
{ejercicio}

Respuesta:
{respuesta_estudiante}

Indica si es correcta, y da retroalimentación y solución si es incorrecta. Usa formato Markdown."""
    response = model.generate_content(prompt)
    return response.text

def generar_pregunta_opcion_multiple(tema):
    prompt = f"""Eres un profesor de Arquitectura de Redes. Crea una pregunta de opción múltiple sobre "{tema}" con 4 opciones (A-D), indica la correcta y justifica.

Formato:
Pregunta: ...
A) ...
B) ...
C) ...
D) ...
Respuesta correcta: ...
Justificación: ..."""
    response = model.generate_content(prompt)
    return response.text

# INTERFAZ PRINCIPAL

def main():
    st.title("🌐 Chatbot de Arquitectura de Redes")

    temas = ["Modelo OSI", "TCP/IP", "Dispositivos de red", "Direcciones IP", "Switching y Routing",
             "Protocolos de comunicación", "Redes LAN y WAN", "WiFi y redes inalámbricas", "Seguridad de red"]
    nivel_estudiante = st.selectbox("Selecciona tu nivel:", ["Básico", "Intermedio", "Avanzado"])
    tema_seleccionado = st.selectbox("Selecciona un tema:", temas)

    opcion = st.radio("¿Qué quieres hacer?",
                      ("Explicar un Concepto", "Proponer un Ejercicio", "Evaluar mi Respuesta", "📝 Examen de opción múltiple"))

    if opcion == "Explicar un Concepto":
        if st.button("🔍 Obtener Explicación"):
            st.markdown(explicar_concepto(tema_seleccionado), unsafe_allow_html=True)

    elif opcion == "Proponer un Ejercicio":
        if st.button("🎲 Generar Ejercicio"):
            ejercicio = generar_ejercicio(tema_seleccionado, nivel_estudiante)
            st.session_state['current_exercise'] = ejercicio
            st.markdown(ejercicio)
            st.info("Ahora responde en 'Evaluar mi Respuesta'.")

    elif opcion == "Evaluar mi Respuesta":
        if 'current_exercise' in st.session_state:
            st.markdown("**Ejercicio:**")
            st.markdown(st.session_state['current_exercise'])
            respuesta = st.text_area("Tu respuesta:")
            if st.button("📋 Evaluar"):
                if respuesta:
                    feedback = evaluar_respuesta_y_dar_feedback(st.session_state['current_exercise'], respuesta)
                    st.markdown(feedback, unsafe_allow_html=True)
                else:
                    st.warning("Escribe tu respuesta primero.")
        else:
            st.info("Primero genera un ejercicio.")

    elif opcion == "📝 Examen de opción múltiple":
        st.subheader("Examen de 10 preguntas, una por una")

        if not st.session_state["respondiendo_examen"]:
            if st.button("🟢 Comenzar Examen"):
                st.session_state["preguntas_lista"] = [generar_pregunta_opcion_multiple(tema_seleccionado) for _ in range(10)]
                st.session_state["indice_pregunta_actual"] = 0
                st.session_state["preguntas_correctas"] = 0
                st.session_state["preguntas_incorrectas"] = 0
                st.session_state["respondiendo_examen"] = True
                st.session_state["respuesta_enviada"] = False

        elif st.session_state["indice_pregunta_actual"] < 10:
            idx = st.session_state["indice_pregunta_actual"]
            pregunta_texto = st.session_state["preguntas_lista"][idx]
            lineas = pregunta_texto.split("\n")
            pregunta = next(l for l in lineas if l.startswith("Pregunta:")).split(":", 1)[1].strip()
            opciones = [l for l in lineas if l.startswith(("A)", "B)", "C)", "D)"))]
            respuesta_correcta = next(l for l in lineas if "Respuesta correcta:" in l).split(":")[1].strip()
            justificacion = next(l for l in lineas if "Justificación:" in l).split(":", 1)[1].strip()

            st.markdown(f"**{idx+1}. {pregunta}**")
            seleccion = st.radio("Selecciona una opción:", opciones, key=f"pregunta_{idx}")

            if not st.session_state["respuesta_enviada"]:
                if st.button("✔️ Verificar respuesta"):
                    eleccion = seleccion[0]
                    if eleccion == respuesta_correcta:
                        st.success("✅ ¡Correcto!")
                        st.session_state["preguntas_correctas"] += 1
                    else:
                        st.error(f"❌ Incorrecto. Respuesta correcta: {respuesta_correcta}")
                        st.info(f"📘 Justificación: {justificacion}")
                        st.session_state["preguntas_incorrectas"] += 1
                    st.session_state["respuesta_enviada"] = True
            else:
                if st.button("➡️ Siguiente pregunta"):
                    st.session_state["indice_pregunta_actual"] += 1
                    st.session_state["respuesta_enviada"] = False

        else:
            st.success("🎉 Examen finalizado")
            st.write(f"✅ Correctas: {st.session_state['preguntas_correctas']}")
            st.write(f"❌ Incorrectas: {st.session_state['preguntas_incorrectas']}")
            if st.button("🔁 Reiniciar Examen"):
                st.session_state["respondiendo_examen"] = False

if __name__ == "__main__":
    main()
