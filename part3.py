# part3.py - Google TTS with pygame beeps
import re
import numpy as np
from gtts import gTTS
import pygame
import tempfile
import os

# Initialize pygame mixer
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

def generate_beep_sound(duration=0.3, frequency=800, sample_rate=22050):
    """Generate beep sound as WAV file for pygame"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    wave = np.sin(2 * np.pi * frequency * t)
    
    # Apply fade in/out
    fade_len = int(sample_rate * 0.01)
    wave[:fade_len] *= np.linspace(0, 1, fade_len)
    wave[-fade_len:] *= np.linspace(1, 0, fade_len)
    
    # Convert to 16-bit integers
    audio = (wave * 32767).astype(np.int16)
    
    # Save as temporary WAV file
    import wave
    beep_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    with wave.open(beep_file.name, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio.tobytes())
    
    return beep_file.name

# Pre-generate beep file
BEEP_FILE = generate_beep_sound()

def play_beep_fast():
    """Play beep sound using pygame"""
    try:
        beep = pygame.mixer.Sound(BEEP_FILE)
        beep.play()
        pygame.time.wait(300)  # Wait for beep to finish
    except Exception as e:
        print(f"Beep error: {e}")

def speak_censored_text(censored_sentence):
    """
    Speak text with natural human voice using Google TTS
    Replace **** with beep sounds
    """
    parts = re.split(r'(\*+)', censored_sentence)
    
    print("\n Speaking...", end=" ", flush=True)
    
    temp_files = []
    interrupted = False
    
    try:
        for part in parts:
            # Check if pygame was quit (means stop was called)
            if not pygame.mixer.get_init():
                interrupted = True
                break
            
            if part and re.fullmatch(r'\*+', part):
                # Play beep for censored words
                play_beep_fast()
            elif part.strip():
                # Generate natural speech with Google TTS
                tts = gTTS(text=part, lang='en', tld='com.au', slow=False)
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                    temp_file = fp.name
                    temp_files.append(temp_file)
                    tts.save(temp_file)
                
                # Play the audio
                try:
                    pygame.mixer.music.load(temp_file)
                    pygame.mixer.music.play()
                    
                    # Wait for playback with interrupt detection
                    while pygame.mixer.music.get_busy():
                        if not pygame.mixer.get_init():
                            interrupted = True
                            break
                        pygame.time.wait(100)
                    
                    if interrupted:
                        break
                        
                except Exception as e:
                    print(f" Error: {e}")
                    break
        
        if interrupted:
            print(" Interrupted!")
        else:
            print(" Done!")
            
    except Exception as e:
        print(f"\n TTS error: {e}")
        print("   Make sure you have internet connection for Google TTS")
    finally:
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass

def process_and_speak(censored_text):
    """
    Main function to output censored text with natural human voice
    """
    if censored_text and censored_text.strip():
        speak_censored_text(censored_text)
    else:
        print(" No text to speak.")