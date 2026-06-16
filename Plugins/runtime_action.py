import pathlib

# Get the current user's login state
login_state = pathlib.Path.home()
login_state.mkdir(parents=True, exist_ok=True)

# Initialize the 'home' folder
login_state /= 'home'