import os
# Force offline mode for Hugging Face and SpeechBrain resolvers at the absolute start
os.environ["HF_HUB_OFFLINE"] = "1"

import sys
from jarvis_core import JarvisCore

def main():
    """
    Main entry point for starting the Jarvis Assistant.
    Bootstraps the central orchestrator (JarvisCore) and manages graceful shutdowns.
    """
    core = JarvisCore()
    try:
        core.start()
    except KeyboardInterrupt:
        print("\n\nTerminating Jarvis Assistant. Cleaning up...")
        core.stop()

if __name__ == "__main__":
    main()
