## NREL 5 MW ROSCO gain-schedule study

`DISCON.IN` is an NREL 5 MW controller input generated with ROSCO 2.10.1.
`libdiscon.so` was built from the official ROSCO v2.10.5 tag for x86-64 Linux:

https://github.com/NatLabRockies/ROSCO/tree/v2.10.5

The required rotor-performance table is the official NREL 5 MW table from
that tag:

https://raw.githubusercontent.com/NatLabRockies/ROSCO/v2.10.5/Examples/Test_Cases/NREL-5MW/Cp_Ct_Cq.NREL5MW.txt

SHA-256 checksums:

```text
45111ec68ce797c9c6f6d0352642f1ebeff2315cff187a846ae1660c780dbfcf  libdiscon.so
a8d9c2d88bd1d9073287256b042d7752d2202a01e611c08e283b9109504caf5b  Cp_Ct_Cq.NREL5MW.txt
```
