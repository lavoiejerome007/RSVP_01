import json
import re
from pathlib import Path

import fitz
import streamlit as st
import streamlit.components.v1 as components


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="RSVP Reader",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b0d12;
        color: #f5f7fc;
    }
    [data-testid="stHeader"] {
        background: transparent;
    }
    [data-testid="stSidebar"] {
        background-color: #121620;
    }
    .hero {
        text-align: center;
        padding: 12px 0 18px 0;
    }
    .hero h1 {
        font-size: 2.5rem;
        margin-bottom: 4px;
    }
    .hero p {
        color: #aab2c5;
        font-size: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "filename" not in st.session_state:
    st.session_state.filename = ""

if "last_upload" not in st.session_state:
    st.session_state.last_upload = None


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <h1>📖 RSVP Reader</h1>
        <p>Une nouvelle façon de lire, un mot à la fois.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.header("📄 Document")

    uploaded_file = st.file_uploader(
        "Choisis un fichier PDF",
        type=["pdf"],
        help="Sélectionne un document PDF depuis ton ordinateur.",
    )

    if uploaded_file is not None:
        upload_id = (
            uploaded_file.name,
            len(uploaded_file.getvalue()),
        )

        if upload_id != st.session_state.last_upload:
            try:
                with fitz.open(
                    stream=uploaded_file.getvalue(),
                    filetype="pdf",
                ) as pdf:
                    pages = [
                        page.get_text("text", sort=True)
                        for page in pdf
                    ]

                extracted_text = "\n\n".join(pages).strip()

                st.session_state.pdf_text = extracted_text
                st.session_state.filename = uploaded_file.name
                st.session_state.last_upload = upload_id

                if extracted_text:
                    st.success(
                        f"PDF importé : "
                        f"{len(extracted_text.split())} mots."
                    )
                else:
                    st.warning(
                        "Aucun texte trouvé. "
                        "Ce PDF est peut-être un document scanné. "
                        "Une fonction OCR sera nécessaire."
                    )

            except Exception as error:
                st.error(f"Erreur lors de la lecture du PDF : {error}")

    st.divider()
    st.header("⚙️ Réglages")

    wpm = st.slider(
        "Vitesse (mots par minute)",
        min_value=60,
        max_value=1200,
        value=300,
        step=20,
    )

    font_size = st.slider(
        "Taille du texte",
        min_value=36,
        max_value=120,
        value=76,
        step=4,
    )

    st.caption(
        "Conseil : commence à 200–300 mots/minute "
        "et augmente progressivement."
    )

    st.divider()

    if st.session_state.pdf_text:
        st.subheader("📚 Document chargé")
        st.write(st.session_state.filename)

        total_words = len(st.session_state.pdf_text.split())
        st.metric("Nombre de mots", f"{total_words:,}".replace(",", " "))

        if st.button("🗑️ Effacer le document", use_container_width=True):
            st.session_state.pdf_text = ""
            st.session_state.filename = ""
            st.session_state.last_upload = None
            st.rerun()


# --------------------------------------------------
# EMPTY STATE
# --------------------------------------------------

if not st.session_state.pdf_text:
    st.info("Importe un PDF dans le panneau de gauche pour commencer.")

    st.markdown(
        """
        ### Fonctionnalités

        - Lecture automatique, un mot à la fois
        - Affichage en plein écran
        - Vitesse de lecture personnalisable
        - Pause et reprise
        - Navigation mot par mot
        - Barre de progression
        - Estimation du temps restant
        - Exportation du texte extrait
        """
    )

    st.stop()


# --------------------------------------------------
# EXPORT EXTRACTED TEXT
# --------------------------------------------------

st.download_button(
    label="⬇️ Télécharger le texte extrait (.txt)",
    data=st.session_state.pdf_text.encode("utf-8"),
    file_name=f"{Path(st.session_state.filename).stem}_extrait.txt",
    mime="text/plain",
)


# --------------------------------------------------
# RSVP READER
# --------------------------------------------------

# Encode the PDF text as a JavaScript string safely.
text_json = json.dumps(st.session_state.pdf_text, ensure_ascii=False)
text_json = text_json.replace("</", "<\\/")

reader_html = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">

<style>
    * {
        box-sizing: border-box;
    }

    body {
        margin: 0;
        background: #0b0d12;
        color: #f5f7fc;
        font-family: Arial, Helvetica, sans-serif;
    }

    .app {
        width: 100%;
        padding: 8px 0;
    }

    .reader {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 340px;
        padding: 30px;
        background: #10141e;
        border: 1px solid #252c3a;
        border-radius: 18px;
        overflow: hidden;
    }

    .word {
        text-align: center;
        font-size: __FONT_SIZE__px;
        font-weight: 700;
        line-height: 1.2;
        overflow-wrap: anywhere;
        max-width: 100%;
    }

    .counter {
        position: absolute;
        top: 14px;
        right: 16px;
        color: #8994aa;
        font-size: 13px;
    }

    .progress-background {
        width: 100%;
        height: 5px;
        margin-top: 12px;
        background: #242b39;
        border-radius: 10px;
        overflow: hidden;
    }

    .progress {
        width: 0%;
        height: 100%;
        background: #8ba7ff;
    }

    .controls {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 8px;
        margin-top: 15px;
    }

    button {
        padding: 11px 15px;
        border: 1px solid #323b4e;
        border-radius: 10px;
        background: #1a2030;
        color: #f5f7fc;
        font-size: 14px;
        cursor: pointer;
    }

    button.primary {
        background: #dce5ff;
        color: #111827;
        font-weight: 700;
    }

    button:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }

    .seek {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 14px;
        color: #aab2c5;
        font-size: 13px;
    }

    .seek input {
        width: 100%;
        accent-color: #8ba7ff;
    }

    .info {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 10px;
        margin-top: 12px;
        color: #8994aa;
        font-size: 12px;
    }

    .app:fullscreen {
        padding: 20px;
        background: #0b0d12;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .app:fullscreen .reader {
        min-height: 65vh;
        border-radius: 18px;
    }

    @media (max-width: 600px) {
        .reader {
            min-height: 260px;
            padding: 20px;
        }

        .word {
            font-size: min(__FONT_SIZE__px, 16vw);
        }
    }
