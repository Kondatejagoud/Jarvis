from tts import TextToSpeech

def test():
    print("Testing Offline Text-to-Speech voice engine...")
    tts = TextToSpeech()
    test_phrase = "Hello! Your Text-to-Speech engine is fully working. Step 8 is complete."
    print(f"Speaking: '{test_phrase}'")
    tts.speak(test_phrase)
    print("TTS test completed successfully!")

if __name__ == "__main__":
    test()
