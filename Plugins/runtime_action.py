pip install steambrowser

import steam # To use the Steam library

url = "https://store.steampowered.com/app/12345/index.html"
browser = steam.SteamBrowser() # Start web browser
browser.open(url) # Open application