import time
import requests
from config import Config

# Shared auth headers — built once, reused across calls.
def _headers():
    return {
        "Authorization": f"Bearer {Config.META_WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

_GRAPH_BASE = "https://graph.facebook.com/v19.0"


def mark_read_and_typing(message_id: str):
    """Marks the inbound message as read and shows a typing indicator.

    This must be called as soon as msg_id is known (before the background
    thread starts) so the customer sees blue ticks + "typing…" while the
    model thinks, rather than a dead silence.

    The typing indicator lasts up to 25 s or until we send our reply —
    whichever comes first. Meta silently ignores the call if the 24-hour
    session window has already closed.
    """
    if not Config.META_WHATSAPP_TOKEN or not Config.META_PHONE_NUMBER_ID:
        return
    try:
        requests.post(
            f"{_GRAPH_BASE}/{Config.META_PHONE_NUMBER_ID}/messages",
            headers=_headers(),
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
                "typing_indicator": {"type": "text"},
            },
            timeout=5,
        )
    except Exception as e:
        # Non-fatal — don't let a typing-indicator hiccup kill the main flow.
        print(f"[WhatsApp] mark_read_and_typing failed (non-fatal): {e}")


def send_whatsapp_message(to_number: str, message_text: str, max_retries: int = 2) -> bool:
    """Sends a text message via Meta's Cloud API with automatic retry.

    Retries up to `max_retries` additional times on transient failures
    (network errors, 5xx responses) using simple exponential back-off.
    Returns True on success, False if all attempts fail.
    """
    if not Config.META_WHATSAPP_TOKEN or not Config.META_PHONE_NUMBER_ID:
        print("[WhatsApp] Skipping message send: Missing META_WHATSAPP_TOKEN or META_PHONE_NUMBER_ID")
        return False

    url = f"{_GRAPH_BASE}/{Config.META_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {
            "preview_url": True,   # allows the payment link to unfurl
            "body": message_text,
        },
    }

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, headers=_headers(), json=payload, timeout=10)
            response.raise_for_status()
            print(f"[WhatsApp] Sent to {to_number} (attempt {attempt + 1}): {message_text[:60].encode('cp1252', errors='replace').decode('cp1252')}...")
            return True
        except requests.exceptions.RequestException as e:
            status = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            body = getattr(e.response, "text", "") if hasattr(e, "response") else ""
            print(f"[WhatsApp] Send attempt {attempt + 1} failed for {to_number}. "
                  f"Status: {status}. Error: {e}. Body: {body}")

            if attempt < max_retries:
                wait = 2 ** attempt  # 1 s, 2 s
                print(f"[WhatsApp] Retrying in {wait}s...")
                time.sleep(wait)

    # All attempts exhausted
    safe_msg = message_text[:80].encode('utf-8', errors='replace').decode('utf-8')
    print(f"[WhatsApp] WARNING ALERT: All {max_retries + 1} send attempts failed for {to_number}. "
          f"Message lost: {safe_msg}")
    return False


def send_whatsapp_buttons(to_number: str, body_text: str, buttons: list, header_text: str = None, image_url: str = None) -> bool:
    """Sends an interactive message with quick reply buttons (max 3 buttons) and optional text or image header."""
    if not Config.META_WHATSAPP_TOKEN or not Config.META_PHONE_NUMBER_ID:
        print("[WhatsApp] Skipping buttons send: Missing META_WHATSAPP_TOKEN or META_PHONE_NUMBER_ID")
        return False

    url = f"{_GRAPH_BASE}/{Config.META_PHONE_NUMBER_ID}/messages"
    
    # Format buttons array for Meta API (max 3, titles <= 20 chars)
    meta_buttons = []
    for i, btn in enumerate(buttons[:3]):
        meta_buttons.append({
            "type": "reply",
            "reply": {
                "id": btn.get("id", f"btn_{i}"),
                "title": btn.get("title")[:20]
            }
        })

    interactive_data = {
        "type": "button",
        "body": {
            "text": body_text
        },
        "action": {
            "buttons": meta_buttons
        }
    }

    if image_url:
        interactive_data["header"] = {
            "type": "image",
            "image": {
                "link": image_url
            }
        }
    elif header_text:
        interactive_data["header"] = {
            "type": "text",
            "text": header_text
        }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": interactive_data
    }

    try:
        response = requests.post(url, headers=_headers(), json=payload, timeout=10)
        response.raise_for_status()
        print(f"[WhatsApp] Sent interactive buttons to {to_number}")
        return True
    except Exception as e:
        print(f"[WhatsApp] Send buttons failed: {e}")
        return False


def get_whatsapp_media_url(media_id: str) -> str:
    """Retrieves the download URL for a given media ID from Meta."""
    url = f"{_GRAPH_BASE}/{media_id}"
    try:
        response = requests.get(url, headers={"Authorization": f"Bearer {Config.META_WHATSAPP_TOKEN}"}, timeout=10)
        response.raise_for_status()
        return response.json().get("url")
    except Exception as e:
        print(f"[WhatsApp] Failed to get media URL for {media_id}: {e}")
        return None


