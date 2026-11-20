"""
main.py - Start Jarvis from here.

    python main.py          -> voice mode (say "Jarvis" to wake it up)
    python main.py --text   -> text mode  (type to Jarvis, no microphone needed)

How voice mode works:
    1. Jarvis waits quietly until it hears its name ("Jarvis" or "Hey Jarvis, open YouTube").
    2. It beeps, listens, and does what you asked.
    3. It keeps listening for follow-ups for a few seconds, then goes back to waiting.

While Jarvis is speaking: say "stop" (voice mode) or press Ctrl+C to interrupt.
When Jarvis is listening: press Ctrl+C to quit.
"""

import argparse
import datetime
import random
import time

import config
from assistant import browser, reminders
from assistant.commands import process_command, set_input, strip_wake_word
from assistant.speech import beep, enable_voice_interrupt, listen, listen_text, speak


def greet() -> None:
    hour = datetime.datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    elif hour < 20:
        greeting = "Good evening"
    else:
        greeting = "Good night"
    speak(f"{greeting} {config.USER_NAME}. {config.ASSISTANT_NAME} is online. How can I help you?")


def announce_reminders() -> None:
    for message in reminders.pop_due():
        beep()
        speak(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{config.ASSISTANT_NAME} voice assistant")
    parser.add_argument("--text", action="store_true", help="type commands instead of speaking")
    args = parser.parse_args()

    text_mode = args.text
    use_wake_word = config.USE_WAKE_WORD and not text_mode

    if text_mode:
        set_input(listen_text)
    else:
        set_input(lambda: listen(active=True))
        enable_voice_interrupt()  # Say "stop" while Jarvis talks to interrupt it

    def stay_awake_until() -> float:
        """How long to keep listening without needing the wake word."""
        return time.time() + config.FOLLOW_UP_SECONDS if use_wake_word else float("inf")

    greet()
    awake_until = stay_awake_until()
    needs_beep = True          # Beep only at the start of each conversation turn
    shown_standby = False

    while True:
        try:
            announce_reminders()

            if text_mode:
                heard = listen_text()
            else:
                awake = time.time() < awake_until
                if not awake and not shown_standby:
                    print(f"\n[Standing by] Say '{config.ASSISTANT_NAME}' to wake me.")
                    shown_standby = True
                heard = listen(active=awake, with_beep=needs_beep)
                needs_beep = False
                if not heard:
                    continue
                if not awake:
                    found, _ = strip_wake_word(heard)
                    if not found:
                        continue  # Not talking to Jarvis - ignore
                    print(f"You: {heard}")

            found, command = strip_wake_word(heard)
            shown_standby = False
            if found and not command:  # You only said "Jarvis"
                speak(random.choice([
                    f"Yes, {config.USER_NAME}?", f"At your service, {config.USER_NAME}.",
                    "I'm listening.", f"How can I help, {config.USER_NAME}?",
                ]))
                awake_until, needs_beep = stay_awake_until(), True
                continue

            status = process_command(command)
            if status == "exit":
                break
            if status == "sleep":
                awake_until = 0.0
                continue
            awake_until, needs_beep = stay_awake_until(), True

        except KeyboardInterrupt:
            print()
            speak(f"Shutting down. Goodbye {config.USER_NAME}.")
            break
        except Exception as error:
            # Keep Jarvis running even if one command fails
            print(f"[Unexpected error: {error}]")
            speak("Sorry, something went wrong with that command.")

    browser.quit()  # Close Jarvis's browser window when Jarvis shuts down


if __name__ == "__main__":
    main()
