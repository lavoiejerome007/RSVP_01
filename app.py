import json
import re

import pymupdf
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Lecteur RSVP",
    page_icon="📖",
    layout="wide",
)

st.title("Lecteur RSVP")
st.write("Lecture rapide avec point de reconnaissance optimal (ORP) et durée proportionnelle avec buffer.")

# Importer un PDF
pdf_file = st.file_uploader("Importer un PDF", type=["pdf"])

pdf_text = ""
if pdf_file:
    try:
        document = pymupdf.open(
            stream=pdf_file.getvalue(),
            filetype="pdf",
        )
        pdf_text = "\n".join(
            page.get_text("text", sort=True)
            for page in document
        )
        document.close()
    except Exception as error:
        st.error(f"Erreur lors de la lecture du PDF : {error}")

# Texte modifiable
text = st.text_area(
    "Texte à lire",
    value=pdf_text,
    height=150,
    placeholder="Colle ton texte ici...",
)

words = re.findall(r"\S+", text.strip()) if text.strip() else []

with st.sidebar:
    st.header("Réglages")

    wpm = st.slider(
        "Vitesse (mots/minute)",
        min_value=60,
        max_value=1200,
        value=300,
        step=10,
    )

    font_size = st.slider(
        "Taille du texte",
        min_value=30,
        max_value=120,
        value=64,
        step=2,
    )

    use_orp = st.checkbox(
        "Afficher la lettre rouge (ORP)",
        value=True,
    )

    st.download_button(
        "Télécharger le texte",
        data=text,
        file_name="texte_rsvp.txt",
        mime="text/plain",
    )

if not words:
    st.info("Importe un PDF ou colle du texte pour commencer.")
    st.stop()

# Préparer les données JavaScript
words_json = json.dumps(words, ensure_ascii=False)
words_json = words_json.replace("<", r"\u003c")

interval = round(60000 / wpm)

html = r"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">

<style>
* {
    box-sizing: border-box;
}

html, body {
    margin: 0;
    padding: 0;
    background: #101114;
    color: white;
    font-family: Arial, sans-serif;
}

.app {
    padding: 14px;
}

.reader {
    position: relative;
    width: 100%;
    height: 300px;
    background: #181a20;
    border: 1px solid #353741;
    border-radius: 12px;
    overflow: hidden;
}

.guide {
    position: absolute;
    top: 12%;
    bottom: 12%;
    left: 50%;
    width: 2px;
    background: #383b44;
    transform: translateX(-1px);
}

.word-line {
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    display: inline-block;

    /* IMPORTANT : toutes les lettres restent sur une ligne */
    white-space: nowrap;
    word-break: keep-all;
    overflow-wrap: normal;

    font-size: FONT_SIZEpx;
    font-weight: 600;
    line-height: 1.2;
    font-kerning: none;
    font-variant-ligatures: none;
}

.orp {
    color: #ff453a;
}

.info {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin: 12px 0;
    color: #c8c8ce;
    font-size: 13px;
}

input[type="range"] {
    width: 100%;
    accent-color: #ff453a;
}

.buttons {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px;
    margin-top: 16px;
}

button {
    padding: 10px 14px;
    color: white;
    background: #292c34;
    border: 1px solid #41444f;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
}

button:hover {
    background: #41444f;
}

.primary {
    background: #d93025;
}

#reader:fullscreen {
    width: 100vw;
    height: 100vh;
    border: none;
    border-radius: 0;
}

#reader:fullscreen .word-line {
    font-size: min(10vw, 120px);
}

.hint {
    margin-top: 12px;
    text-align: center;
    color: #9295a0;
    font-size: 12px;
}
</style>
</head>

<body>
<div class="app">

    <div class="reader" id="reader">
        <div class="guide"></div>
        <div class="word-line" id="wordLine"></div>
    </div>

    <div class="info">
        <span id="counter"></span>
        <span id="speedDisplay"></span>
        <span id="remaining"></span>
    </div>

    <input id="progress" type="range"
           min="0" max="0" value="0">

    <div class="buttons">
        <button id="restart">↺ Recommencer</button>
        <button id="prev">← Précédent</button>
        <button id="play" class="primary">▶ Lire</button>
        <button id="next">Suivant →</button>
        <button id="fullscreen">⛶ Plein écran</button>
    </div>

    <div class="hint">
        Espace : lecture/pause · ←/→ : mots · ↑/↓ : vitesse (±25 WPM)
    </div>
</div>

<script>
const words = WORDS_JSON;
const showORP = SHOW_ORP;

let currentWpm = WPM_VALUE;
let currentInterval = INTERVAL_MS;

const reader = document.getElementById("reader");
const line = document.getElementById("wordLine");
const counter = document.getElementById("counter");
const speedDisplay = document.getElementById("speedDisplay");
const remaining = document.getElementById("remaining");
const progress = document.getElementById("progress");
const playButton = document.getElementById("play");

let index = 0;
let playing = false;
let timer = null;

progress.max = words.length - 1;