</style>
</head>

<body>

<div class="app" id="app">

    <div class="reader">
        <div class="counter" id="counter">Mot 0 / 0</div>
        <div class="word" id="word">Prêt à lire?</div>
    </div>

    <div class="progress-background">
        <div class="progress" id="progress"></div>
    </div>

    <div class="controls">
        <button id="previous">⏮ Précédent</button>
        <button class="primary" id="play">▶ Lecture</button>
        <button id="next">Suivant ⏭</button>
        <button id="fullscreen">⛶ Plein écran</button>
        <button id="restart">↺ Recommencer</button>
    </div>

    <div class="seek">
        <span>Position</span>
        <input id="seek" type="range" min="0" max="0" value="0">
    </div>

    <div class="info">
        <span id="status">En pause</span>
        <span id="remaining">Temps restant : —</span>
    </div>

</div>

<script>
const fullText = __TEXT_JSON__;
const words = fullText.match(/\S+/g) || [];
const wpm = __WPM__;

let index = 0;
let playing = false;
let timer = null;

const wordElement = document.getElementById("word");
const counterElement = document.getElementById("counter");
const progressElement = document.getElementById("progress");
const seekElement = document.getElementById("seek");
const playButton = document.getElementById("play");
const statusElement = document.getElementById("status");
const remainingElement = document.getElementById("remaining");

seekElement.max = Math.max(0, words.length - 1);

