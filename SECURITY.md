# Security

## What the skill runs

The skill is instructions plus one local Python program, `scripts/concept.py`. When an agent uses
it, the program:

- reads the `design.json` file it is given and the files in the skill's `assets/` folder,
- writes outputs under the chosen output folder (by default `output/` next to `design.json`),
- with `--renders` only, starts a local Chrome, Edge or Chromium in headless mode to take
  screenshots of the generated `index.html` from the local disk.

It makes no network requests, collects no telemetry, and needs no credentials or API keys. The
generated 3D page is self-contained; three.js is inlined from the bundled copy, and the page
loads nothing from the internet.

Dependencies: `ezdxf` and `PyMuPDF` from PyPI, plus optionally `arabic-reshaper` and
`python-bidi` for right-to-left labels.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting (the **Security** tab, then **Report a
vulnerability**) rather than a public issue. You can expect an acknowledgement within a week.
