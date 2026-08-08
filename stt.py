import os
import sys
import base64
import httpx
import connectivity
from faster_whisper import WhisperModel
import config

class SpeechToText:
    """
    SpeechToText wraps the local faster-whisper library and Google Gemini API
    to perform high-speed cloud-assisted or local speech transcription.
    """
    def __init__(self, model_size: str = config.WHISPER_MODEL_SIZE):
        print(f"Initializing Speech-to-Text engine (Whisper model: '{model_size}')...")
        
        # Force HuggingFace Hub to offline mode to load cached files instantly without update checks
        os.environ["HF_HUB_OFFLINE"] = "1"
        
        # Resolve model name to absolute cached snapshot path to bypass HF registry latency
        if model_size == "base":
            local_path = os.path.expanduser("~/.cache/huggingface/hub/models--Systran--faster-whisper-base/snapshots/ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66")
            if os.path.exists(local_path):
                model_size = local_path
        elif model_size == "small":
            local_path = os.path.expanduser("~/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120")
            if os.path.exists(local_path):
                model_size = local_path
        
        try:
            # Initialize Whisper Model on CPU with Int8 quantization
            self.model = WhisperModel(
                model_size,
                device="cpu",
                compute_type=config.WHISPER_COMPUTE_TYPE
            )
            print("Speech-to-Text engine loaded successfully.")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize faster-whisper model: {e}")

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe the audio file at audio_path and return the resulting text.
        Routes to cloud Gemini for high-speed bilingual transcription if online,
        falling back to local Whisper if offline.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file for transcription not found: {audio_path}")
            
        gemini_key = os.environ.get("GEMINI_API_KEY")
        is_online = connectivity.is_online() and bool(gemini_key)
        
        if is_online:
            try:
                # Read audio file and encode as Base64
                with open(audio_path, "rb") as audio_file:
                    audio_data = base64.b64encode(audio_file.read()).decode("utf-8")
                
                # Call Gemini API directly for Speech-to-Text
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent?key={gemini_key}"
                headers = {"Content-Type": "application/json"}
                
                # Gemini native generateContent request structure
                payload = {
                    "contents": [{
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/wav",
                                    "data": audio_data
                                }
                            },
                            {
                                "text": "Transcribe the spoken audio exactly. Output only the transcribed text in the language spoken (English or Telugu). Do not translate, add punctuation if needed but do not add any comments or notes."
                            }
                        ]
                    }]
                }
                
                response = httpx.post(url, headers=headers, json=payload, timeout=20.0)
                response.raise_for_status()
                resp_json = response.json()
                
                # Parse text response from Gemini contents output
                transcription = resp_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                return transcription
                
            except Exception as cloud_err:
                print(f"Cloud STT failed: {cloud_err}. Falling back to local Whisper...")
                # Fallback to local Whisper on error
                pass
                
        # Local Offline Fallback (Whisper)
        try:
            print("\033[1;30m[Offline STT: Transcribing locally via Whisper...]\033[0m")
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=5,
                language=config.WHISPER_LANGUAGE,
                initial_prompt=config.WHISPER_INITIAL_PROMPT
            )
            
            transcribed_text = []
            for segment in segments:
                transcribed_text.append(segment.text)
                
            return "".join(transcribed_text).strip()
            
        except Exception as e:
            print(f"Error during local transcription: {e}")
            return ""

if __name__ == "__main__":
    # Test Whisper locally
    print("Testing Speech-to-Text engine...")
    try:
        stt = SpeechToText(model_size="tiny") # Use tiny for a quick test
    except Exception as e:
        print(f"Test failed: {e}")
