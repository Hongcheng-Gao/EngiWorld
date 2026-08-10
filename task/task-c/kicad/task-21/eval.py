from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
KICAD_CLI_PATH = "/usr/bin/kicad-cli"

BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/native_kicad.py': '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', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': 'eNrNPGtz3LiR3+dXdLhXWdJLcTUj7yaZWrrKkbVr1zqyS9bm7krWsSASo2HEVwCMPBOd/vtVNwASfIwerlzu9MEmQaDR6Bca3Y3xPO/klhUbpmoBq1rATZ6y7GAxh4MDOONqI6qDhqk1yKbIFQjesFxEs9nxmqc3EuoKrmomsoiGJU16tZzNI4Cf84JDw4TkcraIAI4/zWFV16oReaWAb3Op5OyIPizGH16aEazKdIeCVTeg1hwEF/VG8QxSUUuZV9fAFH2QDU/zVc4zKOqUqbyu5OzHCODPtVrD8acXkLJGwprdcvjl9A00LCPo3x399YhefKlyla4RIvYMZn+IAN5+mkMuIa2riqc46xVXXziv4EzjdrYI8TtTUHAmFRxGi7KEL3nGQ/rObus8k4Tfz9HxBm44b+qN2ke9TGyWsz/2qQdMwi0r8gzkAd82Ar7kag3+LRcyryuYB7M/IbHqSrG8clCpKw6+2BQcoigK4Kqo05vZ/DCC8zUHxcQ1V0CfJS94qiStVQmGaCHqaV1JJQjmlzxTa91YcCZYlfKZ53mzlahLSJLVRm0ETxLIy6YWClhV1cpwgLqkdYFTYIPtc1xvKsXFzLzW0j7JXftYMrW2z4K3HdYblRf2bbPJMz0JymiRX9kJPuLgmdzJCD9EeSW5UP5hCLVp+VudV759yXJRsZL7SbLKC54kQQheFHlBoGHLdM1L1uKOvDvjclOoEFB39LNda1nWVVQxld/yhNhqx6V12TDBUUcSvsWmEJJVXmW6W5IWeQjmmVe3ISRiU/WgSr5tLDSSjlD/l7CiCIFAmSchVYhis+Gz2fnrT78m795ADJ7VbW/29uTsBGLYS4DZ7BuSlKZgFTe6ryV9G780UkTKigrjyraWNAnb+OiP0Q9R9HIe/RDOvoFdPP8xihYvQ5A1yVq5kUprsdFfnKLeKJlnHNSaIdNTxarrgkezTx/fvztP/gNieHkYHc5+PTn5mHz47Rxi8HGaEGgamP8YHYaweBkdBrPj1x+T89dnv5ycf4IY7rzjT3NvSd2xyx+iH5DJx58W2Phy0Tbe64Ef3kMMh9GPAN9AWYbAq3pzvSYDWdWiZAVcizwDUW+qLK+uZ+dnr49Pkn9/9+b8bfKXd6c0eKEHz/767sP71+fvPpwmxx9+Oz1PiPKCRygQecF94f3X5xefX8DPCAz8z9l3Abw5O4bbvC60HgF+/zcvxFF/+e39+bv3705Pgtlvp8cfTk9Pjs9P3jwD9Kbq7FnDsn3Aj1+fn/zy4ew/J2Fe+Bf/9fny8rvg8+VyNHI2y/gKktaqJ4Kv/FUTLGcAQCRsRN1AXrUi66+aEDxs5ULtPNMT//IVFLzy8VMAr2I4IjuErxfzS4hj8M74igtepdzrRuGfoL0LpBI0+mJxGcyc9tO64hZTzdH8Hzzzqxpt94sQMlE3iaqbpOC3vEiYin9mheQGtXwFVY0akVdSoUE0A4tcKgd7Mxd+M3OjpYAYLi5bWuRVxrchpOu8yJAmvNqUXDClQfZJ4cxH/c2E2jZjQ58E+Uq3XhxeIuQ7D82lF4KnpGJl4933u+NfWlcqrzZ8CGdEDpqTcIdXcNhhgHMhW5jynghdEyViTcOrzHeZQQCDoO3NC8mXD4zV/V0u6++Wz42oFcl9QrtugujwSvlNemXozLdpscl4RhajFWAkmeTXJdeP/6gr7t2705jtzBe8EVMrIEa3HG7Sq4v58nJEnU6u/EcZjU9TAOyf7zK+XVUtSB/styCSigkl0aXwvWuReEEQjPVXJlc70uGOTq0g3923grzqq3STXoXg0LCnFsQ1yVXGV2xTKH9sLEK4uAwsY1fNA1xlV7IuNoonDTqgtczRZJJFaVhmjU6DIhvrnVFbG6Y8DRSHOR8blrlfDUc0gFqQNaKXAH6CI6D9QFkY5rt+ow4jW0B2h1DahrDa4bRFzZSGeTG/DMJeg7VazTaEpuutZ3C7mxbbn/bNAfCjy8DaU7OCVzG8JK0C3FUJS5blrJIQk/sVmVefwGnIW4S6he+g2cIL3SutpW96BnCAeJoPMq/aDzSYVrDrDXb74IfdFFSX+/42hF0rpS7TpRY6wVcZlyFUXCXo1ZinTZmomhqMULTD+gb56XKcT+1y8LvYYNA3VSPbRxshyyb2QZa5s+AfLaDO+EBKK27FdGBA2v5GIu37QCYfs/oDukXXXPl5pVpwWgA9jxZtyf1E8Jb6ED+mwkOs2pG5pMWiSo0nbblrjYht6AlT28vKk7HzyTpXMjE+rU9mEp1Aa0+2ZV6FsC0ZyiI970qGmmE9U91rHsJuDjHQeN20CGG3gBhhUUO2DSFDtdgu4ECPwIfdnL6qhICrREM/RDd1blSV5CeEv6MA+f4BAtrOEUaZV0EIPjXgOASLDQfZjvA5IJSpy84gjhMGfclmV9JvUF7m/GC+GDkWf4ef4HBMdUNW8pUeFn+0uH+H76FxJ23GUIkEZI+2viXHQy6BpVWZVz499/rnKwPwle446TN22JuGc7FpncXWeU5MMMA3IiNDzWdJgiINNXHMDd/5TZ1XE66hTycI/fXi8DKEoyAEt21ObcFMW/XsbyzlVbrr77ydeIaQ6NN6XoFFq5uThXAFMaFDQ4KQnlGsuz52Cnd7ZiFIrvwgiFiW+VeP9L7q9Wa6N01IRoPMLRknfZrKOGLbQtrjFrFq55f6qCqV8bY7ugbwE2nHXGsFthEJiB+Btu28ytr5754z/9fOTlKguXSby1yRW4mUcWjREie9gZicvPHXL2sMB1GfjpdmN6DWqKkbP+htLBXPr9dXdLxwmIT2WyPvB8FybO3NGDraVBbpsZKbD8ReOygY9dKoGePb72aE/6quC79jy+8t4HZzX8u5NcjS8T4H21JfGaqJ3Zv2ydGhstInyomdtoN9Qdsd7nOXEEN1sdCyZJHqew6SX09Mbk8ODgKj7Vzy69F2XrAdF4Me1Ob0IVkZ9KE2pw+vskEPXmXOd20w+j2ozeuZzaFbge8aRfOicTEvOKl5JFiP+ELP9TW8t5/mHjk3iAGGArAR41DeIzNZzlnB9H3tIhP2rkOtGxaXQRDuP2iZwbzK3KH4+shA3ZFIgyODnl50G8qAKFYvjF+S5DJpBJf9MyxKIh5RJ0SRTq6uHGrt0ZzHjyiErOQTnMee1plEFxp+goU9T5KizC81Z85Ozn87O00+vj5/m+iw3Z/ffzj+1XuCBKBEoQVssTYomeV6Q5s16Ww0dbG7JreytyzT7KyM7DRpsOGi3XC7MxU1ICf7hr2jqgYagrfdecHlKGpFMyCpXj4BcZaqDSswpImuy5am3IaQUMhAQwrJC5r+NCFrCGdHnZMQdiM4k5+CoYeC60RfkMEBXNFON+cHRzSU/Im8gn/kja+xD1sHuC/ReqVaerlON3GUyQSjz0sUogAOXjnRdBNmgNhp8xWTN0mexSaijf4WbyhiHVtYetZMbOgNYrAfIsGbgqXc97pUFQZzutSLZ5ysb+Dg4AA+Hv8ZUp2lOTg4cEMBNmauc1XtKlzfLuJC1GS7PcRORxDQqVvCne1/7w0pLbTLL3ZLxzarNdQNypKdBhNCq4HLy7e0CUSCs8xxBJoU3T1KEfjYJ5iA28uHYFYgBC+vckVkRQIN0nteMIUBjshZkbgzWnQCG1njjYIT+g8Pb0wCnyYZDQd6X8IdnyKUlo5IM8iacicx4/dMXOxp6mE+zesUpWFS8ix2g21kJrtQGy7H/G/jmg4hOkh829CRIPZc2dIqEZvB/fDtxEQUh8GzrIZrfX5LWh2Dw9PyODDnkF9Tu96oZqMeHNP2tchjK/nG3tkcGX+28ChDMvdMosSGPFdm1xG35NH6knZqF8sASTWAq13fHmLBnv2RUqdF4aMN7QO+EHx1SdDxWw9Y92n+UGDUbJBIFoqMOjgaSZW8ZJXK06TMZclUuuaOm5evBgRYzibAyloonvl96H2NYUVRf0nK+pZTdoWGOSmrXt8rvqoF9nNDyxOEoQPkOHHRTdUnOFspcjBdqGOSPhNovrLo/i7WM4zPDxMUtjrcSkUXq6/xZOQ7NsAl/8yVGfJCx7B7fR5MAqD07O0wUjILcm/0H10P4zs86JB14OL466A5uE1AfRDJ56YonpSHoqfHUg1PWvUkes5yH8ik/BOxDJ674VR1legqi74UdZI73ohckZ/aW+qq2GFZzPdYEkPODJ4SaBGYUMfCGMzGl2wH6ZpV19yZwuxFd15ffbzlQJ/cULejQt5ySrHu+zvVN/Bzri13V9EjtauBBTjCJmq1QqasSdwIvDnCY3PFlfz63FJ/v7Nhedc3J3Mraa+1h1TBVz3eH38ahuBHJ5a9CSUbM9KswY3K5FoGoYYeBcjWoqHTR49+ckcndjrohtKYPUBaOYKUWeJRBO5/P9dg+9qVdomG8XpdDE3syBztbdbKFQBLEDvCyhgpHSwOjpa9EjHyxlt5SRkJzIXrvly63uYTFLlV5pV3l7LmPtEOv9c/aVkn0szY4+ngUNZqcsqa/hejncZt6MGIbvhO+m4soVM3TYqXBz8scV6W5ljDl3I0pNKpmcu4qjfigUK5yKVbaKvD+g5JlCteSt+RlaZGOesji0GblPW1DfsZbRucgp/KhREnmDLG1QsnJIwYQifO8deWBysPFR2rIky9z31ZQr2COw34fgKy4ZKHrG5PdIN+D1YrZDatSlHkppaW1sG/ji5+hkd4s+bgQQIhltjZpRCVoz1Oo5V3ly2jxQqHMAV3TS2nequ64FRPGJspRsTsSfqPS7jCcs5+KadbxtluLTJJa4EFZNYeUgrniebBDLGWyEq1TWu4wu39cvrGswFzGlcL8BCdXuvI8I/wc3JOT/cyCBASIrlGo15lydHt0dixGM035V24xnSathPuxM3SnnVutYt2E8KttYNEO2M2kFY3ox125EBoPv9hSZYK15i1dYW5xOM/yyuu/TbsgW6PsW65BCpkFXnKimJn4LXJutApLeR4uFjnV5SRueZ1yZXY6YJdLN01tX7aKNpIqwmzomuxJ/j6XN7pWAbFdJLBLGMODjpM8G+1L/AKV2imJNzZyNz9mI+eNmXEpMGCKSrhlbkutsagX6G4aN1Xow1uoiacyM+MMzmaXPOEKhDjyToOE4d4Szo6LOHQ4xcPj188Mr4rhIynErv9VRlkQzvrszmO4LpJxBxxEYsJdW2FdkJNjRtab6Quu7WeP9emmVFtOjaiu6dqaljYhqkDgV2gtyQHzl1zQDygxeJBwa7fO1u0bfrpvi8MTukERk4MOJsio+e86snMvoPmnnIM3UiRCfuMGbqvYYgu0begx8ygHGWPKG2owcVpilWVLnTulox+GdXaD2xQW+g85s94DkNkSh3p2MgeFNHH17m97zBk/yf0yAdlyo8EyoZBs8QUGiRUadAWGvSm/hoelHmVl5tSly6MWWCXOmn18LSJVCZlaNOyr2K4G6z1vizH5L3Qi3ji4i57HLA3UIZJ4MliDBdM5wzIbQhy1ysQ0ssLge+cIiGjDZjPwSF8S3kYWxT/ky6OMV9GaX1M3nAs8ZHbPeU87mqSHYV0sUaP7wJ4AYfRD/1TzMitHQ2n0T7f4ZwEw7eoaiS+hxahUb1yB+enNpd0sbjEncf59qr7dnS5H5tWALuhX2e1cTiXCV1SSIwn8YjNaHGYzBOgyBqodKMC2BWGgnfx4iUu9YoX9Re6MzGW2Rbw0HnCtNWbs9+elrayKbKgH8BOacMm31j30DkToLc1kwneGbLv+EyNaV1ltPNOfdHXiJT0Lp9+/CPSp7p4s3egc0hImTV7Jm89GeOpeONEpska7cmvtfSYyG7ht305NlU30qa8KKxiOwezJy+0T2qzXjywuMt1L4E5661vvKdm2L4GixHVp9HAICoP9tIcxYHMpHYCaPsnwvWjtMqN0OrombJ5N5I7bWVNXHUKqG4z6XcddFu0UV5yEjQwx/fWOm2Vynu2E9FXjFFykRBxENYZqmA6vsthP2YwmMBQfgR/kD1c9cjViYMJ8sS9zxeHXSwddbqtl+uXZeghIXid3jus1yr/hKHGMLhj24xZCxmvrb2OzncNR8J9e443FL+F3/8eXkenXJ3S8SKGb99+mn/r9XCn0SZ5hETq1qNZ0IYsuw+YASCR2esXtQkDdwyKVSSVyBu/n/hs0TDMsPWgKC7G5/GdevS2bIOZi6hTdZI96tpCNhtwXRjflKqlEBWEfjlVeoIFjb7BAZY20qtrA70yR4a65dUtscyQh8lkqWQ6E32K+gsXmj4eXZP1esuya3Yo5Xi4LsE8uqSaDCvU2qupEyPab17wlSHgvdvdVCzYlb49EeCxiEwGhHtiRu5Rp5S9g7nXCw//k9bYbtyTq2zZ07sYvH/Jmm9Tl4nByqGWi32U6Il97/0RUvQ91gkv5//Wj3EvYz/kzsz6+6q5/ERzmvvECSHiOze0lk75lKaLzka2ZVe6kQmVr1iqhu0ET1/q6Bpvcqxjal/N1ExcyyUZ+wupxGU4o4KuLuhf34RQcinZNcaDxneh/Q6xsI9PSDPG+E/ozhY7z4Gz5idv3d3qRtv2nsPmHSJx36IHtjzk1/yYZXD8/p3Bb7xNm6V3m7Nmn+C0BJlfVwxv0fstA+C/6Q47UTHLU6JqCPXV33iqjAAalxS70biAfFNyPn1epTVeTI69jVod/NELdT2VxLgjpY69oKuI+yw+k8R/tuWR7c3jhFYIMYzvMEeSM5GuncIy52JxO27qivJ4ZMoUv65FTg6DLQVwLiBH6D+Q+4BDepWFdy2lve6+tLfEaIs/WEZ0LepN488DikYP1zgovyKIzooMyNEa+0DHJJgC2y3XWxJz/TbzZz/YuLmb+MO6bZmg2ayKnbck/kfCOB4RftSR9Rcv4ATLr1dwRuIFL17YYrX7gd3IRGplUNuOCbMxMhkT5mKg7K2CGOnsDejdq7Rf7LF0fEv0mVtYux6jm92PK0xvYxN5QieCRz/j4Kg3XsvX8MEGyMnZMbURmHlojYLgYlOZSrzpTW3VxtXl5qrMFcYCLUGWcNfSBtd2v2eLJy0wJ1teNniA03kKInwtI17d5qKuKInl/fru+PWb5OSvr98n53/5+ObdmUe/iHHNVfoFSzU1YFU2eDBwwH0PK1PaiNW7yR1eJI/wn5d+EK351tRoqrKJypssF74eJ9tTbC5VUt/Qq57jmld0yx1D7zjf97jhppEmrjc+qadFTnUdvd/LcGtdRZ1iB7Gp+oJxQb+r4Zly30yk+N/BwQpLjOg6t5mSWi23yH1tUQz0e6cHweVAYqrbuPvlDt+sh1e3bpFoPykualwsMi9FF/h38fDem2BfMK6A/aTKuKB7FvYVI+sYJvK8Wf/KDXWMcXCUcYTsP7ABGNMxdaP+uRno52jeM7L0Xqd6Wp3kJk05z+RDqWc9BlV1xfKCY9G1Jsz9/mS9o0uDGwmtFEyYqP+HBOv0ytipyaoVN/c3GvGE2oah6SHhszYM3RlSxaFzYw1aB6ede++YTgn/xRuDP1hP3Ed2X22PMSfQrmDCSSRRnt4S7kZs8lo8sAjPxWnM0o6X3rKPbr/v/WgvWeUVbl5OaoJ+ZykSpRKco0ULIb+uasETY0e0Ke+udCTadkpbQpzlQjuyMXiR1/qx5uq9vpzR/zGmdtzUrYP2Pkh3faT1JfZ7M67zEk+cLeL9GDi70V6P01xIwURoZJ7xAl5aC05t9ERVdihS1KQfHadO1YoVGgI+4fU8JDC10JPrOJLIe0u46LHzTl/aWkIa6aNmN2FqJwTPiii12peBDHlaDKmLvdHjtVU61Ny+YU1grcy0teL3s2G+MKWQrFHU9quzd3pyU5ZM7DSx9LPvuKqYAaYDWpJQ4ChJSpZXSeL1pAh/5YuJ61uMeZmImG0K4BXMTXxgKFKmzBy9+r5MdZgEs/8BKZbYrw==', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('board.kicad_dru', '/home/user/Desktop/board.kicad_dru'), ('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb')]


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


def _call_inner(root: Path):
    module = _load_module(root)
    func = getattr(module, CALL_FUNC)
    args = [_resolve_arg(arg) for arg in CALL_ARGS]
    return func(*args)


def _apply_runtime_env() -> None:
    os.environ["KICAD_CLI"] = KICAD_CLI_PATH


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        _apply_runtime_env()
        return _is_pass(_call_inner(root))
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    print("True" if _run() else "False")
