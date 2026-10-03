# UK Sanctions List Websites

An automatically maintained list of website URLs extracted from the **UK Sanctions List**, published by the UK Government.

The project provides a simple, machine-readable list that can be consumed by web filtering, secure web gateway, firewall, proxy, SIEM and other security platforms.

## Purpose

The UK Sanctions List contains information about individuals, organisations and entities subject to UK sanctions. Some records include associated websites.

While this information is available within the official UK Sanctions List datasets, the website indicators are embedded within the larger dataset and are not provided as a simple standalone feed.

This repository automatically extracts those website indicators and publishes them in a format that is easy to consume by security tools.

The repository is updated automatically from the official UK Sanctions List.

## Files

### `urls.txt`

Contains website URLs extracted from the UK Sanctions List.

One URL per line with no header or comments.

The extraction process performs limited cleanup to make the feed suitable for automated consumption, including:

- Removing unnecessary whitespace.
- Removing duplicate indicators.
- Extracting URLs from descriptive Website fields.
- Repairing clearly malformed HTTP/HTTPS prefixes where safe to do so.
- Preserving URL paths rather than expanding them to their root domain.

For example, a UK Sanctions List value such as:

```text
Social media: http://vk.com/sobolipress
