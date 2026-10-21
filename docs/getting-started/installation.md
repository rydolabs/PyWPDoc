# Installation

## One command for Word DOCX and Hancom HWPX

**Version 0.44.0 and later:**

```bash
pip install pywpdoc
```

The default installation includes `lxml` and `python-docx` so both document formats work without an extra flag. The old `[unified]` extra remains accepted for existing scripts.

**Previously published prerelease `0.44.0rc1`:** its default dependencies are HWPX-only. To use DOCX on that older version, run `pip install "pywpdoc[unified]==0.44.0rc1"`. The `0.44.0` release has not been uploaded merely because this documentation changed.

Requires Python **3.10+**. Microsoft Word/Hancom are not necessary for generating or editing files in Python; native rendering and Office COM validation require the corresponding desktop software.

[Quickstart →](quickstart.md) · [Document API Reference →](../reference/document.md) · [Compatibility →](../compatibility.md)
