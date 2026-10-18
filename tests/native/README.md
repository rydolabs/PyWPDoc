# Windows native validation

Run `RUN_WINDOWS.bat` from this folder **only on a Windows PC with licensed Word and Hancom Office installed**. It uses a project-root `.venv-native` and runs `tests/native/run_rc_windows.py` with COM (not an offline simulation). Results are written under `tests/native/HWP_RC_RESULTS/`.

For the more recent full **48-file business corpus including PDF and line-spacing/margin checks**, use `tests/generators/business_docs/RUN_WINDOWS_BUSINESS_QA.bat` or the separately distributed, validated one-click **v5 Hancom security module** QA kit. The new repository layout for the native shell entry points still needs execution on the user's Windows machine; local Linux tests cannot confirm Word/Hancom launches. These commands NEVER push to GitHub or publish PyPI.

Hancom may display file-access approval prompts. Do not automate GUI button clicking or weaken security settings; use the official trusted automation module setup workflow with explicit approval, as in v5 QA kit, where configured and supported. Do not bundle vendor DLLs in this repository.
