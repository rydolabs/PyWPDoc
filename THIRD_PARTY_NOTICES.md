# Third-party license notes

PyWPDoc is licensed under MIT (see `LICENSE`). The following packages are resolved and installed separately by Python packaging tools; their source distributions and copyright notices remain governed by their own licenses. No third-party code is intentionally bundled into the PyWPDoc wheel.

| Package | Used for | Upstream license | Reference |
| --- | --- | --- | --- |
| `lxml` | Base XML processing dependency | BSD-3-Clause | https://github.com/lxml/lxml/blob/master/LICENSES.txt |
| `python-docx` | Optional DOCX backend (`pywpdoc[unified]`) | MIT | https://github.com/python-openxml/python-docx/blob/master/LICENSE |
| `typing_extensions` | Transitive dependency of python-docx (if installed) | PSF | https://github.com/python/typing_extensions/blob/main/LICENSE |

`lxml` also integrates libxml2 and libxslt and may include platform-specific native library notices. Verify licenses of vendored binaries separately if distributing a fully bundled standalone executable rather than installing wheels from PyPI.

The table is explanatory, not a replacement for each upstream package's own notice.
