#!/usr/bin/env python3

"""
UK Sanctions List Website Extractor

Downloads the official UK Sanctions List XML from the FCDO and generates:

    urls.txt       Cleaned and de-duplicated website URLs extracted from UKSL
    invalid.txt    Website values that could not be safely parsed

Source:
https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml
"""

import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse


SOURCE_URL = (
    "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml"
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent

URLS_FILE = OUTPUT_DIR / "urls.txt"
INVALID_FILE = OUTPUT_DIR / "invalid.txt"


def download_xml() -> bytes:
    """Download the current UK Sanctions List XML."""

    print("Downloading UK Sanctions List:")
    print(f"  {SOURCE_URL}")

    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": (
                "uk-sanctions-list-websites/1.0 "
                "(GitHub automated sanctions feed)"
            )
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()

    except Exception as exc:
        print(f"ERROR: Failed to download sanctions list: {exc}")
        sys.exit(1)

    if not data:
        print("ERROR: Downloaded sanctions list is empty.")
        sys.exit(1)

    print(f"Downloaded {len(data):,} bytes.")

    return data


def clean_value(value: str) -> str:
    """Perform basic whitespace and quote cleanup."""

    value = value.strip()

    # Collapse accidental internal whitespace.
    value = re.sub(r"\s+", " ", value)

    # Remove surrounding quotes.
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in ("'", '"')
    ):
        value = value[1:-1].strip()

    return value


def split_website_field(value: str) -> list[str]:
    """
    Split fields where multiple website values are clearly present.

    We deliberately avoid aggressive splitting because URLs themselves
    may legitimately contain punctuation.
    """

    value = value.replace("\r\n", "\n").replace("\r", "\n")

    parts = re.split(
        r"""
        \n+
        |
        \s*[;,]\s*(?=(?:https?://|www\.))
        """,
        value,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    return [
        clean_value(part)
        for part in parts
        if clean_value(part)
    ]


def extract_website_values(xml_data: bytes) -> list[str]:
    """Extract every Website field from the UKSL XML."""

    try:
        root = ET.fromstring(xml_data)

    except ET.ParseError as exc:
        print(f"ERROR: Invalid XML returned by FCDO: {exc}")
        sys.exit(1)

    values = []

    for element in root.iter():

        # Namespace safe:
        # <Website> and <ns:Website>

        tag = element.tag.split("}")[-1]

        if tag.lower() != "website":
            continue

        if element.text is None:
            continue

        value = element.text.strip()

        if not value:
            continue

        values.extend(split_website_field(value))

    return values


def extract_url(value: str) -> str | None:
    """
    Extract a usable URL from a UKSL Website value.

    Examples:

        https://example.com
            -> https://example.com

        Official web site: http://soboli.net
            -> http://soboli.net

        Social Media: http://vk.com/example
            -> http://vk.com/example

        Company Name (example.com)
            -> example.com

        http:/example.com/
            -> http://example.com/
    """

    value = clean_value(value)

    if not value:
        return None

    # Values that clearly don't contain an indicator.
    if value.casefold() in {
        "unknown",
        "none",
        "n/a",
        "not known",
    }:
        return None

    # Repair an obvious malformed HTTP scheme:
    #
    # http:/example.com
    # ->
    # http://example.com

    value = re.sub(
        r"\b(https?):/(?!/)",
        r"\1://",
        value,
        flags=re.IGNORECASE,
    )

    # Extract HTTP/HTTPS URL from descriptive text.
    #
    # e.g.
    # "Official web site: http://example.com"

    match = re.search(
        r"https?://[^\s,;)\]]+",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        url = match.group(0)

        # Remove punctuation that is clearly surrounding prose.
        url = url.rstrip(".,;:")

        return url

    # Handle www.example.com style values.

    match = re.search(
        r"\bwww\.[a-z0-9][a-z0-9.-]*\.[a-z]{2,}"
        r"(?:/[^\s,;)\]]*)?",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(0).rstrip(".,;:")

    # Handle a bare domain contained in parentheses.
    #
    # Example:
    # Red Box Energy Services (redboxgroup.com)

    match = re.search(
        r"\b[a-z0-9][a-z0-9.-]*\.[a-z]{2,}\b"
        r"(?:/[^\s,;)\]]*)?",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(0).rstrip(".,;:")

    return None


def is_valid_url(value: str) -> bool:
    """
    Perform conservative validation.

    Bare domains are accepted because UKSL may publish website values
    without an explicit scheme.
    """

    candidate = value

    if not re.match(
        r"^https?://",
        candidate,
        flags=re.IGNORECASE,
    ):
        candidate = "https://" + candidate

    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False

    if not parsed.hostname:
        return False

    hostname = parsed.hostname.strip().rstrip(".")

    # Require a dot in the hostname.
    #
    # This deliberately rejects questionable source values such as:
    # http://www.izh-bs/ru

    if "." not in hostname:
        return False

    return True


def deduplicate(values: list[str]) -> list[str]:
    """
    De-duplicate indicators case-insensitively while preserving
    the first published representation.
    """

    unique = {}

    for value in values:
        key = value.casefold()

        if key not in unique:
            unique[key] = value

    return sorted(
        unique.values(),
        key=str.casefold,
    )


def write_text_file(path: Path, values: list[str]) -> None:
    """Write one value per line with no header."""

    content = ""

    if values:
        content = "\n".join(values) + "\n"

    path.write_text(
        content,
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:

    xml_data = download_xml()

    source_values = extract_website_values(xml_data)

    print()
    print(f"Website values found: {len(source_values):,}")

    # Safety check.
    #
    # Don't overwrite the existing feed if FCDO changes the XML
    # structure and we suddenly find no Website fields.

    if len(source_values) == 0:
        print()
        print("ERROR: No Website entries were found.")
        print("The UK Sanctions List XML structure may have changed.")
        print("Existing output files have NOT been overwritten.")
        sys.exit(1)

    urls = []
    invalid = []

    for source_value in source_values:

        extracted = extract_url(source_value)

        if extracted is None:
            invalid.append(source_value)
            continue

        if not is_valid_url(extracted):
            invalid.append(source_value)
            continue

        urls.append(extracted)

    urls = deduplicate(urls)
    invalid = deduplicate(invalid)

    # Additional safety check.
    #
    # Finding Website fields but producing zero valid URLs likely
    # indicates a parsing problem.

    if len(urls) == 0:
        print()
        print("ERROR: Website fields were found but no valid URLs")
        print("could be extracted.")
        print("Existing output files have NOT been overwritten.")
        sys.exit(1)

    write_text_file(
        URLS_FILE,
        urls,
    )

    write_text_file(
        INVALID_FILE,
        invalid,
    )

    print()
    print("Generated:")
    print(f"  urls.txt       {len(urls):,} unique URLs")
    print(f"  invalid.txt    {len(invalid):,} unparsed values")

    if invalid:
        print()
        print("WARNING: Some Website values could not be safely parsed.")
        print("Review invalid.txt.")

    print()
    print("Update complete.")


if __name__ == "__main__":
    main()
