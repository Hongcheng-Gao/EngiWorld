from cavity_common import solve_cavity


Re = 1000
center_ux = solve_cavity(Re)
with open("/home/user/Desktop/re_1000.result", "w", encoding="utf-8") as handle:
    handle.write(f"{Re},{center_ux:.16g}\n")
print(f"Re={Re}, center_ux={center_ux:.16g}")
