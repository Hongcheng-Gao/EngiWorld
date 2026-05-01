import re, base64, zlib

eval_text = open(r'D:\research\project-engiworld\Engiworld\task\task-v\blender\task-11\eval.py', encoding='utf-8').read()

for m in re.finditer(r'CALL_ARGS\s*=.+', eval_text):
    print('CALL_ARGS:', m.group(0))
for m in re.finditer(r'CALL_FUNC\s*=.+', eval_text):
    print('CALL_FUNC:', m.group(0))
for m in re.finditer(r'INIT_MAP\s*=.+', eval_text):
    print('INIT_MAP: ', m.group(0)[:300])

bm = re.search(r'BUNDLE\s*=\s*\{(.+?)\}', eval_text, re.DOTALL)
bundle = ''
if bm:
    for m in re.finditer(r"""['"]([^'"]+\.py)['"]\s*:\s*['"]([A-Za-z0-9+/=]+)['"]""", bm.group(1)):
        try:
            bundle += f"\n# --- {m.group(1)} ---\n" + zlib.decompress(base64.b64decode(m.group(2))).decode('utf-8', errors='replace')
        except Exception as e:
            print('decode err', e)

combined = eval_text + '\n' + bundle
print('\n--- keyword scan ---')
for kw in ['answer.blend','lineart.png','scene.blend','Casting','manifold','face_off','top face','hole','diameter','0.5','0.1','0.9','0.45','0.55','through','blind']:
    idx = combined.find(kw)
    if idx != -1:
        ctx = combined[max(0,idx-40):idx+160].replace('\n',' | ')
        print(f"  {kw!r} -> {ctx}")
    else:
        print(f"  {kw!r} NOT FOUND")

print('\n--- bundle size ---', len(bundle), 'chars')
print('\n--- bundle head ---')
print(bundle[:800])
print('\n--- bundle tail ---')
print(bundle[-800:])
