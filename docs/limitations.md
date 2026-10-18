# Limitations and explicit failure behavior

- **Not HWP binary.** PyWPDoc supports `.hwpx`, not classic binary `.hwp`.
- **Not a universal format converter.** `Document.rebuild()` does not provide general DOCX ↔ HWPX fidelity. DOCX → HWPX rebuild explicitly rejects unsupported snapshot import.
- **Different native rendering.** Word and Hancom may paginate and wrap differently. Previous QA narrowed some spacing differences but did not promise pixel-level equivalence.
- **Picture defaults differ.** Set `width=Mm(...)` and ideally `height=Mm(...)` on portable calls. DOCX supports only inline body picture insertion through this backend API.
- **Section options differ.** The portable common method is `add_section()` with no options; expert section controls are not portable.
- **Compare rejects unsupported structural changes.** Some table moves, paragraph insertions/deletions, unsupported tracked revisions, and ambiguous structure changes are rejected.
- **Unsafe text boundaries.** Search/replace and templates have deliberate protections around native fields, revisions and invalid patterns.
- **No guarantee for passthrough methods.** `Document.__getattr__` exposes backend names for advanced use. Refer only to the [Document reference](reference/document.md) for the portable contract.
- **Proposed, not implemented.** `fill`, `validate`, `merge`, `diff`, `replace_image`, `accept_changes`, and other names in internal design notes are **not** guaranteed public APIs.

Use `DocumentUnsupportedError` and other documented errors to detect unsupported operations, rather than silently ignoring them.
