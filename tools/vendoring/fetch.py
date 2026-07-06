#!/usr/bin/env python3
"""Refetch all vendored dependencies. Run on a CONNECTED machine only.

The build itself never needs the network; this utility repopulates
tools/vendor/ and site-assets/ from pinned upstream versions.
"""
import glob
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DL = REPO / "_vendor_dl"
VENDOR = REPO / "tools" / "vendor"
ASSETS = REPO / "site-assets"
FONTS = ASSETS / "fonts"

WHEELS = {
    "markdown-it-py": ("3.0.0", "markdown_it"),
    "mdurl": ("0.1.2", "mdurl"),
    "mdit-py-plugins": ("0.4.2", "mdit_py_plugins"),
    "Pygments": ("2.19.1", "pygments"),
}
PYYAML_VERSION = "6.0.2"


def resolve_pyyaml_sdist_url(version: str) -> str:
    """Resolve the sdist URL for PyYAML from the PyPI JSON API."""
    with urllib.request.urlopen(f"https://pypi.org/pypi/PyYAML/{version}/json") as resp:
        data = json.load(resp)
    for entry in data["urls"]:
        if entry["packagetype"] == "sdist":
            return entry["url"]
    raise RuntimeError(f"no sdist found for PyYAML {version}")

URLS = {
    ASSETS / "tokens.css": "https://raw.githubusercontent.com/Real-Fruit-Snacks/terminal-workbench-design-system/main/tokens.css",
    ASSETS / "mermaid.min.js": "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js",
    ASSETS / "minisearch.min.js": "https://cdn.jsdelivr.net/npm/minisearch@7.1.1/dist/umd/index.min.js",
    ASSETS / "mermaid-LICENSE.txt": "https://raw.githubusercontent.com/mermaid-js/mermaid/develop/LICENSE",
    ASSETS / "minisearch-LICENSE.txt": "https://raw.githubusercontent.com/lucaong/minisearch/master/LICENSE.txt",
}
JBMONO_ZIP = "https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip"
INTER_ZIP = "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"fetch {url} -> {dest}")
    with urllib.request.urlopen(url) as resp:
        dest.write_bytes(resp.read())


def copy_license(dist_info: Path, out_name: str) -> None:
    candidates = list(dist_info.glob("licenses/*")) + list(dist_info.glob("LICENSE*")) + list(dist_info.glob("COPYING*"))
    if candidates:
        shutil.copyfile(candidates[0], VENDOR / f"{out_name}-LICENSE.txt")
    else:
        print(f"WARNING: no license file found in {dist_info}")


def main() -> int:
    DL.mkdir(exist_ok=True)
    VENDOR.mkdir(parents=True, exist_ok=True)
    FONTS.mkdir(parents=True, exist_ok=True)

    # --- pure-Python wheels ---
    specs = [f"{name}=={ver}" for name, (ver, _) in WHEELS.items()]
    subprocess.check_call([sys.executable, "-m", "pip", "download", "--no-deps",
                           "--dest", str(DL), *specs])
    extract_root = DL / "whl"
    for whl in glob.glob(str(DL / "*.whl")):
        zipfile.ZipFile(whl).extractall(extract_root)
    for name, (_, pkg) in WHEELS.items():
        src = extract_root / pkg
        dest = VENDOR / pkg
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        dist_infos = list(extract_root.glob(f"{pkg.replace('-', '_')}*.dist-info")) or \
            list(extract_root.glob(f"{name.replace('-', '_')}*.dist-info"))
        if dist_infos:
            copy_license(dist_infos[0], name.lower())

    # --- PyYAML from sdist (pure-Python package dir) ---
    # Fetched directly from the pinned sdist URL rather than via
    # `pip download --no-binary`, because that invokes the sdist's build
    # backend just to read metadata, which pulls in Cython and fails to
    # build on this Python version. We only need the pure-Python lib/yaml
    # directory out of the tarball, not a built wheel.
    pyyaml_tgz = DL / f"pyyaml-{PYYAML_VERSION}.tar.gz"
    fetch(resolve_pyyaml_sdist_url(PYYAML_VERSION), pyyaml_tgz)
    for tgz in [pyyaml_tgz]:
        with tarfile.open(tgz) as tf:
            tf.extractall(DL / "sdist")
    sdist_yaml = next((DL / "sdist").glob("*/lib/yaml"))
    dest = VENDOR / "yaml"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(sdist_yaml, dest)
    sdist_license = next((DL / "sdist").glob("*/LICENSE"))
    shutil.copyfile(sdist_license, VENDOR / "pyyaml-LICENSE.txt")

    # --- client assets ---
    for dest_path, url in URLS.items():
        fetch(url, dest_path)

    # --- fonts ---
    fetch(JBMONO_ZIP, DL / "jbmono.zip")
    with zipfile.ZipFile(DL / "jbmono.zip") as zf:
        zf.extractall(DL / "jbmono")
    for weight in ["Regular", "Bold", "Italic", "BoldItalic"]:
        src = next((DL / "jbmono").rglob(f"webfonts/JetBrainsMono-{weight}.woff2"))
        shutil.copyfile(src, FONTS / f"JetBrainsMono-{weight}.woff2")
    ofl = next((DL / "jbmono").rglob("OFL.txt"))
    shutil.copyfile(ofl, FONTS / "OFL-JetBrainsMono.txt")

    fetch(INTER_ZIP, DL / "inter.zip")
    with zipfile.ZipFile(DL / "inter.zip") as zf:
        zf.extractall(DL / "inter")
    for fname in ["InterVariable.woff2", "InterVariable-Italic.woff2"]:
        src = next((DL / "inter").rglob(fname))
        shutil.copyfile(src, FONTS / fname)
    inter_license = next((DL / "inter").rglob("LICENSE*"))
    shutil.copyfile(inter_license, FONTS / "LICENSE-Inter.txt")

    print("Vendoring complete. Review tools/vendor/ and site-assets/, then commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