function formatTime(seconds) {
    seconds = Math.max(0, Math.ceil(seconds));

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;

    if (hours > 0) {
        return `${hours} h ${minutes} min`;
    }

    if (minutes > 0) {
        return `${minutes} min ${remainingSeconds} s`;
    }

    return `${remainingSeconds} s`;
}

function render() {
    if (words.length === 0) {
        wordElement.textContent = "Aucun texte trouvé";
        counterElement.textContent = "Mot 0 / 0";
        return;
    }

    wordElement.textContent = words[index];
    counterElement.textContent = `Mot ${index + 1} / ${words.length}`;

    const percentage = ((index + 1) / words.length) * 100;
    progressElement.style.width = `${percentage}%`;
    seekElement.value = index;

    const secondsRemaining = (
        (words.length - index - 1) * 60 / wpm
    );

    remainingElement.textContent =
        "Temps restant : " + formatTime(secondsRemaining);
}

function stop() {
    playing = false;

    if (timer !== null) {
        clearTimeout(timer);
    }

    timer = null;
    playButton.textContent = "▶ Lecture";
    statusElement.textContent = "En pause";
}

function tick() {
    if (!playing) return;

    if (index >= words.length - 1) {
        stop();
        statusElement.textContent = "Lecture terminée";
        return;
    }

    index++;
    render();

    timer = setTimeout(tick, 60000 / wpm);
}

function start() {
    if (words.length === 0) return;

    if (index >= words.length - 1) {
        index = 0;
    }

    if (timer !== null) {
        clearTimeout(timer);
    }

    playing = true;
    playButton.textContent = "⏸ Pause";
    statusElement.textContent = "Lecture en cours";

    render();
    timer = setTimeout(tick, 60000 / wpm);
}

playButton.addEventListener("click", () => {
    if (playing) {
        stop();
    } else {
        start();
    }
});

document.getElementById("previous").addEventListener("click", () => {
    stop();
    index = Math.max(0, index - 1);
    render();
});

document.getElementById("next").addEventListener("click", () => {
    stop();
    index = Math.min(words.length - 1, index + 1);
    render();
});

document.getElementById("restart").addEventListener("click", () => {
    stop();
    index = 0;
    render();
});

seekElement.addEventListener("input", () => {
    stop();
    index = Number(seekElement.value);
    render();
});

document.getElementById("fullscreen").addEventListener("click", async () => {
    const app = document.getElementById("app");

    try {
        if (!document.fullscreenElement) {
            await app.requestFullscreen();
        } else {
            await document.exitFullscreen();
        }
    } catch (error) {
        statusElement.textContent =
            "Le plein écran n'est pas disponible ici.";
    }
});

document.addEventListener("fullscreenchange", () => {
    document.getElementById("fullscreen").textContent =
        document.fullscreenElement
            ? "⤢ Quitter le plein écran"
            : "⛶ Plein écran";
});

document.addEventListener("keydown", (event) => {
    if (event.code === "Space") {
        const tag = document.activeElement.tagName;

        if (tag !== "INPUT" && tag !== "TEXTAREA") {
            event.preventDefault();
            playing ? stop() : start();
        }
    }

    if (event.code === "ArrowRight") {
        stop();
        index = Math.min(words.length - 1, index + 1);
        render();
    }

    if (event.code === "ArrowLeft") {
        stop();
        index = Math.max(0, index - 1);
        render();
    }
});

render();
</script>

</body>
</html>
"""

reader_html = (
    reader_html
    .replace("__FONT_SIZE__", str(font_size))
    .replace("__TEXT_JSON__", text_json)
    .replace("__WPM__", str(wpm))
)

components.html(
    reader_html,
    height=480,
    scrolling=False,
)

st.caption(
    "Raccourcis clavier : Espace = lecture/pause · "
    "← = mot précédent · → = mot suivant."
)

st.caption(
    "Remarque : les PDF scannés nécessitent un OCR. "
    "La mise en page de certains PDF à colonnes peut aussi "
    "nécessiter un nettoyage du texte."
)