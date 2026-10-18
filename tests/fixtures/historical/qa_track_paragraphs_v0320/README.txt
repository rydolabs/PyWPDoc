PyWPDoc v0.32.0 paragraph Track Changes QA

DOCX:
- paragraph_old_v0320.docx
- paragraph_new_v0320.docx
- paragraph_tracked_review_v0320.docx

HWPX:
- paragraph_old_v0320.hwpx
- paragraph_new_v0320.hwpx
- paragraph_tracked_review_v0320.hwpx

Expected review semantics:
- DELETE THIS PARAGRAPH is a whole-paragraph deletion.
- INSERTED PARAGRAPH is a whole-paragraph insertion.
- B - old value -> B - updated value is an inline revision.
- The table stays in the same structural position.
- Accept All => new; Reject All => old.

The PNG is a LibreOffice render smoke, not Word/Hancom GUI certification.
