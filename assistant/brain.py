"""
brain.py - How Jarvis answers general questions, with conversation memory.

1. If you set ANTHROPIC_API_KEY in .env, understand() lets Claude work out what
   you mean - turning natural sentences into commands, or answering questions -
   and it remembers the recent conversation for follow-ups.
2. Otherwise (or if that fails) questions are answered from Wikipedia, which still
   understands "tell me more" and simple follow-ups like "when was he born?".
"""

import datetime
import json
import urllib.parse
import urllib.request

import config

# Wikipedia requires a descriptive User-Agent, otherwise it blocks the request.
_WIKI_API = "https://en.wikipedia.org/w/api.php"
_WIKI_HEADERS = {"User-Agent": "JarvisVoiceAssistant/1.0 (personal Python project)"}

# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------
_history = []        # Chat messages sent to the AI: [{"role": ..., "content": ...}]
_last_topic = None   # Last Wikipedia page we talked about
_told = ""           # What we already said about it
_told_sentences = 0
_client = None

_MORE_PHRASES = ["tell me more", "more about it", "more about that", "more about him",
                 "more about her", "go on", "continue", "what else", "and then"]
_PRONOUNS = {"it", "he", "she", "him", "her", "they", "them", "his", "its", "their"}

# Filler words removed before searching Wikipedia
_FILLER_PHRASES = [
    "jarvis", "please", "can you", "could you", "tell me about", "tell me",
    "what is", "what are", "what's", "who is", "who was", "who are",
    "where is", "define", "explain", "search wikipedia for", "wikipedia",
    "do you know", "about", "a ", "an ", "the ",
]


def reset_memory() -> None:
    """Forget the conversation so far."""
    global _last_topic, _told, _told_sentences
    _history.clear()
    _last_topic, _told, _told_sentences = None, "", 0


def _clean_query(question: str) -> str:
    text = f" {question.lower()} "
    for phrase in _FILLER_PHRASES:
        text = text.replace(f" {phrase.strip()} ", " ")
    return " ".join(text.replace("?", " ").split())


# ---------------------------------------------------------------------------
# Claude AI: understands human-like sentences and answers questions
# ---------------------------------------------------------------------------
_COMMAND_GUIDE = """You are the brain of a voice assistant running on the user's computer.
Decide whether the user wants an ACTION or is asking a QUESTION / chatting.

For an action, rewrite it as ONE of these exact command formats:
open <website or app>              e.g. open youtube, open notepad, open chrome
close <website or app>             e.g. close youtube, close notepad, close tab, close browser
play <song or video> on youtube
pause video | resume video | next video
search <query> | search <query> on youtube
weather | weather in <city>
news | news about <topic>
remind me in <number> minutes to <task> | remind me at <time like 6:30 pm> to <task>
set a timer for <number> minutes | set an alarm for <time like 7 am>
my reminders | cancel all reminders
volume up | volume down | set volume to <number> | mute | unmute
take a screenshot | lock the computer | shut down the computer | restart the computer | cancel shutdown
tell me a joke | go to sleep | exit | forget everything | what can you do

Reply with exactly ONE line and nothing else:
COMMAND: <the command in one of the formats above>
or
ANSWER: <your spoken reply in 1 to 3 short plain sentences, no markdown, lists or emojis>

Use earlier messages to understand follow-ups like "play it again" or "who founded it".
The user may speak Hinglish; always reply in English."""


def ai_available() -> bool:
    return bool(config.ANTHROPIC_API_KEY)


