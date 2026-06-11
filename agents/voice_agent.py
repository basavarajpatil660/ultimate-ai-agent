import os
import requests
from gtts import gTTS

def generate_voice(text, ELEVENLABS_API_KEY=None,
                   GOOGLE_AI_KEY=None):

    text = text[:2000] if text else ""

    # Provider 1: ElevenLabs
    if ELEVENLABS_API_KEY:
        try:
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.5
                    }
                },
                timeout=30
            )
            if response.status_code == 200:
                with open("/tmp/output.mp3", "wb") as f:
                    f.write(response.content)
                print("Voice generated via ElevenLabs")
                return {"file_path": "/tmp/output.mp3", "provider": "elevenlabs"}
        except Exception as e:
            print(f"ElevenLabs failed: {e}")

    # Provider 2: Google TTS via gTTS fallback
    try:
        tts = gTTS(text=text, lang='en')
        tts.save("/tmp/output.mp3")
        print("Voice generated via gTTS")
        return {"file_path": "/tmp/output.mp3", "provider": "gtts"}
    except Exception as e:
        print(f"gTTS failed: {e}")

    return None

text_to_speech = generate_voice
