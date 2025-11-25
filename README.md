# 🤖 Living Laptop Assistant

Transform your laptop into a living, caring AI companion that monitors your presence, observes your activity, and helps you stay on track with your goals.

## Features

- 👀 **Camera Monitoring**: Detects your presence via facial recognition
- 🖥️ **Screen Awareness**: Captures and analyzes your screen activity
- 🎤 **Speech Recognition**: Listens to you and transcribes using OpenAI Whisper
- 🗣️ **Voice Interaction**: Speaks to you using text-to-speech
- 💬 **Google Chat Integration**: Sends periodic check-ins and reminders
- 🧠 **Smart Decision Making**: Uses OpenAI GPT-4o-mini with vision to decide when and how to engage

## Architecture

```
living_assistant/
├── main.py              # Entry point
├── config.py            # Configuration settings
├── core/                # Core logic
│   ├── brain.py         # LLM decision-making
│   ├── state.py         # Thread-safe state management
│   └── memory.py        # Long-term memory (JSON)
├── senses/              # Sensory inputs
│   ├── eyes.py          # Camera & face recognition
│   ├── ears.py          # Microphone & speech-to-text
│   └── screen.py        # Screen capture
├── actions/             # Output actions
│   ├── voice.py         # Text-to-speech
│   └── chat.py          # Google Chat API
└── utils/               # Utilities
    └── logger.py        # Logging
```

## Installation

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3-dev cmake libopencv-dev portaudio19-dev
```

**macOS:**
```bash
brew install cmake opencv portaudio
```

### 2. Install Python Dependencies

```bash
cd living_assistant
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.template .env
# Edit .env and add your OpenAI and ElevenLabs API keys
nano .env
```

Get your OpenAI API key from: https://platform.openai.com/api-keys
Get your ElevenLabs API key from: https://elevenlabs.io/app/settings/api-keys

(Optional) Set up a Google Chat webhook for messaging.

## Usage

### Start the Assistant

```bash
python main.py
```

The assistant will:
1. Start monitoring your camera for presence
2. Start listening to your microphone for speech
3. Capture screenshots periodically
4. Analyze your activity using GPT-4o-mini with vision
5. Respond to your speech and speak back to you
6. Proactively speak or send messages when appropriate
7. Send scheduled Google Chat reminders at configured times

### Manage Scheduled Reminders

You can manage reminders via voice commands:

**Add a reminder:**
```
"Add a reminder at 6 AM saying you up"
"Remind me at 2:30 PM to take a break"
"Set a reminder at 10 PM saying time for bed"
```

**List your reminders:**
```
"What are my reminders?"
"List my schedules"
"Show my reminders"
```

**Remove a reminder:**
```
"Remove my 6 AM reminder"
"Delete the 2:30 PM reminder"
"Cancel my 10 PM reminder"
```

### Add Goals/Plans

You can programmatically add plans to the memory:

```python
from core.memory import Memory

memory = Memory()
memory.add_plan("Finish the project report by 5 PM")
memory.add_plan("Exercise for 30 minutes")
```

The assistant will check on your progress throughout the day.

## Configuration

Edit `config.py` to adjust:

- `CHECK_INTERVAL_SECONDS`: How often the brain makes decisions (default: 5s)
- `SCREEN_ANALYSIS_INTERVAL_SECONDS`: How often to capture screen (default: 30s)
- `USER_ABSENCE_TIMEOUT_SECONDS`: How long before considering user away (default: 300s)
- `CAMERA_INDEX`: Which camera to use (default: 0)
- `MICROPHONE_MODE`: Microphone activation mode (default: "auto")
  - `"auto"`: Automatic voice detection using threshold (always listening)
  - `"manual"`: GUI button control (push-to-talk)

## Privacy & Security

⚠️ **Important Considerations:**

- The assistant captures your screen, camera feed, and microphone audio
- Screenshots are sent to OpenAI API for vision analysis
- Audio is sent to OpenAI Whisper API for transcription
- All camera/screen/audio data is processed locally except for API queries
- Memory is stored locally in `memory.json`
- No data is persisted beyond the memory file

**Recommendations:**
- Only run on your personal laptop
- Review the code before running
- Keep your API keys secure
- Be mindful of sensitive information on screen

## Troubleshooting

### Camera Issues
- Ensure your camera is not in use by another application
- Check `CAMERA_INDEX` in `config.py` (try 0, 1, or 2)
- Grant camera permissions to your terminal/Python

### Voice Issues
- Install `espeak` if TTS fails
- Check audio output is not muted

### API Errors
- Verify your `OPENAI_API_KEY` and `ELEVENLABS_API_KEY` are correct
- Check API quota limits

### Microphone Issues
- Ensure your microphone is not in use by another application
- Grant microphone permissions to your terminal/Python
- Adjust `SILENCE_THRESHOLD` in `config.py` if speech detection is too sensitive/insensitive
- **Manual Mode**: If the GUI window doesn't appear, check `MICROPHONE_MODE` is set to `"manual"` in `config.py`
- **Auto Mode**: If speech isn't detected automatically, try lowering `SILENCE_THRESHOLD` (default: 0.01)

## Microphone Modes

The assistant supports two microphone activation modes:

### Auto Mode (Default)

Microphone is always listening and automatically detects speech using threshold-based voice activity detection.

```python
# In config.py
MICROPHONE_MODE = "auto"
```

### Manual Mode (GUI Control)

A GUI window appears with a "Start Speaking" button for push-to-talk control.

```python
# In config.py
MICROPHONE_MODE = "manual"
```

**How to use:**
1. Click "Start Speaking" to begin recording
2. Speak your message
3. Click "Stop Speaking" when finished
4. The assistant will transcribe and respond

## Future Enhancements

- [x] Speech-to-text for bidirectional conversation
- [x] Manual microphone activation via GUI
- [x] Scheduled Google Chat reminders
- [ ] Custom wake word detection
- [ ] Better screen activity classification (OCR + window titles)
- [ ] Mobile app integration
- [ ] Advanced personality customization

## License

MIT License - Feel free to modify and extend!
