# School Days HQ Vita Port

Native/homebrew port research project for bringing the PC version of
School Days HQ to PlayStation Vita.

## Goal

Preserve the PC School Days HQ content while replacing/reimplementing
the original Windows runtime with a Vita-compatible runtime.

## Current status

Research phase.

### Current objectives

- [ ] Identify the GPK archive format
- [ ] Extract Script.GPK
- [ ] Identify the script format
- [ ] Locate images, audio and video resources
- [ ] Study the Kotonoha engine
- [ ] Load a real School Days HQ scene on PC
- [ ] Investigate Vita compatibility
- [ ] Port runtime to Vita
- [ ] Build a playable scene on Vita

## Repository structure

- `research/` — reverse engineering notes and documentation
- `tools/` — extraction/conversion/research tools
- `engine/` — runtime/engine work
- `vita/` — PlayStation Vita-specific code
- `docs/` — architecture and project documentation
- `Original/` — local game installation, never committed