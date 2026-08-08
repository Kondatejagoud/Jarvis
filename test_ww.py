import sounddevice as sd
import numpy as np
from openwakeword.model import Model
import sys
import time

def test_ww():
    print("Initializing openWakeWord Model...")
    try:
        oww_model = Model(
            wakeword_models=["hey_jarvis"],
            inference_framework="onnx"
        )
        model_key = list(oww_model.models.keys())[0]
        print(f"Wake word model loaded: '{model_key}'")
    except Exception as e:
        print(f"ERROR loading openWakeWord: {e}")
        return
        
    print("\nStarting microphone stream...")
    try:
        stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype='int16'
        )
        stream.start()
    except Exception as e:
        print(f"ERROR opening stream: {e}")
        return
        
    print("\nListening... Say 'Hey Jarvis' multiple times.")
    print("Scores will print in real-time. Press Ctrl+C to stop.")
    print("-" * 50)
    
    try:
        chunk_size = 1280
        while True:
            pcm, overflowed = stream.read(chunk_size)
            pcm_flat = pcm.flatten()
            
            # Run prediction
            prediction = oww_model.predict(pcm_flat)
            score = prediction[model_key]
            
            # Print real-time scores
            bar = '#' * int(score * 40)
            sys.stdout.write(f"\rConfidence Score: [{bar:<40}] {score:.4f}")
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\nTest stopped.")
    finally:
        stream.stop()
        stream.close()

if __name__ == "__main__":
    test_ww()
