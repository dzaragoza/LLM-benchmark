"""ty wrapper (pre-commit): the type check with the environment fix.

The addendum-91 ruling pinned ty to the ACTIVE environment's
site-packages - but ty only searches sys.prefix site-packages by
default, so on a machine where the requirements (huggingface_hub,
pyarrow, transformers, pytest) live in the USER site (pip install
--user - they are on the interpreter's sys.path, imports work), ty
reports phantom unresolved-imports that fan out into follow-on
errors. This wrapper adds every site-packages directory the RUNNING
interpreter actually searches (site.getsitepackages() plus the user
site) as --extra-search-path entries, so the check is honest
everywhere the code imports cleanly, and exits with ty's own
verdict. Session 39, addendum 21: retired the --no-verify
exceptions - the hook now runs for every commit and every push.
"""

import site
import subprocess
import sys

if __name__ == "__main__":
    paths = [p for p in site.getsitepackages() + [site.getusersitepackages()] if p]
    args = [sys.executable, "-m", "ty", "check"]
    for p in paths:
        args += ["--extra-search-path", p]
    sys.exit(subprocess.call(args))
