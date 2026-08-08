import os
import torchaudio
import torch
from speechbrain.inference.speaker import EncoderClassifier

import config
import security
import audio_recorder

class SpeakerVerifier:
    """
    SpeakerVerifier represents the core security gate for the Jarvis assistant.
    It loads the encrypted speaker profile and compares incoming audio against it
    using cosine similarity on embeddings extracted via SpeechBrain's ECAPA-TDNN model.
    """
    def __init__(self, embedding_path: str = config.EMBEDDING_PATH, threshold: float = config.VERIFICATION_THRESHOLD):
        self.embedding_path = embedding_path
        self.threshold = threshold
        
        print("Initializing Speaker Verifier...")
        
        # Load SpeechBrain ECAPA-TDNN model on CPU
        try:
            self.classifier = EncoderClassifier.from_hparams(
                source=config.MODEL_SOURCE,
                savedir=config.MODEL_DIR,
                run_opts={"device": "cpu"},
                local_strategy=config.LOCAL_STRATEGY
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load speaker recognition model: {e}")
            
        # Load and decrypt the enrolled target speaker embedding
        if not os.path.exists(self.embedding_path):
            raise FileNotFoundError(
                f"Speaker profile embedding not found at: {self.embedding_path}.\n"
                f"Please run 'enroll.py' first to enroll your voice."
            )
            
        try:
            self.target_embedding = security.decrypt_embedding(self.embedding_path)
            # Ensure the target embedding is normalized
            self.target_embedding = torch.nn.functional.normalize(self.target_embedding, p=2, dim=0)
            print("Enrolled speaker profile loaded and decrypted successfully.")
        except Exception as e:
            raise RuntimeError(f"Failed to decrypt and load speaker embedding: {e}")

    def trim_silence(self, signal: torch.Tensor) -> torch.Tensor:
        """
        Trims silent/quiet frames from the audio signal using an energy-based RMS threshold.
        """
        import numpy as np
        
        # Convert PyTorch tensor to 1D NumPy array for analysis
        sig_np = signal.squeeze(0).numpy() if signal.ndim > 1 else signal.numpy()
        
        sample_rate = config.SAMPLE_RATE
        frame_len = int(sample_rate * config.VAD_FRAME_DURATION)
        padding_len = int(sample_rate * config.VAD_PADDING_DURATION)
        
        # Calculate RMS energy of each frame
        num_frames = len(sig_np) // frame_len
        active_mask = np.zeros(len(sig_np), dtype=bool)
        
        for i in range(num_frames):
            start = i * frame_len
            end = start + frame_len
            frame = sig_np[start:end]
            
            # Calculate RMS energy
            rms = np.sqrt(np.mean(frame ** 2))
            
            if rms >= config.VAD_THRESHOLD:
                # Mark frame as active
                active_mask[start:end] = True
                
                # Apply padding window around this active frame
                pad_start = max(0, start - padding_len)
                pad_end = min(len(sig_np), end + padding_len)
                active_mask[pad_start:pad_end] = True
                
        # Extract active speech samples
        trimmed_sig = sig_np[active_mask]
        
        # Return None if the trimmed active speech is too short (under 0.5 seconds)
        if len(trimmed_sig) < int(0.5 * sample_rate):
            return None
            
        return torch.from_numpy(trimmed_sig).unsqueeze(0)

    def verify_audio(self, audio_path: str) -> tuple[bool, float]:
        """
        Extract speaker embedding from the WAV audio file and compare it
        with the enrolled speaker embedding using Cosine Similarity.
        
        Returns:
            pass_gate (bool): True if the similarity is >= the configured threshold.
            similarity (float): The actual similarity score between 0.0 and 1.0 (or -1.0 to 1.0).
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file for verification not found: {audio_path}")
            
        try:
            # Load audio file
            signal, fs = audio_recorder.load_audio(audio_path)
            
            # Resample if not 16000Hz
            if fs != config.SAMPLE_RATE:
                # SpeechBrain models are trained on 16kHz audio.
                # We resample if necessary using torchaudio.transforms.Resample
                resampler = torchaudio.transforms.Resample(orig_freq=fs, new_freq=config.SAMPLE_RATE)
                signal = resampler(signal)
            
            # Convert to mono by averaging channels if necessary, then add batch dim [1, time]
            if signal.ndim > 1:
                signal = signal.mean(dim=0)
            signal = signal.unsqueeze(0)
            
            # Apply VAD to trim silence
            try:
                trimmed_signal = self.trim_silence(signal)
                if trimmed_signal is None:
                    # No active speech detected (under 0.5s), deny access immediately
                    print("\033[1;30m[VAD: No active speech detected. Rejecting static/silence.]\033[0m")
                    return False, 0.0
                signal = trimmed_signal
            except Exception as vad_err:
                print(f"Warning: VAD silence trimming failed: {vad_err}. Proceeding with raw audio.")
            
            # Extract embedding for input audio
            with torch.no_grad():
                embeddings = self.classifier.encode_batch(signal)
                input_embedding = embeddings.squeeze(0).squeeze(0)
                
            # L2-normalize input embedding
            input_embedding = torch.nn.functional.normalize(input_embedding, p=2, dim=0)
            
            # Cosine similarity is the dot product of two L2-normalized unit vectors
            similarity = torch.dot(self.target_embedding, input_embedding).item()
            
            # Check against threshold
            pass_gate = similarity >= self.threshold
            
            return pass_gate, similarity
            
        except Exception as e:
            print(f"Error during speaker verification: {e}")
            return False, 0.0
