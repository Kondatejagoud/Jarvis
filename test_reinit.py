import sounddevice as sd
import pyttsx3
import time

def test_cycle():
    # Loop 2 full cycles
    for cycle in range(1, 3):
        print(f"\n--- CYCLE {cycle} ---")
        
        # 1. Initialize and open stream
        print("Initializing PortAudio and opening stream...")
        try:
            sd._initialize()
        except Exception as e:
            print(f"Warning/Error on initialize: {e}")
            
        try:
            stream = sd.InputStream(samplerate=16000, channels=1, dtype='int16')
            stream.start()
            print("Stream opened successfully. Buffering 0.5 seconds...")
            time.sleep(0.5)
            stream.stop()
            stream.close()
            print("Stream closed successfully.")
        except Exception as e:
            print(f"FAILED to open stream: {e}")
            return
            
        # 2. Terminate
        print("Terminating PortAudio...")
        try:
            sd._terminate()
            print("PortAudio terminated.")
        except Exception as e:
            print(f"FAILED to terminate: {e}")
            return
            
        # 3. Speak
        print("Speaking...")
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 180)
            engine.say(f"Cycle {cycle} completed.")
            engine.runAndWait()
            engine.stop()
            del engine
            print("Speaking completed.")
        except Exception as e:
            print(f"FAILED to speak: {e}")
            return

    print("\nAll cycles passed successfully! PortAudio re-initialization works perfectly!")

if __name__ == "__main__":
    test_cycle()
