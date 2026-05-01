import re, base64, zlib

eval_text = open(r'D:\research\project-engiworld\Engiworld\task\task-v\blender\task-11\eval.py', encoding='utf-8').read()
bm = re.search(r'BUNDLE\s*=\s*\{(.+?)\}', eval_text, re.DOTALL)
bundle = ''
if bm:
    for m in re.finditer(r"""['"]([^'"]+\.py)['"]\s*:\s*['"]([A-Za-z0-9+/=]+)['"]""", bm.group(1)):
        bundle += zlib.decompress(base64.b64decode(m.group(2))).decode('utf-8', errors='replace')

with open(r'D:\research\project-engiworld\Engiworld\_blender11_inner.py', 'w', encoding='utf-8') as f:
    f.write(bundle)
print('wrote', len(bundle), 'chars')
