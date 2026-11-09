# DX12 HWND presentation compatibility fork

This branch carries the restored-window blur workaround discussed in
[wgpu#10196](https://github.com/gfx-rs/wgpu/issues/10196), originally tested for
[FigCraft](https://github.com/storytold/figcraft/issues/778) and PhotoCraft.
It replaces the source-vendoring proposal in
[craft-libs#473](https://github.com/storytold/craft-libs/pull/473).

## Review the fix

Base: upstream **v30.0.1**, `40f4a34ebaf56f9a046231f54125ad046239d3f3`.
Fix: `77049cfcccc3994b37c879ac2d1772064dfa3eb9`.
The fix commit changes only `wgpu-hal/src/dx12/mod.rs`: HWND swap chains use
`DXGI_SCALING_NONE`; composition targets keep `DXGI_SCALING_STRETCH`, required
by `CreateSwapChainForComposition`. Later commits add only test tooling/docs.
This is a downstream compatibility branch, not an upstream release.

## Connect an application

Add this to the **application workspace root** `Cargo.toml`, merging with any
existing patch table. Dependency patches in a shared library do not propagate
to the consuming application.

```toml
[patch.crates-io]
wgpu-hal = { git = "https://github.com/YarilaFox/wgpu.git", rev = "77049cfcccc3994b37c879ac2d1772064dfa3eb9" }
wgpu-types = { git = "https://github.com/YarilaFox/wgpu.git", rev = "77049cfcccc3994b37c879ac2d1772064dfa3eb9" }
wgpu-naga-bridge = { git = "https://github.com/YarilaFox/wgpu.git", rev = "77049cfcccc3994b37c879ac2d1772064dfa3eb9" }
naga = { git = "https://github.com/YarilaFox/wgpu.git", rev = "77049cfcccc3994b37c879ac2d1772064dfa3eb9" }
naga-types = { git = "https://github.com/YarilaFox/wgpu.git", rev = "77049cfcccc3994b37c879ac2d1772064dfa3eb9" }
```

Keep the resulting application `Cargo.lock`. These related packages use local
paths in upstream's workspace; selecting the whole five-package family avoids
duplicate registry/Git types. Their version remains **30.0.1**. The source check
compares their compiler inputs with hash-verified crates.io archives: only the
recorded DX12 patch differs. Git revisions replace registry checksums in the
application lockfile for these packages; never use a floating branch pin.

The remaining wgpu/core/platform packages stay on crates.io. Applications using
a different wgpu release must re-evaluate the patch and dependency graph; do not
assume Cargo selected this override simply because it accepted the manifest.

## Reproduce and inspect

The [portable test](scripts/wgpu-hal-visual/README.md) builds a locked crates.io
baseline and this exact Git revision, captures real egui text in four window
states, and generates before/after PNGs plus a translucent red difference image.
There is no full Craft App build. The
[sample report](scripts/wgpu-hal-visual/example/RESULTS.md) is a local Windows
measurement, not a hosted-runner claim.

The fork's **DX12 visual regression** workflow runs source verification and
Windows build/tests. Its manual `visual_check` option captures screenshots and
retains them in **dx12-window-captures**, even after failure/inconclusive results.
A non-reproducing baseline is inconclusive, never a successful regression test.

## Removal and scope

Remove these overrides when an upstream release supports non-stretch DX12 HWND
presentation and applications explicitly select and validate that behavior.
The scaling-mode prototype currently makes `Auto` prefer `Stretch`; upgrading
without selecting `OneToOne` would not preserve this workaround.

Automated captures cover settled restored/resized/maximized/restored-again
windows. They do not establish correctness during live mouse-drag resizing,
mixed-DPI monitor transitions, or composition presentation. Test those on the
affected systems before treating this as a general presentation policy.

Upstream MIT and Apache-2.0 licence files remain unchanged. Test source and its
generated images retain their [attribution](scripts/wgpu-hal-visual/ATTRIBUTION.md).
