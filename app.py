import os
import uuid
import language_tool_python
from flask import Flask, render_template, request, redirect, url_for
from flask import jsonify
from googletrans import Translator
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment
from spellchecker import SpellChecker
import language_tool_python
from textblob import TextBlob
import eng_to_ipa as ipa

# Set Tesseract OCR Path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)

# Folders to store uploaded files
UPLOAD_FOLDER = "static/uploads"
AUDIO_FOLDER = "static/audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)



app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["AUDIO_FOLDER"] = AUDIO_FOLDER

translator = Translator()
spell = SpellChecker()
grammar_tool = language_tool_python.LanguageToolPublicAPI("en-US")
history = []

#  Home Page
@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html", history=history)

#  Text Translation
@app.route("/translate_text", methods=["POST"])
def translate_text():
    text_to_translate = request.form.get("text", "").strip()
    target_language = request.form.get("language", "en")

    if not text_to_translate:
        return render_template("index.html", error="Please enter text to translate.")

    detected_lang = translator.detect(text_to_translate)
    if not detected_lang or not hasattr(detected_lang, 'lang'):
        return render_template("index.html", error="Could not detect language. Please enter valid text.")

    try:
        translation_result = translator.translate(text_to_translate, src=detected_lang.lang, dest=target_language)
        if translation_result is None:
            return render_template("index.html", error="Translation failed. Try again later.")
        
        translated_text = translation_result.text
        history.append((text_to_translate, detected_lang.lang, translated_text, target_language))
        return render_template("index.html", translated_text=translated_text, history=history)

    except Exception as e:
        return render_template("index.html", error=f"Translation error: {str(e)}")
    
@app.route('/speak', methods=['POST'])
def speak():
    try:
        data = request.get_json()
        text = data.get('text', '')
        language = data.get('language', 'en')

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Generate unique filename
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(AUDIO_FOLDER, filename)

        # Generate speech using gTTS
        tts = gTTS(text=text, lang=language)
        tts.save(filepath)

        # Return audio file path to frontend
        audio_url = f"/{filepath}"
        return jsonify({'audio_url': audio_url})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    




#  Detect Language Only
@app.route("/detect_language", methods=["POST"])
def detect_language():
    text = request.form.get("detect_text", "").strip()

    if not text:
        return render_template("index.html", error="Please enter text to detect language.", history=history)

    try:
        detected_lang = translator.detect(text).lang
        return render_template("index.html", detected_language_only=detected_lang, input_text=text, history=history)
    except Exception as e:
        return render_template("index.html", error=f"Language detection failed: {str(e)}", history=history)


#  Image Translation (OCR)
@app.route("/translate_image", methods=["POST"])
def translate_image():
    if "image" not in request.files:
        return redirect(url_for("index"))

    image = request.files["image"]
    input_language = request.form.get("image_language", "eng")  # Default OCR language is English
    target_language = request.form.get("target_language", "en")  # Default translation to English

    if image.filename == "":
        return redirect(url_for("index"))

    # Save the uploaded image
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], image.filename)
    image.save(image_path)

    # Extract text from image using the selected OCR language
    extracted_text = extract_text_from_image(image_path, lang=input_language)

    if not extracted_text.strip():
        return render_template("index.html", error="No text detected in the image!", history=history)

    # Translate the extracted text
    detected_lang = translator.detect(extracted_text).lang
    translated_text = translator.translate(extracted_text, src=detected_lang, dest=target_language).text

    # Store in history
    history.append((extracted_text, detected_lang, translated_text, target_language))

    return render_template("index.html", extracted_text=extracted_text, translated_text=translated_text, history=history)

@app.route("/pronunciation_guide", methods=["POST"])
def pronunciation_guide():
    from eng_to_ipa import convert as ipa_convert 
    
    text = request.form.get("pronunciation_text", "").strip()
    if not text:
        return render_template("index.html", error="Please enter English text.")

    # Phonetic conversion
    phonetic = ipa_convert(text)

    # Generate pronunciation audio
    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(app.config["AUDIO_FOLDER"], audio_filename)
    try:
        tts = gTTS(text=text, lang="en")
        tts.save(audio_path)
    except Exception as e:
        return render_template("index.html", error=f"Audio error: {str(e)}")
    
    history.append((text, "phonetic", phonetic, "en"))
    return render_template("index.html", original_text=text, phonetic_text=phonetic, pronunciation_audio=audio_filename, history=history)


#  Grammar Checker


