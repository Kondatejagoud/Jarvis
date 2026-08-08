import os
import threading
import httpx
from flask import Flask, render_template, jsonify, request
import config
import main
import tool_router
from tools import tool_schemas
import audit_log
from audit_log import read_audit_entries
from tts import TextToSpeech
import connectivity

app = Flask(__name__)

# Lock for controlling thread creation
thread_lock = threading.Lock()
assistant_thread = None

# Initialize local TTS for keyboard command feedback
tts = TextToSpeech()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "active": main.listener_active,
        "status": main.assistant_status,
        "api_key_loaded": bool(os.environ.get("GEMINI_API_KEY"))
    })

@app.route('/api/toggle', methods=['POST'])
def toggle_assistant():
    global assistant_thread
    with thread_lock:
        if main.listener_active:
            # Signal the background loop to stop
            main.listener_active = False
            main.assistant_status = "idle"
            print("[Web UI] Deactivating Jarvis listener...")
        else:
            # Spin up a new background listener thread
            main.listener_active = True
            main.assistant_status = "idle"
            print("[Web UI] Activating Jarvis listener in background thread...")
            assistant_thread = threading.Thread(target=main.run_voice_pipeline)
            assistant_thread.daemon = True
            assistant_thread.start()
            
    return jsonify({
        "active": main.listener_active,
        "status": main.assistant_status
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        entries = read_audit_entries()
        if not entries:
            return jsonify([])
        # Sort logs to show latest on top
        return jsonify(list(reversed(entries)))
    except Exception as e:
        print(f"Error reading audit logs: {e}")
        return jsonify([])

@app.route('/api/settings', methods=['POST'])
def update_settings():
    data = request.get_json() or {}
    gemini_key = data.get("gemini_key", "").strip()
    
    if gemini_key:
        os.environ["GEMINI_API_KEY"] = gemini_key
        print("[Web UI] Gemini API Key updated in environment.")
        return jsonify({"status": "success", "message": "API key updated."})
    
    return jsonify({"status": "error", "message": "Key cannot be empty."}), 400

@app.route('/api/command', methods=['POST'])
def execute_keyboard_command():
    """
    Executes a keyboard-typed command through the LLM / tool router.
    Writes a VERIFIED action entry to the encrypted log file.
    """
    data = request.get_json() or {}
    command_text = data.get("command", "").strip()
    if not command_text:
        return jsonify({"status": "error", "message": "Command is empty"}), 400
        
    print(f"[Web UI Console Command]: \"{command_text}\"")
    main.assistant_status = "thinking"
    
    # Run hybrid agent loop
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
    else:
        api_url = f"{config.OLLAMA_HOST}/api/chat"
        headers = {}
        model_name = config.OLLAMA_MODEL
        
    try:
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
            
        # Tool execution loop
        while "tool_calls" in message and message["tool_calls"]:
            messages.append(message)
            
            for tool_call in message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args = tool_call["function"]["arguments"]
                
                # Note: Keyboard command bypasses destructive voice prompt,
                # as the user has already typed it intentionally in the UI
                print(f"[Web UI] Executing tool: '{tool_name}'...")
                result = tool_router.execute_tool(tool_name, tool_args)
                
                audit_log.write_audit_entry(
                    command=command_text,
                    gate_score=1.0,  # Explicitly authenticated
                    is_verified=True,
                    tool_name=tool_name,
                    tool_args=str(tool_args),
                    outcome=result
                )
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", "call_default"),
                    "content": result,
                    "name": tool_name
                })
                
            # Send results back to LLM to get the final conversational response
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
                
        # Speak and log response
        if message.get("content"):
            reply_text = message['content']
            main.assistant_status = "speaking"
            tts.speak(reply_text)
            
            audit_log.write_audit_entry(
                command=command_text,
                gate_score=1.0,
                is_verified=True,
                outcome=reply_text
            )
            
            main.assistant_status = "idle"
            return jsonify({"status": "success", "response": reply_text})
            
    except Exception as e:
        err_msg = f"Error executing command: {e}"
        print(err_msg)
        main.assistant_status = "idle"
        return jsonify({"status": "error", "message": err_msg}), 500
        
    main.assistant_status = "idle"
    return jsonify({"status": "success", "response": "Action completed."})

if __name__ == '__main__':
    print("=" * 60)
    print("           JARVIS LOCAL DASHBOARD DEV SERVER")
    print("=" * 60)
    print("Dashboard address: http://127.0.0.1:5000")
    print("-" * 60)
    app.run(host='127.0.0.1', port=5000, debug=False)
