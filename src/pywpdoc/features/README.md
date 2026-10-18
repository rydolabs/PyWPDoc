# PyWPDoc feature modules

High-level functions grow horizontally as independent feature modules.

Dependency direction:

```text
feature -> core contracts / reusable primitives <- backend
```

Forbidden by architecture tests:

- feature -> `pywpdoc._engine.hwpx`
- feature -> `pywpdoc._engine.docx`
- feature -> `pywpdoc.hwpx`
- feature -> `pywpdoc.docx`
- feature -> `docx` / `docx.oxml`
- feature -> sibling feature package

## Implemented

- `find`: literal document search using backend-neutral text primitives.
- `replace`: structure-preserving literal replacement and read-only candidate preview,
  using the same lower-level literal matcher; previews serialize to JSON.
- `template`: logicless variables, opt-in inline sections, and opt-in
  structure-preserving table-row repetition. Structural repetition uses only
  an opaque backend row clone/insert/remove capability.
- `compare`: conservative same-structure tracked text comparison with
  backend-neutral revision planning and backend-local native revision writers.

## Structural template boundary

`template/structure` owns only section syntax, collection/context semantics,
repeat planning, ordering, and rendering cloned row text. It does not import a
concrete HWPX/DOCX implementation. Native row style, cell merge geometry,
height, borders, nested content, media references, and object identities remain
backend responsibilities.

## Planned

- paragraph/block structural repetition
- tracked structural row insertion/deletion
- image replacement
- validation
- richer diff / merge

Large user-facing features may be composed from smaller internal modules, but
feature packages should not form a dependency chain. Shared behavior needed by
multiple features must be extracted downward into a smaller core primitive.
