from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')

GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr",
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = (
    "result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt",
    "report.csv", "result.csv",
    ".dxf", ".dwg", ".step", ".stp", ".fcstd", ".scad", ".stl", ".obj",
    ".blend", ".pcb", ".sch", ".brd", ".dsn", ".opj",
    ".db", ".rst", ".rth", ".wbpj", ".odb", ".cae", ".inp",
    ".nc", ".gcode", ".slb", ".ipt", ".sldprt", ".sldasm",
    "autocad_result", "apdl_", "wb_",
)
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl",
    "ifcopenshell", "openstudio", "energyplus",
    "blender --background", "revitbatchprocessor",
    "ansys", "mapdl", "fluent", "abaqus", "cae noGUI",
    "freecad", "freecadcmd", "openscad", "librecad",
    "ezdxf", "cadquery", "accoreconsole", "autolisp",
    "solidworks", "solvespace", "kicad-cli", "pcbnew",
)


def _read_text_safe(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _desktop_script_artifacts(root):
    if not root.exists() or not root.is_dir():
        return True
    try:
        candidates = list(root.iterdir())
        for directory in list(candidates):
            if directory.is_dir() and directory.name not in {"__pycache__", "_runtime"}:
                try:
                    candidates.extend(directory.iterdir())
                except Exception:
                    pass
        for path in candidates:
            if not path.is_file():
                continue
            if path.name in GUI_BYPASS_ALLOWED_FILENAMES:
                continue
            if path.suffix.lower() in GUI_BYPASS_FORBIDDEN_EXTENSIONS:
                return True
    except Exception:
        return True
    return False


def _history_paths(root):
    home = Path.home()
    return [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/Visual Studio Code Host_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]


def _history_contains_bypass(root):
    for path in _history_paths(root):
        if not path.is_file():
            continue
        text = _read_text_safe(path).lower()
        if not text:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or "eval.py" in line:
                continue
            touches_output = any(token in line for token in GUI_BYPASS_OUTPUT_TOKENS)
            runs_command = any(token in line for token in GUI_BYPASS_COMMAND_TOKENS)
            writes_file = any(
                token in line for token in (">", "tee ", "cat ", "set-content", "out-file", "new-item")
            )
            if touches_output and (runs_command or writes_file):
                return True
            if ("/desktop/" in line or "\\desktop\\" in line) and any(
                ext in line for ext in GUI_BYPASS_FORBIDDEN_EXTENSIONS
            ) and runs_command:
                return True
    return False


def check_no_gui_bypass(root):
    root = Path(root)
    if _desktop_script_artifacts(root):
        return False
    if _history_contains_bypass(root):
        return False
    return True

BUNDLE = {'eval_inner.py': 'eNq9Gmlv28j1O3/FlPlQMpXpI9m0ECID2VgbGM1mDdtpCxguMyJHEiGKZGeGtgXX/73vzUEOKcqyd4EaCETO8e6b8X1/ekfzmsqSkzn8k1SsDt7/lQRfvp+TGSuS5Zry1ZjQNCUnRDIhqzIrpCCyJP/4/Pnwy7ezMPK874Iu2Ngj8Fdt5LIsCAOwUbUhV99//vX86ur8t2/x2fml53XfyboWkiRlIWlWkB/3mVzGsopmPP1BgpTl2R3jdJazkABtP2gh7hlXu16w4GVdpLHktVySOc3zGU1WYUSuJJVZQv7161eSLFmyEqQs8g3Q+Fm/BR9CJPQ4IkBhlsYP65z0/g4OSEW5YIgZAUVw/iQiBbsH4mKWszVDEbjnTycnuE8+mt1TgryQgq4ZWVOZLLNi4ZF9f4f/vr6Io7eHI3InIiIk5ZLxPwtyhBS8iwhgv0uSWGSLguY9iuWSoUbIR717SpZUEEo+KuEmkrP5fvwN8ZZkcqgJIoHiRFEk9sNRvMNNQouUsCIVegXJq4AQxjlLQ+TpveJpAXoc5Ams6xl+GnL3E/QsPw25++EgP8ZahaKuy85PEdhptsiA3sZM4hWrpGYHjNQqlTRWRDnSkcEWwBKwhIA+RPZAnICZyxh8QdJGLmUtq1raI0QdIZMGtn7/C1mNXqCqJQMCViQTyoKKej0DCOUcPZ6lKJW3Cs8LtB6AE4zIx8k7UgEIUbEEhOL7vjfn5ZrE8byWNWdxTLJ1VXIJwixKdNayEJ5n1jizT2Ij7CO4aMRA4yyaao6v4ZmAOUyvNeyKymWezSzgC3j1PAAQ4UYEumJcBkcjEBAPcDMAYrIcSAkjkHmZ37EghLMcpa9/yCHxk3K9Lgs/DDUSAeFkTS0OFU0umahzOSIYQ/UzIW9IUf6Hjsn0/dGJ511/uvp7fH4GyvEZXeQMYquvFzH6Tcgearyr60+X19PL+OdLhNFcBOqyIpPqno9vs5LyFCOjDzgv4sspnOYsAhYqOBJwX0cWP/Q8LwXXacwz4GUpgdprK9uQHJySPBPypl271aGdM1BgQfBGNM+KFOw58KPDQwvLPrRYtO9u4RipwDhGfSh07Q75L/lWFiaVYEISJBvAqOEK8+uH48Y6szkR0YLJwEcUfkgmE42sY7+GE+GyhXgt3Tlb0GQTM50bWSDq2ToTAkw1TjPuEN4oXsOHc1ap3SuOajVOONZeDjDtxlk6MeaClsoqpd0J2izAAitUF8HFgbuxwmGEBaAU7VZkKrSB1ALfyaf+iPht/nQlVmHkALoP1UVXkFXEHsAQRBB2padpgGtVZ3nGGV155q45A2Gl1adiPIJwWSL7c5c8EsBaS18ITiSBGcjwyMkj0Pfkez3tcS2RN9oXybGWD984yMBuUNDXkcrngSYqRPvALaML9pBgiJ6qH9AXRpYOxbqOiGhVQS4LHM8POvyj+CZ+U1WAxCsqBEsnv4Cpsm4sZg8QHiXs+Z1KA+5AbqtpPpnrDaKkNSaP7MlvIYThtixeTOpOMq957VC5l0K/XBmSGtt0ZS/ivvSdWPZqFbRGk6i0oQu0JuM9OrCftLR2WIu5EaMUBAB8ZJ1ogf6jnKcNkJqR8Eldh8yrdvBqN4aGzb4FfbMDdAPjVkutam8U2oHtKb0O3qRCeqSqmKDAWtj3w9uu+Z+MVRHaJGwk7LVG0atwHYszJhLkrAgswSEgJCfhkMkgJU2Fc78sQVVQKKXAjOIBflWpe+hgMFZlgXctyzL5bqyKSFMs6orQKQihKaFKAuqSKZVRU04egjgIIPywOSIrJfpbG7nsNQhdaGjd8IXqSTjqxxxr01JLh9+Ll6wABAnX1tDkSK3GzsGeplnRA+SQbLUJZ16r5U4XsUPHBotS8fGgih09NBXx6eS4pw7XHLeVbbAM6/r9WFXYL9O1aSG2dQ0gjK7xSF/X9toeXZtj/3ddG5L/mK7b7mqHrg2WZ3Tt6OF369pgGdb1T+Ptxki1Q/yOpeqkqqWKRdvlmOB4QARIugmWrxbQcL82ICm0D0PEoIwGm7tOY7ctE0yhaAgObLgLwXLum1fIZQLaDZYGFveTPyzCD+NeP6hbxonT0jXeYrdQ+002goJWLXTka9Oz5jJ2LzZpwJBxAq2f2zXC2zu1pdbicgX3eoAwf7xWYQN98YC2DKFbGLGBt/QMqXHuaw4aDQIIxY2Wqe7/8QlJ31boo68JGmsRQ/y5vnirLsBSl5SnrhrbKsV7Q6bfvpz/87fLr2cQHy4+nV9Oz+Lppy9fp6Y7gRIIuoqiTFmAdI5Iyssqbp1R6IrTBJRkmeUpV3HJBD4V2HAVYxtC6LRPfWCaaTweSbpAgbjhrxu0cCMr6raLsMitYl3a1d428aa4NQJRHCLiEZF1Ba2scQe1TKXk2SzKJJhvEIbhyB5nD9JUSRH0T1kVhL3rlq4RWbHNhLOKh6HtWl/d9XHd+k/29Y2hTTv6gilqseAD/8e8kkTafrWGVOerT2rvcDKENRe1PVB8v7QP1UMtbLvcSl23g51+sVewO6W0e3HPOOO5ucUQhjybcco3fwiDmlnTNMpnfBBHRZMVXbC2Iai2qvYKNWFo6YwhzF1hH3zTJSipsq3uAkJA2wUY4T4/R2nBiT3gjDJeDG9Os7zmzCmH3PHBSIUFBZdZ9xr3yxc1Z0DTRW4Y2rHr3ZTd4IHbkPxpshWyBmodS5CNFHO/l00hltBiwVJIiQj4yW91iJP3iV7WWXCAEdow0qddsCc3/uEqAlQDiY3K+3g60sNinFkEENVjYxt22AI3ekz1GVIVQi+7qM8fNegWh+VqlMyKhAmHtW1GANNOlejwp2zE2KutPcMoL8HeAqUO6xQ+7rVXGiu2kun4xktUpjVjy2lR1jzBaIbj01ldpDm8dPyxNW/leqJr3qKdAA6Zd38I6PjePnADzrcbGo4UAY4QSnb4CPAB3paCTYmsPy2wxmAHtKlYEs97FPDQcykhtEuNCI5qthyL9vZf5GOa5AUr1xAZN8/4mJpu5GmsSgIQLiSrbo8zIok1I2A5bHOYJcsVt9tAPXWnaOz+d+AA3tWGdpWb23AnskbORsaq3kalhlvaAEVYjiNIofUMj1n6BgygDVlu+cTZuryzXjAoVsCFkQZO3xzdWv1jCEL2sLnSr1osBw1NgxSANRw0n2ndBk1HHmjTtkgQ9Xqts6xN/A2AGD8ERPJBOseNZMwtEIzKtcG+6LcN07Y8DmxURm/WjKXcpMHGGYU2EtagGU7KFG5P/FrOD/7mj/SoVEx8rPgS2ZNxL1Zv+8aaYZsklpkeEeBUQIWLDCpPdC9rZSb07vscZnTaN2D7OaK1XIS9y1jDW28ArhslbKWrOkiHA1tUAglqvmFOGo7w3Tk9ECl2RAtjKWnJdITPUuAqm2+MUalWIcO+1wTRXl9mZ8fYleJ83yAYNU834+OTW5WwTJqA3hmcp6CQFUdNwWkmA+rT4cjgAiCI3FJ4x3g2zyD27h4vPyTj3eTpkb36YAgHQ6fMf6ZTNSOXxtBb2mOKQxhNWztwN1j3f1ntThrw/zP006nzPVn5uepzod5AX4NX9YVbLlkGZsFwsGsbVv3TbblMU+GBqcUq9cex6vrieE2zIo5NzwfbalywAVnwxZ1KRyeOSDmIIPBr9T9Dnv9fIUCO/tQFoIRMwY+d4ARr7CGTwUnY7bXaHssQcHN8q49ozEZbRuiBYbEBd+T0YSIpOUMWj6MjnQ+OQ+9/NGWpfg==',
 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs',
 'init_file/board.brd': 'eNrtXeuSpDaW/t8R/Q5sxcTE7tqiELdM1m5PdHdVe3rcN1e1e2Z+UplUFWMScoGsrprn2cfYf/NiK4EkJBAgCSY2dsMTY5ukjj6Ojs5VEuj7PzweMushKau0yF+cQds5s5J8V+zT/O7F2am+BduzP/zw/Nn3/3Lx8fXnv366tJL4Lkus679ef758b501v+x9vT/DRO3fGNrG9hEe/sO+jL8iRHxZJXWNLivu2oqzr/FT9ZDs6qK8LfL6xdlTUp2d8yQItE53cVYnj+jPp2P713Me7a5M99Y+reo43yUvztzgzDrlaY3vvDg7pFn7k1xW9VOGiLI0R0+yDqesTo/4BjzDEMcsfnpxlhdniLVahEQ3eqjkTvurYQu1RjJgV1Z+OtwkZQOexwcE9Lk4nlm7IivQTf/Muk2zrPnrQ1qlN5gN3H8r3tXpQ8IJo4cWUrhXRV0XB4YIjRE3FPFTvK8YnmuMt6V4X9J4DbyI4v2Sl8WpTvYMMzTFdB2KeZEekhxrbifIwBiVDXX9KYt3CYPcGCO6FPFmLUSP8fixTO/SvFqj4z5jc0XQgHH6Af2nWqHvzHZu1kJktlN/ibPTHGTjW2YQmfXcrIXI7Ke+rjkXxPA8PTyP2c6NHC/UxOus5nWZxIchoK8J2BnNCGCgCdjZzJs0T6v7oQPSlWFnMGOIulLsrOVHpDbLhdjZihxPV4adpXxOqnqxVnudnayD11nJT0lyRHFGEqs1Mf3OUvqY0Bizs5Yr1O8y3ckYdTRBO4sZgEJjUGY1DwNQ1xiUGc5FiQCWe0ef2c0fi2wFb+szu3mPmqMslSF6pojMct4ncXUq12CSGc9FsTuhBGi5/fjMfq6S26RE5USyGDPodB3zuTxcB52erwMYMQ4/JPVMrst3GF3L0Bh7r05VxY0zNMRjFviJT8lMuWOmd/10uCk42/MNAZnpKWRjCnDM8nQTJ4p33pVwN0Vc7vEFKgrTHF98TcvEeoQvzoBjY5N8ai9DJONHF6mWZ28R/pPL7n5N9/X9izPk4BrYpug4F5Bom1EkDxXToSYSafPodpzqIHG9kyPN9a5EBX2c4ymBR9qvgOD5Ns5FSR+jTcCxFjAcFOAkODCwcZGBYVw78Icormf70RyKH9peQLihDRog13aooKAN4RDnnOlBlt6UcZkmVffjiejdId2Vxe4+PTbTH8d492t819KRa+p0375DRXIzRZJUuzI91qj+/AEVeFWd7qyLU5xZb3PrXZon1n9Yn74/56mEsYLQDrc+p0GkP90f8I9WYHTAbIiLFjposD/8SpDk/hiktTuV2K7gtq9dAno3kOb8jgDyeMbd/6fB6cjyvFWfPVEdJNxHDIDokGk+ocvW8vdl4+Ec9ANXkPsUUdfN7IkdOo7bh3FbmI0dujooVnUfH1HzAhnVXZH3Ub0WNbCd7Yqofovaim811KBBdVZEDBvEldncNKArS3TbgK48+FEDqq2YM6i4PhBg10GFogTWAXXFsVoH1BO1ah1Qn1P+dRCDnpGugxr2HMo6qJue81sHddv3zAtg8XqHyCNC3WxQ+yr9O36Y3fygUQIJv4xRdtCYyw+/v6u/+/Dy/eX35xhGgEPM+aFPXIlru07EQfZiOEV0z36AMijUwIE+YS4KcWmlgLQdQkV2gHugx1Ikw/GirS4/jqRrnWOEduQEI0LfDIT+5eW7Xzipn5Okj7+u2jKjzRqHCSRemIrLmezx80dUJ/aTR8/KEqSLR5JDkhYTqSPKeCOfpMKonyGutUmmv9mGXK6z9ecTPaQNEOFtmqRmFx9fnN1mcd1Lhhgw7IAfm4cQTtyOk1UeONpHnScOIN3A66o/l6V06HqL6yJSIrmjSWIgwQyDxij7mOxhc5hDPhk7PUxlNgeQYz1n3GsjjvGo3O1A0m25jikrdcDpWFOvbqNwqGLDfLzxMU9NTO15/Omw4XKRmHgbrfZteqD5eOrpPBRUAuIxmyJE5jBVg0sHRqQhA5t1mswJIxv1XNonCVQABShZiKJTD1Pd68G4QxjkZ0hAV2LEWxQAkJ7Fu7QuSvA1PcQzgeC1+20AhqHgNcX4fVZ/d8Qyfv7s/U/XrlWcahxgrMB6tJARWIeDdW5dvcf2gK4nYwUMotao2q63VtredOlNVTfCsEAHBjg0oAfnQ4+y1gxUy1t7t0Vrbiv7dxkeMAYcER1DmwFjvihylDlVHJZxaPkQaYiAQk8yDUa4BmpsD7CJD4SNnbY+36PzqI5qAKFteJQm/kyhyAJb4I+i2BucXjKk5g9GSEALCvBYbcNHLsD2O6iONcRZwBgDmx07GU5/8GhcVlABnZCuWxu6c0Faryp07QgbwhOT7JKw3YEtCdsGoa46Jrs0zmZi3M/Xg/j28yku/87Fti9kk+BEAPNs343YJDHKOlv1oLfd7raaqnF4HBzg8LTgBP5Imdnnj9xmgE7gbJUY5PB4BtfA0+Gvq9wGiwJyaWoMzgQ2mB8qVfRp8BExK8uFoQ8cEZtT4/1G6ODlTjNHtBiQZdj8vHTkLc75GRyqKcONmV8z8ETlbs4LOa6zOYfOwBVdJVVaiZn256djYiF63/oR70y2oDOZW5MudyHLt51QEo7b4RmtewcwwAyHFnFNjrDdRiw9a4NE4zeg7xklrBw2GAEHiuiSlLXFgB1G60MgXR+mj1wCLUdWBNaQiDr4IL2W8Uo9yPzoqZYYpnDSQeLwgDF/QM6gHuBYMWnU3flKUrOQlPZ1ha6ClQpdmeoZy06qKaadHbEzTTMbBGYWrswm/TSbsyjp2Q5ZwoF24C5M/3HyEzpkxXZiFnA2iIsbbUSJew3DJLp5ONdqZd7e74m5t3+ItehDiV5SCsXnAr2pM8cNAPrnLygdU5pAa4M5mTX7SCbS8M9HK/ht8uy3ybP/45NnZMLmt9mz32bPBJxWK1aePls4Wfb/f2psnxb7ZG4P6UcvAJKS9AK35QLXBanoLRdHrvuiTP9e5HWcteVps1tFt0CFkUS5+GkNtfrUAIbbTEwNWlPN6WoeZIuCj10gYdubAwM4frOsLleO0CeS1i1CYP3R6o4zkMyynjgmMqUrv/2sxO0SR9E/6oR9dxsOnTh94sKUwuXyVCm4cejnRALkMgGKQpFAS9lWF7eqiJVZHW7ikaqD6pCNwwE5nlKO2sWrn2aLwbnN2C/nykG9WdnQdvFL3k9dbrAkCHJovd1wC8pDCjVIZaHtRRthWCerQ1F52QYiPrZIs6dBjdnSS/ZfdUYgwzGI7cci28VzL4hc4p0d4SC2X2a7wrp6b5EdG9Y50wwLB3H2uYzpbX+dNbECkuyB0y1HWbvedPEKcAJz7mZFMI41nY1/fFf102Nhh1qv0uJxpuq3SSx+OoCvJTTxWCkxgmcKJ6Cx3pp2Vo6mUab2s0hOK+ZQdmm5w36DbtpzsOfbp6cKe6NN5CvHDbDOpoAO8Bv9fQu93YDtqiVLw5ftBqRgS2on0U/L1XOgT70BM/DRn95++OPly4sZJw3/4rblV5dLOXZEXy/k5n5QGHEDg8k+2q6PtjVJ7Wk7Mb3n0IApHBDxWF+1piLhxt5sh3XZ1vahgehYO0F0MLLDrQkabScOhGPTjFFPcqRdbyA6NGAKxw8E31dg2lnOyviRAKZDweOR8Tbpr8zGlg8GEEejfYj2jDpns0BgzwwPerbnDRXZR+7bRJFpOxGNvFqtKzvulWxe8To0YAonKDLXVz3RjbG33ZiIjrYTRbexoW+CRtv10ahN6ElO7jtNLYyDAyIe9A1dO/QlHoAbCWA6FECqxpr9JW/s9cSH8orIZGhpO3FoUd0VmqDRdn20jYmetM16/WRYwBAMiGisn8C0o/ygcqMATIdBxDOc6JU74qUDIciOPkK7r5xb5/tqihfYm2HyFNqRSe5EmwlY5AVLXbGRZqL+dljAEIwfA66XWiKTsrZF9YqByGgzQWT0JVlNLNpM1NrOCNZxlIYm1cHxQ8D1FBh2lTMCbgyA4SAAmeLqLmkEw1SE27+iwxm3taZjzLd9kzyENhOwyES0rnZwS3xdHzssYAjGqwbXS2DYTW4w+c2hhgMg7PAIfLOeSpzt4iEAwhhsjCo3znUDnjUzNH7KX5i/Cz0DxeVXgrmpoDWXPIEJjPDFJK5vWqKSsGQmJamQ6DjoZqKy4euUfrk7NDWgDkxIprpeAsNuCnOMhiPZDQAYqKleN4HUvwJDxw+knh8YhiQgjUnAUDuAVD2AqX4AuYIAU/cP5P4fmAYnII9OwDR0jjja5YMhfg3O0L6A3CTM8aQZLjBMvYE09waG9QqQVgXANIkE8pIFmKa4I+wZFnpAWukBLl3QQpOmRcAwLxrxncYWJs+zgHFqxHWWtwnTYhTIMzdzxZNOHAHTOS0gn9QCpjNuQD7lBkzLXCCvc4FxoQtGKl1gPLsFRqa3gPH8GxiZgAOm84MjjnmNQRFkaDpdAOQVvjmefE4fmC44APmKAzBdrQHy9RBgPG0ORhZsgPHE/iiLhstdQL7eBfiJUT086SQwMJwFHnerm4VeWhwO02lgobuCSzBdkgMjM9ULlFC+mg5Ml/qBfK0fmG5EAPKdCMB0qQ/I1/qA8WIfGFntA8YL/mBkxR8Yb0kAI3sSgPGmiVFnvcKwgN64mC2agpFVzgWIrm9vJGkX/Q66tmqzhj08ww1KQL5DCRhvUQIje5SEHmuKcJRFox1eQL7FC/DbRfTwpJtjgOnumDHvam53I/ttgPEGGaHLQFRDs51oYGQPzxJFDGzZhFZ71wBuxJAZnil34pDQp+gLkHMMggBNEeWehofTQpOKz1B60qE1HVn5SKwttuUbSAXuTJ0pPwz8Opom3vBzSb4Nvd4GaPIuCb//Odj4iq+iAhdRR+sgkhMSUELjBOsgktMRYGgHcB1E8il3iA9XWQeRfMYdQttfaWTIJ9y39nalgSFfb8fnw6wD2B6HQA5BWAOQnIQg299vigjHXkEwBWwNZsU+t/ay3qiQkw/W0xty8MGKqk0OPVjR/MiBByu6CHLYwYpuDLb2sqKrdVt7WRwOui/loOi8IScDQHvrbg1fkem9wghtz5O8w4jub31f9vJhID8ga2tvIgkOGiPP0cEJEZEMJ0ThWgfHszdQhuOj7FoHB9pwI8MRjlCax9milEUCE6FqWgMltB2ZkEM71JGxZweB9LVVR0vCwrcHOsFwXw9QQAGUvv/yq/ANAQUcyn0fh3ZWFYfKso9DRa+KQ0e2j0MVQVk+4oFoLn+IV6uZykhU9QdI1FaUkagxDpCo9SojUfcwQKL+RBWJOazBW9TUwykj+bYnlTiqDbY6Emf0fd9KHzCKo/TS4LlwFGBc12V6c6oJnfjzAZHFeb1Pbtu/9n7vshif98ku2ZmW7ABhRBmfspo/d5G+3Nm8g3jetOuuWrB9UqV3eXnKkqqH03u1HPU/vzuhTmIKFLSy+rsbHLkuX/747tK6aGDAVXKXZDn+2/lN+3EZ4TsziXWNZL+Pyz0QGqAgme+tqrDukq//+K/7rP7W2uM+VqjF7T/+u7SeP9ujy0OSVnWSWy/zr0m+P+V36PqIe5Lb1nWRZXVipfeodvyUoeCaJ6jVTVIV+T5B917mt0WJrtpW9/FNkn9r1WVye4t+XiNw/ICkbImydHef5M+fXaY5emCWkUZpUlonzOgxwQRl3jQSe3LK8bv2z58liIGDlScn1BCfXZpb8Y2NZd97714u4SQfkbB1hUdqRMCf71E32tETyFF3HxLrJkFMVElt1YW1Kx6S8vmzGOtKgnIR1D+ruLXi4xF1HWcmeWVbfy1OJZIv/mDAKYtLq1WV588O8VOLuE9vm3N8a6tM/vOEqnZ8THD1LR7IY5bEFRqx+NfEqu+T58/yZJdUFX6BNt7/7VTVDakVY2liqCf8rB26XxxQvrRH493y3yrmCY+hFSNxfm2U1B6IEbEZH+gRSdhQr5P6dDyzHvA5ry/O/hX+Owz/jeZ/Hemhfl0cj0nJCB3b8YLDwfpf+q+Mw7dVgfQ5YSyiaIwa/BP+LXn4/s9oVPE/7OnbQ5qNEX6K90p0X9J4lg5hqcAhGhU0RKNCdn1Qeuj1Ya+Ihv6vyNs1+vUOK+4cfd5QVajJ25yHd2XYrXZfpMjaKmQpjNh3RphpjkxX6llddOY1glb9GUeiTnHHyMSHuv4I2Xt8di4v+MiOIqnaVq8yFFAQ6RX2ZZxxB0Pi8gEN+We+Myjcj5C9zXPBV4wSvipq5MlmKRGHH1H8L1UI1Z5NZaQGS6mVsLP3ad4T1ciIItL4sUfqjpI2qCIHM7gi8QxybyhmoHvUU9gDKU9BD4hnkNXlMSCeQparhz+OLm+g8giRKYVHKPXiWAn6JyPoD7iM5k1aVvU0yWVW5HdNKvQOXXBD4UxTf7y9RUnWNP3hAbvPN+hGwlkdlBG+LpP40KOU0GHJSzDlnhRLfUjsjlKnuYyLcWwNahz5ECfv0kNazxBX5VWBEsEcpZFToqhKxK+EcgQTsatMnKEEuzzE2SAjm6Gv3hQl6ugk2/sj4uRdkt/V9xckrd4JTzjI2vwYH9/Eu7rg7EYW41CxsvsVf81zioOG6CWujGep3hT5pPU0RFdJherb3SThqUro10c7Mk+iKPHjZVkWZSfCgPB2zhWwTY19QtIosLdqMSpa1l5wZS0PjUYfFYt3gnTcQDqgLxG2QCfp0eUtKiHryaFGHuyq4fBLW+JPwdVHbCF4zplRlVhdh5SfUC17kZbIi0w8mhK5KkSeCpGvQhSoEIUqRBsVoq0KUaRChFfUFKiUZA6VhA6VpA6VxA6V5A47wccSU74VSh0ZwYcix1gD0xSpXt/jWQb0wKmKZXf7sazvr+vkOE2FnMadQOXJqC4f671AJWXsVZGfKoFM5tFu36O/KZDh9PRwjDm358vIUAWlQvbqVPXIpF344+nuLuWSFKk0Xj4UnOuSPu5TkT3dcWUilAssrhLOzXjBKJE7LauGxlOg8RVoAgWaUIFmo0CzVaCJFGg49zJBBFWIVEQNVWQNVYQNVaQNJz36IRdSIldKcp3cNROFXcmP/icjpKY+T3mVHk/Hd8lDkk2qOSEUMeXJfEv5uajjbEh5fiST7lwq8qbIsuIrwOkx8pt4Ep8mJxYy9RR/hPkpqc4UPK2CeU7wgbxLhZ6zkAlFx+WrOC4lfzOvTBN9bjKv+S7Lmn481imenYa6EhPmrCKVECqnGsQzqBQNoIJQfUfNqqCiSU2MABWjy8TICXZakMMcIlwz7rtqcd9Vi/uuWtx317ILP5iXuTeQuatr7pFidrdVk5KjJiUVAVCjmRKAPxCAp690sK/d52LVmWTtShh3TdDevkbskvVhZDl45mt3nyLVIgvIyKW8fQe59CJ8s233o7kbO2qP5CQvklSHuLpP9i3XVlnUyLfhE0KFhWbyWLy7qN1359j0YDCEF2xU9iedyxCbr/D2Icn7KLPf8W2FRyQzFNIvvIzwKVpxyQno88eoy3U223dOu73Oj+yg3cRFNrHJ5ONuZuTj4/e22/1q9B2lpfLxcdNA4GyhfF4HnHx29CQy8DU9xJycXuMPxHeScjfHlh3PhmS4mpcBzcSEN3KEpFO+7Y31SpATp6NzKoVET/aHkl2Ti0UWLhCZB20ygO0uU5nIohmJuZEdMc2CtheGK6gWD0peSl4qqJ9526Pnb3cS+vmaSacVTWR7mzHRTHui0IYRZd3z/BXE4fk2+aA4OQZtqTCueGHgI4A7QdDjfrtpV/fXdkzIOxB0B7G6RJDD8SDREOxTA28FDUGq6zPI0I+WC+WCF0p7DBUXvciRUyx+ffChv+0Jpv02hpZgHB/SY59d6G9WEUxENuq6yBpXsBwhspMjPDrBkOM6ugzi1I9a7ccL1KUS4E2HEXUokbdCKA+QjsCImHPzfZDFQnEXCYXojLpQfLzFlPgAD43rCkLhIdut54uF4o26FeHQ0U4ueU8uEgtSzQD9je0E5F0JHMXXSHGQ3rguDW6KJwDNychfKiOSMPeSDvEpf+Jtlh7p0D2pOb5BiHduaIdtvCPBpgd/zqf+eF0qzrhLuozUDtEOH7K3w1sQLdKK1AfHeN+8kXE+RvUnSuT3vzsZ2HTXOHk5pNk0TlI+l3Hd7RAlY4OtPnmsG3QI6A7Xlush/1CF/60C/0Gf/60Nh+w7Nt3zvg77rgr7CtyHo9wTR9F8QrS9uRrzngLzrgLzm3HV4bknd1dj31dg31Ngf9tn37Mdd8g+ubsW+69ULDdUYD8afa2X555U1qtxr2K3Km4HOuMv/nL80ymL1fhXMVwVtwMnzvjg+WfvaK/DvorpRirsu+PHMfDsd29xr8O/iu1S1ZjugDfeAc7xc9+QWKcDgUoHVDw/9McViOsA962YdToQqnRAxfvDQIVoO/oJe9Kd3qEaWp2UOQ9edoawo7LbqMhOJfRAFQcPN+OfsueFx77kZSg7Fjd40ZmBjknuw+/G40bX3wnH1cnXHye6oDQ/jfuGtuzphUbi8TQF132fkxsNU9QxyX15/XpechMqd6WQ0HHKOyFdXIc3RN+M0/yikPvisoznqPt+/tZ2aQbQhv0mdQ/sjbtEv3nY1k00sORul2PowpIqsVOvPmz7MF1rJAlPr34hD+sCgjlsO6fYS67Is5bp6jfQ/TKvrK6C+kwoNNPVCTXEsyNyFeMGrQ0OvUFbrGLER/cHrX2YOWzntjhmybOWDdqPHy4UXLNCuHIn0ja83DTrF8J5ms5TBQpa5CpoEVDQIhVnBhUcJ+gHEMfeDvwduWmsixxo5+06UDNnF+AlNPqNp3YFsgdr5Ow6XjmzYc9y2bOMYTuz6VjVsprOFskEmOiXl6LSZUHRwru5Ni23LHP2/FQAeRY7+EUXlX2in0t3uBCySrrz4XfjBTpL714qpDsTxw1KA6COSMaZVynPp3J/5icnXNfPcCy4QZueL9+upPaVqV0H11XRblZMPh+sBTsuuvGZgZ+hRvBQS3ODcTtsC9ReKm9mh15ob73+gHBm2D5KW3Dn3KLA+U0Rl/v2JZYy/prmd+0SQnyX4a9K/A/RyHKE',
 'init_file/testpad.lbr': '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'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('board.brd', '/home/user/Desktop/board.brd'), ('testpad.lbr', '/home/user/Desktop/testpad.lbr')]


def _decode(payload: str) -> bytes:
    return zlib.decompress(base64.b64decode(payload.encode("ascii")))


def _materialize_bundle(root: Path) -> None:
    for rel, payload in BUNDLE.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_decode(payload))
    for dirname in ("init_file", "ground_truth", "_internal"):
        (root / dirname).mkdir(parents=True, exist_ok=True)
    for rel, desktop_path in INIT_MAP:
        src = Path(desktop_path)
        dst = root / "init_file" / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def _bundle_python_paths(root: Path) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        text = str(path)
        if text not in seen:
            seen.add(text)
            paths.append(text)

    add(root)
    for rel in BUNDLE:
        rel_path = Path(rel)
        if rel_path.suffix == ".py" and rel_path.parent != Path("."):
            add(root / rel_path.parent)
    return paths



def _load_module(root: Path):
    spec = importlib.util.spec_from_file_location("eval_inner", root / "eval_inner.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load eval_inner.py")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules["eval_inner"] = module
    added_paths = _bundle_python_paths(root)
    for path in reversed(added_paths):
        sys.path.insert(0, path)
    try:
        spec.loader.exec_module(module)
    finally:
        for path in added_paths:
            try:
                sys.path.remove(path)
            except ValueError:
                pass
    return module
def _is_pass(result) -> bool:
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        if "pass" in result:
            return bool(result["pass"])
        if "passed" in result:
            return bool(result["passed"])
        score = result.get("score")
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    if hasattr(result, "score"):
        try:
            return float(getattr(result, "score")) == 1.0
        except Exception:
            pass
    return False


def _resolve_arg(spec: str):
    if spec == "__DESKTOP_DIR__":
        return str(DESKTOP)
    return spec




def _run() -> bool:
    if not check_no_gui_bypass(DESKTOP):
        return False

    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