def download_whatsapp_media(media_url: str) -> bytes:
    """Downloads binary media content from Meta's CDN."""
    try:
        response = requests.get(media_url, headers={"Authorization": f"Bearer {Config.META_WHATSAPP_TOKEN}"}, timeout=15)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"[WhatsApp] Failed to download media from URL: {e}")
        return None


def transcribe_audio_via_whisper(audio_bytes: bytes) -> str:
    """Transcribes audio bytes (Ogg Opus) using OpenAI Whisper API as primary STT engine.
    If OPENAI_API_KEY is missing or API call fails, falls back to Google Speech Recognition."""
    import os
    import uuid
    import requests

    uid = uuid.uuid4().hex
    temp_ogg = f"temp_voice_{uid}.ogg"
    temp_wav = f"temp_voice_{uid}.wav"

    with open(temp_ogg, "wb") as f:
        f.write(audio_bytes)

    try:
        # --- 1. Primary Path: OpenAI Whisper API ---
        if Config.OPENAI_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {Config.OPENAI_API_KEY}"}
                with open(temp_ogg, "rb") as audio_file:
                    files = {"file": (temp_ogg, audio_file, "audio/ogg")}
                    data = {"model": "whisper-1"}
                    response = requests.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers=headers,
                        files=files,
                        data=data,
                        timeout=20,
                    )
                    response.raise_for_status()
                    transcription = response.json().get("text", "").strip()
                    if transcription:
                        print(f"[WhisperSTT] Transcribed via OpenAI Whisper: {transcription}")
                        return transcription
            except Exception as e:
                print(f"[WhisperSTT] OpenAI Whisper API call failed ({e}), falling back to Google SR...")

        # --- 2. Fallback Path: Google Speech Recognition ---
        import subprocess
        try:
            from static_ffmpeg import add_paths
            add_paths()
        except Exception:
            pass

        try:
            import speech_recognition as sr
        except Exception as spe:
            print(f"[FreeSpeech] speech_recognition import failed: {spe}")
            return None

        converted = False
        try:
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", temp_ogg, "-ar", "16000", "-ac", "1", temp_wav],
                capture_output=True, timeout=15
            )
            converted = os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 0
        except Exception:
            pass

        if not converted:
            try:
                from pydub import AudioSegment
                audio_seg = AudioSegment.from_file(temp_ogg)
                audio_seg = audio_seg.set_frame_rate(16000).set_channels(1)
                audio_seg.export(temp_wav, format="wav")
                converted = os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 0
            except Exception:
                pass

        if not converted:
            print("[FreeSpeech] Could not convert audio to WAV — giving up.")
            return None

        r = sr.Recognizer()
        r.energy_threshold = 200
        r.dynamic_energy_threshold = True

        with sr.AudioFile(temp_wav) as source:
            r.adjust_for_ambient_noise(source, duration=0.3)
            audio_data = r.record(source)

        for lang in ["ml-IN", "en-IN", "en-US"]:
            try:
                transcription = r.recognize_google(audio_data, language=lang)
                if transcription:
                    print(f"[FreeSpeech] Transcribed ({lang}): {transcription}")
                    return transcription
            except Exception:
                continue

        print("[FreeSpeech] All language attempts failed.")
        return None
    except Exception as e:
        print(f"[FreeSpeech] Transcription failed: {e}")
        return None
    finally:
        for path in (temp_ogg, temp_wav):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass


def _upload_media_to_whatsapp(file_path: str, mime_type: str) -> str:
    """Uploads a local audio file to WhatsApp Cloud API media endpoint and returns the media_id."""
    if not Config.META_WHATSAPP_TOKEN or not Config.META_PHONE_NUMBER_ID:
        return None
    url = f"{_GRAPH_BASE}/{Config.META_PHONE_NUMBER_ID}/media"
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {Config.META_WHATSAPP_TOKEN}"},
                files={"file": (file_path, f, mime_type)},
                data={"messaging_product": "whatsapp"},
                timeout=30,
            )
        response.raise_for_status()
        media_id = response.json().get("id")
        print(f"[VoiceReply] Uploaded audio media, ID: {media_id}")
        return media_id
    except Exception as e:
        print(f"[VoiceReply] Media upload failed: {e}")
        return None


