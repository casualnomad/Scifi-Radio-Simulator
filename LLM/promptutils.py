import re
import inflect

p = inflect.engine()


def numbers_to_words(text):
    """Convert digit sequences (e.g. callsign numbers) into spoken word form for TTS."""
    def digit_by_digit(match):
        digits = match.group()
        return "-".join(p.number_to_words(d) for d in digits)

    return re.sub(r'\d+', digit_by_digit, text)


def ship_lines(ships):
    """One compact line per ship. Single source of truth for ship status in prompts."""
    lines = []
    for cs, d in ships.items():
        lines.append(
            f"{cs} | {d.get('type', 'N/A')} | {d.get('status', 'Unknown')} | {d.get('location', 'Unknown')} | "
            f"mood: {d.get('mood', 'Neutral')} | faction: {d.get('faction', 'Unknown')} | job: {d.get('job', 'Unknown')} | {d.get('notes', '')}"
        )
    return "\n".join(lines)


def compact(d):
    """Render a dict as 'key: value, key: value' instead of Python repr punctuation."""
    return ", ".join(f"{k}: {v}" for k, v in d.items())
