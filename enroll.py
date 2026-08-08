import os
import shutil
import sys
import torchaudio
import torch
from speechbrain.inference.speaker import EncoderClassifier

import config
import security
import audio_recorder

# Prompts for enrollment recordings
PROMPTS = [
    "Jarvis, verify my voice and authenticate system control.",
    "The voice verification gate is now active and monitoring.",
    "System control authorized, activate online mode.",
    "Please check system logs and show the current status.",
    "This is my verified voice print for secure access control.",
    "Jarvis, execute system diagnostics and run a full check.",
    "Offline fallback mode will be triggered if connectivity is lost.",
    "Only allowlisted tools can be executed by the assistant.",
    "Secure voice credentials are encrypted at rest with AES.",
    "Jarvis, open my primary development workspace now.",
    "No blind shell execution is permitted in this environment.",
    "Destructive actions require a second spoken confirmation.",
    "Confirm the action and apply the current changes.",
    "Jarvis, search the web for the latest software updates.",
    "Every executed command must be logged locally to the audit log."
]

def main():
    print("=" * 60)
    print("           JARVIS VOICE ENROLLMENT UTILITY")
    print("=" * 60)
    print(f"This utility will enroll your voice by recording {config.NUM_SAMPLES} samples.")
    print("A speaker profile embedding will be generated and encrypted.")
    print("The decryption key will be stored in Windows Credential Manager.")
    print("=" * 60)
    
    # 1. Check audio input devices
    if not audio_recorder.check_input_devices():
        print("Aborting enrollment: No microphone found.")
        sys.exit(1)
        
    # 2. Load SpeechBrain ECAPA-TDNN model
    print("\n[1/4] Initializing speaker recognition model...")
    print("Note: If running for the first time, this will download the pre-trained model (~80MB).")
    try:
        classifier = EncoderClassifier.from_hparams(
            source=config.MODEL_SOURCE,
            savedir=config.MODEL_DIR,
            run_opts={"device": "cpu"},
            local_strategy=config.LOCAL_STRATEGY
        )
        print("Model initialized successfully.")
    except Exception as e:
        print(f"ERROR: Failed to load SpeechBrain model: {e}")
        sys.exit(1)
        
    # 3. Create temp directory for recordings
    temp_dir = "temp_enrollment_audio"
    os.makedirs(temp_dir, exist_ok=True)
    
    all_embeddings = []
    
    try:
        # 4. Collect voice samples
        print("\n[2/4] Starting voice recording phase.")
        print(f"We will record {config.NUM_SAMPLES} samples of about {config.DURATION} seconds each.")
        print("Please read the displayed phrase clearly when recording starts.")
        print("-" * 60)
        
        for i in range(config.NUM_SAMPLES):
            sample_num = i + 1
            prompt_text = PROMPTS[i % len(PROMPTS)]
            
            print(f"\nSample {sample_num}/{config.NUM_SAMPLES}")
            print(f"Phrase to read: \033[1;36m\"{prompt_text}\"\033[0m")
            
            input("Press Enter when you are ready to record...")
            
            wav_path = os.path.join(temp_dir, f"sample_{sample_num}.wav")
            audio_recorder.record_audio(wav_path, duration=config.DURATION, sleep_before=True)
            
            # Extract embedding immediately to verify the file works
            print("Processing voice sample...")
            try:
                signal, fs = audio_recorder.load_audio(wav_path)
                # Convert to mono if stereo, and add batch dimension [1, time]
                if signal.ndim > 1:
                    signal = signal.mean(dim=0)
                signal = signal.unsqueeze(0)
                
                # Extract embedding
                with torch.no_grad():
                    embeddings = classifier.encode_batch(signal)
                    # Squeeze batch and time dimensions to get flat embedding [embedding_dim]
                    emb_tensor = embeddings.squeeze(0).squeeze(0)
                    all_embeddings.append(emb_tensor)
                print("Embedding extracted successfully.")
            except Exception as e:
                print(f"ERROR: Failed to process sample {sample_num}: {e}")
                print("Let's try this sample again.")
                # Decrement counter to retry this index
                i -= 1
                continue
                
        # 5. Aggregate and normalize embeddings
        print("\n[3/4] Aggregating voice samples into speaker profile...")
        # Average all embeddings
        mean_embedding = torch.stack(all_embeddings).mean(dim=0)
        # L2-normalize to allow simple cosine similarity via dot product
        normalized_embedding = torch.nn.functional.normalize(mean_embedding, p=2, dim=0)
        
        # 6. Encrypt and store embedding
        print("\n[4/4] Securing speaker profile...")
        try:
            # Generate key, store in keyring, encrypt embedding and save
            security.encrypt_embedding(normalized_embedding, config.EMBEDDING_PATH)
            print(f"SUCCESS: Enrolled speaker embedding saved and encrypted at: {config.EMBEDDING_PATH}")
            print("Decryption key registered in Windows Credential Manager.")
        except Exception as e:
            print(f"ERROR: Failed to encrypt and store embedding: {e}")
            sys.exit(1)
            
    finally:
        # 7. Cleanup temp files (security policy: discard raw audio)
        print("\nCleaning up temporary audio recordings...")
        if os.path.exists(temp_dir):
            try:
                import gc
                import time
                gc.collect()  # Force garbage collection to release file handles
                time.sleep(0.5)  # Allow time for OS file system synchronization
                shutil.rmtree(temp_dir)
                print("Temporary audio files deleted.")
            except Exception as e:
                print(f"Warning: Could not remove temporary directory {temp_dir}: {e}")
                
    print("\nVoice enrollment is complete! You can now run 'test_verification.py' to test the verification gate.")
    print("=" * 60)

if __name__ == "__main__":
    main()