@app.route("/check_grammar", methods=["POST"])
def check_grammar():
    text = request.form.get("grammar_text", "").strip()

    if not text:
        return render_template("index.html", error="Please enter some text for checking.")

    # Step 1: Spelling Correction using PySpellChecker
    spell_corrected = correct_spelling(text)

    # Step 2: Sentence-level correction using TextBlob
    blob_corrected = str(TextBlob(spell_corrected).correct())

    # Step 3: Final Grammar Fix using LanguageTool
    grammar_corrected = grammar_tool.correct(blob_corrected)

    return render_template("index.html",
        original_text=text,
        spelling_corrected_text=spell_corrected,
        blob_corrected_text=blob_corrected,
        corrected_text=grammar_corrected,
        history=history
    )

def correct_spelling(text):
    corrected_words = []
    words = text.split()
    for word in words:
        if word.isalpha():
            corrected = spell.correction(word)
            corrected_words.append(corrected if corrected else word)
        else:
            corrected_words.append(word)
    return " ".join(corrected_words)



#  Text File Translation
@app.route("/translate_file", methods=["POST"])
def translate_file():
    if "file" not in request.files:
        return redirect(url_for("index"))

    file = request.files["file"]
    target_language = request.form.get("file_language", "en")

    if file.filename == "":
        return redirect(url_for("index"))

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Step 1: Spelling Correction
    corrected_spelling = correct_spelling(content)

    # Step 2: Grammar Correction
    corrected_grammar = grammar_tool.correct(corrected_spelling)

    # Step 3: Translation
    detected_lang = translator.detect(corrected_grammar).lang
    translated_text = translator.translate(corrected_grammar, src=detected_lang, dest=target_language).text
    history.append((corrected_grammar, detected_lang, translated_text, target_language))
   

    return render_template(
        "index.html",
        file_original=content,  # Original text passed here
        file_translation=translated_text,
        file_grammar_corrected=corrected_grammar,
        history=history

    )


#multi language translation
@app.route("/batch_translate", methods=["POST"])
def batch_translate():
    text = request.form.get("batch_text", "").strip()
    selected_languages = request.form.getlist("batch_languages")

    if not text or not selected_languages:
        return render_template("index.html", error="Please provide text and select at least one language.", history=history)

    batch_results = []

    for lang in selected_languages:
        try:
            translated = translator.translate(text, dest=lang)
            batch_results.append((lang, translated.text))
        except Exception as e:
            batch_results.append((lang, f"Error: {str(e)}"))
    
    history.append((text,batch_results, lang))
    return render_template("index.html", batch_text=text, batch_results=batch_results, history=history)




#  Audio File Translation (Speech-to-Text → Translation)
@app.route("/translate_audio", methods=["POST"])
def translate_audio():
    if "audio" not in request.files:
        return redirect(url_for("index"))

    audio = request.files["audio"]
    target_language = request.form.get("audio_language", "en")

    if audio.filename == "":
        return redirect(url_for("index"))

    # Save the uploaded audio file
    audio_path = os.path.join(app.config["UPLOAD_FOLDER"], audio.filename)
    audio.save(audio_path)

    # Convert audio to WAV format for SpeechRecognition compatibility
    audio_wav_path = os.path.splitext(audio_path)[0] + ".wav"
    try:
        sound = AudioSegment.from_file(audio_path)
        sound.export(audio_wav_path, format="wav")
    except Exception as e:
        return render_template("index.html", error=f"Error processing audio: {str(e)}")

    # Recognize speech from audio
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            detected_text = recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            return render_template("index.html", error="Could not recognize speech.")
        except sr.RequestError:
            return render_template("index.html", error="Error with speech recognition service.")

    # Detect language and translate
    detected_lang = translator.detect(detected_text).lang
    translated_text = translator.translate(detected_text, src=detected_lang, dest=target_language).text
    history.append((detected_text, detected_lang, translated_text, target_language))

    return render_template("index.html", detected_text=detected_text, translated_text=translated_text, history=history)

#  OCR Text Extraction
def extract_text_from_image(image_path, lang="eng"):
    img = Image.open(image_path)
    img = img.convert("L")  # Convert to grayscale
    img = ImageEnhance.Sharpness(img).enhance(2)  # Enhance sharpness
    img = img.filter(ImageFilter.MedianFilter())  # Reduce noise
    
    # Extract text using the specified language
    text = pytesseract.image_to_string(img, lang=lang).strip()
    return text


#  Generate Speech (Translated Text to Audio)
def generate_speech(text, lang):
    try:
        audio_filename = f"{uuid.uuid4()}.mp3"
        audio_path = os.path.join(app.config["AUDIO_FOLDER"], audio_filename)
        tts = gTTS(text=text, lang=lang)
        tts.save(audio_path)
        return audio_filename
    except Exception:
        return None


#  Clear History
@app.route("/clear_history", methods=["POST"])
def clear_history():
    global history
    history = []
    return redirect(url_for("index"))

#  Run Flask App
if __name__ == "__main__":
    app.run(debug=True)

