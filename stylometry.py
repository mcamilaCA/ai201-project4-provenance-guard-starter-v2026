"""
Signal two: the style signal. ← YOU BUILD THIS IN MILESTONE 4

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

Three measures are stubbed below because the brief names those three. They are
stubs, not implementations: what they compute is yours, and so is how you
combine them.

    sentence_length_spread   do sentences vary in length, or march in step?
    type_token_ratio         how much of the vocabulary repeats?
    punctuation_density      how much punctuation, and how varied?

Why these might differ between human and AI writing: generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

⚠️ **The blind spot, which you have to name in Milestone 1.**

This signal cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — adding typos,
breaking up sentences, pasting in a quotation. That is a very cheap thing for
someone to do on purpose, and unit 8's attack set will do it to you.

Build each function on its own and call it from a terminal before you wire
anything together:

    python stylometry.py "some text to look at"
"""

import re
import statistics

# Words counted by type_token_ratio. The ratio falls as text gets longer, so
# every text is cut to this length before measuring.
TTR_WINDOW = 100

# Raw-value bounds each measure is scaled between in style_signal. Starting
# guesses; tune them against the calibration texts.
MAX_RATIO = 1.0
MIN_RATIO = 0.0
MAX_SPREAD = 1.5
MIN_SPREAD = 0.0
MAX_PUNCT = 0.5
MIN_PUNCT = 0.0

def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into lowercase words, punctuation stripped. Given to you."""
    return re.findall(r"[a-z0-9']+", text.lower())


# ── The three measures — YOU BUILD THESE ─────────────────────────────────────

def sentence_length_spread(text: str) -> float:
    """
    How much sentence length varies. ← TODO

    Returns:
        A float. Decide yourself what scale it's on and which direction means
        "more human" — then write that down, because your combining rule
        depends on knowing it.

    A hint on what you're reaching for: the standard deviation of sentence
    lengths, probably divided by the mean so a long text and a short one are
    comparable. `statistics.stdev` is imported for you.

    Watch the edge case: a one-sentence submission has no spread at all, and
    `stdev` raises on fewer than two values. Decide what that should return
    before the attack set decides for you.
    """

    # Scale: coefficient of variation (stdev / mean), roughly 0 to 1.5.
    # Direction: HIGHER = MORE HUMAN. style_signal must flip this one.
    sents = sentences(text)

    lengths = [len(words(s)) for s in sents]

    # No sentences, or sentences with no words (e.g. "..."): nothing to
    # measure. 0.0 reads as "no spread", so this leans AI-ish after the flip.
    if not lengths or statistics.mean(lengths) == 0:
        return 0.0

    # One sentence has no spread to measure and stdev raises on it. Return a
    # neutral middle value so a short text isn't scored as uniform just
    # because it is short.
    if len(lengths) < 2:
        return 0.3

    return statistics.stdev(lengths) / statistics.mean(lengths)


def type_token_ratio(text: str) -> float:
    """
    Unique words over total words. ← TODO

    Returns:
        A float between 0 and 1. Higher means more varied vocabulary.

    Worth knowing before you rely on it: this measure falls as text gets
    longer, because common words repeat. Two texts of different lengths aren't
    directly comparable on it, and if your test inputs vary a lot in length,
    that alone can look like a signal.
    """
    # Scale: 0 to 1. Direction: HIGHER = MORE HUMAN. style_signal must flip it.
    # Only the first TTR_WINDOW words are counted, so a long text and a short
    # one are compared over the same number of words.
    ws = words(text)[:TTR_WINDOW]

    # Empty text has no vocabulary: 0.0 leans AI-ish after the flip.
    if not ws:
        return 0.0

    return len(set(ws)) / len(ws)


def punctuation_density(text: str) -> float:
    """
    How much punctuation, relative to length. ← TODO

    Returns:
        A float. Whether you count all punctuation or only some kinds — commas,
        semicolons, dashes — is a real choice. Semicolons and em dashes are
        more interesting than full stops, because they vary more between
        writers.
    """
    # Unit: marks per word. Typically about 0 to 0.5.
    # Direction: HIGHER = MORE HUMAN (more varied punctuation). style_signal
    # must flip it.
    # Counted: : ; , ( ) ? ! and the em/en dash. Not counted: full stops, which
    # appear in everything, and the hyphen, which mostly marks compound words.
    marks = ":;,()?!—–"

    word_count = len(words(text))
    if word_count == 0:
        return 0.0

    count = sum(1 for ch in text if ch in marks)
    return count / word_count


# ── Combining them ───────────────────────────────────────────────────────────

def _scale(x: float, low: float, high: float) -> float:
    """Map x from the range [low, high] onto 0-1, clamped at both ends."""
    scaled = (x - low) / (high - low)
    return min(max(scaled, 0.0), 1.0)


def style_signal(text: str) -> float:
    """
    The style signal as a 0–1 score. **Higher means more likely AI.**

    Combine your three measures into one number. Same direction as
    `detector.model_signal`, so that `scoring.combine_signals` can treat them
    the same way — if one of your signals runs backwards, everything above it
    is wrong in a way that's hard to see.

    Two things to decide and write down:

      1. Which direction each measure points. Low spread means more AI-ish, so
         it needs flipping. Work out which of your three need that.
      2. How to get each onto a comparable scale. A raw type-token ratio sits
         between 0 and 1; a raw punctuation count doesn't. Adding them
         unscaled means whichever has the bigger numbers wins by default.

    Test it on the four calibration inputs from Milestone 4 — clearly AI,
    clearly human, plain conventional human writing, lightly-edited AI — before
    you trust it. Plain and ordinary, not formal: formal prose reads as *human*
    to signal one, and it is plain writing that gets accused.
    """
    # All three raw measures run "higher = more human". Each is scaled onto
    # 0-1 first, then flipped, so every value below is "higher = more AI".
    spread_ai = 1 - _scale(sentence_length_spread(text), MIN_SPREAD, MAX_SPREAD)
    ratio_ai = 1 - _scale(type_token_ratio(text), MIN_RATIO, MAX_RATIO)
    punct_ai = 1 - _scale(punctuation_density(text), MIN_PUNCT, MAX_PUNCT)

    # Equal-weight average: the weights sum to 1, so the result stays in 0-1.
    score = (spread_ai + ratio_ai + punct_ai) / 3

    return round(score, 4)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")
