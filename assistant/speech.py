"""
speech.py - Jarvis's mouth (speak), ears (listen) and the listening beep.

Voice: a realistic neural voice (edge-tts) is used when online; if that fails,
Jarvis automatically falls back to the offline voice (pyttsx3).

Interrupting Jarvis while it speaks:
    * Say "stop" (or any word in config.STOP_WORDS)  -> voice mode only
    * Press Ctrl+C                                  -> works in every mode
After stopping, Jarvis immediately listens for your next command.
"""

import asyncio
import io
import math
import os
import struct
import threading
import time
import wave

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # Hide pygame's hello message

import speech_recognition as sr

import config

try:
    import pygame
except ImportError:
    pygame = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

_recognizer = sr.Recognizer()
_calibrated = False
_voice_interrupt_enabled = False   # Turned on by main.py in voice mode
_stop_event = threading.Event()    # Set when you ask Jarvis to stop talking

_mixer_ready = None                # None = not tried yet
_beep_sound = None
_edge_loop = None
_edge_failed_at = 0.0              # When the online voice last failed
_last_network_warning = 0.0


def enable_voice_interrupt() -> None:
    """Allow saying 'stop' while Jarvis is speaking (voice mode only)."""
    global _voice_interrupt_enabled
    _voice_interrupt_enabled = config.VOICE_INTERRUPT


def was_interrupted() -> bool:
    """True if the last thing Jarvis said was stopped by you."""
    return _stop_event.is_set()


# ---------------------------------------------------------------------------
# Audio player (pygame) and the listening beep
# ---------------------------------------------------------------------------
def _init_mixer() -> bool:
    global _mixer_ready
    if _mixer_ready is None:
        if pygame is None:
            _mixer_ready = False
        else:
            try:
                pygame.mixer.init()
                _mixer_ready = True
            except Exception as error:
                print(f"[Audio player unavailable: {error}]")
                _mixer_ready = False
    return _mixer_ready


def _tone(frequency, milliseconds, rate=44100, volume=0.35) -> bytes:
    count = int(rate * milliseconds / 1000)
    fade = int(rate * 0.008)  # Tiny fade in/out so the beep doesn't click
    frames = bytearray()
    for i in range(count):
        envelope = min(1.0, i / fade, (count - i) / fade)
        sample = volume * envelope * math.sin(2 * math.pi * frequency * i / rate)
        frames += struct.pack("<h", int(32767 * sample))
    return bytes(frames)


def _build_beep():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(44100)
        wav.writeframes(_tone(660, 90) + _tone(990, 120))  # Two-tone "ding"
    buffer.seek(0)
    return pygame.mixer.Sound(file=buffer)


def beep() -> None:
    """Short sound that means 'I'm listening now'."""
    global _beep_sound
    if not config.LISTEN_BEEP:
        return
    try:
        if _init_mixer():
            if _beep_sound is None:
                _beep_sound = _build_beep()
            _beep_sound.play()
            time.sleep(_beep_sound.get_length())
            return
    except Exception:
        pass
    try:  # Fallback beep on Windows
        import winsound
        winsound.Beep(880, 150)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Background "stop" listener - runs only while Jarvis is talking
# ---------------------------------------------------------------------------
def _on_background_audio(recognizer, audio) -> None:
    if _stop_event.is_set():
        return
    try:
        heard = recognizer.recognize_google(audio, language=config.LANGUAGE).lower()
    except Exception:
        return  # Noise, Jarvis's own voice, or no internet - ignore
    if any(f" {word} " in f" {heard} " for word in config.STOP_WORDS):
        print(f"\n(You said '{heard}' - stopping)")
        _stop_event.set()


def _start_stop_listener():
    """Start listening for 'stop' in the background. Returns a function that ends it."""
    if not _voice_interrupt_enabled:
        return None
    try:
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = _recognizer.energy_threshold
        recognizer.dynamic_energy_threshold = False  # Don't let Jarvis's voice raise the threshold
        return recognizer.listen_in_background(
            sr.Microphone(), _on_background_audio, phrase_time_limit=3
        )
    except Exception:
        return None  # No mic available - Ctrl+C still works


# ---------------------------------------------------------------------------
# Realistic online voice (edge-tts)
# ---------------------------------------------------------------------------
async def _edge_audio(text: str) -> bytes:
    communicate = edge_tts.Communicate(
        text, config.EDGE_VOICE, rate=config.EDGE_RATE, pitch=config.EDGE_PITCH
    )
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            audio.extend(chunk["data"])
    return bytes(audio)


