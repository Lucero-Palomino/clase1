# app.py
import streamlit as st
import google.generativeai as genai
import os

# Configurar clave API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# Funciones
def explicar_concepto(tema):
    prompt = f"""Eres un tutor universitario experto en análisis de series de tiempo. Explica el concepto de "{tema}" de forma clara, paso a paso, con ejemplos sencillos y fórmulas si es necesario."""
    response = model.generate_content(prompt)
    return response.text

def generar_ejercicio(tema, nivel):
    prompt = f"""Eres un docente de estadística. Crea un ejercicio sobre "{tema}" para un estudiante de nivel {nivel}. No des la solución, solo el enunciado. Usa datos realistas."""
    response = model.generate_content(prompt)
    return response.text

def evaluar_respuesta_y_dar_feedback(ejercicio, respuesta):
    prompt = f"""Eres un profesor de estadística. Evalúa la siguiente respuesta del estudiante al ejercicio dado y proporciona retroalimentación clara. Luego resuelve el ejercicio paso a paso.
    
    Ejercicio: {ejercicio}
    Respuesta del estudiante: {respuesta}
    
    Da tu evaluación en formato Markdown."""
    response = model.generate_content(prompt)
    return response.text

# Interfaz
def main():
    st.title("📊 Chatbot de Series de Tiempo")
    st.markdown("Asistente para aprender, practicar y evaluar temas de series temporales.")

    temas = ["Tendencia", "Estacionalidad", "Suavizamiento exponencial", "ARIMA", "Descomposición", "Pronóstico", "Correlograma"]
    nivel = st.selectbox("Nivel del estudiante:", ["Básico", "Intermedio", "Avanzado"])
    tema = st.selectbox("Selecciona un tema:", temas)
    opcion = st.radio("¿Qué quieres hacer?", ["Explicar un Concepto", "Proponer un Ejercicio", "Evaluar mi Respuesta"])

    if opcion == "Explicar un Concepto":
        if st.button("Explicar"):
            with st.spinner("Generando explicación..."):
                st.write(explicar_concepto(tema))
    
    elif opcion == "Proponer un Ejercicio":
        if st.button("Generar"):
            with st.spinner("Generando ejercicio..."):
                ejercicio = generar_ejercicio(tema, nivel)
                st.session_state['ejercicio_actual'] = ejercicio
                st.write(ejercicio)
                st.info("Ahora puedes ir a 'Evaluar mi respuesta' para que lo corrija.")
    
    elif opcion == "Evaluar mi Respuesta":
        if 'ejercicio_actual' in st.session_state:
            st.write("**Ejercicio:**")
            st.write(st.session_state['ejercicio_actual'])
            respuesta = st.text_area("Tu respuesta:")
            if st.button("Evaluar"):
                with st.spinner("Evaluando..."):
                    st.write(evaluar_respuesta_y_dar_feedback(st.session_state['ejercicio_actual'], respuesta))
        else:
            st.warning("Primero debes generar un ejercicio.")

if __name__ == "__main__":
    main()
