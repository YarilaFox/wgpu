"""Check the pinned fork against the released 30.0.1 compiler inputs."""

import argparse
import difflib
import hashlib
import io
import json
import pathlib
import subprocess
import tarfile
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
HASHES = {
    "wgpu-hal": "b6b7fb58561a792bc237628ba0792e332de418fefe145f13b5ed8201e6d52f58",
    "wgpu-types": "99dad6f1fbdbbdb4c278a6508b059d44688f5cebddf78d005a46a31340269286",
    "wgpu-naga-bridge": "d2f62e73117bb7a62bfd9c5a5841438a823f6566c6442a808ee269d2d055c081",
    "naga": "a616d2fb8c89516ac2723a581f69d6c18576046bed761bd6b305e5618e6ae130",
    "naga-types": "590afbf58a6f4f62873cd5cff4468061844bafa1cdf399cc954537c22d768d49",
}


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def normalized(data):
    return data.replace(b"\r\n", b"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crate-cache", type=pathlib.Path)
    args = parser.parse_args()
    backend = json.loads((HERE / "backend.json").read_text(encoding="utf-8"))
    assert set(backend["packages"]) == HASHES.keys(), "Unexpected package set"
    assert backend["version"] == "30.0.1", "Re-audit source checks for a new release"
    assert git("rev-parse", backend["revision"] + "^") == backend["upstream"]
    changed = git("diff", "--name-only", backend["upstream"], backend["revision"])
    assert changed == "wgpu-hal/src/dx12/mod.rs", "Pinned fix changes more than DX12 presentation"
    changed = git("diff", "--name-only", backend["upstream"], "--", *backend["packages"])
    assert changed == "wgpu-hal/src/dx12/mod.rs", "Checkout has extra graphics changes"
    count = 0
    for name, digest in HASHES.items():
        filename = name + "-30.0.1.crate"
        if args.crate_cache:
            data = (args.crate_cache / filename).read_bytes()
        else:
            url = "https://static.crates.io/crates/" + name + "/" + filename
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read(16 * 1024 * 1024 + 1)
        assert hashlib.sha256(data).hexdigest() == digest, "Archive hash differs: " + name
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            released = {}
            for member in archive.getmembers():
                path = pathlib.PurePosixPath(member.name).relative_to(name + "-30.0.1")
                if member.isfile() and (path.parts[0] == "src" or str(path) == "build.rs"):
                    assert member.size <= 16 * 1024 * 1024, "Oversized source file"
                    released[str(path)] = normalized(archive.extractfile(member).read())
        local = {
            str(path.relative_to(ROOT / name).as_posix()): normalized(path.read_bytes())
            for path in (ROOT / name / "src").rglob("*")
            if path.is_file()
        }
        build = ROOT / name / "build.rs"
        if build.is_file():
            local["build.rs"] = normalized(build.read_bytes())
        assert local.keys() == released.keys(), "Compiler input file list differs: " + name
        changes = {path for path in local if local[path] != released[path]}
        expected = {"src/dx12/mod.rs"} if name == "wgpu-hal" else set()
        assert changes == expected, "Unexpected source changes in " + name + ": " + repr(changes)
        if changes:
            path = "src/dx12/mod.rs"
            diff = "".join(difflib.unified_diff(
                released[path].decode().splitlines(keepends=True),
                local[path].decode().splitlines(keepends=True),
                fromfile="a/" + path, tofile="b/" + path,
            ))
            expected_diff = (HERE / "dx12-window-scaling.patch").read_text(encoding="utf-8")
            assert diff == expected_diff, "DX12 change differs from the recorded patch"
        count += len(local)
    print(f"Verified {count} compiler input files across 5 released packages; only the recorded DX12 patch differs.")


if __name__ == "__main__":
    main()
