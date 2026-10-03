# UK Sanctions List Websites

An automatically maintained collection of website URLs and domains extracted from the **UK Sanctions List**, published by the UK Government.

The project provides simple, machine-readable indicator lists that can be consumed by web filtering, DNS filtering, firewall, proxy, SIEM and other security platforms.

## Purpose

The UK Sanctions List contains information about individuals, organisations and entities subject to UK sanctions. Some records include associated websites.

While this information is available within the official UK Sanctions List datasets, the website indicators are embedded within the larger dataset and are not provided as a simple standalone feed.

This repository automatically extracts those website indicators and publishes them in formats that are easy to consume by security tools.

The repository is updated automatically from the official UK Sanctions List.

## Files

### `urls.txt`

Contains the website values extracted from the UK Sanctions List.

One URL per line.

Example:

```text
https://www.example.com
http://example.org/page
https://subdomain.example.co.uk
```

This list is intended for systems capable of matching or filtering specific URLs.

### `domains.txt`

Contains unique root/registrable domains derived from the website indicators.

One domain per line.

For example:

```text
example.com
example.org
example.co.uk
```

A source value such as:

```text
https://portal.subdomain.example.co.uk/path
```

would result in:

```text
example.co.uk
```

This list is intended for systems performing domain-level filtering, DNS filtering or threat-indicator matching.

### `mappings.csv`

Provides traceability between the website value contained in the UK Sanctions List and the root domain derived from it.

Example:

```csv
source_url,root_domain
https://portal.example.co.uk/path,example.co.uk
https://www.example.com,example.com
```

### `invalid.txt`

Contains any website values encountered in the source data that could not be safely parsed.

These entries are retained rather than silently discarded so that parsing problems or unusual data can be reviewed.

## Automated Updates

A GitHub Action periodically downloads the latest UK Sanctions List and processes its website fields.

The update process:

1. Downloads the latest official UK Sanctions List.
2. Extracts website entries.
3. Removes duplicate entries.
4. Generates the exact URL list.
5. Derives and de-duplicates root domains.
6. Generates the URL-to-domain mapping.
7. Records values that could not be parsed.
8. Commits the generated files only when the resulting data has changed.

This allows the raw files in this repository to be used as automatically maintained feeds.

## Using the Lists

The lists are deliberately provided as simple text files with **one indicator per line** and no headers or comments.

This makes them suitable for ingestion into systems such as:

- Web filtering platforms
- Secure web gateways
- DNS filtering systems
- Firewalls
- Proxy servers
- SIEM platforms
- SOAR platforms
- Threat intelligence systems
- Custom security tooling

Consumers should determine whether URL-level or domain-level blocking is appropriate for their environment.

## Data Source

The source data is the **UK Sanctions List**, published by the UK Government.

This repository is an independent project and is **not affiliated with, endorsed by, or operated by the UK Government or the Foreign, Commonwealth & Development Office (FCDO).**

The official UK Sanctions List remains the authoritative source.

## Important Notice

The presence of a URL or domain in this repository means that it was derived from a website value contained within the UK Sanctions List.

It does **not necessarily mean that every resource, service, hostname or piece of content associated with that domain is itself sanctioned**.

Domain-level blocking can have a substantially broader effect than blocking a specific URL. Organisations should assess the indicators and determine the appropriate filtering policy for their environment.

This repository should not be treated as legal advice or as a replacement for sanctions compliance processes, appropriate due diligence, or consultation of the official UK Sanctions List.

## Licence

The source sanctions data is published by the UK Government. Users should review the applicable terms and licensing associated with the original UK Sanctions List.

Any scripts and original code contained within this repository may be licensed separately under the repository's stated software licence.

## Contributions

Issues and pull requests relating to parsing, automation, compatibility with security platforms, or other technical improvements are welcome.

Changes to sanctions information itself should be directed to the appropriate UK Government authority, as this repository only processes the official source data.
