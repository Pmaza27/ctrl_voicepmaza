import os
import json
import time
import glob
import streamlit as st
from PIL import Image
import paho.mqtt.client as paho
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from gtts import gTTS
from deep_translator import GoogleTranslator  # ✅ reemplazo moderno y compatible


# ───────────────────────────────────────────────
# CONFIGURACIÓN MQTT
# ───────────────────────────────────────────────
def on_publish(client, userdata, result):
    print("✅ Dato publicado correctamente\n")


def on_message(client, userdata, message):
    global message_received
    time.sleep(2)
    message_received = str(message.payload.decode("utf-8"))
    st.write(f"📩 Mensaje recibido: {message_received}")


broker = "broker.mqttdashboard.com"
port = 1883
client1 = paho.Client("isabela")
client1.on_message = on_message


# ───────────────────────────────────────────────
# CONFIGURACIÓN DE LA PÁGINA
# ───────────────────────────────────────────────
st.set_page_config(page_title="Control por Voz", page_icon="🎙️", layout="centered")

st.markdown(
    """
    <style>
        body {
            background-color: #fdf6ec;
            color: #2b2b2b;
        }
        h1 {
            font-family: 'Poppins', sans-serif;
            font-weight: 800;
            color: #1b1b1b;
            text-align: center;
        }
        h2, h3, h4 {
            font-family: 'Poppins', sans-serif;
            color: #444;
        }
        .stButton > button {
            background-color: #ffb74d;
            color: white;
            border: none;
            padding: 0.7rem 2rem;
            border-radius: 12px;
            font-size: 1.1rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background-color: #ffa726;
            transform: scale(1.05);
        }
        img {
            border-radius: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            display: block;
            margin: 1rem auto;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ───────────────────────────────────────────────
# INTERFAZ
# ───────────────────────────────────────────────
st.title("🎙️ INTERFACES MULTIMODALES")
st.subheader("CONTROL POR VOZ CON MQTT Y TRADUCCIÓN")

# Imagen de cabecera
image_path = "voice_ctrl.jpg"
if os.path.exists(image_path):
    st.image(image_path, width=250)
else:
    st.warning("⚠️ No se encontró 'voice_ctrl.jpg'. Verifica el nombre o ubicación del archivo.")

st.write("Toca el botón y habla lo que quieras enviar o traducir:")

# Botón de reconocimiento de voz
stt_button = Button(label="🎧 Iniciar Escucha", width=250)
stt_button.js_on_event("button_click", CustomJS(code="""
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = function (e) {
        var value = "";
        for (var i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
                value += e.results[i][0].transcript;
            }
        }
        if (value != "") {
            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
        }
    }
    recognition.start();
"""))

# Captura del texto hablado
result = streamlit_bokeh_events(
    stt_button,
    events="GET_TEXT",
    key="listen",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0
)

# ───────────────────────────────────────────────
# PROCESAMIENTO DE RESULTADOS
# ───────────────────────────────────────────────
if result and "GET_TEXT" in result:
    user_text = result.get("GET_TEXT").strip()
    st.success(f"🗣️ Texto detectado: **{user_text}**")

    # Conexión MQTT
    client1.on_publish = on_publish
    client1.connect(broker, port)
    message = json.dumps({"Act1": user_text})
    client1.publish("voice_isabela", message)

    # Crear carpeta temporal si no existe
    os.makedirs("temp", exist_ok=True)

    # Selección de idiomas
    in_lang = st.selectbox(
        "Selecciona el lenguaje de entrada",
        {"Inglés": "en", "Español": "es", "Francés": "fr", "Alemán": "de", "Italiano": "it"}
    )
    out_lang = st.selectbox(
        "Selecciona el lenguaje de salida",
        {"Inglés": "en", "Español": "es", "Francés": "fr", "Alemán": "de", "Italiano": "it"}
    )

    # Traducción
    try:
        trans_text = GoogleTranslator(source=in_lang, target=out_lang).translate(user_text)
        st.markdown(f"### 🈹 Traducción: \n**{trans_text}**")
    except Exception as e:
        st.error(f"❌ Error al traducir: {e}")
        trans_text = user_text

    # Convertir texto traducido a audio
    tts = gTTS(trans_text, lang=out_lang)
    file_name = f"temp/{user_text[:10].replace(' ', '_')}.mp3"
    tts.save(file_name)

    with open(file_name, "rb") as audio_file:
        st.audio(audio_file.read(), format="audio/mp3")

    # Limpieza automática de audios viejos
    def remove_old_files(days=7):
        mp3_files = glob.glob("temp/*.mp3")
        now = time.time()
        for f in mp3_files:
            if os.stat(f).st_mtime < now - (days * 86400):
                os.remove(f)
    remove_old_files()
