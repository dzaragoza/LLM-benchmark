"""JS gate for the picker pages (pre-commit, session 37 addendum 23).

The addendum-22 incident class: an edit to cpu-picker.html or
gpu-picker.html that leaves the page's <script> broken (duplicated
blocks, spliced braces, missing functions at boot). Caught three
times by ad-hoc /tmp scripts run manually; per wow.md, a class of
bug becomes a tool guarantee - here it is a BLOCKING pre-commit hook.

Layer 1 (syntax): extract the <script> block and run `node --check`.
Layer 2 (boot): run the extracted script under a stub DOM (node vm
context) and call pick(); the page must render a verdict without
throwing. This is the layer that catches "eligible is not defined" -
runtime breakage that syntax alone passes.

Exit 1 blocks the commit on any failure.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

PAGES = ["docs/cpu-picker.html", "docs/gpu-picker.html"]

BOOT_STUB = """
function $(id) { return __doc.getElementById(id); }
"""

BOOT_JS = """
sandbox.pick();
var html = sandbox.__doc.getElementById("result").innerHTML;
var ok = html.indexOf("Recommended") >= 0 || html.indexOf("earns") >= 0
  || html.indexOf("No measured") >= 0 || html.indexOf("No model") >= 0;
if (!ok) throw new Error("pick() rendered no verdict: " + html.slice(0, 120));
"""


def extract_script(page_text: str) -> str:
    m = re.search(r"<script>(.*?)</script>", page_text, re.S)
    if not m:
        raise SystemExit("js-check: no <script> block found")
    return m.group(1)


def check_syntax(js: str, tmp: Path, name: str) -> None:
    f = tmp / f"{name}.js"
    f.write_text(js)
    r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"js-check: {name} SYNTAX FAIL")
        print(r.stderr[:2000])
        raise SystemExit(1)


def make_doc() -> str:
    return """
(function () {
  var els = {};
  function el(id) {
    if (!els[id]) {
      els[id] = {
        value: id === "vram" ? "24" : id === "ram" ? "32" : "1",
        innerHTML: "",
        textContent: "",
        dataset: {},
        style: {},
        checked: false,
        addEventListener: function () {},
        closest: function () { return null; },
      };
    }
    return els[id];
  }
  return {
    getElementById: el,
    querySelector: function () { return { value: "silver", checked: true }; },
    querySelectorAll: function () { return []; },
    body: { addEventListener: function () {} },
  };
})();
"""


def check_boot(js: str, name: str) -> None:
    if shutil.which("node") is None:
        print("js-check: node not found - boot layer skipped (syntax passed)")
        return
    boot = f"""
const vm = require("vm");
const doc = {make_doc()}
const sandbox = {{
  document: doc,
  console: {{ log() {{}} }},
  parseFloat: parseFloat,
  isNaN: isNaN,
}};
sandbox.$ = (id) => doc.getElementById(id);
vm.createContext(sandbox);
{BOOT_STUB}
try {{
  vm.runInContext(process.argv[2], sandbox);
}} catch (e) {{
  console.error("js-check: {name} BOOT FAIL (page body threw): " + e.message);
  process.exit(1);
}}
{BOOT_JS}
if (sandbox.__doc === undefined) {{ /* doc captured by closure below */ }}
"""
    # the stub's __doc: expose doc to the script via sandbox
    boot = boot.replace(
        "sandbox.$ = (id) => doc.getElementById(id);",
        "sandbox.$ = (id) => doc.getElementById(id);\nsandbox.__doc = doc;",
    )
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(boot)
        boot_path = fh.name
    r = subprocess.run(["node", boot_path, js], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"js-check: {name} BOOT FAIL")
        print(r.stderr[:2000])
        raise SystemExit(1)


def main() -> None:
    root = Path(__file__).resolve().parent
    failed = False
    for page in PAGES:
        path = root / page
        if not path.exists():
            continue
        js = extract_script(path.read_text())
        with tempfile.TemporaryDirectory() as td:
            check_syntax(js, Path(td), Path(page).name)
        check_boot(js, page)
        print(f"js-check: {page} OK (syntax + boot)")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
