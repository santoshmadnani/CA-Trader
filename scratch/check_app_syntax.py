import sys
sys.stdout.reconfigure(encoding='utf-8')
import py_compile

try:
    py_compile.compile('app.py', doraise=True)
    print("app.py compiled cleanly with no errors!")
except py_compile.PyCompileError as e:
    print("Compilation error:", e)

