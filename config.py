import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = ""
GOOGLE_CHAT_WEBHOOK = ""
ELEVENLABS_API_KEY = ""

# Behavior Settings
CHECK_INTERVAL_SECONDS = 5
USER_ABSENCE_TIMEOUT_SECONDS = 300  # 5 minutes
SCREEN_ANALYSIS_INTERVAL_SECONDS = 30  # Analyze screen every 30s to save cost/latency

# Camera Settings
CAMERA_INDEX = 0

# Microphone Settings
ENABLE_SPEECH_TO_TEXT = True  # Set to False to disable microphone/speech-to-text
MICROPHONE_MODE = "manual"  # "auto" for threshold-based detection, "manual" for GUI button control
SILENCE_THRESHOLD = 0.01  # RMS threshold for voice activity detection (0-1 for sounddevice)
SILENCE_DURATION = 2.0    # Seconds of silence before processing speech

# TTS Backend Settings
TTS_BACKEND = "paroli"  # "elevenlabs" or "paroli"

# ElevenLabs Voice Settings (used when TTS_BACKEND="elevenlabs")
VOICE_ID = "lhTvHflPVOqgSWyuWQry"  # Rachel - warm, friendly female voice
# Popular voice options:
# - "21m00Tcm4TlvDq8ikWAM" - Rachel (female, warm)
# - "EXAVITQu4vr4xnSDxMaL" - Bella (female, soft)
# - "pNInz6obpgDQGcFmaJgB" - Adam (male, deep)

# Paroli TTS Settings (used when TTS_BACKEND="paroli")
import os
PAROLI_ENCODER_PATH = os.path.join(os.path.dirname(__file__), "ttsmodel/encoder.onnx")
PAROLI_DECODER_PATH = os.path.join(os.path.dirname(__file__), "ttsmodel/decoder.onnx")
PAROLI_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "ttsmodel/en_US-nika+RT-medium.onnx.json")
PAROLI_USE_GPU = True  # Enable CUDA GPU acceleration
PAROLI_ESPEAK_DATA_PATH = os.path.join(os.path.dirname(__file__), "paroli/build/espeak-ng-data")  # Optional

# Schedule Settings
SCHEDULES_FILE = "schedules.json"
SCHEDULER_CHECK_INTERVAL_SECONDS = 60  # Check every minute for scheduled messages
