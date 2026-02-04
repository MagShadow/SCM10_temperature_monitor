import re


def parse_temperature(response: str) -> float:
    """Parse a temperature reading from the SCM10 response string."""
    if response is None:
        raise ValueError("Empty response")
    text = response.strip()
    if not text:
        raise ValueError("Empty response")
    # Extract the first numeric token (supports scientific notation).
    match = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text)
    if not match:
        raise ValueError(f"No numeric value in response: {response!r}")
    return float(match.group(0))
