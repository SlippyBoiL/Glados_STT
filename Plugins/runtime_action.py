# code
import os
import platform

if platform.system() == 'Windows':
    os.system('cmd /c "type nul > new_skills.txt"')
else:
    os.system('echo > new_skills.txt')