import re

def redact(text):
    text = re.sub(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", "[REDACTED NAME]", text)
    text = re.sub(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "[REDACTED IP]", text)
    text = re.sub(r"\S+@\S+", "[REDACTED EMAIL]", text)
    return text

