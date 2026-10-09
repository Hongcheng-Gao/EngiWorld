from cavity_common import solve_cavity


Re = 400
center_ux = solve_cavity(Re)
with open("/home/user/Desktop/re_400.result", "w", encoding="utf-8") as handle:
    handle.write(f"{Re},{center_ux:.16g}\n")
print(f"Re={Re}, center_ux={center_ux:.16g}")
