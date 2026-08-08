import sounddevice as sd
import pyttsx3
import time
import sys

def test():
    print("1. Opening microphone stream...")
    try:
        stream = sd.InputStream(samplerate=16000, channels=1, dtype='int16')
        stream.start()
        print("Stream active. Buffering audio for 1 second...")
        time.sleep(1.0)
        
        print("2. Closing stream...")
        stream.stop()
        stream.close()
    except Exception as e:
        print(f"Error during stream test: {e}")
        
    print("3. Terminating PortAudio context completely...")
    try:
        sd._terminate()
        print("PortAudio terminated successfully.")
    except Exception as e:
        print(f"Failed to terminate PortAudio: {e}")
        
    print("4. Attempting speech synthesis...")
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
        engine.setProperty('volume', 1.0)
        
        voices = engine.getProperty('voices')
        if len(voices) > 0:
            engine.setProperty('voice', voices[0].id)
            
        print("Speaking: 'Testing audio release'...")
        engine.say("Testing audio release.")
        engine.runAndWait()
        print("Speaking finished successfully!")
        
        # Clean up
        engine.stop()
        del engine
    except Exception as e:
        print(f"Speech synthesis failed: {e}")

if __name__ == "__main__":
    test()
