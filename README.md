# archerageStats

archerageStats is a program that reads the game's logs to make graphs in similar fashion to a damage meter. It is intended to be used after the event/combat in-game is over.

**NOTE:** This will only work with logs from ArcheRage!

## Features

- Read log data to make graphs and an output.txt
- Re-use output.txt files to quickly regenerate graphs and cut on filesizes
- All files generated will be organized according to their date
- The following data will be collected: Damage total, Healing total, Damage received total, Self-healing total, Song buff uptime, Song debuff uptime, and experimentally a list of all skills used reported by the logs.
- - The program will try to remove data from non-player sources or targets but it is not flawless. Self-healing will record all non-player sources.
- - Self-healing is any healing originating from most gear, items, pets or abilities outside vitalism. For example, healing pots are included, as is the phoenix powerpet's heal or auramancy's absorb damage passive.
- Fully supports english client logs, partial support for russian client logs.
- Game log files may record all data only from within the user's render distance, which in open-world is around 100 to 110 meters.

## Usage

[Releases](https://github.com/Frailcoder/archerageStats/releases) will include an .exe file bundled with all dependencies. Open the executable and follow the prompts. There is little customization, it only requires a combat.log file usually found in `C:\Users\<your user>\Documents\ArcheRage`

Alternatively, running the source archerageStats.py with the dependencies on your computer will be equivalent.

Any files generated will be in the directory the .exe or .py file is located in, inside a combatLogs folder. They are .png or .txt files.

**NOTE:** By default, the game won't create the required combat.log files. You can enable them in the settings menu, as shown below.
Previous session logs are stored in LogBackups. This requires enabling combat numbers from everyone in render distance, possibly cluttering the screen.
![game-settings](https://github.com/Frailcoder/archerageStats/assets/134928956/89479421-61e1-4cb2-add5-b461ee6a136d)

### Example output

![example](https://github.com/Frailcoder/archerageStats/assets/134928956/07d8438a-ac5a-4b85-9804-6a39c59c0cc3)

## Requirements

- Windows
- ArcheRage logs from version 7.5.3 (may or may not work from differing versions)
- If using the archerageStats.py file directly, Python 3.7.9 or later and dependencies.

### Dependencies

- regex module: https://github.com/mrabarnett/mrab-regex (PYPI: https://pypi.org/project/regex/)
- matplotlib module: https://matplotlib.org/stable/index.html (PYPI: https://pypi.org/project/matplotlib/)
- Python 3.7.9 or later, preferably 3.11
- pyinstaller only if you wish to make your own .exe: https://pyinstaller.org/en/stable/ (PYPI: https://pypi.org/project/pyinstaller/)

### License

This work is used under the MIT license.

### Closing statement

This program was used as a learning ground for python and its modules and has seen many iterations before being public. I rarely play now, so it is being released.
All criticism is welcome as is any contributions. You can contact me on discord: Pedro#7476
