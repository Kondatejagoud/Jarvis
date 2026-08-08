import os
import sys
import time
import json
import httpx
import sounddevice as sd
import soundfile as sf
import shutil

# Local modules
import connectivity
import tool_router
from tools import tool_schemas
from events import EventBus
from config_manager import ConfigManager
from verify_speaker import SpeakerVerifier
from stt import SpeechToText
from tts import TextToSpeech
from wake_word import WakeWordDetector
import audio_recorder
from datetime import datetime
from memory_manager import MemoryManager
from verify_tools_outcome import verify_action_outcome

class JarvisCore:
    """
    JarvisCore is the central orchestration layer responsible for
    managing runtime states, routing Event Bus events, loading pipelines,
    validating voice gates, executing tool callbacks, and handling LLM routing.
    """
    def __init__(self, config_path: str = "config.json"):
        self.config_manager = ConfigManager(config_path)
        self.event_bus = EventBus()
        self.memory_manager = MemoryManager()
        
        # Inject memory manager to tools
        import tools.memory_tools
        tools.memory_tools.memory_manager = self.memory_manager
        
        self.status = "idle"  # idle, listening, thinking, speaking
        self.listener_active = False
        self.session_active = False
        self.is_session_authenticated = False
        
        self.detector = None
        self.verifier = None
        self.stt = None
        self.tts = None
        
        self.temp_command_file = "temp_command.wav"
        
        # Subscribe status updates to event bus
        self.event_bus.subscribe("STATUS_CHANGE", self._on_status_change)
        
    def _on_status_change(self, event_type: str, data: dict) -> None:
        if data and "status" in data:
            self.status = data["status"]

    def _resolve_and_execute_tool(self, tool_call, command_text, score) -> str:
        """
        Determines permission levels, requests voice confirmation/verification
        if required, executes the tool, runs output verification, and returns the result.
        """
        tool_name = tool_call["function"]["name"]
        tool_args = tool_call["function"]["arguments"]
        
        self.event_bus.publish("TOOL_STARTED", {"tool_name": tool_name, "args": tool_args})
        
        # Determine permission level
        perm_level = self.config_manager.get("TOOL_PERMISSIONS", {}).get(tool_name, "safe")
        
        # Contextual promotion to dangerous for file overwriting
        if tool_name == "create_file":
            if isinstance(tool_args, str):
                try:
                    args = json.loads(tool_args)
                except:
                    args = {}
            else:
                args = tool_args
            file_path = args.get("file_path", "")
            if file_path and os.path.exists(file_path):
                perm_level = "dangerous"  # Overwriting is dangerous!
                
        if perm_level == "safe":
            result = tool_router.execute_tool(tool_name, tool_args)
            self._log_audit(command_text, score, tool_name, tool_args, result)
            
        elif perm_level == "moderate":
            warn_text = f"Tool '{tool_name}' requires authorization. Do you want to proceed?"
            print(f"\033[1;33m[Authorization Check: '{tool_name}' needs confirmation]\033[0m")
            print(f"\033[1;35mJarvis: {warn_text} (Say Yes or No)\033[0m")
            self.set_status("speaking")
            self.speak_and_release(warn_text)
            
            self.set_status("listening")
            stream = self.create_stream()
            try:
                audio_recorder.record_from_stream(stream, self.temp_command_file, max_duration=4.0, silence_timeout=1.0)
                confirm_text = self.stt.transcribe(self.temp_command_file)
                print(f"\033[1;36mTranscribed Confirmation: \"{confirm_text}\"\033[0m")
                
                norm_confirm = confirm_text.lower().strip().replace(".", "").replace(",", "")
                affirmative = ["yes", "yep", "proceed", "okay", "sure", "do it", "agree"]
                if any(word in norm_confirm for word in affirmative):
                    print("\033[1;32m[Voice Confirmation Passed: Executing tool.]\033[0m")
                    result = tool_router.execute_tool(tool_name, tool_args)
                    self._log_audit(command_text, score, tool_name, tool_args, f"User confirmed. Result: {result}")
                else:
                    print("\033[1;31m[Voice Confirmation Failed: Action aborted.]\033[0m")
                    result = f"Error: Action '{tool_name}' cancelled by user."
                    self._log_audit(command_text, score, tool_name, tool_args, "Aborted: User said no/aborted confirmation")
            except Exception as rec_err:
                print(f"Error capturing confirmation: {rec_err}")
                result = "Error: Failed to capture voice confirmation."
            finally:
                self.close_stream(stream)
                stream = None
                self._cleanup_temp_file()
                
        elif perm_level == "dangerous":
            warn_text = f"Warning: Tool '{tool_name}' is dangerous. Confirm your identity to proceed."
            print(f"\033[1;31m[Security Gate: '{tool_name}' is dangerous and requires voice biometric verification!]\033[0m")
            print(f"\033[1;35mJarvis: {warn_text} (Say Yes or No)\033[0m")
            self.set_status("speaking")
            self.speak_and_release(warn_text)
            
            self.set_status("listening")
            stream = self.create_stream()
            try:
                audio_recorder.record_from_stream(stream, self.temp_command_file, max_duration=4.0, silence_timeout=1.0)
                
                # Perform full speaker verification on the confirmation audio
                print("\033[1;33m[Running Speaker Verification Gate on confirmation...]\033[0m")
                v_threshold = self.config_manager.get("VERIFICATION_THRESHOLD", 0.35)
                self.verifier.threshold = v_threshold
                is_verified_confirm, score_confirm = self.verifier.verify_audio(self.temp_command_file)
                print(f"Confirm Gate Score: {score_confirm:.4f} (Threshold: {v_threshold:.2f})")
                
                if is_verified_confirm:
                    confirm_text = self.stt.transcribe(self.temp_command_file)
                    print(f"\033[1;36mTranscribed Confirmation: \"{confirm_text}\"\033[0m")
                    
                    norm_confirm = confirm_text.lower().strip().replace(".", "").replace(",", "")
                    affirmative = ["yes", "yep", "proceed", "okay", "sure", "do it", "agree"]
                    if any(word in norm_confirm for word in affirmative):
                        print("\033[1;32m[Biometric Confirmation Passed: Executing dangerous tool.]\033[0m")
                        result = tool_router.execute_tool(tool_name, tool_args)
                        self._log_audit(command_text, score, tool_name, tool_args, f"Confirmed and executed. Result: {result}")
                    else:
                        print("\033[1;31m[Biometric Confirmation Failed: User cancelled action.]\033[0m")
                        result = f"Error: Dangerous action '{tool_name}' cancelled by user."
                        self._log_audit(command_text, score, tool_name, tool_args, "Aborted: Cancelled by user during spoken confirmation")
                else:
                    print("\033[1;31m[Access Denied: Speaker verification failed for confirmation. Action aborted!]\033[0m")
                    result = f"Error: Speaker verification failed for dangerous action '{tool_name}'."
                    self._log_audit(command_text, score, tool_name, tool_args, f"Aborted: Speaker verification failed on confirmation (Gate Score: {score_confirm:.4f})")
            except Exception as rec_err:
                print(f"Error capturing confirmation: {rec_err}")
                result = "Error: Failed to capture voice confirmation."
            finally:
                self.close_stream(stream)
                stream = None
                self._cleanup_temp_file()
                
        # Run Output Verification
        is_ok, verified_result = verify_action_outcome(tool_name, tool_args, result)
        if not is_ok:
            print(f"\033[1;31m[Output Verification Failed: {verified_result}]\033[0m")
        result = verified_result

        self.event_bus.publish("TOOL_COMPLETED", {"tool_name": tool_name, "outcome": result})
        return result

    def set_status(self, new_status: str) -> None:
        """Publishes status updates across the Event Bus."""
        self.status = new_status
        self.event_bus.publish("STATUS_CHANGE", {"status": new_status})

    def initialize_subsystems(self) -> bool:
        """Loads and pre-warms all local models."""
        print("=" * 60)
        print("               JARVIS MAIN CONTROL PIPELINE")
        print("=" * 60)
        
        # Check enrolled speaker profile print
        embedding_path = self.config_manager.get("EMBEDDING_PATH", "speaker_embedding.enc")
        if not os.path.exists(embedding_path):
            print(f"ERROR: Enrolled speaker profile not found at: {embedding_path}")
            print("Please run 'enroll.py' first to register your voice print.")
            return False
            
        if not audio_recorder.check_input_devices():
            return False
            
        try:
            print("Initializing subsystems...")
            self.detector = WakeWordDetector()
            self.verifier = SpeakerVerifier()
            self.stt = SpeechToText()
            self.tts = TextToSpeech()
            print("All subsystems initialized successfully.")
            return True
        except Exception as e:
            print(f"\nPipeline Initialization Failed: {e}")
            self.event_bus.publish("ERROR_ENCOUNTERED", {"error": str(e), "stage": "initialization"})
            return False

    def create_stream(self) -> sd.InputStream:
        """Initializes and opens PortAudio input stream with automatic recovery for driver locks."""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
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
            except Exception as e:
                print(f"\n\033[1;33m[Audio System Warning] Driver busy or in transition: {e}.\033[0m")
                if attempt < max_retries - 1:
                    print(f"Retrying connection in {retry_delay} second(s)... (Attempt {attempt + 1}/{max_retries})")
                    try:
                        sd._terminate()
                    except:
                        pass
                    time.sleep(retry_delay)
                else:
                    print("\033[1;31m[Audio System Error] Failed to bind to audio hardware after multiple attempts.\033[0m")
                    raise e

    def close_stream(self, stream: sd.InputStream) -> None:
        """Closes the stream. Does NOT terminate PortAudio to maintain instant speed."""
        if stream:
            try:
                stream.stop()
                stream.close()
            except:
                pass

    def speak_and_release(self, text: str) -> None:
        """Terminates PortAudio context, speaks, and re-initializes PortAudio."""
        try:
            sd._terminate()
        except:
            pass
            
        self.tts.speak(text)
        
        try:
            sd._initialize()
        except:
            pass

    def start(self) -> None:
        """Starts the central listener event loop."""
        if not self.initialize_subsystems():
            return
            
        self.listener_active = True
        self.session_active = False
        
        print("\n" + "=" * 60)
        print("         JARVIS IS READY AND RUNNING")
        print("=" * 60)
        print("Press Ctrl+C to terminate the assistant.")
        
        self.event_bus.publish("SESSION_STARTED", {"timestamp": time.time()})
        
        try:
            while self.listener_active:
                if not self.session_active:
                    self.set_status("idle")
                    print(f"\n\033[1;30m[Jarvis is idle. Say \"Hey Jarvis\" to wake me...]\033[0m")
                    
                    # Wait for wake word detection
                    stream = self.create_stream()
                    try:
                        self.detector.wait_for_wake_word(stream)
                    finally:
                        self.close_stream(stream)
                        stream = None
                        
                    if not self.listener_active:
                        break
                        
                    self.session_active = True
                    self.is_session_authenticated = False
                    self.event_bus.publish("WAKE_WORD_DETECTED", {
                        "timestamp": time.time(),
                        "score": self.config_manager.get("WAKE_WORD_THRESHOLD")
                    })
                    
                    self.set_status("speaking")
                    print("\n\033[1;32m[Jarvis: Session activated!]\033[0m")
                    self.speak_and_release("Jarvis is active.")
                    
                # Active conversation loop (executed when session is active)
                self.set_status("listening")
                print("\n\033[1;32m[Jarvis: Listening...]\033[0m")
                
                # Record command audio
                stream = self.create_stream()
                try:
                    silence_timeout = self.config_manager.get("TIMEOUTS", {}).get("silence", 1.5)
                    audio_recorder.record_from_stream(stream, self.temp_command_file, silence_timeout=silence_timeout)
                except Exception as e:
                    print(f"Error capturing audio: {e}")
                    self.event_bus.publish("ERROR_ENCOUNTERED", {"error": str(e), "stage": "listening"})
                    continue
                finally:
                    self.close_stream(stream)
                    stream = None
                    
                self.set_status("thinking")
                if not self.is_session_authenticated:
                    print("\033[1;33m[Running Speaker Verification Gate...]\033[0m")
                    v_threshold = self.config_manager.get("VERIFICATION_THRESHOLD", 0.35)
                    self.verifier.threshold = v_threshold
                    is_verified, score = self.verifier.verify_audio(self.temp_command_file)
                    print(f"Gate Score: {score:.4f} (Threshold: {v_threshold:.2f})")
                    if is_verified:
                        self.is_session_authenticated = True
                        print("\033[1;32m[Access Granted: Speaker Verified!]\033[0m")
                        greeting = self.memory_manager.get_restored_greeting()
                        self.speak_and_release(greeting)
                else:
                    is_verified = True
                    score = 1.0
                
                if is_verified:
                    self.event_bus.publish("SPEAKER_VERIFIED", {"score": score})
                    
                    print("[Transcribing audio command...]")
                    command_text = self.stt.transcribe(self.temp_command_file)
                    print(f"\033[1;36mTranscribed Command: \"{command_text}\"\033[0m")
                    
                    self.event_bus.publish("COMMAND_RECEIVED", {"text": command_text})
                    
                    if not command_text.strip():
                        print("\033[1;30m[STT: Empty transcription. Skipping processing.]\033[0m")
                        self._cleanup_temp_file()
                        continue
                        
                    # Check for session termination commands
                    normalized_command = command_text.lower().strip().replace(".", "").replace(",", "")
                    termination_phrases = self.config_manager.get("TERMINATION_COMMANDS", ["goodbye", "stop jarvis", "go to sleep"])
                    if any(phrase in normalized_command for phrase in termination_phrases):
                        goodbye_text = "Goodbye! Going back to sleep."
                        print(f"\033[1;35mJarvis: {goodbye_text}\033[0m")
                        self.set_status("speaking")
                        self.speak_and_release(goodbye_text)
                        self.session_active = False
                        self.is_session_authenticated = False
                        self.event_bus.publish("SESSION_ENDED", {"timestamp": time.time(), "reason": "user_goodbye"})
                        time.sleep(0.5)
                        self._cleanup_temp_file()
                        continue
                        
                    # Run cognitive LLM pipeline
                    self.execute_llm_chain(command_text, score)
                else:
                    print("\033[1;31m[Access Denied: Speaker Unverified!]\033[0m")
                    print("No transcription or action performed. Command discarded.")
                    self.event_bus.publish("SPEAKER_UNVERIFIED", {"score": score})
                    
                    try:
                        if os.path.exists(self.temp_command_file):
                            shutil.copy(self.temp_command_file, "failed_command.wav")
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
                        
                    self.session_active = False
                    self.is_session_authenticated = False
                    
                self._cleanup_temp_file()
        except KeyboardInterrupt:
            print("\n\nTerminating Jarvis Assistant. Cleaning up...")
        finally:
            self.stop()

    def execute_llm_chain(self, command_text: str, score: float) -> None:
        """Routes user prompt to LLM and handles iterative tool executions."""
        # Retrieve context instructions from memory manager
        memory_context = self.memory_manager.get_memory_context_string()
        
        # Get actual current local system time
        now = datetime.now()
        current_time_str = now.strftime("%A, %B %d, %Y, %I:%M:%S %p")
        time_context = f"Current Local System Time: {current_time_str}"
        
        full_system_instruction = f"{self.config_manager.get('SYSTEM_INSTRUCTION')}\n\n{time_context}\n\n{memory_context}"
        
        messages = [
            {"role": "system", "content": full_system_instruction},
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
            model_name = self.config_manager.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
            print(f"\033[1;30m[Running in ONLINE mode: routing to {model_name}...]\033[0m")
        else:
            api_url = f"{self.config_manager.get('OLLAMA_HOST')}/api/chat"
            headers = {}
            model_name = self.config_manager.get("OLLAMA_MODEL", "llama3.2:1b")
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
                timeout=self.config_manager.get("TIMEOUTS", {}).get("llm", 60.0)
            )
            response.raise_for_status()
            resp_json = response.json()
            
            if "choices" in resp_json:
                message = resp_json["choices"][0]["message"]
            else:
                message = resp_json["message"]
                
            # Keep resolving tools as long as the LLM requests them
            while "tool_calls" in message and message["tool_calls"]:
                messages.append(message)
                
                for tool_call in message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    result = self._resolve_and_execute_tool(tool_call, command_text, score)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", "call_default"),
                        "content": result,
                        "name": tool_name
                    })
                    
                self.set_status("thinking")
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
                    timeout=self.config_manager.get("TIMEOUTS", {}).get("llm", 60.0)
                )
                response.raise_for_status()
                resp_json = response.json()
                if "choices" in resp_json:
                    message = resp_json["choices"][0]["message"]
                else:
                    message = resp_json["message"]
                    
            # If a plan was registered, execute it sequentially
            from tools.planner_tool import active_plan
            if active_plan.status == "active":
                plan_msg = f"Drafted a plan with {len(active_plan.steps)} steps. Starting step 1."
                print(f"\n\033[1;32m[Jarvis: {plan_msg}]\033[0m")
                self.set_status("speaking")
                self.speak_and_release(plan_msg)
                
                while active_plan.status == "active":
                    current_step = active_plan.get_current_step()
                    step_num = active_plan.current_index + 1
                    print(f"\n\033[1;34m[Planner: Running Step {step_num} of {len(active_plan.steps)}]\033[0m")
                    print(f"\033[1;30m{current_step}\033[0m")
                    
                    # Prompt LLM with the active step
                    step_prompt = f"Executing plan step: {current_step}. Do not register a new plan, execute the tool calls for this step."
                    messages.append({
                        "role": "user",
                        "content": step_prompt
                    })
                    
                    self.set_status("thinking")
                    response = httpx.post(
                        api_url,
                        headers=headers,
                        json={
                            "model": model_name,
                            "messages": messages,
                            "tools": tool_schemas,
                            "stream": False
                        },
                        timeout=self.config_manager.get("TIMEOUTS", {}).get("llm", 60.0)
                    )
                    response.raise_for_status()
                    resp_json = response.json()
                    if "choices" in resp_json:
                        step_message = resp_json["choices"][0]["message"]
                    else:
                        step_message = resp_json["message"]
                        
                    step_failed = False
                    # Keep executing tools returned for this plan step
                    while "tool_calls" in step_message and step_message["tool_calls"]:
                        messages.append(step_message)
                        for t_call in step_message["tool_calls"]:
                            t_name = t_call["function"]["name"]
                            t_result = self._resolve_and_execute_tool(t_call, command_text, score)
                            
                            # If a step failed output verification or returned error, fail the plan
                            if "Verification Error" in t_result or "Error:" in t_result or "Access Denied" in t_result:
                                step_failed = True
                                
                            messages.append({
                                "role": "tool",
                                "tool_call_id": t_call.get("id", "call_default"),
                                "content": t_result,
                                "name": t_name
                            })
                            
                        self.set_status("thinking")
                        response = httpx.post(
                            api_url,
                            headers=headers,
                            json={
                                "model": model_name,
                                "messages": messages,
                                "tools": tool_schemas,
                                "stream": False
                            },
                            timeout=self.config_manager.get("TIMEOUTS", {}).get("llm", 60.0)
                        )
                        response.raise_for_status()
                        resp_json = response.json()
                        if "choices" in resp_json:
                            step_message = resp_json["choices"][0]["message"]
                        else:
                            step_message = resp_json["message"]
                            
                    # Append final response text from step
                    messages.append(step_message)
                    message = step_message  # Keep message updated for post-loop content checking
                    
                    if step_failed:
                        active_plan.fail()
                        err_msg = f"Plan execution aborted. Step {step_num} failed verification."
                        print(f"\033[1;31m[Planner: {err_msg}]\033[0m")
                        self.set_status("speaking")
                        self.speak_and_release(err_msg)
                        break
                    else:
                        active_plan.advance()
                        
                if active_plan.status == "completed":
                    done_msg = "All steps of the plan have been executed and verified successfully."
                    print(f"\033[1;32m[Planner: {done_msg}]\033[0m")
                    self.set_status("speaking")
                    self.speak_and_release(done_msg)
                    active_plan.reset()
                    
            if message.get("content"):
                reply_text = message['content']
                print(f"\033[1;35mJarvis: {reply_text}\033[0m")
                self.set_status("speaking")
                self.speak_and_release(reply_text)
                self._log_audit(command_text, score, outcome=reply_text)
                
        except Exception as e:
            print(f"Error communicating with LLM engine ({model_name}): {e}")
            self.event_bus.publish("ERROR_ENCOUNTERED", {"error": str(e), "stage": "llm_routing"})

    def _log_audit(self, command: str, gate_score: float, tool_name: str = None, tool_args: str = None, outcome: str = None) -> None:
        try:
            import audit_log
            audit_log.write_audit_entry(
                command=command,
                gate_score=gate_score,
                is_verified=True,
                tool_name=tool_name,
                tool_args=str(tool_args) if tool_args else None,
                outcome=outcome
            )
        except Exception as log_err:
            print(f"Log Error: {log_err}")

    def _cleanup_temp_file(self) -> None:
        if os.path.exists(self.temp_command_file):
            try:
                os.remove(self.temp_command_file)
            except:
                pass

    def stop(self) -> None:
        """Stops listeners and releases sound card context."""
        self.listener_active = False
        try:
            sd._terminate()
        except:
            pass
        if self.detector:
            try:
                self.detector.close()
            except:
                pass
        print("Jarvis shut down successfully.")
        print("=" * 60)
        self.event_bus.publish("SESSION_ENDED", {"timestamp": time.time(), "reason": "shutdown"})
