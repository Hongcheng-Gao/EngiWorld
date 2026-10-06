[English](README.txt) | [简体中文](README_CN.txt)

task-45 — Library Consistency Check report
==========================================

Open init_file/test.lbr in EAGLE's library editor. The library contains
4 devicesets, 3 of which carry deliberately-seeded defects that the
Library -> Consistency Check tool flags:

  - LDO_OK         : clean (no defects; passes Consistency Check).
  - REG_BADPAD     : <connect pad="99"> references a pad that does
                     not exist in SOT23-3. Expect "missing pad" error.
  - AMP_DUPPIN     : symbol AMP has two pins with the same displayed
                     logical name IN, encoded as IN@1 and IN@2 so the
                     library remains loadable. Report this as a duplicate
                     logical-pin defect.
  - BUF_UNCOVERED  : symbol BUF has pins IN/OUT/EN; EN is not in any
                     <connect>, and one of the <connect> rows uses
                     pin="NOPE" which does not exist. Expect
                     "uncovered pin EN" AND "missing pin NOPE".

Task: run Library -> Consistency Check (in the library editor's Tools
menu). When the report dialog appears, save its text as a Markdown
file named `consistency.md` at the root of the submission.

If the GUI is unavailable, you may reconstruct the same report by hand
or by running an ULP that scans the library structure.  The grader
only checks that `consistency.md` mentions each of the four defect
kinds (missing pad, duplicate pin, missing pin, uncovered pin).