def _speak_edge(text: str) -> bool:
    """Speak with the neural voice. Returns False if it couldn't (use fallback)."""
    global _edge_loop, _edge_failed_at
    if edge_tts is None or not _init_mixer():
        return False
    if time.time() - _edge_failed_at < 60:
        return False  # Failed recently (probably offline) - don't keep retrying

    try:
        if _edge_loop is None:
            _edge_loop = asyncio.new_event_loop()
        audio = _edge_loop.run_until_complete(asyncio.wait_for(_edge_audio(text), timeout=15))
    except KeyboardInterrupt:
        raise
    except Exception as error:
        print(f"[Realistic voice unavailable ({type(error).__name__}) - using offline voice]")
        _edge_failed_at = time.time()
        try:
            _edge_loop.close()
        except Exception:
            pass
        _edge_loop = None
        return False
    if not audio:
        return False

    try:
        pygame.mixer.music.load(io.BytesIO(audio), "mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if _stop_event.is_set():
                break
            time.sleep(0.05)
        return True
    except KeyboardInterrupt:
        raise
    except Exception as error:
        print(f"[Couldn't play audio: {error}]")
        return False
    finally:
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Offline voice (pyttsx3)
# ---------------------------------------------------------------------------
def _speak_pyttsx3(text: str) -> None:
    import pyttsx3

    engine = None
    try:
        # A fresh engine each time avoids a known pyttsx3 bug where
        # it goes silent after the first sentence on some systems.
        engine = pyttsx3.init()
        engine.setProperty("rate", config.VOICE_RATE)
        engine.setProperty("volume", config.VOICE_VOLUME)
        voices = engine.getProperty("voices")
        if voices and 0 <= config.VOICE_INDEX < len(voices):
            engine.setProperty("voice", voices[config.VOICE_INDEX].id)

        def on_word(name, location, length):  # Called before every word
            if _stop_event.is_set():
                engine.stop()

        engine.connect("started-word", on_word)
        engine.say(text)
        engine.runAndWait()
    except KeyboardInterrupt:
        _safe_shutdown(engine)
        raise
    except Exception as error:  # Never crash just because audio failed
        print(f"[Voice output unavailable: {error}]")
    finally:
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass


def _safe_shutdown(engine) -> None:
    """Cleanly end the offline engine after Ctrl+C so the next speak() works."""
    if engine is None:
        return
    for action in (engine.stop, engine.endLoop):
        try:
            action()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Speaking
# ---------------------------------------------------------------------------
def speak(text: str) -> None:
    """Print the text and say it out loud. Can be interrupted (see top of file)."""
    text = (text or "").strip()
    if not text:
        return
    print(f"{config.ASSISTANT_NAME}: {text}")
    _stop_event.clear()
    stop_listener = _start_stop_listener()
    try:
        spoken = False
        if config.TTS_ENGINE == "edge":
            spoken = _speak_edge(text)
        if not spoken and not _stop_event.is_set():
            _speak_pyttsx3(text)
    except KeyboardInterrupt:
        _stop_event.set()
        print("\n(Stopped speaking)")
    finally:
        if stop_listener:
            stop_listener(wait_for_stop=False)


# ---------------------------------------------------------------------------
# Listening
# ---------------------------------------------------------------------------
def _network_warning() -> None:
    global _last_network_warning
    if time.time() - _last_network_warning > 60:  # Don't repeat every few seconds
        _last_network_warning = time.time()
        speak("I can't reach the speech service. Please check your internet connection.")


def listen(active: bool = True, with_beep: bool = True) -> str:
    """Listen through the microphone and return what you said (lowercase).

    active=False is the quiet 'waiting for wake word' mode: no beep, no messages.
    Returns an empty string if nothing was heard or understood.
    """
    global _calibrated
    if active and with_beep and _calibrated:
        beep()
    try:
        with sr.Microphone() as source:
            if not _calibrated:
                print("Calibrating for background noise... please stay quiet.")
                _recognizer.adjust_for_ambient_noise(source, duration=config.AMBIENT_NOISE_DURATION)
                _calibrated = True
                if active and with_beep:
                    beep()
            if active:
                print("\nListening...")
            audio = _recognizer.listen(
                source,
                timeout=config.LISTEN_TIMEOUT,
                phrase_time_limit=config.PHRASE_TIME_LIMIT,
            )
    except sr.WaitTimeoutError:
        return ""  # You didn't say anything - just listen again
    except (OSError, AttributeError) as error:
        print(f"[Microphone error: {error}]")
        print("Tip: check your mic, or run in text mode:  python main.py --text")
        raise SystemExit(1)

    try:
        if active:
            print("Recognizing...")
        text = _recognizer.recognize_google(audio, language=config.LANGUAGE)
        if active:
            print(f"You: {text}")
        return text.lower().strip()
    except sr.UnknownValueError:
        if active:
            print("(Didn't catch that)")
        return ""
    except sr.RequestError:
        _network_warning()
        return ""


def listen_text() -> str:
    """Text mode: type commands instead of speaking (great for testing)."""
    try:
        return input("\nYou (type): ").lower().strip()
    except EOFError:
        return "exit"
