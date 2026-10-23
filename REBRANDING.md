# WarpCoil rebranding

WarpCoil is the new name of the same project originally published as LocalDrop v1.3.0.

## Compatibility decisions

- `localdrop.py` and `test_localdrop.py` filenames are deliberately unchanged.
- The `X-LocalDrop-Token` header and `LOCALDROP_BOOT` variable are intentionally retained.
- Existing browser storage keys and `.localdrop-parts` transfer metadata are unchanged.
- The default receiving folder stays at `~/Videos/LocalDrop` to avoid splitting existing libraries.

No large-file transfer algorithm changes are included in v1.3.1. The MPL-2.0 license and copyright notices carry over unchanged.

## Publishing checklist

Rename the GitHub repository to `warpcoil`, merge the rebranding branch, create GitHub Release `v1.3.1`, and upload the standalone source ZIP as a real release asset. Recheck GitHub Pages deployment under the new repository URL.
