import sounddevice as sd
import numpy as np
import time
import sys

def test_mic():
    print("Testing active microphone stream...")
    print("Please speak or make some noise to see the volume change.")
    print("Press Ctrl+C to stop.")
    print("-" * 50)
    
    try:
        stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype='int16'
        )
        stream.start()
    except Exception as e:
        print(f"ERROR: Could not open microphone stream: {e}")
        return
        
    try:
        while True:
            data, overflowed = stream.read(1280)
            # Calculate RMS energy of int16 signal
            float_data = data.astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean((float_data - np.mean(float_data)) ** 2))
            
            # Print energy bar
            bar_len = int(rms * 200)
            bar = '#' * min(bar_len, 40)
            sys.stdout.write(f"\rVolume Level: [{bar:<40}] RMS: {rms:.5f}")
            sys.stdout.flush()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nTest stopped.")
    finally:
        stream.stop()
        stream.close()

if __name__ == "__main__":
    test_mic()
