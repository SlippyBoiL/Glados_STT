# DESCRIPTION: A simple class to keep track of skill usage counts.
# --- GLADOS SKILL: skill_usage_counter.py ---

class SkillUsageCounter:
    def __init__(self):
        self.counts = {}

    def increment(self, skill_name):
        if skill_name in self.counts:
            self.counts[skill_name] += 1
        else:
            self.counts[skill_name] = 1

    def get_total_usage(self):
        return sum(self.counts.values())

    def get_skill_usage(self, skill_name):
        return self.counts.get(skill_name, 0)


def main():
    counter = SkillUsageCounter()

    def update_counter(*args):
        if not args:
            print("Counter update skipped")
        else:
            skill_name = args[0].__name__
            counter.increment(skill_name)
            print(f"Counter updated for {skill_name}")
        print(f"Total count: {counter.get_total_usage()}")
        print(f"Count for {skill_name}: {counter.get_skill_usage(skill_name)}")
        if skill_name == "SkillUsageCounter":
            import inspect
            print(f"Called with args: {inspect.signature(update_counter).bind(*args).args}")

    from runtime_action import runtime_action
    from your_skills import whoami
    result = runtime_action(update_counter)
    print(result)
    whoami()


if __name__ == "__main__":
    main()