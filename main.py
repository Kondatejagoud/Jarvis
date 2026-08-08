import os
import sys

# Force HuggingFace Hub to offline mode immediately to prevent check update delays
os.environ["HF_HUB_OFFLINE"] = "1"

import time
import config
import audio_recorder
from verify_speaker import SpeakerVerifier
from stt import SpeechToText
from wake_word import WakeWordDetector
from tts import TextToSpeech
import httpx
import connectivity
import tool_router
from tools import tool_schemas

# Web UI hooks
assistant_status = "idle"  # idle, listening, thinking, speaking
listener_active = False    # Control flag for background thread

import sounddevice as sd

def create_stream():
    try:
        sd._initialize()
    except:
        pass
    stream = sd.InputStream(
        samplerate=16000,
        channels=1,
        dtype='int16'
    )
    stream.start()
    return stream

def close_stream(stream):
    if stream:
        try:
            stream.stop()
            stream.close()
        except:
            pass
    try:
        sd._terminate()
    except:
        pass

def run_voice_pipeline():
    global assistant_status, listener_active
    print("=" * 60)
    print("               JARVIS MAIN CONTROL PIPELINE")
    print("=" * 60)
    
    # 1. Verify Speaker Profile and Microphone Availability
    if not os.path.exists(config.EMBEDDING_PATH):
        print(f"ERROR: Enrolled speaker profile not found at: {config.EMBEDDING_PATH}")
        print("Please run 'enroll.py' first to register your voice print.")
        return
        
    if not audio_recorder.check_input_devices():
        return
        
    # 2. Load pipelines
    try:
        # Load local openWakeWord detector
        detector = WakeWordDetector()
        
        # Load local speaker verification gate
        verifier = SpeakerVerifier()
        
        # Load local Speech-to-Text transcriber
        stt = SpeechToText()
        
        # Load local Text-to-Speech synthesizer
        tts = TextToSpeech()
        
    except Exception as e:
        print(f"\nPipeline Initialization Failed: {e}")
        return
        
    print("\n" + "=" * 60)
    print("         JARVIS IS READY AND RUNNING")
    print("=" * 60)
    print("Press Ctrl+C to terminate the assistant.")
    
    temp_command_file = "temp_command.wav"
    
    import soundfile as sf
    
    stream = None
    try:
        session_active = False
        
        while listener_active:
            if not session_active:
                assistant_status = "idle"
                print(f"\n\033[1;30m[Jarvis is idle. Say \"Hey Jarvis\" to wake me...]\033[0m")
                
                # Open stream only for wake word detection
                stream = create_stream()
                try:
                    detector.wait_for_wake_word(stream)
                finally:
                    close_stream(stream)
                    stream = None
                
                # Double check if listener was deactivated during blocking wait
                if not listener_active:
                    break
                    
                session_active = True
                print("\n\033[1;32m[Jarvis: Session activated!]\033[0m")
                assistant_status = "speaking"
                tts.speak("Jarvis is active.")
                
                print("\n\033[1;32m[Jarvis: Listening...]\033[0m")
                assistant_status = "listening"
                
                # Open stream only for capturing command audio
                stream = create_stream()
                try:
                    audio_recorder.record_from_stream(stream, temp_command_file)
                except Exception as e:
                    print(f"Error capturing audio: {e}")
                    continue
                finally:
                    close_stream(stream)
                    stream = None
                    
                assistant_status = "thinking"
                print("\033[1;33m[Running Speaker Verification Gate...]\033[0m")
                is_verified, score = verifier.verify_audio(temp_command_file)
                
                print(f"Gate Score: {score:.4f} (Threshold: {config.VERIFICATION_THRESHOLD:.2f})")
                
                if is_verified:
                    print("\033[1;32m[Access Granted: Speaker Verified!]\033[0m")
                    print("[Transcribing audio command...]")
                    
                    # Transcribe
                    command_text = stt.transcribe(temp_command_file)
                    print(f"\033[1;36mTranscribed Command: \"{command_text}\"\033[0m")
                    
                    if not command_text.strip():
                        print("\033[1;30m[STT: Empty transcription. Skipping processing.]\033[0m")
                        # Clean up temp recording (privacy requirement)
                        if os.path.exists(temp_command_file):
                            try:
                                os.remove(temp_command_file)
                            except:
                                pass
                        continue
                    
                    # Check for explicit session termination commands
                    normalized_command = command_text.lower().strip().replace(".", "").replace(",", "")
                    if any(phrase in normalized_command for phrase in config.TERMINATION_COMMANDS):
                        goodbye_text = "Goodbye! Going back to sleep."
                        print(f"\033[1;35mJarvis: {goodbye_text}\033[0m")
                        assistant_status = "speaking"
                        tts.speak(goodbye_text)
                        session_active = False
                        # Wait 0.5 seconds to prevent the word 'goodbye' itself from immediately re-triggering openwakeword
                        time.sleep(0.5)
                        # Clean up temp recording (privacy requirement)
                        if os.path.exists(temp_command_file):
                            try:
                                os.remove(temp_command_file)
                            except:
                                pass
                        continue
                    
                    # Run hybrid agent loop (Online Gemini / Offline Ollama)
                    messages = [
                        {"role": "system", "content": config.SYSTEM_INSTRUCTION},
                        {"role": "user", "content": command_text}
                    ]
                    
                    gemini_key = os.environ.get("GEMINI_API_KEY")
                    is_online = connectivity.is_online() and bool(gemini_key)
                    
                    if is_online:
                        api_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
                        headers = {
                            "Authorization": f"Bearer {gemini_key}",
                            "Content-Type": "application/json"
                        }
                        model_name = config.GEMINI_MODEL
                        print(f"\033[1;30m[Running in ONLINE mode: routing to {model_name}...]\033[0m")
                    else:
                        api_url = f"{config.OLLAMA_HOST}/api/chat"
                        headers = {}
                        model_name = config.OLLAMA_MODEL
                        print(f"\033[1;30m[Running in OFFLINE mode: routing to local {model_name}...]\033[0m")
                    
                    try:
                        print("\033[1;30m[Thinking...]\033[0m")
                        response = httpx.post(
                            api_url,
                            headers=headers,
                            json={
                                "model": model_name,
                                "messages": messages,
                                "tools": tool_schemas,
                                "stream": False
                            },
                            timeout=60.0
                        )
                        response.raise_for_status()
                        resp_json = response.json()
                        
                        if "choices" in resp_json:
                            message = resp_json["choices"][0]["message"]
                        else:
                            message = resp_json["message"]
                        
                        while "tool_calls" in message and message["tool_calls"]:
                            messages.append(message)
                            
                            for tool_call in message["tool_calls"]:
                                tool_name = tool_call["function"]["name"]
                                tool_args = tool_call["function"]["arguments"]
                                
                                # Check if the tool is destructive (e.g. overwriting a file)
                                is_destructive = False
                                if tool_name == "create_file":
                                    if isinstance(tool_args, str):
                                        import json
                                        args = json.loads(tool_args)
                                    else:
                                        args = tool_args
                                    file_path = args.get("file_path", "")
                                    if file_path and os.path.exists(file_path):
                                        is_destructive = True
                                
                                if is_destructive:
                                    warn_text = "This action will overwrite or modify an existing resource. Do you want to proceed?"
                                    print(f"\033[1;31m[Destructive Action Warning: '{tool_name}' wants to overwrite/modify an existing resource!]\033[0m")
                                    print(f"\033[1;35mJarvis: {warn_text} (Say Yes or No)\033[0m")
                                    assistant_status = "speaking"
                                    tts.speak(warn_text)
                                    
                                    assistant_status = "listening"
                                    # Open stream only for confirmation recording
                                    stream = create_stream()
                                    try:
                                        audio_recorder.record_from_stream(stream, temp_command_file, max_duration=4.0, silence_timeout=1.0)
                                    except Exception as rec_err:
                                        print(f"Error capturing confirmation: {rec_err}")
                                        result = "Error: Failed to capture voice confirmation."
                                        is_destructive = False
                                    finally:
                                        close_stream(stream)
                                        stream = None
                                        
                                    if is_destructive:
                                        # Run speaker verification on confirmation
                                        print("\033[1;33m[Running Speaker Verification Gate for confirmation...]\033[0m")
                                        is_verified_confirm, score_confirm = verifier.verify_audio(temp_command_file)
                                        print(f"Confirm Gate Score: {score_confirm:.4f} (Threshold: {config.VERIFICATION_THRESHOLD:.2f})")
                                        
                                        if is_verified_confirm:
                                            # Transcribe response
                                            confirm_text = stt.transcribe(temp_command_file)
                                            print(f"\033[1;36mTranscribed Confirmation: \"{confirm_text}\"\033[0m")
                                            
                                            # Normalize and check for affirmative response
                                            norm_confirm = confirm_text.lower().strip().replace(".", "").replace(",", "")
                                            affirmative = ["yes", "yep", "proceed", "okay", "sure", "do it", "agree"]
                                            
                                            if any(word in norm_confirm for word in affirmative):
                                                print("\033[1;32m[Spoken Confirmation Passed: Proceeding with action.]\033[0m")
                                                result = tool_router.execute_tool(tool_name, tool_args)
                                                
                                                try:
                                                    import audit_log
                                                    audit_log.write_audit_entry(
                                                        command=command_text,
                                                        gate_score=score,
                                                        is_verified=True,
                                                        tool_name=tool_name,
                                                        tool_args=str(tool_args),
                                                        outcome=f"Confirmed and executed. Result: {result}"
                                                    )
                                                except Exception as log_err:
                                                    print(f"Log Error: {log_err}")
                                            else:
                                                print("\033[1;31m[Spoken Confirmation Failed: Action aborted by user.]\033[0m")
                                                result = "Error: Action cancelled by user."
                                                
                                                try:
                                                    import audit_log
                                                    audit_log.write_audit_entry(
                                                        command=command_text,
                                                        gate_score=score,
                                                        is_verified=True,
                                                        tool_name=tool_name,
                                                        tool_args=str(tool_args),
                                                        outcome="Aborted: Cancelled by user during spoken confirmation"
                                                    )
                                                except Exception as log_err:
                                                    print(f"Log Error: {log_err}")
                                        else:
                                            print("\033[1;31m[Access Denied: Speaker verification failed for confirmation. Action aborted!]\033[0m")
                                            result = "Error: Speaker verification failed during confirmation. Action aborted."
                                            
                                            try:
                                                import audit_log
                                                audit_log.write_audit_entry(
                                                    command=command_text,
                                                    gate_score=score,
                                                    is_verified=True,
                                                    tool_name=tool_name,
                                                    tool_args=str(tool_args),
                                                    outcome=f"Aborted: Speaker verification failed on confirmation (Gate Score: {score_confirm:.4f})"
                                                )
                                            except Exception as log_err:
                                                print(f"Log Error: {log_err}")
                                            
                                        # Clean up temp confirmation file
                                        if os.path.exists(temp_command_file):
                                            try:
                                                os.remove(temp_command_file)
                                            except:
                                                pass
                                else:
                                    # Execute non-destructive tool safely
                                    result = tool_router.execute_tool(tool_name, tool_args)
                                    
                                    try:
                                        import audit_log
                                        audit_log.write_audit_entry(
                                            command=command_text,
                                            gate_score=score,
                                            is_verified=True,
                                            tool_name=tool_name,
                                            tool_args=str(tool_args),
                                            outcome=result
                                        )
                                    except Exception as log_err:
                                        print(f"Log Error: {log_err}")
                                
                                 # Append output back to conversation history
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.get("id", "call_default"),
                                    "content": result,
                                    "name": tool_name
                                })
                            
                            print("\033[1;30m[Thinking...]\033[0m")
                            response = httpx.post(
                                api_url,
                                headers=headers,
                                json={
                                    "model": model_name,
                                    "messages": messages,
                                    "tools": tool_schemas,
                                    "stream": False
                                },
                                timeout=60.0
                            )
                            response.raise_for_status()
                            resp_json = response.json()
                            
                            if "choices" in resp_json:
                                message = resp_json["choices"][0]["message"]
                            else:
                                message = resp_json["message"]
                            
                        # Output verbal assistant response
                        if message.get("content"):
                            reply_text = message['content']
                            print(f"\033[1;35mJarvis: {reply_text}\033[0m")
                            assistant_status = "speaking"
                            tts.speak(reply_text)
                            
                            try:
                                import audit_log
                                audit_log.write_audit_entry(
                                    command=command_text,
                                    gate_score=score,
                                    is_verified=True,
                                    outcome=reply_text
                                )
                            except Exception as log_err:
                                print(f"Log Error: {log_err}")
                            
                    except Exception as e:
                        print(f"Error communicating with LLM engine ({model_name}): {e}")
                    
                else:
                    print("\033[1;31m[Access Denied: Speaker Unverified!]\033[0m")
                    print("No transcription or action performed. Command discarded.")
                    try:
                        import shutil
                        if os.path.exists(temp_command_file):
                            shutil.copy(temp_command_file, "failed_command.wav")
                            print("\033[1;33m[Debug: Saved failed recording to 'failed_command.wav' for diagnostic playback]\033[0m")
                    except Exception as ex:
                        print(f"Debug copy failed: {ex}")
                        
                    try:
                        import audit_log
                        audit_log.write_audit_entry(
                            command=None,
                            gate_score=score,
                            is_verified=False,
                            outcome="Access Denied: Speaker verification failed"
                        )
                    except Exception as log_err:
                        print(f"Log Error: {log_err}")
                        
                    session_active = False
                    
                # Clean up temp recording (privacy requirement)
                if os.path.exists(temp_command_file):
                    try:
                        os.remove(temp_command_file)
                    except Exception as e:
                        print(f"Warning: Could not remove {temp_command_file}: {e}")
                        
    except KeyboardInterrupt:
        print("\n\nTerminating Jarvis Assistant. Cleaning up...")
    finally:
        close_stream(stream)
        if detector:
            detector.close()
        print("Jarvis shut down successfully.")
        print("=" * 60)

def main():
    global listener_active
    listener_active = True
    try:
        run_voice_pipeline()
    except KeyboardInterrupt:
        print("\n\nTerminating Jarvis Assistant. Cleaning up...")
    finally:
        listener_active = False

if __name__ == "__main__":
    main()
