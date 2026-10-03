# UK Sanctions List Websites

An automatically maintained list of website URLs extracted from the **UK Sanctions List**, published by the UK Government.

The project provides a simple, machine-readable list of website indicators that can be consumed by web filtering, secure web gateway, firewall, proxy, SIEM and other security platforms.

## Purpose

The UK Sanctions List contains information about individuals, organisations and entities subject to UK sanctions. Some records include associated websites.

While this information is available within the official UK Sanctions List datasets, the website indicators are embedded within the larger dataset and are not provided as a simple standalone feed.

This repository automatically extracts those website indicators and publishes them in a format that is easy to consume by security tools.

The repository is updated automatically from the official UK Sanctions List.

## Files

### `urls.txt`

Contains website URLs extracted from the UK Sanctions List.

The file contains **one URL per line with no header or comments**, making it suitable for automated ingestion.

The extraction process performs limited and conservative cleanup, including:

- Removing unnecessary whitespace
- Removing duplicate indicators
- Extracting URLs from descriptive Website fields
- Repairing clearly malformed HTTP/HTTPS prefixes where safe to do so
- Preserving URL paths
- Preserving specific pages and profiles rather than expanding them to their root domain

For example, a UK Sanctions List Website value such as:

```text
Social media: http://vk.com/sobolipress
```

is published in `urls.txt` as:

```text
http://vk.com/sobolipress
```

The feed deliberately does **not** convert this into:

```text
vk.com
```

Doing so could result in an entire shared or social-media platform being blocked when the UK Sanctions List identifies only a specific page or profile.

### `invalid.txt`

Contains Website values from the source data that could not be safely converted into a usable URL.

These entries are retained for review rather than being silently discarded or automatically corrected based on assumptions.

This also provides a simple way to identify changes in the formatting or structure of Website data published in the UK Sanctions List.

## Automated Updates

A GitHub Action runs daily and downloads the latest official UK Sanctions List XML.

The update process:

1. Downloads the latest official UK Sanctions List XML.
2. Extracts all Website entries.
3. Performs conservative formatting cleanup.
4. Extracts usable website URLs.
5. Removes duplicate indicators.
6. Records values that cannot be safely parsed in `invalid.txt`.
7. Compares the generated files with the versions currently in the repository.
8. Commits and pushes an update only when the resulting data has changed.

The workflow can also be manually triggered from the GitHub Actions interface.

This allows `urls.txt` to act as an automatically maintained security feed.

## Using the List

`urls.txt` is deliberately provided as a simple text file containing:

```text
one-indicator-per-line
```

There are no headers, comments or additional metadata within the file.

This makes it suitable for ingestion into systems such as:

- Web filtering platforms
- Secure Web Gateways (SWG)
- Firewalls
- Proxy servers
- SIEM platforms
- SOAR platforms
- Threat intelligence platforms
- URL blocklists
- Custom security tooling

Consumers should determine the appropriate filtering and enforcement policy for their own environment.

## Why Root Domains Are Not Included

This project deliberately does **not** generate a root-domain blocklist.

Some Website indicators in the UK Sanctions List point to individual pages, profiles or resources hosted on shared platforms.

For example:

```text
http://vk.com/sobolipress
```

Automatically converting this indicator to:

```text
vk.com
```

would significantly broaden the scope of the original indicator.

A security product consuming such a domain list could consequently block the entire `vk.com` domain rather than the specific resource identified in the UK Sanctions List.

The same issue can occur with:

- Social-media platforms
- Shared hosting providers
- Blogging platforms
- Cloud services
- Content hosting services
- Other multi-tenant platforms

This project therefore remains as close as practical to the Website indicators published in the source data and does not automatically broaden their scope.

## Conservative Parsing

The parser deliberately avoids guessing when a Website value is ambiguous or malformed.

Where a URL can be safely identified within descriptive text, it is extracted.

For example:

```text
Official web site: http://example.com
```

becomes:

```text
http://example.com
```

Likewise:

```text
Social Media: http://example.com/profile
```

becomes:

```text
http://example.com/profile
```

Clearly identifiable formatting problems may also be corrected where the intended URL is unambiguous.

Values that cannot be safely interpreted are written to:

```text
invalid.txt
```

rather than attempting to guess the intended website.

## Data Source

The source data is the **UK Sanctions List**, published by the UK Government.

Official source:

https://www.gov.uk/government/publications/the-uk-sanctions-list

The automated parser retrieves the XML version of the UK Sanctions List from:

https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml

The official UK Sanctions List remains the authoritative source.

## Disclaimer

This repository is an independent project and is **not affiliated with, endorsed by, or operated by the UK Government or the Foreign, Commonwealth & Development Office (FCDO).**

The presence of a URL in this repository means that it was derived from a Website value contained within the UK Sanctions List.

It does **not necessarily mean that every resource, service, hostname, domain or piece of content associated with that URL is itself sanctioned**.

In particular, Website fields may identify specific pages or profiles hosted by third-party or shared platforms.

Organisations consuming this data should assess the indicators and determine the appropriate filtering and enforcement policy for their environment.

This repository should not be treated as legal advice or as a replacement for:

- Sanctions compliance processes
- Appropriate due diligence
- Risk assessment
- Legal advice
- Consultation of the official UK Sanctions List

Always refer to the official UK Sanctions List when determining the current sanctions status of an individual, organisation or entity.

## Reliability

The update script includes safeguards intended to prevent an unexpected change to the UK Sanctions List XML format from replacing the existing feed with an empty list.

Website values that cannot be safely parsed are retained in `invalid.txt` so that unusual or newly introduced formatting can be reviewed.

Consumers of this repository should nevertheless implement appropriate validation and change-control processes before automatically enforcing externally maintained indicator lists.

## Licence

The source sanctions data is published by the UK Government.

Users should review the applicable copyright, licensing and reuse terms associated with the original UK Sanctions List.

Scripts and other original code contained within this repository are subject to the licence specified by this repository.

## Contributions

Issues and pull requests relating to:

- Website parsing
- Automation
- Feed reliability
- Security platform compatibility
- Documentation
- Other technical improvements

are welcome.

Changes or corrections to the sanctions information itself should be directed to the appropriate UK Government authority.

This repository only processes information published by the official UK Sanctions List and does not independently determine which individuals, organisations, entities or websites should be subject to sanctions.
