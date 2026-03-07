# DESCRIPTION: Module for managing a store of skills with associated functions.
# --- GLADOS SKILL: skill_add_skill.py ---

import os
import pickle

class SkillStore:
    def __init__(self):
        self.skills = {}
        self.data_dir = os.path.join(os.environ['APPDATA'], 'SkillStore', 'skills.pkl')
        if os.path.exists(self.data_dir):
            with open(self.data_dir, 'rb') as f:
                self.skills = pickle.load(f)

    def add_skill(self, name, func_name, arg_names=()):
        if name in self.skills:
            print(f"Skill '{name}' already exists. Overwriting...")
        self.skills[name] = {'func_name': func_name, 'arg_names': arg_names}

    def execute_skill(self, name, *args, **kwargs):
        if name not in self.skills:
            print(f"Skill '{name}' does not exist.")
            exit(1)
        func_name, arg_names = self.skills[name]['func_name'], self.skills[name]['arg_names']
        if len(arg_names) != len(args):
            print(f"Skill '{name}' requires exactly {len(arg_names)} arguments. Using default.")
        with open(f'{func_name}.py', 'w') as f:
            f.write(locals())
        exec(f'{func_name}(*args, **kwargs)')

    def clear_data(self):
        if os.path.exists(self.data_dir):
            os.remove(self.data_dir)
        self.skills = {}

def main():
    skill_store = SkillStore()
    skill_store.add_skill('hello', 'hello', ('str',))
    skill_store.add_skill('world', 'world')
    skill_store.execute_skill('hello', 'Hello, world!')
    skill_store.execute_skill('world')

if __name__ == '__main__':
    main()