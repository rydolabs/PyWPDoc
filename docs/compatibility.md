# Supported functionality — 0.44.0rc1

| Feature | DOCX | HWPX | Contract status |
| --- | --- | --- | --- |
| New/open/save document | Yes | Yes | Common |
| Paragraphs / tables / properties | Yes | Yes | Common subset |
| Picture insertion (PNG, JPEG, GIF, BMP) | Yes for backend-recognized images | Yes for backend-recognized images | Common signature; size must be explicit for parity |
| Add section | Yes | Yes | Only `add_section()` portable |
| Literal search / preview / replacement | Supported cases | Supported cases | Common |
| Regex search/replacement | Supported safe cases | Supported safe cases | Common with restrictions |
| Template check / render | Supported cases | Supported cases | Common with restrictions |
| Tracked text comparison | Supported structures | Supported structures | Common with restrictions |
| Format-specific start/insert section | `start_type` | `after` | Format-specific |
| Generic file-format conversion | No universal guarantee | No universal guarantee | Unsupported as a generic converter |
| Word/Hancom pixel-identical pagination | Not guaranteed | Not guaranteed | Not a contract |

**Important:** common *method names* do not mean identical XML structures or native editor rendering. The 2026-10-18 historical Windows QA concerns a prior build. The reorganized release candidate must still complete its native Windows acceptance run.

[Limitations](limitations.md) · [API Reference](reference/document.md)
