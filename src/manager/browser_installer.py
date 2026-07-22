import os
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
from typing import List, Optional

from src.config import EXTENSION_DIR


@dataclass
class BrowserInfo:
    name: str
    executable: str
    family: str  # "chromium" or "firefox"


CHROMIUM_BROWSERS = [
    ("Chrome", ["google-chrome-stable", "google-chrome"]),
    ("Chromium", ["chromium", "chromium-browser"]),
    ("Brave", ["brave-browser"]),
    ("Edge", ["microsoft-edge-stable", "microsoft-edge"]),
]

FIREFOX_BROWSERS = [
    ("Firefox", ["firefox"]),
    ("Firefox ESR", ["firefox-esr"]),
]


def detect_browsers() -> List[BrowserInfo]:
    found: List[BrowserInfo] = []
    seen: set = set()

    for name, binaries in CHROMIUM_BROWSERS + FIREFOX_BROWSERS:
        family = "firefox" if name.startswith("Firefox") else "chromium"
        for binary in binaries:
            path = shutil.which(binary)
            if path and path not in seen:
                seen.add(path)
                found.append(BrowserInfo(name=name, executable=path, family=family))
                break

    return found


def _copy_extension_path_to_clipboard(path: str) -> bool:
    for cmd in (
        ["wl-copy", path],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
    ):
        if shutil.which(cmd[0]):
            try:
                if cmd[0] == "wl-copy":
                    subprocess.run([cmd[0], path], check=True)
                elif cmd[0] == "xclip":
                    subprocess.run(
                        ["xclip", "-selection", "clipboard"],
                        input=path.encode(),
                        check=True,
                    )
                else:
                    subprocess.run(
                        ["xsel", "--clipboard", "--input"],
                        input=path.encode(),
                        check=True,
                    )
                return True
            except (subprocess.CalledProcessError, OSError):
                continue
    return False


def install_chromium_extension(browser: BrowserInfo) -> dict:
    ext_path = os.path.abspath(EXTENSION_DIR)
    if not os.path.isdir(ext_path):
        return {"success": False, "message": f"Extension directory not found: {ext_path}"}

    steps = []

    try:
        subprocess.Popen(
            [browser.executable, f"--load-extension={ext_path}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        steps.append("Browser launched with extension loaded for this session.")
    except OSError as e:
        return {"success": False, "message": f"Failed to launch {browser.name}: {e}"}

    try:
        webbrowser.get(f"{browser.executable} %s").open("chrome://extensions")
        steps.append("Opened chrome://extensions for permanent install.")
    except webbrowser.Error:
        subprocess.Popen(
            [browser.executable, "chrome://extensions"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        steps.append("Opened chrome://extensions for permanent install.")

    copied = _copy_extension_path_to_clipboard(ext_path)
    steps.append(
        "Extension path copied to clipboard."
        if copied
        else f"Extension path: {ext_path}"
    )
    steps.extend([
        "Enable Developer mode.",
        'Click "Load unpacked" and select the extension folder.',
    ])

    return {"success": True, "message": "\n".join(steps), "extension_path": ext_path}


def install_firefox_extension(browser: BrowserInfo) -> dict:
    manifest_path = os.path.join(EXTENSION_DIR, "manifest.json")
    ext_path = os.path.abspath(EXTENSION_DIR)
    if not os.path.isfile(manifest_path):
        return {"success": False, "message": f"manifest.json not found: {manifest_path}"}

    steps = []
    url = "about:debugging#/runtime/this-firefox"

    try:
        subprocess.Popen(
            [browser.executable, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        steps.append(f"Opened {url} in {browser.name}.")
    except OSError as e:
        return {"success": False, "message": f"Failed to launch {browser.name}: {e}"}

    copied = _copy_extension_path_to_clipboard(ext_path)
    steps.append(
        "Extension path copied to clipboard."
        if copied
        else f"Extension folder: {ext_path}"
    )
    steps.extend([
        'Click "Load Temporary Add-on…".',
        f"Select: {manifest_path}",
        "Note: Firefox temporary add-ons are removed when the browser closes.",
    ])

    return {"success": True, "message": "\n".join(steps), "extension_path": ext_path}


def install_extension(browser: BrowserInfo) -> dict:
    if browser.family == "firefox":
        return install_firefox_extension(browser)
    return install_chromium_extension(browser)


def open_web_panel() -> dict:
    from src.config import daemon_base_url

    url = daemon_base_url()
    opened = webbrowser.open(url)
    if opened:
        return {"success": True, "message": f"Opened {url}"}
    return {"success": False, "message": f"Could not open browser. Visit {url} manually."}
