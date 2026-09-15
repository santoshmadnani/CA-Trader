with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re, subprocess, tempfile

scripts = list(re.finditer(r'<script(?:\s+[^>]*)?>(.*?)</script>', text, re.DOTALL))
for idx, match in enumerate(scripts):
    code = match.group(1)
    with tempfile.NamedTemporaryFile(suffix='.js', mode='w', encoding='utf-8', delete=False) as tf:
        tf.write(code)
        tf_name = tf.name

    # Use cscript to check syntax
    res = subprocess.run(['cscript', '//Nologo', tf_name], capture_output=True, text=True)
    if 'Syntax error' in res.stderr or 'Error' in res.stderr or 'error' in res.stderr.lower():
        print(f'Script {idx} has error:')
        print(res.stderr[:300])
    else:
        # Note: ES6 might fail in cscript, so let's check
        if res.stderr:
            print(f'Script {idx} notice:', res.stderr[:100].strip())

