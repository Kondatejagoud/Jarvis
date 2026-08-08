import sys
import time
import sounddevice as sd
import soundfile as sf
import config

def check_input_devices() -> bool:
    """Check if there is at least one active audio input device."""
    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if d.get('max_input_channels', 0) > 0]
        if not input_devices:
            print("ERROR: No audio input devices (microphones) detected.")
            return False
        
        default_dev = sd.default.device[0]
        if default_dev == -1:
            print("ERROR: No default input device selected in the system.")
            return False
            
        print(f"Detected default input device: {devices[default_dev]['name']}")
        return True
    except Exception as e:
        print(f"Error checking input devices: {e}")
        return False

def record_audio(output_path: str, duration: float = config.DURATION, sample_rate: int = config.SAMPLE_RATE, sleep_before: bool = False) -> None:
    """
    Record mono audio from the default input device and save it to the output path.
    Displays a real-time progress bar in the terminal.
    """
    if sleep_before:
        print(f"Recording starting in 1 second... Get ready.")
        time.sleep(1.0)
    
    # Begin recording (non-blocking)
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype='float32'
    )
    
    # Print progress bar in terminal while recording
    steps = int(duration * 10)  # Update 10 times a second
    sleep_interval = duration / steps
    
    for i in range(steps):
        percent = int((i + 1) / steps * 20)  # 20 char wide progress bar
        bar = '=' * percent + ' ' * (20 - percent)
        sys.stdout.write(f"\rRecording: [{bar}] {duration - (i * sleep_interval):.1f}s remaining")
        sys.stdout.flush()
        time.sleep(sleep_interval)
        
    # Wait for the recording to finish completely (in case of slight timing drift)
    sd.wait()
    
    sys.stdout.write(f"\rRecording: [{'=' * 20}] Finished!                   \n")
    sys.stdout.flush()
    
    # Save using soundfile
    sf.write(output_path, recording, sample_rate)
    print(f"Audio successfully saved to: {output_path}")

def load_audio(path: str) -> tuple[torch.Tensor, int]:
    """
    Load a WAV audio file using soundfile and return a PyTorch tensor of shape [channels, time]
    along with its sample rate. Bypasses torchaudio's backend requirement.
    """
    import torch
    
    data, sample_rate = sf.read(path)
    # Convert numpy array to PyTorch float tensor
    signal = torch.from_numpy(data).float()
    
    # sf.read returns shape [time] for mono, or [time, channels] for multi-channel.
    # We want it to be [channels, time].
    if signal.ndim == 1:
        signal = signal.unsqueeze(0)  # shape [1, time]
    else:
        signal = signal.transpose(0, 1)  # shape [channels, time]
        
    return signal, sample_rate

def record_from_stream(stream, output_path, max_duration=10.0, silence_timeout=1.5, sample_rate=16000):
    """
    Record audio dynamically from a persistent input stream, detecting speech start
    and stopping automatically after silence_timeout seconds of silence.
    """
    import numpy as np
    
    # 100ms block size
    block_size = int(sample_rate * 0.1)
    recorded_chunks = []
    
    start_time = time.time()
    last_active_time = None
    has_spoken = False
    
    sys.stdout.write("\r[Jarvis: Listening...]")
    sys.stdout.flush()
    
    while True:
        try:
            # Read a block of audio
            data, overflowed = stream.read(block_size)
            recorded_chunks.append(data)
        except Exception as read_err:
            print(f"\nError reading from audio stream: {read_err}")
            break
            
        # Convert int16 samples to float32 range [-1.0, 1.0] for RMS check
        float_data = data.astype(np.float32) / 32768.0
        
        # Calculate RMS with DC offset correction
        rms = np.sqrt(np.mean((float_data - np.mean(float_data)) ** 2))
        
        current_time = time.time()
        elapsed = current_time - start_time
        
        if not has_spoken:
            if rms >= 0.003:
                has_spoken = True
                last_active_time = current_time
                sys.stdout.write("\r[Jarvis: Recording speech...]")
                sys.stdout.flush()
            elif elapsed > 3.0:
                # User did not start speaking within 3 seconds
                break
        else:
            if rms >= 0.002:
                last_active_time = current_time
                
            # Check if silence timeout exceeded
            silence_duration = current_time - last_active_time
            if silence_duration >= silence_timeout:
                break
                
        # Limit total duration
        if elapsed >= max_duration:
            break
            
    # Clear the listening status line from console
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()
    
    # Concatenate all recorded blocks
    if recorded_chunks:
        recording = np.concatenate(recorded_chunks, axis=0)
    else:
        recording = np.zeros((0, 1), dtype='float32')
        
    sf.write(output_path, recording, sample_rate)

if __name__ == "__main__":
    # Test recording
    print("Testing audio recorder...")
    try:
        record_audio("test_recording.wav", duration=3.0)
    except Exception as e:
        print(f"Test failed: {e}")
