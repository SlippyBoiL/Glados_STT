import os
import sys

# Self-replicating code: writes itself to Kernel.py
self_code = '''print("GLADOS self-coded successfully!")
import os
print("Files:", os.listdir("."))'''

with open("Kernel.py", "w") as f:
    f.write(self_code)

print("Self-coded as Kernel.py")
exec(open("Kernel.py").read())