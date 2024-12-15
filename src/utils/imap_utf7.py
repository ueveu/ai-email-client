def encode_utf7(text: str) -> str:
    """Encode a string to IMAP UTF-7."""
    return text.encode('utf-7').decode('ascii').replace('/', ',')


def decode_utf7(text: str) -> str:
    """Decode a string from IMAP UTF-7."""
    return text.replace(',', '/').encode('ascii').decode('utf-7') 