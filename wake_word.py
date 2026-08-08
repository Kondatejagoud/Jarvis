import sys
import sounddevice as sd
import numpy as np
from openwakeword.model import Model
import config

class WakeWordDetector:
    """
    WakeWordDetector listens to the default input microphone stream in real-time,
    processing small audio blocks via openWakeWord to detect the wake word offline.
    """
    def __init__(self):
        try:
            # Initialize openWakeWord Model with ONNX framework
            self.oww_model = Model(
                wakeword_models=[config.WAKE_WORD_MODEL],
                inference_framework="onnx"
            )
            # Find the exact model key from the loaded models list (e.g. 'hey_jarvis_v0.1')
            self.model_key = list(self.oww_model.models.keys())[0]
            print(f"Wake Word Detector initialized (Keyword model: '{self.model_key}').")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize openWakeWord: {e}")

    def wait_for_wake_word(self, stream) -> None:
        """
        Listen to the passed input stream and block execution until
        the wake word is successfully detected.
        """
        chunk_size = 1280
        while True:
            # Read a chunk from the microphone stream
            pcm, overflowed = stream.read(chunk_size)
            
            # Convert shape [1280, 1] numpy array to a flat 1D array of int16
            pcm_flat = pcm.flatten()
            
            # Process audio chunk
            prediction = self.oww_model.predict(pcm_flat)
            
            # Get prediction score
            score = prediction[self.model_key]
            if score >= config.WAKE_WORD_THRESHOLD:
                print(f"\nWake word detected! (Score: {score:.4f})")
                self.oww_model.reset()
                return

    def close(self) -> None:
        """No native C resources to release, but kept for compatibility."""
        pass
