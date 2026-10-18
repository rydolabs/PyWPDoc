# Pictures and sections

## Picture insertion — common size when specified

The **same call** supports both formats; the Common facade recognizes PNG, JPEG, GIF, and BMP file signatures when `image_format` is omitted. Supply `image_format` for unrecognized bytes (the backend may still reject unsupported formats).

```python
--8<-- "examples/manual/pictures.py"
```

Run: `python examples/manual/pictures.py docx ./output` (or `hwpx`). `width` and `height` accept `pywpdoc.Mm` or HWP units. For predictable cross-format physical sizes, **always specify `width` and `height`**. If `width=None`, DOCX uses intrinsic image size while HWPX retains its native default of 14400 HWP units (2 inches). DOCX currently supports **inline pictures only** (`treat_as_char=False` is rejected).

Unknown binary image signatures without explicit `image_format` raise `DocumentValueError(code="common-image-format-unknown")` **before modifying the document**.

## Sections — portable subset

```python
--8<-- "examples/manual/sections.py"
```

The portable contract is `doc.add_section()` **without options**. DOCX has `start_type`, while HWPX has `after`; neither is accepted by the portable method. Use the matching [format-specific API](../reference/formats.md) when such controls are required. Resulting page layout and section-start pagination can differ.
