document.addEventListener("DOMContentLoaded", () => {
    const darkModeToggle = document.getElementById("toggle-dark-mode");
    const clearHistoryButton = document.getElementById("clear-history");
    const speakButton = document.getElementById("speak-button");
    const translateTextArea = document.querySelector("textarea[name='text']");
    const playAudioButton = document.getElementById("play-audio");

    //  Dark Mode Toggle
    darkModeToggle.addEventListener("click", () => {
        document.body.classList.toggle("dark-mode");
        localStorage.setItem("darkMode", document.body.classList.contains("dark-mode"));
    });

    // Load Dark Mode Preference
    if (localStorage.getItem("darkMode") === "true") {
        document.body.classList.add("dark-mode");
    }

    //  Clear Translation History
    clearHistoryButton.addEventListener("click", () => {
        fetch("/clear_history", { method: "POST" })
            .then(() => location.reload());
    });

    //  Speech-to-Text (Voice Input)
    if (speakButton) {
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = "en-US";

        speakButton.addEventListener("click", () => {
            recognition.start();
        });

        recognition.onresult = (event) => {
            translateTextArea.value = event.results[0][0].transcript;
        };

        recognition.onerror = (event) => {
            alert("Speech Recognition Error: " + event.error);
        };
    }

    //  Text-to-Speech (Play Translated Audio)
    if (playAudioButton) {
        playAudioButton.addEventListener("click", () => {
            const translatedText = document.getElementById("translated-text").innerText;
            const lang = document.querySelector("select[name='language']").value;

            const speech = new SpeechSynthesisUtterance(translatedText);
            speech.lang = lang;
            window.speechSynthesis.speak(speech);
        });
    }
});

document.getElementById('play-audio')?.addEventListener('click', function () {
    const text = document.getElementById('translated-text')?.innerText;
    const language = document.getElementById('outputLanguage')?.value;

    if (!text || !language) {
        alert("Text or language missing!");
        return;
    }

    fetch('/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text, language: language })
    })
    .then(response => response.json())
    .then(data => {
        if (data.audio_url) {
            const audio = new Audio(data.audio_url);
            audio.play();
        } else {
            alert('TTS Error: ' + data.error);
        }
    })
    .catch(error => console.error('TTS fetch error:', error));
});

