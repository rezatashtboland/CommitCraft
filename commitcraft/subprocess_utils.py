"""Subprocess helpers with safe captured-output decoding."""

from __future__ import annotations

import locale
import subprocess


def run_capture(
    command: list[str],
    *,
    cwd: str | None = None,
    input: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command and decode captured bytes without reader-thread failures."""

    result = subprocess.run(
        command,
        cwd=cwd,
        input=input.encode("utf-8") if input is not None else None,
        capture_output=True,
        check=False,
    )
    return subprocess.CompletedProcess(
        args=result.args,
        returncode=result.returncode,
        stdout=_decode_output(result.stdout),
        stderr=_decode_output(result.stderr),
    )


def _decode_output(output: bytes) -> str:
    """Decode subprocess bytes, replacing malformed characters instead of raising."""

    if not output:
        return ""

    encodings = ["utf-8-sig", locale.getpreferredencoding(False)]
    for encoding in dict.fromkeys(encodings):
        try:
            return output.decode(encoding)
        except UnicodeDecodeError:
            continue
    return output.decode(encodings[-1], errors="replace")
