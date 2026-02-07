import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
from datetime import datetime
import sys
import io

# Import your existing parts
from part1 import start_speech_recognition
from part2 import filter_toxicity
from part3 import process_and_speak

class ToxicityFilterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🛡️ EchoClean")
        self.root.geometry("1400x900")
        self.root.configure(bg="#0a0a0f")
        
        # Variables
        self.is_listening = False
        self.text_queue = queue.Queue()
        self.speech_queue = queue.Queue()  # Queue for TTS output
        self.listening_thread = None
        self.stop_flag = threading.Event()
        self.stop_tts_flag = threading.Event()  # Flag to interrupt TTS
        
        # Start TTS worker thread
        self.start_tts_worker()
        
        # Setup UI
        self.setup_ui()
        
        # Start queue checker
        self.check_queue()
        
        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Statistics
        self.total_phrases = 0
        self.total_filtered = 0
    
    def setup_ui(self):
        """Create the beautiful UI"""
        
        # ============= HEADER =============
        header_frame = tk.Frame(self.root, bg="#1a1a2e", height=120)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        header_frame.pack_propagate(False)
        
        title = tk.Label(header_frame, text="🛡️EchoClean", 
                        font=("Segoe UI", 36, "bold"), bg="#1a1a2e", fg="#00ff88")
        title.pack(pady=15)
        
        subtitle = tk.Label(header_frame, text="AI-Powered Real-time Toxic Speech Content Filter", 
                           font=("Segoe UI", 13), bg="#1a1a2e", fg="#888888")
        subtitle.pack()
        
        # ============= CONTROL PANEL =============
        control_frame = tk.Frame(self.root, bg="#0a0a0f")
        control_frame.pack(pady=15)
        
        # Modern button styling
        button_style = {
            "font": ("Segoe UI", 12, "bold"),
            "bd": 0,
            "padx": 30,
            "pady": 15,
            "cursor": "hand2",
            "relief": tk.FLAT
        }
        
        self.live_btn = tk.Button(control_frame, text="🎤 Start Live Filter", 
                                  bg="#00ff88", fg="#0a0a0f",
                                  activebackground="#00cc70",
                                  command=self.toggle_live_listening,
                                  **button_style)
        self.live_btn.grid(row=0, column=0, padx=10)
        
        file_btn = tk.Button(control_frame, text="📁 Upload Audio File(WAV only)", 
                            bg="#4a90e2", fg="white",
                            activebackground="#3a7bc8",
                            command=self.upload_audio_file,
                            **button_style)
        file_btn.grid(row=0, column=1, padx=10)
        
        clear_btn = tk.Button(control_frame, text="🗑️ Clear All", 
                             bg="#e74c3c", fg="white",
                             activebackground="#c0392b",
                             command=self.clear_all,
                             **button_style)
        clear_btn.grid(row=0, column=2, padx=10)
        
        # Status indicator
        self.status_frame = tk.Frame(self.root, bg="#0a0a0f")
        self.status_frame.pack(pady=10)
        
        self.status_dot = tk.Label(self.status_frame, text="●", 
                                   font=("Segoe UI", 20), bg="#0a0a0f", fg="#888888")
        self.status_dot.pack(side=tk.LEFT, padx=5)
        
        self.status_label = tk.Label(self.status_frame, text="Ready to filter", 
                                     font=("Segoe UI", 11), bg="#0a0a0f", fg="#888888")
        self.status_label.pack(side=tk.LEFT)
        
        # ============= MAIN CONTENT AREA =============
        content_frame = tk.Frame(self.root, bg="#0a0a0f")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # Left Panel - Original Text
        left_panel = tk.Frame(content_frame, bg="#16213e", relief=tk.FLAT, bd=0)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        left_header = tk.Frame(left_panel, bg="#1a1a2e", height=50)
        left_header.pack(fill=tk.X)
        left_header.pack_propagate(False)
        
        tk.Label(left_header, text="🔴 ORIGINAL TEXT", 
                font=("Segoe UI", 13, "bold"), bg="#1a1a2e", fg="#ff6b6b").pack(pady=12)
        
        self.original_text = tk.Text(left_panel, 
                                     font=("Consolas", 11), 
                                     bg="#1e2a47", 
                                     fg="#ffffff",
                                     insertbackground="#00ff88",
                                     relief=tk.FLAT,
                                     padx=20,
                                     pady=20,
                                     wrap=tk.WORD,
                                     spacing1=5,
                                     spacing3=5)
        self.original_text.pack(fill=tk.BOTH, expand=True)
        
        # Right Panel - Filtered Text
        right_panel = tk.Frame(content_frame, bg="#16213e", relief=tk.FLAT, bd=0)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        right_header = tk.Frame(right_panel, bg="#1a1a2e", height=50)
        right_header.pack(fill=tk.X)
        right_header.pack_propagate(False)
        
        tk.Label(right_header, text="🟢 FILTERED TEXT", 
                font=("Segoe UI", 13, "bold"), bg="#1a1a2e", fg="#00ff88").pack(pady=12)
        
        self.filtered_text = tk.Text(right_panel, 
                                     font=("Consolas", 11), 
                                     bg="#1e2a47", 
                                     fg="#ffffff",
                                     insertbackground="#00ff88",
                                     relief=tk.FLAT,
                                     padx=20,
                                     pady=20,
                                     wrap=tk.WORD,
                                     spacing1=5,
                                     spacing3=5)
        self.filtered_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for highlighting
        self.original_text.tag_config("toxic", foreground="#ff6b6b", font=("Consolas", 11, "bold"))
        self.filtered_text.tag_config("censored", foreground="#ffd93d", font=("Consolas", 11, "bold"))
        self.original_text.tag_config("timestamp", foreground="#888888", font=("Consolas", 9))
        self.filtered_text.tag_config("timestamp", foreground="#888888", font=("Consolas", 9))
        
        # ============= FOOTER - STATS =============
        stats_frame = tk.Frame(self.root, bg="#1a1a2e", height=60)
        stats_frame.pack(fill=tk.X, side=tk.BOTTOM)
        stats_frame.pack_propagate(False)
        
        self.stats_label = tk.Label(stats_frame, 
                                    text="Filtered: 0 words | Total: 0 phrases", 
                                    font=("Segoe UI", 10), 
                                    bg="#1a1a2e", 
                                    fg="#888888")
        self.stats_label.pack(pady=18)
    
    def start_tts_worker(self):
        """Start a worker thread that processes TTS queue sequentially"""
        def tts_worker():
            while True:
                try:
                    filtered_text = self.speech_queue.get(timeout=1)
                    if filtered_text is None:  # Poison pill to stop worker
                        break
                    
                    # Check if we should skip this item
                    if self.stop_tts_flag.is_set():
                        self.speech_queue.task_done()
                        continue
                    
                    try:
                        # This blocks, but it's in its own thread so speech recognition continues
                        process_and_speak(filtered_text)
                    except Exception as e:
                        print(f"TTS error: {e}")
                    
                    self.speech_queue.task_done()
                except queue.Empty:
                    continue
        
        self.tts_thread = threading.Thread(target=tts_worker, daemon=True)
        self.tts_thread.start()
    
    def stop_tts(self):
        """Stop all queued TTS and clear the queue - FORCEFUL"""
        print("🛑 Stopping TTS...")
        
        # Set stop flag
        self.stop_tts_flag.set()
        
        # Clear the queue
        cleared = 0
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                cleared += 1
            except queue.Empty:
                break
        
        if cleared > 0:
            print(f"   Cleared {cleared} queued items")
        
        # Stop pygame mixer
        try:
            import pygame
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            pygame.mixer.quit()
            
            # Small delay then reinitialize
            import time
            time.sleep(0.2)
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        except Exception as e:
            print(f"   Mixer error: {e}")
        
        # Clear flag for next use
        self.stop_tts_flag.clear()
        
        print("✅ TTS stopped!")
    
    def toggle_live_listening(self):
        """Start/Stop live speech recognition"""
        if not self.is_listening:
            self.start_listening()
        else:
            self.stop_listening()
    
    def start_listening(self):
        """Start live speech recognition using modified part1 with stop control"""
        self.is_listening = True
        self.stop_flag.clear()
        self.live_btn.config(text="🛑 Stop Live Filter", bg="#e74c3c", activebackground="#c0392b")
        self.status_dot.config(fg="#00ff88")
        self.status_label.config(text="🎧 Listening... Speak now!", fg="#00ff88")
        
        def listen_thread():
            try:
                # Call start_speech_recognition with our stop_flag
                start_speech_recognition(self.handle_recognized_text, self.stop_flag)
            except Exception as e:
                self.text_queue.put(("error", str(e)))
                self.stop_listening()
        
        self.listening_thread = threading.Thread(target=listen_thread, daemon=True)
        self.listening_thread.start()
    
    def stop_listening(self):
        """Stop live speech recognition by setting the stop flag"""
        if not self.is_listening:
            return
        
        self.is_listening = False
        self.stop_flag.set()  # Signal part1 to stop
        
        # Also stop TTS
        self.stop_tts()
        
        self.live_btn.config(text="🎤 Start Live Filter", bg="#00ff88", activebackground="#00cc70")
        self.status_dot.config(fg="#888888")
        self.status_label.config(text="✅ Stopped - Ready to filter", fg="#888888")
    
    def handle_recognized_text(self, text):
        """
        This is your handle_recognized_text function from app.py
        Called automatically when part1 detects speech.
        """
        # Add to queue for GUI processing
        self.text_queue.put(("speech", text))
    
    def upload_audio_file(self):
        """Upload and process audio file"""
        filename = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio Files", "*.wav *.mp3 *.flac *.ogg"),
                ("All Files", "*.*")
            ]
        )
        
        if not filename:
            return
        
        import os
        self.status_label.config(text=f"🔄 Processing: {os.path.basename(filename)}", fg="#4a90e2")
        
        def process_file():
            try:
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                
                with sr.AudioFile(filename) as source:
                    audio = recognizer.record(source)
                    text = recognizer.recognize_google(audio)
                    self.text_queue.put(("file", text))
            except Exception as e:
                self.text_queue.put(("error", f"File processing error: {str(e)}"))
        
        threading.Thread(target=process_file, daemon=True).start()
    
    def process_text(self, original_text):
        """Process text through your filter_toxicity function"""
        def process_in_thread():
            # Add timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Call your filter_toxicity function from part2
            filtered_text = filter_toxicity(original_text)
            
            # Schedule GUI updates in main thread
            self.root.after(0, lambda: self.update_gui(original_text, filtered_text, timestamp))
            
            # Add to TTS queue instead of blocking here
            # The TTS worker will handle it sequentially without blocking recognition
            self.speech_queue.put(filtered_text)
        
        # Run processing in separate thread to avoid blocking speech recognition
        threading.Thread(target=process_in_thread, daemon=True).start()
    
    def update_gui(self, original_text, filtered_text, timestamp):
        """Update GUI elements (must be called from main thread)"""
        # Update original text panel
        self.original_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        
        # Highlight toxic words in original
        words = original_text.split()
        filtered_words = filtered_text.split()
        
        for orig_word, filt_word in zip(words, filtered_words):
            if filt_word == "****":
                self.original_text.insert(tk.END, orig_word + " ", "toxic")
                self.total_filtered += 1
            else:
                self.original_text.insert(tk.END, orig_word + " ")
        
        self.original_text.insert(tk.END, "\n")
        self.original_text.see(tk.END)
        
        # Update filtered text panel
        self.filtered_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        
        for word in filtered_words:
            if word == "****":
                self.filtered_text.insert(tk.END, word + " ", "censored")
            else:
                self.filtered_text.insert(tk.END, word + " ")
        
        self.filtered_text.insert(tk.END, "\n")
        self.filtered_text.see(tk.END)
        
        # Update stats
        self.total_phrases += 1
        self.stats_label.config(text=f"Filtered: {self.total_filtered} words | Total: {self.total_phrases} phrases")
    
    def check_queue(self):
        """Check for new text from speech recognition - Non-blocking"""
        try:
            # Process all available items quickly
            processed = 0
            while processed < 10:  # Limit to prevent blocking
                msg_type, data = self.text_queue.get_nowait()
                
                if msg_type == "speech":
                    self.process_text(data)
                elif msg_type == "file":
                    self.process_text(data)
                    self.status_label.config(text="✅ File processed successfully", fg="#00ff88")
                elif msg_type == "error":
                    messagebox.showerror("Error", data)
                    self.status_label.config(text="Ready to filter", fg="#888888")
                
                processed += 1
        except queue.Empty:
            pass
        
        # Check again very quickly for continuous operation
        self.root.after(50, self.check_queue)  # Reduced from 100ms to 50ms
    
    def clear_all(self):
        """Clear all text and stop speaking"""
        # Stop TTS first
        self.stop_tts()
        
        # Clear text panels
        self.original_text.delete(1.0, tk.END)
        self.filtered_text.delete(1.0, tk.END)
        
        # Reset statistics
        self.total_phrases = 0
        self.total_filtered = 0
        self.stats_label.config(text="Filtered: 0 words | Total: 0 phrases")
        
        print("🗑️ All cleared")
    
    def on_closing(self):
        """Handle window close"""
        if self.is_listening:
            self.stop_listening()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ToxicityFilterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()