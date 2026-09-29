[English](README.md) | [简体中文](README_CN.md)

Generate the real Allegro NC drill output for `demo.brd`.

Required files:
- `demo-1-4.drl`
- `ncdrill.log`

Typical workflow:
1. Copy `demo.brd` and `nc_param.txt` into the same writable working directory.
2. Point `NCDPATH` to that directory.
3. Run `nctape demo.brd`
4. Submit `demo-1-4.drl` and `ncdrill.log`.
