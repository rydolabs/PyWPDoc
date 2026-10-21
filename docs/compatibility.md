# Supported functionality — 0.44.0

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

**Important:** common *method names* do not mean identical XML structures or native editor rendering. The earlier 0.44.0rc1 candidate passed [focused Word/Hancom native acceptance](testing/native-qa-0440rc1-2026-10-18.md) (11/11 focused and 7/7 extended QA). A previous build supplied the 48/48 PDF-export evidence; the new candidate has not completed a fresh PDF/pixel-layout run.

[Limitations](limitations.md) · [API Reference](reference/document.md)
