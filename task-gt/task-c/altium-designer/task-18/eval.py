from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('C:\\Users\\Administrator\\Desktop')
BUNDLE = {'_shared/build_native_task.py': 'eNqdVE2PmzAUvCPxHyxOoLKptKcqEr01x1UPvbWV5cUP4gZs9PzcZv99/cFXVnvILocoNjPzZgZDh2ZknHeOHALnTI2TQWJCa0OClNE2z/Js3v1jjV4X9uxIDXnWBYVJ0HlQzwv9u18GXp5J6BiCBeIk7IVLhbZc/h0jrmIPXxm5aYCfYVnHzd/HPGP+UlpRgLKGLSz2mRVxu1MDFAnWvwXq0TgtOaGj84xT3ap4gKuyZMtqnhSuFOmAIyFAuSCrldvfyexveMvA8eJ/y0kgaLLND3RQsyjFzSUuq32Yu+EI/tHpdUw987f6WzO9cO0f5l+InZXWOGwhtV8zCZZ2T+LJaDiuif0pYAn+VmoUygI7ec0nQ6fQ9jdEg/OA2V/QP6QYd2ea6wzOH2e1ZLTaYlktJns2dBMtnMNdmOcXAnubJiDekyXgb5uOCghC8ihfVjcnnYx/j/aWtn59BEHimFy9LvsjNUXOP1QEs5Wgv7OTbsF1gpZA8vD67hpa7EjV0ms3MeM73UROGklwpXLrNgw+SDdOyWHtD6v0Ys2jF9I2fHiEbZVqTmKwULFPrPili3rjg26NVLpvCkfdw5fllp/7H6CvhhI=', '_shared/native_altium.py': 'eNrVWFtv2zYUfg+Q/6DxSUpcI277sAXQCjdxi2CpUzjpsM32BFqiHC0yJVBU4iDOf985JCVRshOvGPYwA4FNniu/c+FhYpGtnCCIS1kKFgROssozIR3KeSapTDJeHB4cHpjdv4qM1wvBDg9ilM6pvE2TRSX6FZaGIh/zhC8rwoVkgi5ShgqvLkfBl+HnizPHdxZktj4/ma3PPs3Wg8FsPYLfQ/j+CH+DIawHBEUODyIWO4wX6CgH3+5ZkKXMRfOnyqrnvPnZGWecnR4eOPCJqKSgHxn6gtEoWDxKVriepiaxA2dUTP1CUiGLh0TeurVnntGCH0GTgjm/0rRkIyEy4cbkSanldMWenaRQqih3hqlMypUDSpwwg2OXPHKiLCxXjEviNcdQ7qRwCD7oHqCQwlgWDILCt/3vRyzMIuYSrYD0HIZOFT5JljwTzDaUU1GwIE9yFsQJS6PCLdgSvTlFQ8pglIRyCose7syN7awEjjYFoHx61tQ4E6hZOgl3jL5+kaeJdMmG2MAByMQnCp2EKxGLiJ8w43CGkjW7dz3nXkVN1Dp9OOLAa1jAuekd+nPfAgq2rURZS0FDGRThbaBCwcHJogt2mhRyiseszr07v4xtCUrBajd4hrpIs/CuUPR+nPAogXx3rRwis81kdHY1OfcHs03/6IP7wbd3NvXi3U+4+sMjvUYaTVvLOKXLwgdD12bT+NCc9NQ6G/g0nTeRW1EZ3mI8tMdWRNQGcCuO/lJkZe6eWMDrFNLR6aSVErVYI1ZANlIJ9nxVlA3pHutoaxdcxzza2le5Jlborw2sBed7jedscwMg+e70z838yJttxlCbenUMK0gh7WInARHYQHnUc7Ca8XBiZc4+8HrW6q3XFsUOoiR8h6jeQDq67cM2dto8LLXVnGkQdilq8NmlCuAOVjr3CkZFeGsD9O79FkDHFUDndZwsjFoFrFR3HGpFVzHUiLUiqpMRO0dbnsCFIVhMTk1K9ZcM6vwyWUxYzATjITSxXkeksQlizaLLdq8joYHvEsMK3wrOLsMaSIHMgoRLt+VaFqrrsP8b8bY8e9wn9PsOISghwB9SuQDpp+cuWdCHQAUDqOrbYnj+P1RHHf2pfdT5FNXMX8jipn31aZ4zHrn1jtdq9Q1j0/Gx0y8egyYzus2+uc7sjt+56aqGaV91aA0RfuVOsYFrFQfy6Wyw8nerwAyhgz7ecw1xbrTtv/PycBEoeM3dvPvas277f3HrGT+mYEphhd8AFQpV1/dsfXJCPDULbIgZGea7vRZlyl6+pJtZpHJc8Z/u5Ohcesav1yHqji6Tb5ejXy7G580IA+x7JxjlVJXAOwcwrw2eEtgNyD8YXbZRQaH/EJXrq2+Ts9H56Pri83h4czVpoeOAVvJ1eHMzmoy/Dzbl9ffApgR2w7bIqIgqyRfbgFUBrye5VrRnIK7Hqhca8Uf0abZRPRcasmfPf4ampz497Fkznh0Ac7+UOTxc2A6YsMSOWwPcwOvgpjkb4NBZEBeFVPVn4dVzjnoqO++ARb0Y9DWgfjobNamZgW0HtIbBKlVUE6TZA8POWG301Ub1LEP1NQsuKnI9brEU3mLNjIjQo6puHjetpJO/SNAduSpvgJwQrzb0g99xdm/qGteM3+Y5qMCh8ABsDI6HX0bbxhrR/a2laRitkGo4WgGlabrVTrfjua+VIOOLsap6v9BBeCUCCvdXQYfpFw1Y9wIMVPgPh5b7+FrXZdh97KtX8oOAolMdzEXRflRCh3BRqAfORdDR/Le96rajRZgk/icK6eRByZAZx5c0h6d1wpc+KWX85kf7KV1NeGpmsStAuQKUdr7DifXsD+lgbW8FTXUf8bhNrm0ZtNk6ZLm0/gvxksa/AR3nVXA=', 'eval_inner.py': 'eNq1WEtv4zYQvutXMOpFAhwnu+jJgBdogxRboIeg3VtgEIxE2+rKlEpSecD1f+8MHyJlyY7TornEJGe+mflmOKS4ls2OULrudCc5paTatY3UhAnRaKarRqgkcXN/qkb43+pNJWtULZq65oUR9Lp3TSc0l3a9ZXpbV09+7QGGSfL1/vd7sjSDDGxXNVjO55Krpn7mWT5vmeRCJ2BkjvrzSigudXY7I0rLDLWdCLkhKVVb+F2meZ5YkwL8fuaU1brqdt4wf9WSFZqqYkuLBuYEqCtCfiCi+YstyP2Pt5+TJCn5moR1+p2/ZThakLIqdE6uv6AHi4TAn+RAmSC4PN9wnaUQpuTrNCeNJGkagzHJnmp+jIQ/BlB7M8A/j7WYgJ8FqWdWd3wgZGdiGVjbQSgDKT8Xy6GTOw55U6n1MQvy0dqM7A+50zu4GDlYpU2n206rzP6nZSWPggwLPvWRaEi+kWVCUcw8SEZqkGwQq5RuJEU2mHyb/3H39bdff06NViUq7dVMiYGCmcMKS3EElSK4Qmyp1UDXFc1mBLCRUM4l1bLT2/RdFyQ31bYkeyBNIZW/sFrxGUlDHDCJZRxFD0Qa/9dQjLoPfs5fwZDK8kWfJQv/CD4w2IzpCgytU/7awg7kpaOKYLRkVylVic2C7D3cIY1gTL1ZNGtby7dgxpAWdglEqjCm6T2U9bTnPcDmA+pD5gPGxQA+QKvKXwveanJv/kFbIkzh3DscdgJ3KNENxK6QTk+mSzLwCCDnKTQ8QMdQgPg40URysobOgL9AdJLjld8ol8NMIpRdSxEfEBS4x8sMlI0a/J+BDjRoVHadOus9z+eV5jsoOaxFK/aFfMp7UHDtUkwfxTlImPGuvpMfE43LBdlCSkGvrgqmeWAAHVGQKA95MluRafDyHcvDOrjENmhcUCjRIQTdYirPtmO/WzSHZLTjPoC4OYH3r8AmkYBpBYfIwFBOrpZm9iig863O9eJr04v7jIQcACAptkxsoBd2wrfF+g2watNk7P72B8L56kDv/rPD/5ePtmUzCadz3yqi7ThRKhhSfBcZpAN1VybEWOQIwQqtPD81F1nkgdH+dOlJxV+hj0PQgOzCiCjCqjSJJibRM7KBQ3Ef2Tq7sYMcmIyUHm9Xlra+ZfXxTdDlm1YIqOjw3nJ8nYup6UWfmOLkBJdB6oUJfSQ1kZRwJq9NZq/ioIJ3TgKdBAl0YLh2MiWiEdcuA+NinSpUaHJgOUrB6VSEk1zoSnQ8GTBEza0SSxdHj/ElcxWzHuRgcEIMuQxyODqFZyOCzcXr0rS2gadm2lSI/QWF0V+8Z/6+PQuXanOoGXNGfuXJd8Me+zByIHg3ckLAwtAr8Acn0R3sQRF7OfnbTEUE5MdFEa2Z6zxC5d7T0cKEzx/gY1h1vmqoEfSZcVSBZz3oUVo4XJkneQxlHhE+tHJh3e+N/gHvyTumiy20orjHHBa26wRLV/Iws3t2PzQIC5duBp9I13ssKxB+nIhR4/FfBq4AxgU0jrjfcGPeJgsheHMhe71xskcQoGD6UDsi9aM8XRLvmbAmC/+iCLORkHErNdGeK5r0hKIvppE7UVlNujtZXfmFPJoPpnBhN1ea3gf4PB93k+sJvgdnkIEccnjig6o/7AV/IVG7Y2WJ36rHzO0N8lGwE7ceb818XqOtb9IVul8ptrz4btcew/uGO+T81/vg6t6aS4fecvcMQNwnffQ88q2puWSi4DcPzQuXN3e245GuLZm28aD+6DLTiPotxmF1TRqQlOPjVoFzO4Z3kRJG8IFRD++CFmWVTBCT4O2OYsFQSpZw8aQUkShNbar8q57cQCKUO4hZCwz5qflPctNhRA84kv4dpp1Duihza1n8iuEk5AZPMBA0MCiqnDJQ3dXmuz1+H0KBefT2YURbWQE6PjDOy27XqszqYp9ELpafZ4QLhS+UTBVVtTSPKrnVxVdC/lrp7Bbr0yr6ZysokdyeJvDF+Q/Evrp0', 'ground_truth/resistor_library.SCHLIB': 'eNrtfXuQK9l5V8++vF4SZ01sYxvHURyvs3Zu3+2nHnEmdj/V3eqXultSd/Pw9kg998qrkcYaze69RiQOBMfkbRdhDaxxTOyKHSBxIFTAFePKTYqCggK7+CeEFDj8ATYVyEJSpCgSL1/rMdPSSEctzfT4xrWa+kavbvXvfOc753ue01/8d6/+8id+6Y2/gy09vg97EPvaS6/EHkl9tgfUnL95HMMegqcHgL720ksvJR89CPTSy48/UY/Rwxg2ViROlJx9ezgYxb3C4WBYaHX7ncFzJwW84LZvx0fRqNsu6N2DYTS8W5A63REcwnf7yTu524sLzXh40h30C+xNYtyKu7duj/apIjM2uv3BcPbdfnHc6Hffdxqr4j4fSC071KyxPOiP1I4wOO2P9umx231/TO6TxORjMzqCN173KD4pmPFzBWdwFPUnh1DpQ6h9btiNepMv6PQX9L4S956NAXg0bpzEBi+4+95YPeEtAZ7d23E8ckd3e/F+ZcwPhp14aPXnn5unRwfx0D2O2nHys/skNeaGcSQMeoPhPlmkyVKxwo7dfnRcHXY70/Nmb6bHE+Nm96R70IvPvk+9nx8inJ6MBkf+PlkmiPm7YPYOAE8/mOCB8534MB7G/XYcDvrxyeQnxe7JcS+6+x7g6mgffmBwdDxlZHEMPQUnEPuCYeMEUQEiyCLOTo4R45P2EL663T0uOPFJF64yvFEgiULNun10o/DdT+EF8okbBeImxRZaNwo4yxZGgwIJT534lgBHUkSx8CRNkcWCEY+G3fbbx3Y0HE0uTexTs2uTs2tTybVLRZw+vza5zw+iYacgDPr9uD25Opu8GUXt0ZMnb4crQF8/N3llRL34RsEdDaNEpBJQRKVc6Pbbtwt2d9S+Dd8NetB1BS8eHoE49m4UWre7o7ig9k9Oe9Hkt524HR/Db/fic5zkGU5qASeDU+c4qYs46WvGSZ3hpGc4CaKYxghCHg1BIE6ycFOGcZzgvIhOGHaPjlPg9EH7mW7/1o2CGY1Oh1EvjdPund46R0ifIWTOEDI4eY6QWYWwtBkhU8mGcBXbmDNQ7BkoIi2C8HEEozFL1+bBNHafOtOpnwelOnYkwXLEfXKGejrSV44gGP390aQN3eNRMqtediztzXT4q4H+GPTBt8NzovNfAfQo0CuBHgP6U0DfBPTNQK8C+papCTDR/X8anr8V6DVArwV6HdCfAXo90BuA3gj0Z4HeBPRtQG8GaszO/Q54fgvQdwK9FegJoLcBfRfQk0BvB3oH0HcD3QDCgW4CPTU7n4TnhJs0EAPEAhWBSkBloArQ9wC9E+h7gfYntg2GvQvo3UAcED/7LRGeJSAZqAqkAKlAGlANSAcygEwgC8gGqgM5QC6QN/udhFrw2gcKgMLZ5/fjY97/ie2W2HMPb9n/idws93/S1k39n8hZAegy/U8AXVX/C0BZ+z9p37r+b8xs5OX+/3NAfx7oLwD9RaD3AD0NFAEdALWBOkAx0CHQLaDbQF2g9wI9A9QDOgLqAw2AjoHeBzQEOgEaAZ0CPQv0HNAdoLtA7wf6S0BjoL8M9P1APwD0AaC/umn+WbQeLsw/udgRMH/PrBtj0InnH6n9TnxH7U9NItAx1nP9eJico3aSt8LpEHCPZh+QY3dwOmzHM6M1sQjnmug9Ynw0GHvR8FY8SqzXyXfvOLdOxbrsaq5eTRt9JFuplEuJXpu8pcoTsKqYTPpxZ18em4MRGG0i7yWKZfKLYKEBW2711VF8BICWucn1ena3P2tbMgz2Hpj6WHtTX+uhwmMwoP7PxLHao/ao6VhZPugtydicHUTuJYPhV7BUhzJg8AIyrt2OJ/ZnYgGnuUgtMDHF0hT7E7EYtKOkt28GwGgGmAB8HN709yli/hq+SMzOftzqdka3988YVSyRZLFMrGLlGb8bLdvWQ7+G/UgKOkMuIqWXu/sMk78PFlEK4QRgcqUyXS4XifLUyUikWz1Rup1OnBjPXnwnaf2ko6AbTs7RSL5vCK1GbYGRy2iYq0XzRMOTy09MMMEAufdZYTwez9/BmwlKI7pTsI7jIfxw/xaYHUeT16fD+By6oXGqIlkG9lMI6GwOjCRusk9MUXqDHsCC2eMclWpxTc7DfhKBqZgDJpYgjlqzDh48Fw/PASk1SQwVS8N+HAGphIBUuTggMkEiiWemgJpR7zTdbzU/bHJKDXseAaicmUdU9gFAEM0ZokFvFN2KC85EvM6haTUl0Kp+FQmtkgM0bwgcmkBzBopbSHRPrxv1R6lpw1RUwQeu/U0ENPCzrx5borqm2IToJH7KjtrPAO/Okfmm5DhOTcL+KQoZebXIUnMIvjCH4Kk5pNvfNIc0nZavWHUV+zso7FQOXHWNGchEJU7xtW/34dxbd1Nj1zZsned47G+j4GVXFpnR2VE/Ohn0u+35bNw/PQQnC3iXmlkMyZaa9VDGfh6Fjrl6dJKj4WXJlEnwF5sXERaSaxWmYa1ztLrqthzLlJBjm2SvHm2ze3I7uotipKIr9ZasVbFfQEErXj00wRFayfDGSaJGyDWJy8pMo9rw65wdoGej0tUjDmDqGaB4KXKWaDjVAPsHKGTlq0fmCAknZQcnSsBNPSsnq6FtNTneS5u7s/zDQ8RjE6dwtU08P4h6bOKxpmziL6VaXtxkEpNLNnHaqk1eu7ej41lceNnKnXNpatWXxz65zxBjn9qnS+MA/o99ep9mxj6zT5PjgNnH4RN2n2LHAZt8WdwnK+OgOPm4lMxiQSn5uJxosdSoDe2W4CnYz6QaBT+6wTtaZ76s6U36Ym++a9qBU6cmCWuNnTjqWP3eXXcUjRJunCvAZl0LFcfE/j5C5LJjXGtirUA580TBEX0m8UHJJ6aOJsUShbk5CLbEUZy2JHyxzktNUZ8EOc7gMthnU74xM5sHJ01Iumy5LQinmMJ14NTJjQI/6Nwt0DfpO+TNEnsEXrJqCwV98FxBjPsn3dHdceJv9aZWj+QKiXPsFwmfYQ2dZD3wtibfe3ePwaYVeF3lx2I0ig7Bh51KHDk9oBmd9kbVBrSsRNNiiapQOC1RNM4U6RLOC7KEMwRVLoPMFissPT0n8VInp7AMR/MyI+EcQxE4w1XKOE8KMk4IVEWmSrTMcvL0FCd+tptkdianEYTIspIk4xxcCmfYCrxiKgQuFkmJ52SJ5XhqetocsgRafnSXQLV0fmit2+8QkyZ3D6DLZ54+9PlZF5q+anCyYk3iTWd9Vlzos+Lil+WlLz+yKKvpL8sbYw8Z7W1xKoHcs1G3N4lA20NgYvxcQT2CaTzlhQqGoDRt18F+7lpk0Ig73dOjjWJoXp8YUmWOEliZw4sUzeAMKVI4L5ZZvFiu8DDVFis0WCYXxVCWSEKUWBF0jsDhTImU8XKJK+IUU6FKEkswZVDpGcTQ3CiGZ10VCoKrhWD0rRc9mkCIHny5XvRo6tpFrxXwhu4ETexT1yJ6SvfW7Y2Cp1+f4BU5US6KnIAXGaEMgicLOMcXeZyuVFhKKBGEUCZXCF6pVBIrjFjB+bJIwvwnV3AQURIvsqJQFGWRAjnOInh6dsEzRamhBZKNEjwGJXgMSvCK1y54mtpoGJrpYC8/ru9x6Rz1qlg9uW2sfhaltyOwst+xe+S+2bIM3rfELSL3XtbI/XkeNh25Z7EfXDGEsgQyiQwDaEV4ui6ptqJrTTjM6A6Hg2HSBuyjKNcuB0yr414KH9atutBYxIaK1FA5YFsXyvQ1UxAk2cuOjs4B3bpoZosLuGa9Fi6i+7tXk4PIjC5JMszG5gX+mY4saookZecfm4fkzSsdCokZkHKLhYZYCzhzEd2nribpsBX/NgRYHcFqWA3HyA60lAfQzZHg0PKqpsbVF4F+/EpSFFsARUWDHU7wa4G+BPEjV5KqyA6xGsMVUgEsSXW4Gq/5i6iev6IsBZHV8DIGvfgOKjDo1UKxKps89ukrSlNkhsbSdInFCRbanTEoWGvUeVVoCQtYN6a3yeX8dgo7TSyEmFjiPK3NptLaZ2KQWA4rzAr1BMymbicdi7A0m+M5s5bUsyzFJrHvefOk+uUsNvng+G3jtcelkv/I4353ehy9R6OP+y/T45g9Bn3cb06PY/fY6XHP7xppXOTx+hE1EQptiwBj6EkN03cEZAp3CVoaWBrWDNQczeo4YpLhnkYSWQIRSRSWQ4hH633oi2jPvd/zAYLLg8HoeNjtj+YH5Ov+VoioVO502vjBARWBHwvnlUtMCa+UygwRx+WDuMyscH8POx2y3DmAgykK3N8IrlQuHVJ4RJPFUrvdYeKYXO3+opqaPf4X1lSPr+suKv5HTQrEzr4sLXxJJza/Oi+hJmfviP3+aa+HihtSl/S/MtZ/ziuTN9d/XneN8v3k/1m1hinrYZif/5f0Q9r/o6/f/9PcOmc3s1vh5DVa4YHSqjbqrnR/eoA13avrRku7Pz1Ax+Droigo2T175to8e89vBJzietl9Afa6fYFAMptWTfHvewdQMxtuI9Sl+94BVDleCkOnmd27Kl+DdyVbRqvpiUL2QEnlmgMlbuhUA66h3O/+n1WVOd/0va+b/0dn9/9U1TZ0w6nn5v/RV+f/NVTLcptqdZV/RWX0/6iM/h+1yv+7//w1vV7nqlYj3MZfQ0EDDwaJbVnALjhqhlsPgxpvL/tr/2atv0ZWkDlP19JuFChiIdVJ0jcJ4k75ZrGYJDsnVnaBvEmV0JUf8EskVbLLJcKn2SJOEcZ1+H105yAuHlJtPCrHZXDgShX84JBk8JhkKLYTV9pForTC7+uwlTLbIcAsLpXbcCWWxA9Y8B4PyXaJIcAnhKYs+nITP468abcPEmdupUu4jgPZ3UFJqtoaKFqUO0ig3EFyR3eQ2Nb/S9ZLzddfq+1Bv5BEHcD2ynr+t6XOB08hkf6ETWersJPFeHtf3KOS9Vp3XvjWpw+wvb1HH8b2fgh7YvJN4r78lWQdENAPAf211Bq2D81eJ+syfnT2+sfv47VsLz+2f3x8U/zhfMXxhdjD13nt8f0UefBkuy7pCr9V5GFFlGHK7cUM80c3mDxfhxB3vanW1AD0+TdKiPuFXf1EdsFiYjMvdqgXbNXE3dp5QCUZNYXJlhSpnDVvuCavBdhP7+oe7ojPnJWUg6yPwCaX4yXfUPcExw5qdexv7eoO7gjM1hvVKbTExHoKLtTrLXPN412xKgc69vd29Qp3BDeZ3ZLJbe7WTJzred9OJryUS1PjHNUwJOwXd/YMd4RJ3mSema0SEbtxD6buYbddaHVHt09GUb+TYJ6H0J7khLenihSkuiyaoY9e5EDmKI9G907cmXP0JL3kCgw+q9ZADmT0sqVdmTkFNnVYC4PDROWdgBaLOnEnVTzh1Vq+6TjI8YJet7QjPnYZ30XmCVxN4MEhQq9XY64WXHrNK7Gw5pXYZs1r1W/oqmRUsY/tvIhpR8YG8cksoBtHYM64TUVYFdblm7IXaLyHXlBXzGU2oirs+Ww0cUl5UO+dUWoWCquSJdSrGjKCRuahYsiqMwU2M/CS/aOmadfF9cNGIIii35TREbRynpOOqiej5nAwPFqE5iuq0Qh1FS18eWiamXF8gYGT01MVeVJDUALPw34WlYLJQ8fwFueIBcEyTUnwLAedNgrrQtPi/TpyjFB56BXBAg3sCCqnz8cyDN+Dbi8JyZxbu3qoCZogoRNZeSiXqdu0aCIuB8TDsOVwdsih0eWhWhpnTJu5jGCIgf0QDVOKr9FU/KbEm8j5hWLyUHwkWaRXxJfdeNhNl53Lqmg2QqeJRpiHBplsQpUhtVVzWmooVP2FJX8XEOahQuBaHmdWGzrnLAoh+MvgF/RTaq4uKMlCGDQX89AjuiXUVLO6xEdrEqIopGLQdZ53vbBpIE0wqpyLIqZL5SVFLMbHaTWs6ZIn21qIfQIFrpLLIK4whSY+C5TLvejoaDYBXkhsqVxV8xzeQWpimsjV1lqTPLe1lsw3dBGdzSdz6VyWoZc6V4/7t9K9W2/4bhDwOppxVI4mjCoJq02YlhaageEayC0L6Dy0h2l5BdeWBFVWJXFxdpG7/e7J7QJeMJYkUBFCvqnVA+znUGjz0Ca2BXOgGkpiQbEa7tl8Yw960bD7/qnxVYtTkzZXE2tiXbfRfc7m2Oeiaq7u85ATdbfOa0h9QuehT0o3k4Xy5pnZGg8njJMHw3aMg7eXKudompprugIyhkPnoU+gS+/GJ6DdLhjXII3xZLPZ85qdmh80a0oVuVkUnYdOMRq6p9q6VDA4D6SxYHOO5xa4JqfqHK9LCwEodSoDyTVS20IEjtV0ADrK6acruTn9OEOkN6lhiC02qQk0y1cVD+0vMHkoIjC+4yQpYZ8OjwcnM+NtamukbCFb4FpK1USGyZhc3JkkmTLbiWuaUVlE5nCe5xoNGxkmY/JQRBRxtGRCrvL1vZbaCExLQU6aDP11WS3R8Jyw5trIahmGyaNaJnFkcIIlMlfLSFqtVW/o+jVVgthbVIKY1ZoaNhvalVWCFDdUgiwx70IlSF1pyYpSa2av3GfKqMr9s+tdd+V+u9TpEB0ywtsHxQ7O0EyEV6hiBS9HJBmVDtvRwcoKjihq03QxgjMqJRZnSm0KP2DpDvC1TVfaUal0UIzWVO4jmpq9VMMNapJfB5NufakGU0GUarDEbqUaTOXlxd/w+Mjm/P98P+8s+f+cd/a+n1L+Nq+ZglyvXj7lnzA4nfIvLVQDb5Xyx8nF2bGcyvmTqZx/slnVxd1aM+f/TU/z1RD09E+kgJY3VWOugx3swyTuRJ3u6UlyF4i4PUiCiHfPPkHsK3ueJfD1mi1ziwk2kt5y/9u0mlnCt5KNRSIbuIZY9z3d3Ipd9Hp2MZdmV1A3mk5VEbdjF5ORXcwadjHZ2CXZSkN0w+2ki13PLurS7NI5162B6bIdu4oZ2UWtYReVjV2cw6l8qDUm+3lnZVdpCdslGaQ0A8fwbHmyr3hmBpVRDEqzJAuEuipzftVqLOw0vIkNlfVSg19ebBotqcV7or7gbm3kylLNx3q5wdcJDp5RcmpCg5MDXl7YMHrjNI6Yx/HLz0yyaSie0nC35FnWmRxfNzfhGScn3RB4pWp42/EMMZnjl1d+YtWSm6ZnbcmzrNM5vk794Rn1n2sqtcAOnRXleA8Rb8Yem9yZAV0uOD3uSWxTueD0uNdgm8oFp8fN3iDKBafH/e5SueC642ZlhcW9Ivq435geV9orbS4/RCeWF+29MnG1iW+br8pNx0KuQkSnlnfFt7H2guM8zeXqFjpjxuSBDS4m2R4nzMOs6ysReb/Vsn3RQMaz0LnlnTt4QyhQ0J1aTZINdMK2mAe0jJVTpu4aYt0wkdU16JTyrghdD2yqqrK87nSpd/Vqy1ECx8Y+uXNGeVeAW5XX6EKj4dcFdAkaOrm8K07yJsUeHS2IYW+5ENawpIakiC10EoW4YnipVEQ5XX5Y3qb6sKE0q6pUq2H/bOe08+WgXyaLUlNrGqfL6LImOhftQ9wk2SK6IsITQlXTLR+pe+hcdc/apLkWcJbhaBJyQNFMPpxjyE3lBkLYAuWkVJEL9OlctM5kO5IsO3fVNFv2PA6pvelctA9JEEa2ylON4wSlaWrI+Z0u5dPNBFPJupLADXxNagUuUlHSueihbGm9oFrlLJlXkXYunYsCypSwbbr1kA+cOrLYgCHywLdF+ZUcyoaj+ApyvmbIPFCWNi8iMExFtHyhid6xhMpzvl5b8KLX66Hh6ugb8jC56JJL12kErmJLloIu4WZy0TXbVMIoiiTVDd5B3vKByUXn7FJIpoYW7/uej1SRTC76J3O9atPUVWeD78iU8hxQ61b/mbwZcKoQoMd6OV/fcU0lqGy2FM+X0JW0TCWnuEDGamkrrJtSrcohDUg2J4WzuWg/0AKVa+k2Gl4umibLigfRcexAdDikOcHm5bhQxU1rqlr1lsYbkoscuWy+YbM16yQdq6VxtioiTUU2F22SbaFkwwzrWsNXkVMLu4UeqVxdCZjEiXLL8kTsMyhsxTywsSRBkThRyl4DpqiayDmCvMDIrWrAMvf01kVggiLyVZvTtykCQ5Y5VDYVgS1y70IRmGrXLdMPjeUisPbaIrAigSgCk238/JK4IVevo/4rjuL2Adlm8GJEHeJMRMX4QblE4DRbjii20ymV41X1X3Bgu0O1WfygUobTqEMaPyjGbbxDF1mmTZaIqHK4uv5rTSuzl37ZfL3pNEwHUfpVJBGlX0Vqt9KvIvly3df88bHN9V8gQmvu/T25nUuGvWe/0Xd/0dy6YahN9fKlYMTS/UVo7MOZ95ddnBMZ4uoXZahSQxR1W0Uuv8kF49bLb4yW6LWMloBOreYBNZudA21Rdd1x0OtbcmHlFl59w/Q9VRA85OowJg+Uuzj1Eq+5LVNFL7Nj80C70Ss1fIF3q7yH9EqLeUDbIsBoS82qIFktpNtXygNkpiitKWq22Qy13W+TvrMwbkoINTS7KYrVBtKtquQBLeNGUvVkYNQD8xLb0F6WeeuCSYYoSUoTvPmP77yp0K7Qsm4RYBiyK3kb9qcgqXyGb4ZwjVdVHbmuo/fvyUWZXDq87XO2pvAw5zy/895DlxXMdbESqSVqTpMPlk2wLbYW2hXa8s4QqVyflQzjuo/er6eYr5JDlu00ZdvS6s0qMmtK5qJGtqqKMd2qUlVdHX3zvFz1ydqEla9aSt0KBaS5QOaiULIHsV21LvicqWGf3XlzoZ1t7F13sNMcUzBCw0JvlpOLsqE351C5ViuwGk4NXaiVi57JEndv+a4daoqCrHairlrPXNVGcUaLDz3NRJoZVC6KJutOZ3LS+/UwQEPMReFkTUq2QsVzOCu4sqrRLSbNbFue1atVTvE1Di2kpfyE9FIledVmKOi2gp4ActFJWTZWNTTPaYq2jA6q5KKWMm1m6Dc8jjftKrpmMFcvZ229ehDUPEOT0V1Lk/nwjmaKG2oGDV8E37pZQ9e6UfnA22LX3BqnKNWWgC4Kp3PxdbLVutU5wZC0wEfXuuWiZzKt6XAsXuKbDfES+xLtjG/DkgRRl/xQqAXoguRiTkNk0xZtoVbnq0rIoyeXLRQLe3WZ6UZN4iTOqyIz09tUgLLb7k5CZ89MNzTHbvKWjv2Tbe7lQ1eyp4O3W3+cedW7a1RVUwfzfJsVpgyR58JkTrFdrh7YC0Nm8zpu8ppWJuu+pAihsXCTxI0Mo652aXJLk3nJUfyF5dGbWURf5dpkR/WUwLKbWy0aZZhcFycHrizqgehtt2iUYa9rcbLH6VzN4exNizw3LhrFMi4aXb7HxFUVzjBXVzjT8gVd8UTxygpn2Ey7J9FrC2fCaqsaOKqVvXCGpTYVzswveV2FM2WWJNjOAYV3DssHONOhGRw0QAenD6mYKMbMAXlIrrrlcQxqohxX8LjEkDhTbh/iB+VyGacqpQO6FB+USm0CUThzsZXZC2equiJWqwaHKJxhadSeScxuhTPwoy8/vrEee/SKO4Ntcf5bF+8/5t49Ohj0zqb389uQFae3IXtqcjG3/fTTn44ePfxQ58X4+ODFWy9GH3rFgfXIux5pffC48D/uPX7vy7/29L9++l9i2A8eP/w/p2fSO5yZBf93LOKXT/vtZG5M30ONxMQp+P0JhNoUwtMvdl5sP3p4HL+4d3Drg48Xvnrvy//i8cde8/D/+t43/NGv/e9/++43vvV19wCK8svfJ/zMe9uPYOYnvuXZ+7D/HWwAfyOsgElYH56H2N2tzn8d9vDe/F5ij8L7337fuz7/+z/1UfMDv/W53m9+7jMfXHfeB75z+ixjXayHxZgCFGEd+D/c8voP7L0KnucYsp535+Hps4AZmI3hGAF/ldkzgZEgrzjGZvidAoya+bWTkfR/X//u39P+ODR+4bX/9XPhrz4+kcHnsPf+w//44H+YmxuT++fNX4vQ6hHQro/HsAew9P3cspyTNP1vvO5i+6mz9pcm7aeztR97BJ4fmP3uv/q9L/S4vf9U/ZT5Neel53/yTdfQ/r1t2580/d43o9vPwGtqy/5/RSLX//zf//Zr/9tv1T75eezX/+De4WlyzOF33V/tN4G+tKL9yV8xY7vnj9dD+78Jnh8CeiXQV/7xo4++6g/+n/gjH/3C50cf6/7h/dj+AtAfvXl1+5N+J7ds//zaiQ383z/8uZeeeOfv135671df+MXfob+SHNMw76/2Jzcp/cO3rm4/kXHcp9o/8aMSNysRqV/6yveH773xj6TP/Pwvf/jL927/50kbT/Nv/6tnOiDLOULCg7dMX7tw9QHonAi7hcU7XP/xHebfRCm+YfbaBv3Xxzy49h1Asj03Xg/tf3CCI3v7fziRyYXru6D1j7AD4EQP0yefxFgLnjuA5jbyt962Q/v/OtALC9eXsVP434ardQFDfws+FHa4/o8BHV2R/QR6b2H8jQ/v/Wj7h59896e/+rNfUn/l139g1Tlf28JO2fb6X3jn25w3/cZrai88//EvfvKr3y5uuv7/B6PDY+Y='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('harness_parts.SCHLIB', 'C:\\Users\\Administrator\\Desktop/harness_parts.SCHLIB')]


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
    print("true" if _run() else "false")
