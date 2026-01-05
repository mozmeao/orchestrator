# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv
import html
import io
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests
from django.core.management.base import BaseCommand


def parse_version(version_string: str) -> tuple[int | None, int | None]:
    """Parse version string into (major, minor) tuple."""
    if not version_string or not isinstance(version_string, str):
        return None, None

    version_string = version_string.rstrip(".")
    parts = version_string.split(".")

    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else None

    minor = None
    if len(parts) > 1:
        minor_match = re.match(r"^(\d+)", parts[1])
        if minor_match:
            minor = int(minor_match.group(1))
    elif len(parts) == 1 and major is not None:
        minor = 0

    return major, minor


def extract_version_from_url(url: str) -> str | None:
    """Extract version number from URL path."""
    match = re.search(r"/whatsnew/(\d+(?:\.\d+)*(?:\.\d+)?)/?", url)
    return match.group(1) if match else None


def clean_text(text: str) -> str:
    """Clean and normalize text by decoding HTML entities and normalizing whitespace."""
    if not text:
        return text
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_cta_pairs(html_content: str) -> list[tuple[str, str]]:
    """
    Extract CTA UID and text pairs from HTML content.

    Uses a simple two-step approach:
    1. Find all elements with data-cta-uid attribute
    2. Extract both attributes from each matched element

    Returns:
        List of (uid, text) tuples
    """
    element_pattern = r"<[^>]*data-cta-uid[^>]*>"
    elements = re.findall(element_pattern, html_content)

    cta_pairs = []
    for element in elements:
        uid_match = re.search(r'data-cta-uid\s*=\s*["\']([^"\']+)["\']', element)
        text_match = re.search(r'data-cta-text\s*=\s*["\']([^"\']+)["\']', element)

        if uid_match and text_match:
            cta_pairs.append((uid_match.group(1), clean_text(text_match.group(1))))

    return cta_pairs


def fetch_locale_data(
    base_url: str, locale: str, path: str
) -> tuple[str, list[tuple[str, str]]]:
    """Fetch and parse CTA data for a specific locale. Returns (url, cta_pairs)."""
    url = f"{base_url.rstrip('/')}/{locale}/{path.lstrip('/')}"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    sys.stdout.write(f"Fetched HTML for {locale} from {url}\n")

    cta_pairs = extract_cta_pairs(response.text)
    sys.stdout.write(f"Extracted {len(cta_pairs)} CTA pairs for {locale}\n")

    return url, cta_pairs


class CSVWriter:
    """Handles CSV writing operations for CTA data."""

    FIELDNAMES = [
        "create_date",
        "locale",
        "data_cta_uid",
        "major_version",
        "minor_version",
        "native_locale_text",
        "english_text",
    ]

    @classmethod
    def write_to_file(cls, rows: list[dict], filename: str) -> str:
        """Write rows to a CSV file, auto-incrementing filename if it exists."""
        base, ext = os.path.splitext(filename)
        counter = 1
        output_filename = filename

        while os.path.exists(output_filename):
            output_filename = f"{base}_{counter}{ext}"
            counter += 1

        with open(output_filename, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=cls.FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        return output_filename

    @classmethod
    def write_to_buffer(cls, rows: list[dict]) -> io.StringIO:
        """Write rows to a string buffer."""
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=cls.FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
        buffer.seek(0)
        return buffer


def cta_uid_parser(base_url: str, path: str, locales: list[str]) -> str:
    """
    Parse CTA UIDs from multiple locales and generate CSV output.

    Args:
        base_url: Base URL for fetching pages
        path: Path component to append to URL
        locales: List of locale codes to process

    Returns:
        Path to the generated CSV file
    """
    create_date = datetime.now(timezone.utc).isoformat()
    locale_data = {}
    locale_urls = {}
    for locale in locales:
        try:
            url, cta_pairs = fetch_locale_data(base_url, locale, path)
            locale_data[locale] = {uid: text for uid, text in cta_pairs}
            locale_urls[locale] = (url, cta_pairs)
        except requests.RequestException as e:
            sys.stdout.write(f"Error fetching {locale}: {e}\n")
        except Exception as e:
            sys.stdout.write(f"Unexpected error processing {locale}: {e}\n")

        time.sleep(1)
    english_data = locale_data.get("en-US", {})
    rows = []

    for locale, (url, cta_pairs) in locale_urls.items():
        version_string = extract_version_from_url(url)
        major_version, minor_version = (
            parse_version(version_string) if version_string else (None, None)
        )

        for uid, text in cta_pairs:
            rows.append(
                {
                    "create_date": create_date,
                    "locale": locale,
                    "data_cta_uid": uid,
                    "major_version": major_version,
                    "minor_version": minor_version,
                    "native_locale_text": text,
                    "english_text": english_data.get(uid),
                }
            )
    if rows:
        output_dir = os.path.join(os.path.dirname(__file__), "../../output")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "output.csv")

        output_path = CSVWriter.write_to_file(rows, output_file)
        sys.stdout.write(f"Wrote {len(rows)} rows to {output_path}\n")
        return output_path

    sys.stdout.write("No data to write\n")
    return None


class Command(BaseCommand):
    help = "Parses CTA UIDs from HTML and writes to CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url", required=True, help="Base URL for fetching data"
        )
        parser.add_argument("--path", required=True, help="Path to fetch")
        parser.add_argument(
            "--locales",
            required=True,
            help="Comma-separated list of locales (e.g. en-US,fr)",
        )

    def handle(self, *args, **options):
        base_url = options["base_url"]
        path = options["path"]
        locales = [loc.strip() for loc in options["locales"].split(",") if loc.strip()]

        output_file = cta_uid_parser(base_url, path, locales)

        if output_file:
            self.stdout.write(self.style.SUCCESS(f"Output saved to {output_file}"))
        else:
            self.stdout.write(self.style.WARNING("No output generated"))
