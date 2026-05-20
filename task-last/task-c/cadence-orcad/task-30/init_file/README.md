Export the real Allegro etch-length reports for `fulladd_placed_routed.brd`.

Required files:
- `eln.txt`
- `eld.txt`

Typical workflow:
1. Copy `fulladd_placed_routed.brd` into a writable working directory.
2. Run `report -v eln fulladd_placed_routed.brd eln.txt`
3. Run `report -v eld fulladd_placed_routed.brd eld.txt`
4. Submit both files.
