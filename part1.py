# part1.py — Final Tuned Version (Accurate + Small Model)
import os
import json
import queue
import threading
import time
import zipfile
import urllib.request
import pyaudio
import speech_recognition as sr


def download_vosk_model():
    """Download and extract small Vosk model if not found."""
    model_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    model_zip = "vosk-model-small-en-us-0.15.zip"
    model_folder = "vosk-model-small-en-us-0.15"

    if os.path.exists(model_folder):
        return model_folder

    print("\n Downloading Vosk small model (40MB)...")
    def progress(block_num, block_size, total_size):
        percent = min(block_num * block_size * 100 / max(total_size, 1), 100)
        print(f"\r   Progress: {percent:.1f}%", end="", flush=True)

    urllib.request.urlretrieve(model_url, model_zip, progress)
    print("\n\n Extracting...")
    with zipfile.ZipFile(model_zip, "r") as z:
        z.extractall(".")
    os.remove(model_zip)
    print(" Model ready.")
    return model_folder


def find_vosk_model():
    """Find local Vosk model directory."""
    for name in [
        "vosk-model-small-en-us-0.15",
        "model",
        "vosk-model-en-us-0.22",
        "vosk-model-en-us-0.22-lgraph"
    ]:
        if os.path.isdir(name):
            return name
    return None


def start_speech_recognition(callback, stop_flag=None):
    """
    Continuously listens to microphone and sends recognized text
    to the provided callback(text) function.
    """
    from vosk import Model, KaldiRecognizer

    model_path = find_vosk_model() or download_vosk_model()
    model = Model(model_path)

    recognizer = KaldiRecognizer(model, 16000)
    recognizer.SetWords(True)
    recognizer.SetMaxAlternatives(0)

    RATE = 16000
    CHUNK = 1024             
    audio_q = queue.Queue(maxsize=20)  
    stop_event = stop_flag if stop_flag is not None else threading.Event()

    def audio_producer():
        """Record audio and feed the recognition queue."""
        p = pyaudio.PyAudio()

        
        try:
            print("🎧 Calibrating mic for background noise (2s)...")
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=2)
            print(" Mic calibrated! Speak clearly.")
        except Exception as e:
            print(f" Noise calibration skipped: {e}")

        # Start PyAudio stream
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        # Warm up the mic to stabilize audio input
        print("🎙️ Warming up mic for 1 second...")
        time.sleep(1)

        stream.start_stream()
        print("✅ Mic active and ready!\n")

        while not stop_event.is_set():
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                try:
                    audio_q.put_nowait(data)
                except queue.Full:
                    audio_q.get_nowait()  # drop oldest
                    audio_q.put_nowait(data)
            except Exception as e:
                if not stop_event.is_set():
                    print(f"Audio read error: {e}")
                break

        stream.stop_stream()
        stream.close()
        p.terminate()

    def recognizer_consumer():
        """Process audio chunks using Vosk recognizer."""
        last_partial = ""
        confidence_threshold = 0.35  # lower to accept more short phrases

        while not stop_event.is_set() or not audio_q.empty():
            try:
                data = audio_q.get(timeout=0.5)
            except queue.Empty:
                continue

            if stop_event.is_set():
                break

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()

                if text:
                    result_dict = result.get("result", [])
                    if result_dict:
                        avg_conf = sum(w.get("conf", 1.0) for w in result_dict) / len(result_dict)
                        if avg_conf < confidence_threshold:
                            print(f"\r⚠️ Low confidence ({avg_conf:.2f}), skipped", end="", flush=True)
                            continue

                    # Send text to callback (GUI handler)
                    callback(text)
                    last_partial = ""
                    print()  # newline
                    time.sleep(0.1)  # balance producer-consumer timing
            else:
                partial = json.loads(recognizer.PartialResult()).get("partial", "")
                if partial and partial != last_partial:
                    print(f"\r🎤 {partial}...", end="", flush=True)
                    last_partial = partial

    # Launch producer and consumer threads
    producer_thread = threading.Thread(target=audio_producer, daemon=True)
    consumer_thread = threading.Thread(target=recognizer_consumer, daemon=True)

    producer_thread.start()
    consumer_thread.start()

    print("\n🎙️ Listening... Speak now!\n" + "-" * 60)

    if stop_flag is None:
        try:
            while not stop_event.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            stop_event.set()
            print("\n👋 Stopping...")
            producer_thread.join(timeout=2)
            consumer_thread.join(timeout=2)

    return stop_event
