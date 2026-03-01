# Core Agent Notes

- Do not try to land very large single-file `apply_patch` additions or replacements in one shot. For substantial files, add or update them in smaller chunks to avoid patch failure and partial retries.
- When replacing a large file, prefer a delete-then-add sequence only if the new content is small enough to apply reliably; otherwise patch incrementally.
- If a patch fails because the payload is too large or the context is too broad, immediately switch to smaller, targeted patches instead of repeating the same oversized patch.
