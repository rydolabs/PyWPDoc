# Install

For **both** formats after PyPI publication:

```bash
python -m pip install "pywpdoc[unified]"
```

For **HWPX-only** creation/editing, after publication:

```bash
python -m pip install pywpdoc
```

At the review-candidate stage, install from the provided wheel or locally from the reviewed source checkout:

```bash
python -m pip install -e ".[unified]"
```

Requires **Python 3.10+**. The DOCX backend uses the optional `python-docx>=1.2,<2`; HWPX uses the package's own engine. Desktop Word/Hancom is **not required** to generate or edit files, but native rendering/COM validation requires the corresponding installed application.

[Quickstart →](quickstart.md) · [Compatibility →](../compatibility.md)
