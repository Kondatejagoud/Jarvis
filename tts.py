import os
import re
import sys
import subprocess

class TextToSpeech:
    """
    TextToSpeech handles local, offline text-to-speech synthesis
    by spawning a clean subprocess running speak_helper.py.
    This bypasses COM apartment state deadlocks caused by PyTorch/ONNX.
    """
    def __init__(self):
        print("Offline Subprocess Speech Synthesizer initialized successfully.")

    def speak(self, text: str) -> None:
        """
        Cleans technical structures from the text and speaks it out loud.
        """
        if not text:
            return
            
        # Clean technical artifacts so they aren't spoken literally
        cleaned = text.strip()
        cleaned = re.sub(r'[\{\}\[\]"\\`*]', ' ', cleaned)
        cleaned = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        if not cleaned:
            return
            
        try:
            # Print speaking progress
            sys.stdout.write(f"\r[Speaking: \"{cleaned[:60]}...\"]")
            sys.stdout.flush()
            
            # Run helper script in a clean process space
            helper_path = os.path.join(os.path.dirname(__file__), "speak_helper.py")
            subprocess.run(
                [sys.executable, helper_path, cleaned],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            # Clear console progress
            sys.stdout.write(f"\r{' ' * 80}\r")
            sys.stdout.flush()
        except Exception as e:
            print(f"\nWarning: TTS speaking error: {e}")
