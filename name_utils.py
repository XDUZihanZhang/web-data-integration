import re
import unicodedata
from typing import Optional


def _decode_literal_hex_sequences(text: str) -> str:
    """
    Decode literal backslash-x hex sequences (e.g. \"\\xc3\\xa1\") into
    their UTF-8 characters.
    This operates on the *literal* backslash characters as they appear in
    the data, not on Python string escapes.
    """
    if not isinstance(text, str):
        return ""

    def decode_sequence(match: re.Match) -> str:
        # Match groups are pairs (or triplets) of hex bytes
        hex_bytes = []
        for i in range(1, len(match.groups()) + 1):
            try:
                hex_bytes.append(int(match.group(i), 16))
            except ValueError:
                # If anything goes wrong, fall back to the original substring
                return match.group(0)
        try:
            return bytes(hex_bytes).decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            return match.group(0)

    # First handle 2- and 3-byte UTF-8 sequences, then single bytes
    text = re.sub(r"\\x([0-9a-fA-F]{2})\\x([0-9a-fA-F]{2})\\x([0-9a-fA-F]{2})", decode_sequence, text)
    text = re.sub(r"\\x([0-9a-fA-F]{2})\\x([0-9a-fA-F]{2})", decode_sequence, text)

    def decode_single(match: re.Match) -> str:
        try:
            return chr(int(match.group(1), 16))
        except (ValueError, OverflowError):
            return match.group(0)

    text = re.sub(r"\\x([0-9a-fA-F]{2})", decode_single, text)
    return text


def _strip_accents(text: str) -> str:
    """Remove diacritical marks (accents) from a Unicode string."""
    if not isinstance(text, str):
        return ""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _strip_suffixes(text: str) -> str:
    """
    Remove common name suffix tokens such as Jr, Sr, II, III, IV, V.
    Operates on a lowercase, space-normalized string.
    """
    if not isinstance(text, str):
        return ""
    suffix_tokens = {"jr", "sr", "ii", "iii", "iv", "v"}
    tokens = [tok for tok in text.split() if tok not in suffix_tokens]
    return " ".join(tokens)


def normalize_name_for_blocking(text: Optional[str]) -> str:
    """
    Canonical name normalization used for all blocking and matching.

    Steps:
    1) Decode literal \"\\xHH\" hex sequences into UTF-8 characters.
    2) Unicode-normalize (NFD) and strip accents.
    3) Lowercase and trim.
    4) Remove backslashes and standardize punctuation:
       - remove periods and commas
       - replace hyphens with spaces
       - remove apostrophes
    5) Collapse multiple spaces into a single space.
    6) Remove common suffix tokens (jr, sr, ii, iii, iv, v).

    The function is idempotent and safe on non-string inputs.
    """
    if not isinstance(text, str):
        return ""

    # Step 1: decode literal hex sequences
    text = _decode_literal_hex_sequences(text)

    # Step 2: strip accents
    text = _strip_accents(text)

    # Step 3: lowercase and strip
    text = text.lower().strip()

    # Step 4: handle backslashes and punctuation
    text = text.replace("\\ ", " ")
    text = text.replace("\\", " ")
    text = text.replace(".", "")
    text = text.replace(",", "")
    text = text.replace("-", " ")
    text = text.replace("'", "")

    # Step 5: normalize whitespace
    text = re.sub(r"\\s+", " ", text).strip()

    # Step 6: remove common suffixes
    text = _strip_suffixes(text)

    # Final whitespace cleanup
    text = re.sub(r"\\s+", " ", text).strip()
    return text


