import os
import sys
import audio_recorder
import config
from verify_speaker import SpeakerVerifier

def main():
    print("=" * 60)
    print("        JARVIS SPEAKER VERIFICATION GATE TESTER")
    print("=" * 60)
    
    # Check if speaker profile exists
    if not os.path.exists(config.EMBEDDING_PATH):
        print(f"ERROR: Enrolled profile not found at: {config.EMBEDDING_PATH}")
        print("Please run 'enroll.py' first to enroll your voice profile.")
        sys.exit(1)
        
    try:
        # Initialize verifier (decrypts embedding, loads model)
        verifier = SpeakerVerifier(threshold=config.VERIFICATION_THRESHOLD)
    except Exception as e:
        print(f"Initialization Error: {e}")
        sys.exit(1)
        
    print("-" * 60)
    print(f"Current Cosine Similarity Threshold: \033[1;33m{config.VERIFICATION_THRESHOLD}\033[0m")
    print("-" * 60)
    
    while True:
        print("\nOptions:")
        print("1. Record a live voice sample and verify")
        print("2. Verify an existing WAV audio file")
        print("3. Exit")
        
        choice = input("Select an option (1-3): ").strip()
        
        if choice == "1":
            temp_test_wav = "temp_test_voice.wav"
            print(f"\nWe will record a {config.DURATION}-second sample.")
            print("Please speak standard phrases like 'Jarvis, verify my voice'.")
            input("Press Enter when ready to record...")
            
            try:
                # Record
                audio_recorder.record_audio(temp_test_wav, duration=config.DURATION, sleep_before=True)
                
                # Verify
                print("\nRunning verification gate...")
                pass_gate, similarity = verifier.verify_audio(temp_test_wav)
                
                print("=" * 60)
                if pass_gate:
                    print(f"RESULT: \033[1;32mPASS (AUTHORIZED)\033[0m")
                else:
                    print(f"RESULT: \033[1;31mFAIL (REJECTED)\033[0m")
                print(f"Cosine Similarity Score: {similarity:.4f}")
                print(f"Threshold Required:      {config.VERIFICATION_THRESHOLD:.4f}")
                print("=" * 60)
                
            except Exception as e:
                print(f"Error during test: {e}")
            finally:
                # Clean up
                if os.path.exists(temp_test_wav):
                    try:
                        os.remove(temp_test_wav)
                    except Exception as e:
                        print(f"Warning: Could not remove {temp_test_wav}: {e}")
                        
        elif choice == "2":
            file_path = input("\nEnter path to WAV file: ").strip()
            # Remove enclosing quotes if user dragged and dropped file
            if file_path.startswith('"') and file_path.endswith('"'):
                file_path = file_path[1:-1]
            if file_path.startswith("'") and file_path.endswith("'"):
                file_path = file_path[1:-1]
                
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                continue
                
            print("\nRunning verification gate...")
            try:
                pass_gate, similarity = verifier.verify_audio(file_path)
                
                print("=" * 60)
                if pass_gate:
                    print(f"RESULT: \033[1;32mPASS (AUTHORIZED)\033[0m")
                else:
                    print(f"RESULT: \033[1;31mFAIL (REJECTED)\033[0m")
                print(f"Cosine Similarity Score: {similarity:.4f}")
                print(f"Threshold Required:      {config.VERIFICATION_THRESHOLD:.4f}")
                print("=" * 60)
            except Exception as e:
                print(f"Error processing file: {e}")
                
        elif choice == "3":
            print("\nExiting. Thank you!")
            break
        else:
            print("Invalid option. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
