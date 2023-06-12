from handlers.utilities_handler import *
import platform
import requests
import json


def compare(
    current_ver: str = "Unknown", latest_ver: str = "Unknown", name: str = "None"
):
    print(f"Local {name} installation version: {COLORS.YELLOW+COLORS.BOLD+current_ver}")
    print(
        f"{COLORS.RESET}Latest {name} installation: {COLORS.YELLOW+COLORS.BOLD+latest_ver}"
    )

    if latest_ver == "Unknown":
        print(
            f"{COLORS.UNDERLINE}Your {name} installation is potentially outdated, but the latest version could not be checked."
        )
        sleep(2)
    elif latest_ver != current_ver and latest_ver != "Unknown":
        print(
            f"{COLORS.RED+COLORS.UNDERLINE}Your {name} installation IS OUTDATED! Consider updating it."
        )
        sleep(2)
    else:
        print(f"{COLORS.GREEN}Your {name} installation is up-to-date!")
        sleep(0.2)

    print(f"{COLORS.RESET}------------------")


def check_version():
    clear()

    # Python
    current_version = platform.python_version()

    try:
        (r := requests.get("https://endoflife.date/api/python.json")).raise_for_status()
        latest_version = r.json()[0]["latest"]
    except:
        latest_version = None

    compare(current_version, latest_version, "Python")

    # discord.py
    current_version = discord.__version__

    try:
        r = requests.get("https://pypi.org/pypi/discord.py/json")
        (r := requests.get("https://pypi.org/pypi/discord.py/json")).raise_for_status()
        latest_version = list(json.loads(r.text)["releases"].keys())[-1]
    except:
        latest_version = None

    compare(current_version, latest_version, "discord.py")