def _prepare_voice_text(text: str) -> str:
    """Transforms structured bot reply text into natural, conversational spoken language
    before passing it to TTS. Strips markdown, lists, product IDs and rewrites
    them into sentences a real person would naturally say out loud."""
    import re

    # Remove emoji characters (they don't read well aloud)
    text = re.sub(r'[^\x00-\x7F\u00C0-\u024F\u1E00-\u1EFF]', ' ', text)

    # Convert markdown bold/italic to plain text
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # Remove product card separator lines
    text = re.sub(r'[-=]{3,}', '', text)
    text = re.sub(r'\u2501+', '', text)

    # Convert bullet/list items to natural sentence flow
    text = re.sub(r'^\s*[•\-\*]\s+', '', text, flags=re.MULTILINE)

    # Remove raw product IDs
    text = re.sub(r'(?:Product\s+ID|ID)\s*[:\-]?\s*[A-Z0-9\-]{5,}', '', text, flags=re.IGNORECASE)

    # Technical abbreviations & Hardware pronunciation map
    pronunciation_map = {
        r'\bSC-P(\d+)\b': r'SureColor P \1',
        r'\bSC-T(\d+)\b': r'SureColor T \1',
        r'\bCX-02\b': r'Citizen C X 0 2',
        r'\bCZ-01\b': r'Citizen C Z 0 1',
        r'\bOEM\b': r'original manufacturer',
        r'\bGSM\b': r'G S M grams',
        r'\b700ml\b': r'700 milliliters',
        r'\b350ml\b': r'350 milliliters',
        r'\b220ml\b': r'220 milliliters',
        r'\b110ml\b': r'110 milliliters',
        r'\bAED\s*(\d+(?:\.\d+)?)\b': r'\1 dirhams',
        r'(\d+(?:\.\d+)?)\s*AED\b': r'\1 dirhams',
    }
    for pat, rep in pronunciation_map.items():
        text = re.sub(pat, rep, text, flags=re.IGNORECASE)

    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)

    # Insert slight micro-pause punctuation after common filler openers
    fillers = ["got it", "oh nice", "sure thing", "good call", "hmm let me check", "welcome in", "hello there"]
    for filler in fillers:
        text = re.sub(rf'\b({re.escape(filler)})\b', r'\1, ...', text, flags=re.IGNORECASE)

    # Collapse multiple newlines/spaces to single space
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r' {2,}', ' ', text)

    # Fix missing spaces after punctuation
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)

    return text.strip()


def send_whatsapp_voice(to_number: str, text: str, voice: str = "en-US-AndrewNeural") -> bool:
    """Converts text to speech using Microsoft Edge Neural TTS with natural prosody
    and sends it as a WhatsApp voice note.

    Voices:
      Male (Persona Jishan): en-US-AndrewNeural or en-US-GuyNeural
      Female:                 en-US-AriaNeural
    """
    import os
    import uuid
    import asyncio
    
    uid = uuid.uuid4().hex
    temp_mp3 = f"temp_reply_{uid}.mp3"

    clean_text = _prepare_voice_text(text)
    if not clean_text:
        print("[VoiceReply] Nothing to speak after text cleanup — skipping.")
        return False

    print(f"[VoiceReply] Speaking ({voice}): {clean_text[:120]}...")

    async def _synthesize(plain_text, voice_name, output_path):
        import edge_tts
        communicate = edge_tts.Communicate(
            plain_text,
            voice_name,
            rate="-6%",      # slightly slower = natural conversational pacing
            volume="+0%",
            pitch="+2Hz",    # warm, friendly tone
        )
        await communicate.save(output_path)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_synthesize(clean_text, voice, temp_mp3))
        loop.close()
        print(f"[VoiceReply] Edge Neural TTS saved to {temp_mp3}")
    except Exception as e:
        print(f"[VoiceReply] Edge TTS failed ({e}), trying gTTS fallback...")
        try:
            from gtts import gTTS
            gTTS(text=clean_text, lang="en", slow=False).save(temp_mp3)
            print(f"[VoiceReply] Fallback gTTS saved to {temp_mp3}")
        except Exception as e2:
            print(f"[VoiceReply] All TTS methods failed: {e2}")
            return False

    try:
        media_id = _upload_media_to_whatsapp(temp_mp3, "audio/mpeg")
        if not media_id:
            return False

        url = f"{_GRAPH_BASE}/{Config.META_PHONE_NUMBER_ID}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "audio",
            "audio": {"id": media_id},
        }
        res = requests.post(url, headers=_headers(), json=payload, timeout=10)
        res.raise_for_status()
        print(f"[VoiceReply] Sent humanized voice message to {to_number}")
        return True
    except Exception as e:
        print(f"[VoiceReply] Sending voice message failed: {e}")
        return False
    finally:
        if os.path.exists(temp_mp3):
            try:
                os.remove(temp_mp3)
            except Exception:
                pass


def synthesize_text_to_audio_file(text: str, output_path: str, voice: str = "en-US-AndrewNeural") -> bool:
    """Converts plain text to speech (Edge Neural TTS or gTTS fallback) and saves to output_path."""
    import os
    import asyncio
    
    clean_text = _prepare_voice_text(text)
    if not clean_text:
        return False

    async def _synthesize(plain_text, voice_name, path):
        import edge_tts
        communicate = edge_tts.Communicate(
            plain_text,
            voice_name,
            rate="-6%",
            volume="+0%",
            pitch="+2Hz",
        )
        await communicate.save(path)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_synthesize(clean_text, voice, output_path))
        loop.close()
        print(f"[TTS] Edge Neural TTS saved to {output_path}")
        return True
    except Exception as e:
        print(f"[TTS] Edge TTS failed ({e}), trying gTTS fallback...")
        try:
            from gtts import gTTS
            gTTS(text=clean_text, lang="en", slow=False).save(output_path)
            print(f"[TTS] Fallback gTTS saved to {output_path}")
            return True
        except Exception as e2:
            print(f"[TTS] All TTS methods failed: {e2}")
            return False