function getORPIndex(word) {
    const length = Array.from(word).length;

    if (length <= 1) return 0;
    if (length <= 5) return 1;
    if (length <= 9) return 2;
    if (length <= 13) return 3;

    return 4;
}

// Calcule l'intervalle avec une durée minimale de 0.75 * temps de base
function getWordInterval(word, baseInterval) {
    const length = Array.from(word).length || 1;
    const proportionalInterval = baseInterval * (length / 5);
    const minInterval = baseInterval * 0.75; // Buffer minimum de 0.75x
    return Math.max(minInterval, proportionalInterval);
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;

    return minutes > 0
        ? `${minutes} min ${secs} s`
        : `${secs} s`;
}

function render() {
    const word = words[index];
    const chars = Array.from(word);
    const anchorIndex = showORP ? getORPIndex(word) : -1;

    line.replaceChildren();

    chars.forEach((char, i) => {
        const span = document.createElement("span");
        span.textContent = char;

        if (i === anchorIndex) {
            span.className = "orp";
        }

        line.appendChild(span);
    });

    requestAnimationFrame(() => {
        if (anchorIndex >= 0) {
            const anchor = line.children[anchorIndex];

            const anchorRect = anchor.getBoundingClientRect();
            const lineRect = line.getBoundingClientRect();
            const readerRect = reader.getBoundingClientRect();

            const anchorCenter =
                anchorRect.left + anchorRect.width / 2;

            const lineLeft = lineRect.left;

            const anchorOffset = anchorCenter - lineLeft;

            const targetOffset = readerRect.width / 2;

            line.style.left =
                `${targetOffset - anchorOffset}px`;
        } else {
            line.style.left = "50%";
            line.style.transform =
                "translate(-50%, -50%)";
        }
    });

    counter.textContent =
        `Mot ${index + 1} / ${words.length}`;

    speedDisplay.textContent = 
        `Vitesse base (5 lett.) : ${currentWpm} WPM`;

    progress.value = index;

    // Calcul exact du temps restant
    let remainingMs = 0;
    for (let i = index + 1; i < words.length; i++) {
        remainingMs += getWordInterval(words[i], currentInterval);
    }
    const secondsLeft = Math.ceil(remainingMs / 1000);

    remaining.textContent =
        `Temps restant : ${formatTime(secondsLeft)}`;
}

function stop() {
    playing = false;
    clearTimeout(timer);
    timer = null;
    playButton.textContent = "▶ Lire";
}

function tick() {
    if (!playing) return;

    if (index >= words.length - 1) {
        stop();
        render();
        return;
    }

    index++;
    render();

    const wordInterval = getWordInterval(words[index], currentInterval);
    timer = setTimeout(tick, wordInterval);
}

function togglePlay() {
    if (playing) {
        stop();
        return;
    }

    if (index >= words.length - 1) {
        index = 0;
    }

    playing = true;
    playButton.textContent = "⏸ Pause";

    render();
    const wordInterval = getWordInterval(words[index], currentInterval);
    timer = setTimeout(tick, wordInterval);
}

document.getElementById("restart").onclick = () => {
    stop();
    index = 0;
    render();
};

document.getElementById("prev").onclick = () => {
    stop();
    index = Math.max(0, index - 1);
    render();
};

document.getElementById("next").onclick = () => {
    stop();
    index = Math.min(words.length - 1, index + 1);
    render();
};

playButton.onclick = togglePlay;

document.getElementById("fullscreen").onclick = async () => {
    try {
        if (!document.fullscreenElement) {
            await reader.requestFullscreen();
        } else {
            await document.exitFullscreen();
        }
    } catch (error) {
        alert("Impossible d'activer le plein écran.");
    }
};

progress.oninput = () => {
    stop();
    index = Number(progress.value);
    render();
};

document.addEventListener("keydown", event => {
    if (event.code === "Space") {
        event.preventDefault();
        togglePlay();
    } else if (event.code === "ArrowLeft") {
        stop();
        index = Math.max(0, index - 1);
        render();
    } else if (event.code === "ArrowRight") {
        stop();
        index = Math.min(words.length - 1, index + 1);
        render();
    } else if (event.code === "ArrowUp") {
        event.preventDefault();
        currentWpm = Math.min(1200, currentWpm + 25);
        currentInterval = Math.round(60000 / currentWpm);
        render();
    } else if (event.code === "ArrowDown") {
        event.preventDefault();
        currentWpm = Math.max(60, currentWpm - 25);
        currentInterval = Math.round(60000 / currentWpm);
        render();
    }
});

window.addEventListener("resize", render);

render();
</script>
</body>
</html>
"""

html = (
    html.replace("WORDS_JSON", words_json)
        .replace("WPM_VALUE", str(wpm))
        .replace("INTERVAL_MS", str(interval))
        .replace("FONT_SIZE", str(font_size))
        .replace("SHOW_ORP", json.dumps(use_orp))
)

components.html(
    html,
    height=500,
    scrolling=False,
)