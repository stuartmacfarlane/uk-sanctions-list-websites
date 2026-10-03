#!/usr/bin/env python3

"""
UK Sanctions List Website Extractor

Downloads the official UK Sanctions List XML from the FCDO and generates:

    urls.txt       Exact website values from the UK Sanctions List
    domains.txt    Unique registrable/root domains
    mappings.csv   Mapping between source website and derived domain
    invalid.txt    Website values that could not be safely parsed

Source:
https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml
"""

import csv
import ipaddress
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import tldextract


SOURCE_URL = (
    "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml"
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent

URLS_FILE = OUTPUT_DIR / "urls.txt"
DOMAINS_FILE = OUTPUT_DIR / "domains.txt"
MAPPINGS_FILE = OUTPUT_DIR / "mappings.csv"
INVALID_FILE = OUTPUT_DIR / "invalid.txt"


# Use the bundled Public Suffix List snapshot supplied by tldextract.
# This avoids downloading the PSL during every GitHub Action run.
extractor = tldextract.TLDExtract(suffix_list_urls=())


def download_xml() -> bytes:
    """Download the current UK Sanctions List XML."""

    print(f"Downloading UK Sanctions List:")
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
    """Perform minimal cleanup while preserving the published value."""

    value = value.strip()

    # Remove surrounding quotes if present.
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in ("'", '"')
    ):
        value = value[1:-1].strip()

    return value


def split_website_field(value: str) -> list[str]:
    """
    Split website fields where multiple websites are clearly present.

    New lines and common separators are supported.

    We deliberately avoid aggressive splitting because URLs themselves
    can legitimately contain punctuation.
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

    cleaned = []

    for part in parts:
        part = clean_value(part)

        if part:
            cleaned.append(part)

    return cleaned


def extract_websites(xml_data: bytes) -> list[str]:
    """Extract every Website field from the XML."""

    try:
        root = ET.fromstring(xml_data)

    except ET.ParseError as exc:
        print(f"ERROR: Invalid XML returned by FCDO: {exc}")
        sys.exit(1)

    websites = []

    for element in root.iter():

        # Handles both:
        #
        # <Website>
        #
        # and namespaced forms such as:
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

        websites.extend(split_website_field(value))

    # De-duplicate exact values.
    #
    # Case is preserved in urls.txt but duplicate comparison
    # is case-insensitive.

    unique = {}

    for website in websites:
        key = website.casefold()

        if key not in unique:
            unique[key] = website

    return sorted(
        unique.values(),
        key=str.casefold,
    )


def prepare_for_parsing(value: str) -> str:
    """
    Add a scheme when required so urllib can correctly identify
    the hostname.

    The original value is NOT modified in urls.txt.
    """

    value = value.strip()

    if value.startswith("//"):
        return "https:" + value

    if not re.match(
        r"^[a-z][a-z0-9+.-]*://",
        value,
        flags=re.IGNORECASE,
    ):
        return "https://" + value

    return value


def derive_domain(value: str) -> str | None:
    """
    Derive a registrable/root domain from a website value.

    Examples:

        https://www.example.com/path
            -> example.com

        portal.example.co.uk
            -> example.co.uk

        https://sub.domain.example.org/login
            -> example.org
    """

    candidate = prepare_for_parsing(value)

    try:
        parsed = urlparse(candidate)

    except ValueError:
        return None

    hostname = parsed.hostname

    if not hostname:
        return None

    hostname = hostname.strip().rstrip(".").lower()

    if not hostname:
        return None

    # Handle literal IP addresses separately.
    #
    # An IP does not have a registrable domain, but it is still
    # useful as a filtering indicator.

    try:
        ip = ipaddress.ip_address(hostname)
        return str(ip)

    except ValueError:
        pass

    # Convert Unicode IDNs to ASCII/Punycode so the output is
    # consistent for security tooling.

    try:
        hostname = hostname.encode("idna").decode("ascii")

    except UnicodeError:
        return None

    extracted = extractor(hostname)

    # registered_domain/domain+suffix
    #
    # example.co.uk
    # example.com
    # example.org

    if extracted.domain and extracted.suffix:
        return f"{extracted.domain}.{extracted.suffix}".lower()

    # If there is no recognised public suffix, do not guess.
    return None


def write_text_file(path: Path, values: list[str]) -> None:
    """Write one value per line."""

    content = ""

    if values:
        content = "\n".join(values) + "\n"

    path.write_text(
        content,
        encoding="utf-8",
        newline="\n",
    )


def write_mapping_file(
    path: Path,
    mappings: list[tuple[str, str]],
) -> None:
    """Write source URL -> root domain mappings."""

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.writer(
            handle,
            lineterminator="\n",
        )

        writer.writerow(
            [
                "source_url",
                "root_domain",
            ]
        )

        for source_url, root_domain in mappings:
            writer.writerow(
                [
                    source_url,
                    root_domain,
                ]
            )


def main() -> None:

    xml_data = download_xml()

    urls = extract_websites(xml_data)

    print()
    print(f"Website indicators found: {len(urls):,}")

    mappings = []
    invalid = []
    domains = set()

    for source_url in urls:

        domain = derive_domain(source_url)

        if domain is None:
            invalid.append(source_url)
            continue

        domains.add(domain)

        mappings.append(
            (
                source_url,
                domain,
            )
        )

    domains = sorted(
        domains,
        key=str.casefold,
    )

    mappings.sort(
        key=lambda item: (
            item[1].casefold(),
            item[0].casefold(),
        )
    )

    invalid.sort(
        key=str.casefold,
    )

    # Safety check.
    #
    # If FCDO unexpectedly changes the XML structure and we suddenly
    # find zero websites, fail the Action instead of committing an
    # empty blocklist over the previous valid data.

    if len(urls) == 0:
        print()
        print("ERROR: No Website entries were found.")
        print("The UK Sanctions List XML structure may have changed.")
        print("Existing output files have NOT been overwritten.")
        sys.exit(1)

    write_text_file(
        URLS_FILE,
        urls,
    )

    write_text_file(
        DOMAINS_FILE,
        domains,
    )

    write_mapping_file(
        MAPPINGS_FILE,
        mappings,
    )

    write_text_file(
        INVALID_FILE,
        invalid,
    )

    print()
    print("Generated:")
    print(f"  urls.txt       {len(urls):,} indicators")
    print(f"  domains.txt    {len(domains):,} indicators")
    print(f"  mappings.csv   {len(mappings):,} mappings")
    print(f"  invalid.txt    {len(invalid):,} unparsed values")

    if invalid:
        print()
        print("WARNING: Some website values could not be parsed.")
        print("Review invalid.txt.")

    print()
    print("Update complete.")


if __name__ == "__main__":
    main()
