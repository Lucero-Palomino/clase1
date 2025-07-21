import streamlit as st
import google.generativeai as genai
import os

# Configurar API de Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# Estado inicial
if "preguntas_correctas" not in st.session_state:
    st.session_state["preguntas_correctas"] = 0
if "preguntas_incorrectas" not in st.session_state:
    st.session_state["preguntas_incorrectas"] = 0
if "indice_pregunta" not in st.session_state:
    st.session_state["indice_pregunta"] = 0
if "mostrar_resultado" not in st.session_state:
    st.session_state["mostrar_resultado"] = False
if "pregunta_actual" not in st.session_state:
    st.session_state["pregunta_actual"] = ""

# Generar una sola pregunta
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

# Interfaz principal
def main():
    st.title("📝 Examen de Arquitectura de Redes (10 preguntas)")
    temas = ["Modelo OSI", "TCP/IP", "Dispositivos de red", "Direcciones IP", "Switching y Routing",
             "Protocolos de comunicación", "Redes LAN y WAN", "WiFi y redes inalámbricas", "Seguridad de red"]
    tema_seleccionado = st.selectbox("Selecciona un tema:", temas)

    if not st.session_state["mostrar_resultado"] and st.session_state["indice_pregunta"] < 10:
        if st.session_state["pregunta_actual"] == "":
            with st.spinner("Generando pregunta..."):
                st.session_state["pregunta_actual"] = generar_pregunta_opcion_multiple(tema_seleccionado)

        texto = st.session_state["pregunta_actual"]
        try:
            lineas = texto.split("\n")
            pregunta = next(l for l in lineas if l.startswith("Pregunta:")).split(":", 1)[1].strip()
            opciones = [l for l in lineas if l.startswith(("A)", "B)", "C)", "D)"))]
            respuesta_correcta = next(l for l in lineas if "Respuesta correcta:" in l).split(":")[1].strip()
            justificacion = next(l for l in lineas if "Justificación:" in l).split(":", 1)[1].strip()

            st.markdown(f"**Pregunta {st.session_state['indice_pregunta'] + 1}: {pregunta}**")
            seleccion = st.radio("Selecciona una respuesta:", opciones, key=f"respuesta_{st.session_state['indice_pregunta']}")

            if st.button("✔️ Verificar respuesta"):
                eleccion = seleccion[0]
                if eleccion == respuesta_correcta:
                    st.success("✅ ¡Correcto!")
                    st.session_state["preguntas_correctas"] += 1
                else:
                    st.error(f"❌ Incorrecto. La respuesta correcta era: {respuesta_correcta}")
                    st.info(f"🧠 Justificación: {justificacion}")
                    st.session_state["preguntas_incorrectas"] += 1

                st.session_state["indice_pregunta"] += 1
                st.session_state["pregunta_actual"] = ""

                if st.session_state["indice_pregunta"] >= 10:
                    st.session_state["mostrar_resultado"] = True

                st.experimental_rerun()

        except Exception:
            st.warning("Error al interpretar la pregunta.")
            st.text_area("Texto generado:", texto)

    elif st.session_state["mostrar_resultado"]:
        st.subheader("📊 Resultado del examen")
        st.write(f"✅ Correctas: {st.session_state['preguntas_correctas']}")
        st.write(f"❌ Incorrectas: {st.session_state['preguntas_incorrectas']}")
        if st.button("🔁 Reiniciar"):
            for key in ["preguntas_correctas", "preguntas_incorrectas", "indice_pregunta", "mostrar_resultado", "pregunta_actual"]:
                st.session_state[key] = 0 if isinstance(st.session_state[key], int) else ""
            st.experimental_rerun()

if __name__ == "__main__":
    main()
