"""String helpers."""

SMALL = {"a", "an", "and", "of", "the", "to"}


def is_palindrome(s: str) -> bool:
    """True if s reads the same backwards, ignoring case and spaces."""
    s = s.replace(" ", "").lower()
    return s == s[::-1]


def truncate(s: str, width: int) -> str:
    """Cut s to at most `width` characters, ending with '…' when cut."""
    if len(s) <= width:
        return s
    return s[: width - 1] + "…"


def word_count(s: str) -> int:
    """Number of whitespace-separated words."""
    return len(s.split())


def slugify(s: str) -> str:
    """Lowercase, spaces to '-', drop everything except letters, digits and '-'."""
    s = s.strip().lower().replace(" ", "-")
    return "".join(c for c in s if c.isalnum() or c == "-")


def title_case(s: str) -> str:
    """Capitalise words, except small words after the first."""
    out = []
    for i, w in enumerate(s.lower().split()):
        if i > 0 and w in SMALL:
            out.append(w)
        else:
            out.append(w.capitalize())
    return " ".join(out)
