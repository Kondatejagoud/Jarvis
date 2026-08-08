import sys
import pyttsx3

def main():
    if len(sys.argv) < 2:
        return
    text = sys.argv[1]
    try:
        # Fresh process space with clean COM apartment state
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
        engine.setProperty('volume', 1.0)
        
        # Use Microsoft David (Male Voice)
        voices = engine.getProperty('voices')
        if len(voices) > 0:
            engine.setProperty('voice', voices[0].id)
            
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        sys.stderr.write(f"TTS Process Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