def understand(text: str):
    """Ask Claude what the user means.

    Returns ("command", "<command text>") for actions,
            ("answer", "<reply>")         for questions/chat,
            None                          if AI isn't available or failed.
    """
    global _client
    if not ai_available():
        return None
    try:
        import anthropic

        if _client is None:
            _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        now = datetime.datetime.now()
        system = (
            f"You are {config.ASSISTANT_NAME}, a witty, polite assistant in the style of Jarvis "
            f"from Iron Man. Address the user as '{config.USER_NAME}'. "
            f"It is {now.strftime('%A, %d %B %Y, %I:%M %p')}.\n\n{_COMMAND_GUIDE}"
        )
        recent = _history[-config.MEMORY_TURNS * 2:]
        message = _client.messages.create(
            model=config.AI_MODEL,
            max_tokens=config.AI_MAX_TOKENS,
            system=system,
            messages=recent + [{"role": "user", "content": text}],
        )
        reply = "".join(block.text for block in message.content if block.type == "text").strip()
        if not reply:
            return None
        line = next((l.strip() for l in reply.splitlines() if l.strip()), "")

        _history.extend([{"role": "user", "content": text}, {"role": "assistant", "content": line}])
        del _history[:-config.MEMORY_TURNS * 2]  # Keep memory small

        if line.upper().startswith("COMMAND:"):
            return "command", line[len("COMMAND:"):].strip().lower()
        if line.upper().startswith("ANSWER:"):
            return "answer", line[len("ANSWER:"):].strip()
        return "answer", reply
    except Exception as error:
        print(f"[AI unavailable, using offline mode: {error}]")
        return None


# ---------------------------------------------------------------------------
# Wikipedia
# ---------------------------------------------------------------------------
def _wiki_api(params: dict) -> dict:
    """Call the official Wikipedia API and return its JSON."""
    params = {**params, "format": "json", "formatversion": 2}
    url = _WIKI_API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers=_WIKI_HEADERS)
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def _search(query: str) -> list:
    data = _wiki_api({"action": "query", "list": "search", "srsearch": query, "srlimit": 3})
    return [item["title"] for item in data.get("query", {}).get("search", [])]


def _pick_title(titles: list) -> str:
    """Skip 'disambiguation' pages (lists of meanings) and pick a real article."""
    data = _wiki_api({"action": "query", "prop": "pageprops", "ppprop": "disambiguation",
                      "titles": "|".join(titles)})
    pages = data.get("query", {}).get("pages", [])
    ambiguous = {p.get("title") for p in pages if "disambiguation" in p.get("pageprops", {})}
    return next((t for t in titles if t not in ambiguous), titles[0])


def _summary(title: str, sentences: int) -> str:
    data = _wiki_api({
        "action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
        "exsentences": min(sentences, 10), "titles": title, "redirects": 1,
    })
    pages = data.get("query", {}).get("pages", [])
    text = pages[0].get("extract", "") if pages else ""
    return " ".join(text.split())  # Tidy line breaks and extra spaces


def _tell_more():
    """Continue talking about the last Wikipedia topic."""
    global _told, _told_sentences
    if _told_sentences >= 10:
        return f"That's everything in my summary about {_last_topic}."
    try:
        wanted = _told_sentences + 3
        full = _summary(_last_topic, wanted)
        extra = full[len(_told):].strip() if full.startswith(_told) else full
        _told, _told_sentences = full, wanted
        return extra or f"That's all I know about {_last_topic}."
    except Exception as error:
        print(f"[Wikipedia error: {error}]")
        return None


def ask_wikipedia(question: str):
    """Look up a short Wikipedia summary. Returns text or None."""
    global _last_topic, _told, _told_sentences
    lowered = question.lower()
    if _last_topic and any(phrase in lowered for phrase in _MORE_PHRASES):
        return _tell_more()

    query = _clean_query(question)
    words = query.split()
    if _last_topic and _PRONOUNS.intersection(words):
        # "when was he born" -> "when was <last topic> born"
        query = " ".join(_last_topic if w in _PRONOUNS else w for w in words)
    if not query:
        return None

    try:
        results = _search(query)
        if not results:
            return None
        title = _pick_title(results)
        text = _summary(title, config.WIKIPEDIA_SENTENCES)
        if not text:
            return None
        _last_topic, _told, _told_sentences = title, text, config.WIKIPEDIA_SENTENCES
        return text
    except Exception as error:
        print(f"[Wikipedia error: {error}]")
        return None


def answer(question: str):
    """Offline answer from Wikipedia, or None."""
    return ask_wikipedia(question)
