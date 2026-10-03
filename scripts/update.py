#!/usr/bin/env python3

"""
UK Sanctions List Website Extractor

Downloads the official UK Sanctions List XML from the FCDO and generates:

    urls.txt       Cleaned and de-duplicated website URLs extracted from UKSL
    invalid.txt    Website values that could not be safely parsed or validated

Source:
https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml
"""

import ipaddress
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
    """
    Perform basic whitespace and quote cleanup.

    This intentionally performs only conservative cleanup so that the
    resulting indicator remains as close as possible to the value
    published by the UK Sanctions List.
    """

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
    Split Website fields containing multiple indicators.

    Handles:
        - New lines
        - Pipe separators
        - Semicolon/comma separators where another obvious URL follows

    Example:

        https://one.example|https://two.example

    becomes:

        https://one.example
        https://two.example
    """

    value = value.replace("\r\n", "\n").replace("\r", "\n")

    parts = re.split(
        r"""
        \n+
        |
        \s*\|\s*
        |
        \s*[;,]\s*(?=(?:https?://|www\.))
        """,
        value,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    cleaned = []

    for part in parts:
        part = clean_value(part)

        if part:
            cleaned.append(part)

    return cleaned


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
        #
        # <Website>
        #
        # and:
        #
        # <ns:Website>

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
    Extract a usable URL/domain from a UKSL Website value.

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

    # Repair an obvious malformed HTTP/HTTPS scheme:
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
    # Example:
    #
    # Official web site: http://example.com

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
        r"\bwww\.[^\s,;)\]]+",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(0).rstrip(".,;:")

    # Handle bare domain names.
    #
    # This also catches domains embedded in descriptive text such as:
    #
    # Red Box Energy Services (redboxgroup.com)
    #
    # Validation happens later, so merely matching here does not mean
    # that the value will be accepted.

    match = re.search(
        r"\b[a-zA-Z0-9\u0080-\uffff]"
        r"[a-zA-Z0-9\u0080-\uffff.-]*"
        r"\.[a-zA-Z\u0080-\uffff]{2,}"
        r"(?:/[^\s,;)\]]*)?",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(0).rstrip(".,;:")

    return None


def validate_hostname(hostname: str) -> bool:
    """
    Validate a hostname conservatively.

    Requirements:

        - Must be convertible to IDNA/Punycode
        - Must not exceed DNS hostname limits
        - Must contain at least one dot
        - Must contain a plausible TLD
        - Individual DNS labels must be valid
        - Labels cannot start or end with a hyphen

    Examples rejected:

        www.izh-bs
        www.farhang
        www.sbu
        example..com
        -example.com
        example-.com

    Internationalised domains are supported through IDNA conversion.
    """

    hostname = hostname.strip().rstrip(".")

    if not hostname:
        return False

    # Literal IP addresses are valid indicators.

    try:
        ipaddress.ip_address(hostname)
        return True

    except ValueError:
        pass

    # Convert internationalised domains to their ASCII/Punycode
    # representation for DNS validation.
    #
    # Example:
    #
    # дом.рф
    # ->
    # xn--d1aqf.xn--p1ai

    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")

    except UnicodeError:
        return False

    ascii_hostname = ascii_hostname.lower()

    # DNS hostname maximum length.

    if len(ascii_hostname) > 253:
        return False

    # A domain must contain at least one dot.

    if "." not in ascii_hostname:
        return False

    labels = ascii_hostname.split(".")

    # Empty labels indicate malformed domains such as:
    #
    # example..com

    if any(not label for label in labels):
        return False

    # Validate each DNS label.

    for label in labels:

        if len(label) > 63:
            return False

        # DNS labels may contain letters, numbers and hyphens.

        if not re.fullmatch(
            r"[a-z0-9-]+",
            label,
            flags=re.IGNORECASE,
        ):
            return False

        # Labels cannot begin or end with a hyphen.

        if label.startswith("-") or label.endswith("-"):
            return False

    # Validate the final component / TLD.
    #
    # Accept:
    #
    # com
    # co.uk -> final label "uk"
    # рф     -> xn--p1ai
    #
    # Reject things such as:
    #
    # www.izh-bs

    tld = labels[-1]

    if tld.startswith("xn--"):

        # IDN TLD.
        if len(tld) <= 4:
            return False

    else:

        # Normal TLDs should contain letters only and be at least
        # two characters long.

        if not re.fullmatch(
            r"[a-z]{2,63}",
            tld,
            flags=re.IGNORECASE,
        ):
            return False

    return True


def is_valid_url(value: str) -> bool:
    """
    Validate an extracted URL/domain.

    UKSL contains both full URLs and bare domain names, so bare domains
    are accepted when their hostname passes validation.
    """

    candidate = value.strip()

    if not candidate:
        return False

    # Bare domains are temporarily given a scheme so urlparse can
    # reliably determine the hostname.

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

    # Only accept HTTP and HTTPS.

    if parsed.scheme.lower() not in {
        "http",
        "https",
    }:
        return False

    return validate_hostname(parsed.hostname)


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


def write_text_file(
    path: Path,
    values: list[str],
) -> None:
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

        # Nothing usable could be extracted.

        if extracted is None:
            invalid.append(source_value)
            continue

        # Something URL-like was extracted but the hostname does not
        # pass conservative validation.

        if not is_valid_url(extracted):
            invalid.append(source_value)
            continue

        urls.append(extracted)

    # Remove duplicates and provide deterministic ordering so GitHub
    # commits only occur when the actual data changes.

    urls = deduplicate(urls)
    invalid = deduplicate(invalid)

    # Additional safety check.
    #
    # Finding Website fields but producing zero valid URLs likely
    # indicates a parsing or source-data problem.

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
    print(f"  invalid.txt    {len(invalid):,} unparsed/invalid values")

    if invalid:

        print()
        print(
            "WARNING: Some Website values could not be safely "
            "parsed or validated."
        )
        print("Review invalid.txt.")

    print()
    print("Update complete.")


if __name__ == "__main__":
    main()
