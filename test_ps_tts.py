import subprocess
import sys

def speak(text: str):
    # Escape single quotes for PowerShell syntax
    cleaned = text.replace("'", "''").strip()
    if not cleaned:
        return
    ps_command = (
        f"Add-Type -AssemblyName System.Speech; "
        f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"try {{ $synth.SelectVoice('Microsoft David Desktop') }} catch {{}}; "
        f"$synth.Speak('{cleaned}')"
    )
    print(f"Speaking via PowerShell: '{cleaned}'")
    result = subprocess.run(["powershell", "-Command", ps_command], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error speaking: {result.stderr}")

if __name__ == "__main__":
    speak("Hello! I am speaking through the native Windows system voice synthesizer. This is a male voice.")
