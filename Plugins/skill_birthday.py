# DESCRIPTION: Calculates age in days from a birthday.
# --- GLADOS SKILL: skill_birthday.py ---

import datetime


def get_age_in_days(birthday):
    """birthday: datetime.date or YYYY-MM-DD string."""
    if isinstance(birthday, str):
        birthday = datetime.datetime.strptime(birthday, "%Y-%m-%d").date()
    delta = datetime.date.today() - birthday
    return delta.days


def main():
    # Example: 30 years ago today
    today = datetime.date.today()
    example = today.replace(year=today.year - 30)
    days = get_age_in_days(example)
    print(f"Example: birthday {example} → age in days: {days}")


if __name__ == "__main__":
    main()
