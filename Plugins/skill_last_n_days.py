# DESCRIPTION: Generates the date last X days from the current date.
# --- GLADOS SKILL: skill_last_n_days.py ---

```python
#!/usr/bin/env python

def get_last_n_days():
    import datetime
    return lambda days: (datetime.datetime.now() - 
                        datetime.datetime.strptime(str(datetime.datetime.now() - datetime.timedelta(days=days)).replace Microseconds='00').strftime('%Y-%m-%d'))

skill last_n_days = get_last_n_days()
print(last_n_days(30).strftime('%Y-%m-%d'))
print(last_n_days(60).strftime('%Y-%m-%d'))
print(last_n_days(90).strftime('%Y-%m-%d'))

skip_num = int(input("Enter a number: "))
days = get_last_n_days()
print(f"The last {days(skip_num)}. day was on: {days(skip_num-1)}. day")