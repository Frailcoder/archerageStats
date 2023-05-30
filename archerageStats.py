# python3
# archerageStats.py

# getattr(object, attribute, "default")
"""Based on a combat.log: output stats found in it and plots them into graphs and an output.txt. The output data, a folder named combatLogs,
will be located in the current working directory (CWD). If the module is run at top level, the CWD will be the script's residing directory.
You will be prompted to choose a file with correct combat.log formatting, or an output.txt created from one.
Output files will momentarily reside in the CWD, where it will overwrite any files with the same name without asking.
They will be moved to a combatLog folder in the CWD where it will create a numbered folder inside the datefolder if there are conflicting files.
"""

import copy
import os
import shutil
import sys
import time
import json
import traceback
from tkinter import filedialog

import matplotlib.pyplot as plt # https://pypi.org/project/matplotlib/
import regex as re # https://pypi.org/project/regex/
re.DEFAULT_VERSION = re.VERSION1

# uncomment if using as a python file
if __name__ == '__main__':
    os.chdir(sys.path[0])
# or
# uncomment if using as an .exe file through pyinstaller
#app_path = os.path.dirname(sys.executable)


class LogStats():
    """Object with compiled info of a combat.log. See __init__ 's docstring for expected formatting.
    Just a class working as a container because I'm lazy and for clarity
    """
    def __init__(self):
        """dmg_log = {player : {total : int, ability1 : int, ability2 : int, ...}, ...}
        received_dmg_log = {player : {total : int, ability1 : int, ability2 : int, ...}, ...}
        heal_log = {player : {total : int, ability1 : int, ability2 : int, ...}, ...}
        self_heal_log = {player : {total : int, ability1 : int, ability2 : int, ...}, ...}
        tracked_songs_total_buffs = {player : {song : timespent_int, song1 : timeinint, ...}, ...}
        tracked_songs_total_debuffs = {player : {song : timespent_int, song1 : timeinint, ...}, ...}
        tracked_player_skills = {player : {ability1 : int, ability2 : int, ...}, ...}
        tracked_skill_players = {ability : {player1 : int, player2 : int, ...}, ...}
        log_start_time = int (unix epoch)
        log_end_time = int (unix epoch)
        log_elapsed_time = int
        """
        self.dmg_log = {}
        self.received_dmg_log = {}
        self.heal_log = {}
        self.self_heal_log = {}
        self.tracked_songs_total_buffs = {}
        self.tracked_songs_total_debuffs = {}
        self.tracked_player_skills = {}
        self.tracked_skill_players = {}
        self.log_start_time = -1
        self.log_end_time = -1
        self.log_elapsed_time = -1
        self.langs_contained = set()


class Locale():
    """Contain info relevant to main_log_builder()'s language checks.
    combat.log formatting is often different depending on language,
    so simply changing this object may not be enough.
    Available languages: ("EN", "RU"). When adding a language,
    a new definition for it must be added in this class & edit main_log_builder()
    """
    def __init__(self):
        """Use a locale method after calling the object to initialize it.
        Available languages: ("EN", "RU")
        """
        self.all_lang_available = ("EN", "RU")
        self.all_heal_potions = {"EN" : ('healing potion', 'minor healing potion', 'found wild ginseng!', 'healing grimoire',
            'phoenix tears tincture', 'enhanced judge\'s longing', 'orange goblet of honor', 'sand soulshard',
            'absorb damage', 'earth lunafrost', 'blessed rune: zena basta 6', 'revitalizing cheer', 'health regen food',
            "judge's longing", 'absorb lifeforce', 'flame conversion shield (rank 5)', "wind soulshard",
            "conversion shield (rank 5)", "for the battle"),
            "RU" : ("исцеление", 'благосклонность акритеса ii', "благосклонность акритеса i", "письмена войны",
            "надежда луны", "непреодолимое сопротивление", "кража жизни", "целебные эликсиры", "сансам",
            "энергетический щит v", "гримуар тайного знания", """слова силы: а'ше"н'валь vi""",
            "энергия забытого сада", "восстанавливающая здоровье еда")} # RU has unverified (by me) translations
        self.all_heal_pets = {"EN" : ('phoenix flame',),
            "RU" : ("",)} # pets that provide self-healing to the owner (target is owner, source is pet)
        self.all_songs = {"EN" : ('bulwark ballad (rank 2)', 'bloody chantey (rank 2)', 'quickstep (rank 5)',
            'unguarded', 'lethargy (bloody chantey)', 'unpleasant sensation (quickstep)'),
            "RU" : ("Гимн земли II","Рапсодия битвы II","Походный марш V",
            "Уязвимость","Аура беспомощности","Замедление")} # maintain order here

    def EN(self):
        """EN locale"""
        
        self.current_lang = "EN"

        self.pve_bosses = ('Kraken', 'Meina', 'Glenn', 'Anthalon', 'Charybdis') # only need provide bosses without a space in the name
        self.unwanted_events = ("|r is casting |", "|r mana.", "|r! Attack Missed.", "|r! Attack Immune!",
            "|r! Attack Evaded," , "|cffff00000|r", "|r took", "attacked |r") # "|cffff00000|r": 0 dmg event (5 zeroes instead of 4)
            # "attacked |r" somehow, you can have a target of a dmg event that is 0-length.
        # self.no_spaces_in_names_regex = re.compile(r"(?:\[.+\] \S+\|r)(?: attacked \S+\|r| targeted \S+\|r| successfully| is casting| gained| was|\'s)")
        self.damage_regex = re.compile(r'\] (.+)\|r attacked (.+)\|r using \|cff25fcff(.*)\|r.+\|cffff0000-(\d+)\|r')
        self.auto_attack_regex = re.compile(r"\] (.+)\|r attacked (.+)\|r(?|! Attack (?:Blocked|Parried), resulting in \|cffff(0000)-(\d+)\|r| and caused \|cffff(0000)-(\d+)\|r)")
        self.heal_regex = re.compile(r'\] (.+)\|r targeted (.+)\|r using \|cff25fcff(.*)\|r to restore \|cff00ff00(\d+)\|r health')
        self.buff_debuff_regex = re.compile(r"\[(.+)\] (?|(?|(.+)\|r (gained) the buff: \|cff25fcff(.+)\|r|(.+)\|r was (struck) by a \|cff25fcff(.+)\|r debuff!)|(.+)\|r\'(s) \|cff25fcff(.+)\|r)")
        self.skill_cast_regex = re.compile(r"\] (.+)\|r successfully cast \|cff25fcff(.+)\|r!")
    
    def RU(self):
        """RU locale"""
        
        self.current_lang = "RU"

        self.pve_bosses = ("Ксанатос", "Кракен")
        self.unwanted_events = (             "маны.", "Промах!", "невосприимчивостью ",
            "уклоняется.", "|cffff00000|r", "падение", "(|", "Восстанавливает по |nc;5000 очков работы|r.") # (| = fall dmg or similar
            # "Восстанавливает по |nc;5000 очков работы|r."? :pensive: this breaks regex formating and its just the 5k labor pot
        # self.no_spaces_in_names_regex = re.compile(r"\] \S+\|r(?|: применено умение| применяет умение «\|.+\|r»\. \S+\|r |: наложен |: эффект | атакует\. \S+\|r п)")
        self.damage_regex = re.compile(r"\] (.+)\|r применяет умение «\|cff25fcff(.+)\|r»\. (.+?)\|r .*-(\d+)\|r ед\.")
        self.auto_attack_regex = re.compile(r"\] (.+)\|r атакует.*\. (.+)\|r .*\|cffff(0000)-(\d+)\|r")
        self.heal_regex = re.compile(r"\] (.+)\|r применяет умение «\|cff25fcff(.+)\|r»\. (.+)\|r восстанавливает \|cff00ff00(\d+)\|r .*\.")
        self.buff_debuff_regex = re.compile(r"\[(.+)\] (.+)\|r: (?|(наложен) (?:усиливающий|ослабляющий) эффект «\|cff25fcff(.+)\|r»\.|(эффект) «\|cff25fcf(.+)\|r» рассеялся.)")
        self.skill_cast_regex = re.compile(r"\] (.+)\|r: применено умение «\|cff25fcff([^\|\n]+)")

        self.is_casting_regex = re.compile(r"\] .+\|r применяет умение «\|cff25fcff[^\|]+(?:\|r»)?\.?$") # the only difference between is casting or has cast is a colon...


def generate_output(log_stats, perf_counter_start = 0, user_file = None,
    custom_text_field = "undefined_custom_text_field", write_output = True):
    """Generate output from a LogStats object. If user_file is not None, will copy it to output folder."""

    log_start = time.strftime(r"%d/%m/%y %H:%M:%S", time.localtime(log_stats.log_start_time))
    log_end = time.strftime(r"%d/%m/%y %H:%M:%S", time.localtime(log_stats.log_end_time))

    output_filenames = []

    dmg_log_simple = build_simple_dict(log_stats.dmg_log)
    heal_log_simple = build_simple_dict(log_stats.heal_log)
    received_dmg_log_simple = build_simple_dict(log_stats.received_dmg_log)
    item_heal_log_simple = build_simple_dict(log_stats.self_heal_log)

    dmg_graph = horizontal_bar_plot(dmg_log_simple, title='Outgoing Damage\n%s -- %s' % (log_start, log_end), x_label='Damage Given (no pve)', color='crimson', filename='Outgoing Damage.png')
    if dmg_graph is not None:
        output_filenames.append(dmg_graph)

    heal_graph = horizontal_bar_plot(heal_log_simple, title='Outgoing Healing\n%s -- %s' % (log_start, log_end), x_label='Healing Given', color='tab:green', filename='Outgoing Healing.png')
    if heal_graph is not None:
        output_filenames.append(heal_graph)

    received_dmg_graph = stacked_horizontal_bar_plot(received_dmg_log_simple, item_heal_log_simple, title='Received Damage & Self-Healing\n%s -- %s' % (log_start, log_end), x_label='Quantity')
    if received_dmg_graph is not None:
        output_filenames.append(received_dmg_graph)

    song_buff_graph = complex_song_plot(log_stats.tracked_songs_total_buffs, True,
        title='Time spent in songs (logged time = %s' % (log_stats.log_elapsed_time) + 's)\n%s -- %s' % (log_start, log_end),
        y_label='Entity', y_limit=20, filename='Song Buffs.png')
    if song_buff_graph is not None:
        output_filenames.append(song_buff_graph)

    song_debuff_graph = complex_song_plot(log_stats.tracked_songs_total_debuffs, False,
        title='Time spent charmed by songs (logged time = %s' % (log_stats.log_elapsed_time) + 's)\n%s -- %s' % (log_start, log_end),
        y_label='Entity', y_limit=20, filename='Song Charms.png')
    if song_debuff_graph is not None:
        output_filenames.append(song_debuff_graph)

    try:
        os.unlink('Output.txt')
    except(FileNotFoundError):
        pass

    if write_output:
        write_to_txt(True, custom_message="Combat.log times (based on log's client's system time):\nSTART: %s | END: %s\n%s | (~%s seconds elapsed)" %
            (time.strftime(r"%d/%m/%y %H:%M:%S", time.localtime(log_stats.log_start_time)),
            time.strftime(r"%d/%m/%y %H:%M:%S", time.localtime(log_stats.log_end_time)),
            custom_text_field, log_stats.log_elapsed_time))

        if len(log_stats.langs_contained) > 1:
            write_to_txt(True, custom_message="More than one language in combat.log! %s" % (log_stats.langs_contained))
        else:
            write_to_txt(True, custom_message='combat.log language is %s' % (log_stats.langs_contained))
        write_to_txt(False, title='OUTGOING DMG', dict_container=log_stats.dmg_log)
        write_to_txt(False, title='RECEIVED DMG', dict_container=log_stats.received_dmg_log)
        write_to_txt(False, title='OUTGOING HEALING', dict_container=log_stats.heal_log)
        write_to_txt(False, title='SELFHEALING', dict_container=log_stats.self_heal_log)
        write_to_txt(False, title='SONG BUFF STATS', dict_container=log_stats.tracked_songs_total_buffs)
        write_to_txt(False, title='SONG CHARM STATS', dict_container=log_stats.tracked_songs_total_debuffs)
        write_to_txt(False, title='SKILLS USED BY PLAYER (experimental)', dict_container=log_stats.tracked_player_skills)
        write_to_txt(False, title='PLAYERS THAT USED A SKILL (experimental)', dict_container=log_stats.tracked_skill_players)
        output_filenames.append('Output.txt')

    if user_file == os.path.abspath('compiled_combat.log'): # this may cause issues
        output_filenames.append('compiled_combat.log')

    elif user_file is not None:
        shutil.copy(user_file, os.getcwd())
        output_filenames.append(os.path.basename(user_file))

    output_folder_name = time.strftime(r"%Y %m %d", time.localtime(log_stats.log_start_time))
    output_subfolder_name = move_to_folder(output_filenames, 'combatLogs\\' + output_folder_name)

    print("Log interval (DD/Mo/YYYY, hh/mm/ss) (log's client's system time):\nSTART: %s | END: %s" %
        (log_start, log_end))
    print('Log time elapsed: ~ %s seconds' % (log_stats.log_elapsed_time))
    print('Script time elapsed: ~ %s seconds' % (time.perf_counter() - perf_counter_start))
    print('Output folder is "%s".' % (output_folder_name))
    if output_subfolder_name is not None:
        print('WARNING: Program created subfolder "%s" in the output folder "%s"' % (output_subfolder_name, output_folder_name))

    if len(log_stats.langs_contained) > 1:
        print('WARNING: More than one language contained in combat.log. %s' % (log_stats.langs_contained))
    
    print("\nData generation done, returning.")


def user_prompt_main():
    """Introduce user to archeragestats.py and ask for input, looping."""

    print("""archeragestats.py: Using archerage's combat.log, this program can generate graphs and ordered data. By Pedro#7476
You may pick to parse a combat.log, or regenerate data from an output.txt made by this program in the past.
Any generated files will be included in the directory where this program is located.""")
    while True:
        print('\nType (1) to generate from a combat.log, (2) to regenerate from an output.txt, or (Q) to quit.')
        user_input = input().lower()
        if user_input == "q":
            print("Quitting\n")
            break
        
        elif user_input == "1":
            print("Picked combat.log reading.\n")
            
            user_prompt_log_builder()
        
        elif user_input == "2":
            print("Picked output.txt regeneration.\n")
            
            user_prompt_regenerate_logstats()

        else:
            print("Unknown command, looping")
            continue
    
    print("Goodbye, see you soon!")

def user_prompt_log_builder():
    """While prompting user for options, call functions to generate a LogStats object from a combat.log."""
    user_file = user_prompt_file()

    if user_file is None:
        return None

    copy_user_file = user_prompt_copy_log("combat.log")

    user_file_lines = user_prompt_timeframe(user_file)
    if user_file_lines is not None:
        user_file_chosen = user_file_lines
    else:
        user_file_chosen = user_file

    print('Please indicate custom text to add to the final output.txt')
    custom_text_field = input()

    perf_counter_start = time.perf_counter()
    try:
        log_stats = main_log_builder(user_file_chosen)
    except:
        log_stats = None
        error_traceback_print()
    
    if not copy_user_file:
        user_file = None
    
    if log_stats is not None:
        generate_output(log_stats, perf_counter_start=perf_counter_start, user_file=user_file,
            custom_text_field=custom_text_field)

        user_prompt_dynamic_create_plot(log_stats)


def main_log_builder(input_lines) -> LogStats:
    """Accepts a list of lines or a combat.log system path. Returns a filled LogStats object.
    """
    if isinstance(input_lines, list):
        pass
    else:
        with open(input_lines, 'r', encoding='utf-8') as f:
            input_lines = f.readlines()

    # combat.log timestamps are in MM/DD/YY client's system time
    log_start_time = 0
    log_end_time = 0
    if 'BackupNameAttachment="' in input_lines[0]:
        log_start_time = int(time.mktime(time.strptime(input_lines[1][1:18],'%m/%d/%y %H:%M:%S')))
        i_start = 1 # 
    else:
        log_start_time = int(time.mktime(time.strptime(input_lines[0][1:18],'%m/%d/%y %H:%M:%S')))
        i_start = 0
    log_end_time = int(time.mktime(time.strptime(input_lines[-1][1:18],'%m/%d/%y %H:%M:%S')))

    if log_start_time > log_end_time:
        raise ValueError("Combat.log's last line has a timestamp earlier than its first line. Is the file edited manually?\n start: %s | end: %s"
            % (log_start_time, log_end_time))

    # _event = list of lists e.g. dmg_event: [["player", "target", "method", "value", "lang"], [...], ...]
    # the last index in any of the lists will always be the language used to obtain it.
    dmg_event = [] # any damage event. 
    heal_event = [] # any heal event
    buff_debuff_event = [] # skill casts, BUFFS&DEBUFFS obtained&lost, skills successfully cast.
    skill_cast_event = [] # |r successfully cast | events

    lang_current = Locale()
    lang_current_str = ""
    langs_contained = set()
    
    def language_check(line):
        """Checks the language of the provided string line. Edits parent variable to correct language.
        """
        nonlocal lang_current_str

        EN_lang_regex = re.compile(r"^.+?\|r(?:\'s)? [a-z]")
        RU_lang_regex = re.compile(r"^.+?\|r(?:\:)? [\u0400-\u04FF]")
        if EN_lang_regex.match(line) is not None:
            lang_current.EN()
            langs_contained.add("EN")
            if lang_current_str == "EN":
                raise ValueError("Language changed despite not being required, infinite loop: %s" % (line))
            lang_current_str = "EN"
        elif RU_lang_regex.match(line) is not None:
            lang_current.RU()
            langs_contained.add("RU")
            if lang_current_str == "RU":
                raise ValueError("Language changed despite not being required, infinite loop: %s" % (line))
            lang_current_str = "RU"

        else:
            raise ValueError("cannot find lang: " + line)

    def sort_log_events_EN(line_EN):
        """Checks a string line obtained from a combat.log. english locale.
        parses it into an event list, directly appending parent's list.
        """
        if any(a in line_EN for a in lang_current.unwanted_events)\
        or any(a in line_EN for a in lang_current.pve_bosses):
            return None

        if "|r's" in line_EN or "was struck by a" in line_EN or "gained the buff:" in line_EN:
            buff_debuff_event_line = lang_current.buff_debuff_regex.findall(line_EN)[0] + ("EN",)
            buff_debuff_event.append(buff_debuff_event_line)

        elif "|r successfully cast |" in line_EN:
            skill_cast_event_line = lang_current.skill_cast_regex.findall(line_EN)[0] + ("EN",)
            skill_cast_event.append(skill_cast_event_line)
        
        elif "|r attacked " in line_EN and "|r using |" in line_EN:
            dmg_event_line = lang_current.damage_regex.findall(line_EN)[0] + ("EN",)
            dmg_event.append(dmg_event_line)

        elif "|r targeted " in line_EN:
            heal_event_line = lang_current.heal_regex.findall(line_EN)[0] + ("EN",)
            if "orange goblet of honor" in heal_event_line[2]: # goblet can have many ranks appended
                heal_event_line[2] = "orange goblet of honor"
            heal_event.append(heal_event_line)

        elif "|r attacked " in line_EN:
            autoattack_event_line = lang_current.auto_attack_regex.findall(line_EN)[0] + ("EN",)
            dmg_event.append(autoattack_event_line)
        
        else:
            raise ValueError()
    
    def sort_log_events_RU(line_RU):
        if any(a in line_RU for a in lang_current.unwanted_events)\
        or any(a in line_RU for a in lang_current.pve_bosses)\
        or lang_current.is_casting_regex.search(line_RU) is not None:
            return None
        
        elif ": наложен" in line_RU or "эффект " in line_RU:
            buff_debuff_event_line = lang_current.buff_debuff_regex.search(line_RU)
            if "наложен" in buff_debuff_event_line.group(3):
                identifier = "gained"
            elif "эффект" in buff_debuff_event_line.group(3):
                identifier = "s"

            for index, method in enumerate(lang_current.all_songs["RU"]):
                if method == buff_debuff_event_line.group(4):
                    method = lang_current.all_songs["EN"][index]
                    break
            
            buff_debuff_event_line = (buff_debuff_event_line.group(1), buff_debuff_event_line.group(2),
                                    identifier, method, "RU")
            buff_debuff_event.append(buff_debuff_event_line)

        elif ": применено умение" in line_RU:
            skill_cast_event_line = lang_current.skill_cast_regex.findall(line_RU)[0] + ("RU",)
            skill_cast_event.append(skill_cast_event_line)

        elif "снижается на" in line_RU and " атакует" not in line_RU\
        or "блокирует " in line_RU and " атакует" not in line_RU\
        or "парирует " in line_RU and " атакует" not in line_RU:
            dmg_event_line = lang_current.damage_regex.search(line_RU)
            dmg_event_line = (dmg_event_line.group(1), dmg_event_line.group(3),
                            dmg_event_line.group(2), dmg_event_line.group(4), "RU")
            dmg_event.append(dmg_event_line)

        elif "восстанавливает " in line_RU:
            heal_event_line = lang_current.heal_regex.search(line_RU)
            if "orange goblet of honor" in heal_event_line.group(3): # goblet can have many ranks appended
                heal_event_line[2] = "orange goblet of honor"
            heal_event_line = (heal_event_line.group(1), heal_event_line.group(3),
                            heal_event_line.group(2), heal_event_line.group(4), "RU")
            heal_event.append(heal_event_line)

        elif " атакует" in line_RU:
            autoattack_event_line = lang_current.auto_attack_regex.findall(line_RU)[0] + ("RU",)
            dmg_event.append(autoattack_event_line)

        else:
            raise ValueError()

    language_check(input_lines[i_start])

    n = i_start
    while n < len(input_lines):
        try:
            if lang_current_str == "EN":
                sort_log_events_EN(input_lines[n])
            elif lang_current_str == "RU":
                sort_log_events_RU(input_lines[n])
        
        except(ValueError):
            language_check(input_lines[n])
        
        else:
            n += 1

    def sort_dmg_event(event_list) -> tuple[dict, dict]:
        """Sorts events as given by event_list, obtained from sort_log_events()'s dmg_event.
        
        Returns two sorted dictionaries: player and dmg total, player and dmg taken total.
        Format {player : {total : int, ability1 : int, ability2 : int, ...}}
        """
        damage_dealt = {}
        damage_received = {}
        for event in event_list:
            source = event[0]
            target = event[1]
            method = event[2].lower()
            value = event[3]
            
            if " " in source:
                continue
            if " " in target:
                continue

            damage_dealt.setdefault(source, {"total":0})
            damage_dealt[source].setdefault(method, 0)
            
            damage_dealt[source]["total"] += int(value)
            damage_dealt[source][method] += int(value)

            damage_received.setdefault(target, {"total":0})
            damage_received[target].setdefault(method, 0)
            
            damage_received[target]["total"] += int(value)
            damage_received[target][method] += int(value)
        
        damage_dealt = dict(sorted(damage_dealt.items(), key=lambda x: x[1]["total"], reverse=True))
        damage_received = dict(sorted(damage_received.items(), key=lambda x: x[1]["total"], reverse=True))
        
        for k in damage_dealt:
            damage_dealt[k] = dict(sorted(damage_dealt[k].items(), key=lambda x: x[1], reverse=True))
        
        for k in damage_received:
            damage_received[k] = dict(sorted(damage_received[k].items(), key=lambda x: x[1], reverse=True))

        return (damage_dealt, damage_received)


    def sort_heal_event(event_list) -> tuple[dict, dict]: # for healing-related sources, especially to ensure healing and selfhealing is separated.
        """Sorts events as given by event_list, obtained from sort_log_events()'s heal_event.
        
        Returns two sorted dictionaries: player and heal total, player and item/buffs self-healing total
        (not self-targeting outgoing healing like vitalism, i.e rather healing pots, orange goblet, phoenix powerstone pet...).
        Format {player : {total : int, ability1 : int, ability2 : int, ...}}
        """
        healing_dealt = {}
        healing_self_items = {}

        for event in event_list:
            source = event[0]
            target = event[1]
            method = event[2].lower()
            value = event[3]
            lang = event[4]

            if " " in source:
                continue
            if " " in target:
                continue

            if method in lang_current.all_heal_potions[lang]:
                healing_self_items.setdefault(source, {"total" : 0})
                healing_self_items[source].setdefault(method, 0)

                healing_self_items[source]["total"] += int(value)
                healing_self_items[source][method] += int(value)
            
            elif method not in lang_current.all_heal_pets[lang]: # normal heal
                healing_dealt.setdefault(source, {"total" : 0})
                healing_dealt[source].setdefault(method, 0)
                
                healing_dealt[source]["total"] += int(value)
                healing_dealt[source][method] += int(value)

            else: # healing pets
                healing_self_items.setdefault(target, {"total" : 0})
                healing_self_items[target].setdefault(method, 0)

                healing_self_items[target]["total"] += int(value)
                healing_self_items[target][method] += int(value)

        healing_dealt = dict(sorted(healing_dealt.items(), key=lambda x: x[1]["total"], reverse=True))
        healing_self_items = dict(sorted(healing_self_items.items(), key=lambda x: x[1]["total"], reverse=True))

        for k in healing_dealt:
            healing_dealt[k] = dict(sorted(healing_dealt[k].items(), key=lambda x: x[1], reverse=True))
        
        for k in healing_self_items:
            healing_self_items[k] = dict(sorted(healing_self_items[k].items(), key=lambda x: x[1], reverse=True))
        
        return (healing_dealt, healing_self_items)

    def sort_buff_debuff_event(event_list) -> tuple[dict, dict, int]:
        """Sorts events as given by event_list, obtained from sort_log_events()'s buff_debuff_event.
        
        Returns two dictionaries in format {player : {song : timeinint, song1 : timeinint, ...}, ...}.
        First dictionary tracks the buff versions of songs, second tracks the debuff versions.
        Also returns combatlog elapsed time
        """
        timer = int(time.mktime(time.strptime(event_list[0][0],'%m/%d/%y %H:%M:%S')))
        log_elapsed_time = 0
        tracking_temporary = {} # {str Entity : {str Song: int Seconds, str Song: int Seconds, ...}}
        tracked_songs_total_buffs = {} # ditto
        tracked_songs_total_debuffs = {} # ditto
        BUFFS = ('bulwark ballad (rank 2)', 'bloody chantey (rank 2)', 'quickstep (rank 5)') 
        DEBUFFS = ('unguarded', 'lethargy (bloody chantey)', 'unpleasant sensation (quickstep)')

        def tracked_songs_total_addition(entity, sub_dict_key, sub_dict_value):
            if sub_dict_key in BUFFS:
                dictionary_reference = tracked_songs_total_buffs
            else:
                dictionary_reference = tracked_songs_total_debuffs
            
            dictionary_reference.setdefault(entity, {})

            if sub_dict_key in dictionary_reference[entity]:
                dictionary_reference[entity][sub_dict_key] += sub_dict_value
            else:
                dictionary_reference[entity].update({sub_dict_key: sub_dict_value})

        for event in event_list:
            entity = event[1]

            if " " in entity:
                continue
            
            identifier = event[2] # if 's', lost buff or debuff. if 'gained' or 'struck', gained buff or debuff.
            song = event[3].lower()

            if song not in (BUFFS + DEBUFFS):
                continue

            event_time = int(time.mktime(time.strptime(event[0],'%m/%d/%y %H:%M:%S')))

            time_difference = event_time - timer
            log_elapsed_time += time_difference

            delete_queue = []
            for k in tracking_temporary:
                for s in tracking_temporary[k]:
                    tracking_temporary[k][s] += time_difference
                    if tracking_temporary[k][s] > 4: # songs cannot be over 5 seconds in length + handles mismatch
                        tracking_temporary[k][s] = 5
                        tracked_songs_total_addition(k, s, tracking_temporary[k][s])
                        delete_queue.append([k,s])
            for n in delete_queue:
                k, s = n
                del tracking_temporary[k][s]

            timer = event_time

            tracking_temporary.setdefault(entity, {})

            if identifier == 'gained' or identifier == 'struck':
                tracking_temporary[entity].update({song: 0})

            elif identifier == 's':
                try:
                    tracked_songs_total_addition(entity, song, tracking_temporary[entity][song])
                    del tracking_temporary[entity][song]
                except(KeyError): # if mismatch occurs: de/buff loss event without ever acquiring it
                    pass

        def add_time_total(dictionary_reference):
            for k in dictionary_reference: 
                entity_total_song_time = 0
                for s in dictionary_reference[k]:
                    entity_total_song_time += dictionary_reference[k][s]
                dictionary_reference[k].update({'time_total' : entity_total_song_time})

        add_time_total(tracked_songs_total_buffs)
        add_time_total(tracked_songs_total_debuffs)

        tracked_songs_total_buffs = dict(sorted(tracked_songs_total_buffs.items(), key=lambda x: x[1]['time_total'], reverse=True))
        tracked_songs_total_debuffs = dict(sorted(tracked_songs_total_debuffs.items(), key=lambda x: x[1]['time_total'], reverse=True))
        
        for k in tracked_songs_total_buffs:
            del tracked_songs_total_buffs[k]['time_total']
        for k in tracked_songs_total_debuffs:
            del tracked_songs_total_debuffs[k]['time_total']
        
        return tracked_songs_total_buffs, tracked_songs_total_debuffs, log_elapsed_time

    def sort_skill_cast_event(event_list) -> tuple[dict, dict]:
        """Return two sorted dicts. First is all skills used per player, second is all players that used a skill."""
        player_skills = {}
        skill_players = {}
        
        for event in event_list:
            entity = event[0]

            if " " in entity:
                continue

            skill = event[1].lower()
            
            player_skills.setdefault(entity, {})
            skill_players.setdefault(skill, {})

            player_skills[entity].setdefault(skill, 0)
            skill_players[skill].setdefault(entity, 0)

            player_skills[entity][skill] += 1
            skill_players[skill][entity] += 1

        player_skills = dict(sorted(player_skills.items(), key=lambda x: x[0]))
        skill_players = dict(sorted(skill_players.items(), key=lambda x: x[0]))
            
        for k in player_skills:
            player_skills[k] = dict(sorted(player_skills[k].items(), key=lambda x: x[1], reverse=True))
        
        for k in skill_players:
            skill_players[k] = dict(sorted(skill_players[k].items(), key=lambda x: x[1], reverse=True))
        
        return player_skills, skill_players

    log_stats = LogStats()

    log_stats.dmg_log, log_stats.received_dmg_log = sort_dmg_event(dmg_event)
    
    log_stats.heal_log, log_stats.self_heal_log = sort_heal_event(heal_event)

    log_stats.tracked_songs_total_buffs, log_stats.tracked_songs_total_debuffs,\
        log_stats.log_elapsed_time = sort_buff_debuff_event(buff_debuff_event)

    log_stats.tracked_player_skills, log_stats.tracked_skill_players = sort_skill_cast_event(skill_cast_event)

    log_stats.log_end_time = log_end_time
    log_stats.log_start_time = log_start_time
    log_stats.langs_contained = langs_contained
    
    return log_stats


def user_prompt_regenerate_logstats():
    """Prompts user for an output.txt file to regenerate LogStats with, using regenerate_logstats()"""

    print("Pick a valid output.txt to regenerate graphs & dictionary data with")
    user_file = user_prompt_file()

    if user_file is None:
        return None
    
    with open(user_file, 'r', encoding='utf-8') as f:
        input_lines = f.readlines()
    
    print("Generate output? Skip if you only want the dynamic plots.\n(Y) for Yes, or (N) for No.")
    while True:
        user_input = input().lower()
        if user_input == "y":
            print("Picked Yes.")
            copy_user_file = user_prompt_copy_log("output.txt")
            if not copy_user_file:
                user_file = None
            else:
                print('Please indicate custom text to add to the final output.txt')
                custom_text_field = input()
            
            perf_counter_start = time.perf_counter()
            try:
                log_stats = regenerate_logstats(input_lines)
            except:
                log_stats = None
                error_traceback_print()
            
            if log_stats is not None:
                generate_output(log_stats, perf_counter_start=perf_counter_start, write_output=False,
                    user_file=user_file, custom_text_field=custom_text_field)
           
            break
        elif user_input == "n" or user_input == "q":
            print("Picked No.")
            try:
                log_stats = regenerate_logstats(input_lines)
            except:
                log_stats = None
                error_traceback_print()
            break
        else:
            print("Unknown command. Type (Y) for Yes or (N) for No.")

    if log_stats is not None:
        user_prompt_dynamic_create_plot(log_stats)


def regenerate_logstats(lines) -> LogStats:
    """Regenerate a LogStats object with an output.txt file"""
    
    log_stats = LogStats()
    time_regex = re.compile(r"START: (\d{2}\/\d{2}\/\d{2} \d{2}:\d{2}:\d{2}) \| END: (\d{2}\/\d{2}\/\d{2} \d{2}:\d{2}:\d{2})")
    elapsed_time_regex = re.compile(r".+\| \(~(\d+) seconds elapsed\)")
    
    log_stats.log_start_time, log_stats.log_end_time = time_regex.findall(lines[1])[0]
    log_stats.log_start_time = int(time.mktime(time.strptime(log_stats.log_start_time, r"%d/%m/%y %H:%M:%S")))
    log_stats.log_end_time = int(time.mktime(time.strptime(log_stats.log_end_time, r"%d/%m/%y %H:%M:%S")))
    
    log_stats.log_elapsed_time = elapsed_time_regex.findall(lines[2])[0]
    log_stats.langs_contained.add("language_not_checked")

    def detect_dict_type(line):
        data_types = {"OUTGOING DMG" : 0, "RECEIVED DMG" : 1, "OUTGOING HEALING" : 2, "SELFHEALING" : 3,
            "SONG BUFF STATS": 4, "SONG CHARM STATS" : 5, "SKILLS USED BY PLAYER (experimental)" : 6,
            "PLAYERS THAT USED A SKILL (experimental)" : 7}

        line = line[:-1].strip("- ") # \n
        if line in data_types:
            return data_types[line]
        else:
            raise ValueError(line)

    data_types = {0 : log_stats.dmg_log, 1 : log_stats.received_dmg_log,
    2 : log_stats.heal_log, 3 : log_stats.self_heal_log,
    4 : log_stats.tracked_songs_total_buffs, 5 : log_stats.tracked_songs_total_debuffs,
    6 : log_stats.tracked_skill_players, 7 : log_stats.tracked_player_skills}
    
    data_type = -1
    log_stats_attribute_current = None
    n = 3
    while n <= len(lines) -3:
        n += 1
        m = lines[n]
        if m == "\n":
            continue
        
        elif m[0] == " ":
            data_type = detect_dict_type(m)
            log_stats_attribute_current = data_types[data_type]

        else:
            m = fix_dict_formatting(m)
            log_stats_attribute_current.update(m)
    
    return log_stats


def user_prompt_dynamic_create_plot(log_stats):
    """Pass a LogStats object. It will dynamically output graphs for the user using user_prompt_dynamic_create_plot_outer()."""
    while True:
        print('View some data and optionally create graphs dynamically? Experimental\n(Y) for Yes, (N) for No.')
        user_input = input().lower()
        if user_input == 'y':
            print('Picked Yes.')
            user_prompt_dynamic_create_plot_outer(log_stats.tracked_player_skills, log_stats.tracked_skill_players,
                log_stats.dmg_log, log_stats.heal_log, log_stats.received_dmg_log, log_stats.self_heal_log,
                dict_names=["player_skills", "skill_players", "dmg_log", "heal_log", "received_dmg_log", "self_heal_log"])
            break
        elif user_input == 'n':
            print('Picked No.')
            break
        else:
            print('Unknown command')


def user_prompt_dynamic_create_plot_outer(*dicts, dict_names=None):
    """Gives user an overview on the dictionaries given. May pick one to see its contents.
    The dictionaries are expected to have a nested dictionary in the value of each key.
    Intended for use on skill graphs (there is too much data). User may create a graph through called functions.
    If dict_names is provided with a list of strings of same length as the amount of dictionaries given,
    the strings will be used in the same order to describe/name the dicts & resulting graph.
    
    dict1 = {entity : {skill : quantity, skill : quantity, ...}, entity : {...}, ...},
    dict2 = ditto...
    """
    num_dicts = [a + 1 for a in range(len(dicts))]
    
    if len(dicts) == len(dict_names):
        pass
    else:
        dict_names = []
        for n in range(len(dicts)):
            dict_names.append(n)

    print('You may now pick a set of data to create graphs from.')
    while True:
        print("Indicate a dictionary number or type (Q) to exit.\nAvailable data sets: %s (type a number)" % (num_dicts))
        for n in dict_names:
            print(n, end=" ")
        print()
        user_input = input().lower()
        if user_input == 'q':
            print('Exiting')
            return None
        elif not user_input.isdigit():
            print('Numbers, please')
            continue
        user_input = int(user_input)
        
        if user_input in num_dicts:
            print('Picked "%s", dictionary "%s"' % (user_input, dict_names[user_input - 1]))
            user_prompt_dynamic_create_plot_inner(dicts[user_input - 1], dict_name=dict_names[user_input - 1])
            continue
        else:
            print('Unknown command')
            continue


def user_prompt_dynamic_create_plot_inner(dictionary, dict_name=""):
    """Given a dictionary with no dictionary nesting, ask user wether to see its values and create a graph.
    Intended to be called by user_prompt_dynamic_create_plot_outer().
    dict_name = is the dict's name.
    """
    available_keys = dictionary.keys()
    
    while True:
        print('Pick a key to see its contents, or type (Q) to go back.\nAvailable keys (CASE-SENSITIVE):\n%s' % (available_keys))
        user_input = input()
        if user_input.lower() == 'q':
            print('Returning.')
            return None
        elif user_input in available_keys:
            print('Picked %s\nCONTENTS:\n%s' % (user_input, dictionary[user_input]))
            print('\nCreate a simple graph with this data? (Y) for Yes, (N) for No.')
            user_input_2 = input().lower()
            if user_input_2 == 'n':
                print('Picked No, returning to key view.')
                continue
            elif user_input_2 == 'y':
                print("Picked Yes.\nType graph's filename:")
                filename_input = input()
                print('Type color of graph bars (common colors: "tab:green", "royalblue", "crimson"):')
                color_input = input()
                horizontal_bar_plot(dictionary[user_input], title=user_input + " | " + dict_name, x_label='Quantity', y_limit=30, color=color_input, filename=filename_input + '.png')
                print('Saved file to CWD. Press enter to return to key view.')
                input()
                continue
            else:
                print('Unknown command, returning')
                continue
        else:
            print('Unknown command, or key not found.')
            continue


def user_prompt_timeframe(file_dir) -> list[str] | None:
    """Ask wether to use user_prompt_log_timeframe().
    Returns compiled lines within that timeframe, if yes, None if user quits or says no.
    """
    while True:
        print('''Choose a time range to use within the file instead of the whole file?
(Y) for Yes, (N) for No.''')
        user_input = input().lower()
        if user_input == 'y':
            print('Picked Yes.')
            test_value = user_prompt_log_timeframe(file_dir)
            if test_value is None:
                return None
            else:
                return test_value
        elif user_input == 'n':
            print('Picked No.')
            return None


def user_prompt_log_timeframe(combat_log) -> list[str] | None:
    """Turn a given path to a valid combat.log into a lines list within a certain timeframe given by input.
    Returns that list. If user quits early, returns None.
    """
    with open(combat_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # format: [12/31/99 19:09:57] len = 19
    start_timestamp = lines[1][4:7] + lines[1][1:4] + lines[1][7:18]
    start_timestamp_epoch = int(time.mktime(time.strptime(start_timestamp, r'%d/%m/%y %H:%M:%S')))
    end_timestamp = lines[-1][4:7] + lines[-1][1:4] + lines[-1][7:18]
    end_timestamp_epoch = int(time.mktime(time.strptime(end_timestamp, r'%d/%m/%y %H:%M:%S')))

    print('-----\nStart timestamp: %s\nEnd timestamp: %s\n-----\n(dd/mm/yy)' % (start_timestamp, end_timestamp))

    print('Please indicate the start date of the range.')
    while True:
        start_date = user_prompt_validate_date()
        if start_date is None:
            return None
        elif start_date < start_timestamp_epoch:
            print('The given start date occurs outside the combat.log')
            continue
        else:
            break
    
    print('Now indicate the end date of the range')
    while True:
        end_date = user_prompt_validate_date()
        if end_date is None:
            return None
        elif end_date > end_timestamp_epoch:
            print('The given end date occurs outside the combat.log')
            continue
        else:
            break
    
    if start_date > end_date: # lmao
        print('\nERROR: Chosen start timestamp occurs after end timestamp\n')
        recursive_return = user_prompt_log_timeframe(combat_log)
        if recursive_return is None:
            return None
        else:
            return recursive_return

    for n in range(len(lines) - 1, 0, -1):
        if int(time.mktime(time.strptime(lines[n][1:18], r'%m/%d/%y %H:%M:%S'))) <= end_date:
            end_index = n
            break

    for n in range(1, len(lines)):
        if int(time.mktime(time.strptime(lines[n][1:18], r'%m/%d/%y %H:%M:%S'))) >= start_date:
            start_index = n
            break
    
    compiled_lines = []
    compiled_lines.append(lines[0])
    compiled_lines += lines[start_index : end_index+1]
    return compiled_lines


def user_prompt_validate_date() -> (int|None):
    """Asks for user input to obtain a date in DD MM YYYY HOUR MIN SECOND format.
    Returns seconds since epoch, local timezone. Returns None if user quits early.
    """
    date_regex = re.compile(r'\D*(\d{1,2})\D*(\d{1,2})\D*(\d{4}|\d{2})')
    time_regex = re.compile(r'\D*(\d{1,2})\D*(\d{1,2})\D*(\d{1,2})')
    separator_regex = re.compile(r'(.*)[\-\|\_](.*)') 

    while True:
        print('''Input full date, format: DD MM YYYY - HOUR MIN SECOND.
Type (Q) to quit out of timeframe selection''')
        user_input = input()
        if user_input.lower() == 'q':
            print('Quitting')
            return None
        if separator_regex.match(user_input) is None:
            print('''Missing separator character between date and hour
Valid characters: - | _''')
            continue
        user_input_group_1, user_input_group_2 = separator_regex.match(user_input).groups()
            
        if date_regex.match(user_input_group_1) is None:
            print('Missing date in input')
            continue
        if time_regex.match(user_input_group_2) is None:
            print('Missing time in input')
            continue
        user_date_start = date_regex.match(user_input_group_1).groups()
        user_time_start = time_regex.match(user_input_group_2).groups()
            
        try:
            time_test = " ".join(user_date_start) + " " + " ".join(user_time_start)
            time_test = int(time.mktime(time.strptime(time_test, r'%d %m %y %H %M %S')))
        except(ValueError):
            print('Invalid date given')
            continue
        
        finished = False
        while True:   
            print('Is this date correct? (Y) for Yes, (N) for No.\n%s' % (time.strftime(r'%d/%m/%y %H:%M:%S', time.localtime(time_test))))
            user_input = input().lower()
            if user_input == 'n':
                print('Picked No, looping')
                break
            elif user_input == 'y':
                print('Picked Yes')
                finished = True
                break
            else:
                print('Unknown command')
                continue
        if finished:
            break
        else:
            continue
    
    return time_test


def horizontal_bar_plot(container, title='unknowntitle', x_label='unknownlabel', y_limit=30, color='royalblue', filename='unknown.png') -> ( str | None ):
    """Create simple horizontal bar graphs. Excepted dictionary is a simple one, format {player : int, player : int, ...}.
    Will return filename that was saved to CWD, or None if container is empty.
    """
    BAR_HEIGHT = 0.8
    BAR_SEPARATION_MODIFIER = 0.4
    fig, axis = plt.subplots()
    y_tick_labels = []
    y_tick_pos = []

    if len(container) == 0:
        return None
    if len(container) < y_limit:
        y_limit = len(container)
    
    y_pos = BAR_HEIGHT
    for k in container:
        axis.barh(y_pos, container[k], color=color)
        y_pos += BAR_HEIGHT + BAR_SEPARATION_MODIFIER
    
    for n in range(y_limit):
        key = tuple(container.keys())[n]
        key = truncate_string(key, 14)
        y_tick_labels.append(key)
        y_tick_pos.append(BAR_HEIGHT + ((BAR_HEIGHT + BAR_SEPARATION_MODIFIER) * n))
    
    y_tick_labels.append('')
    y_tick_pos.append(y_tick_pos[-1] + BAR_HEIGHT) # ghost tick
    
    axis.set_ybound(0, y_limit)
    axis.set_xlabel(x_label)
    axis.set_ylabel('Entity')
    axis.set_title(title)
    axis.set_yticks(y_tick_pos, labels=y_tick_labels)
    plt.gca().invert_yaxis()
    plt.tight_layout()
    fig.set_facecolor('gainsboro')
    plt.grid(axis='x')
    axis.set_axisbelow(True)
    plt.savefig(filename)
    plt.clf()
    return filename


def stacked_horizontal_bar_plot(dict1, dict2, title='unknowntitle', x_label='unknownlabel', y_limit=30,
color1='royalblue', color2='tab:green', filename='Received Damage.png', dict1_name='Received Damage', dict2_name='Self-Healing') -> ( str | None ):
    """Create two bars stacked ontop of eachother per player. Will return filename that was saved to CWD, or None if dict1 is empty.
    Expected dictionaries are simple {player:int,player:int,...}. dict2 will be ontop of dict1.
    """
    BAR_HEIGHT = 0.8
    BAR_SEPARATION_MODIFIER = 0.4
    y_tick_labels = []
    y_tick_pos = []
    fig, axis = plt.subplots()

    if len(dict1) == 0:
        return None
    elif len(dict1) < y_limit:
        y_limit = len(dict1)
    
    dict2_copy = copy.deepcopy(dict2)
    
    y_pos = BAR_HEIGHT
    for k in dict1:
        dict2_copy.setdefault(k, 0)
        axis.barh(y_pos, dict1[k], color=color1, label='bar1')
        axis.barh(y_pos, dict2_copy[k], color=color2, label='bar2', hatch='/' * 5)
        y_pos += BAR_HEIGHT + BAR_SEPARATION_MODIFIER
        

    for n in range(y_limit):
        key = tuple(dict1.keys())[n]
        key = truncate_string(key, 14)
        y_tick_labels.append(key)
        y_tick_pos.append(BAR_HEIGHT + ((BAR_HEIGHT + BAR_SEPARATION_MODIFIER) * n))
    
    y_tick_labels.append('')
    y_tick_pos.append(y_tick_pos[-1] + BAR_HEIGHT) # ghost tick

    axis.set_xlabel(x_label)
    axis.set_ybound(0, y_limit + BAR_HEIGHT) # but why even ask? it forces it to the ticks you set, yet this is required? what am I missing?
    axis.set_ylabel('Player')
    axis.set_title(title)
    axis.set_yticks(y_tick_pos, labels=y_tick_labels)
    axis.legend((dict1_name, dict2_name), loc='lower right', fontsize='x-small')
    fig.set_facecolor('gainsboro')
    fig.text(0.005, 0.01, 'Only unabsorbed received damage represented, no pve\nSelf-healing is any from outside vitalism (items, buffs, gear...) INCLUDING pve',
    fontsize='x-small')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.grid(axis='x')
    axis.set_axisbelow(True)
    fig.savefig(filename)
    plt.clf()

    return filename


def complex_song_plot(container, buff_or_debuff:bool, title='unknowntitle', y_label='unknownlabel', filename='Songchart.png', y_limit=20) -> ( str | None ):
    """Create 'complex' songchart. Will return filename that was saved to CWD, or None if container is empty.
    buff_or_debuff == True for buff, False for debuff.
    """
    def customSongSort(element):
        scanned = element[0][0:3]
        scan_dict = {'bul' : 0, 'blo' : 1, 'qui' : 2,
                     'ung' : 3, 'let' : 4, 'unp' : 5} # shortening of song names, see BUFFS/DEBUFFS below
        return scan_dict[scanned]

    BAR_HEIGHT = 1
    BAR_SEPARATION_MODIFIER = 0.7
    BUFFS = ('bulwark ballad (rank 2)', 'bloody chantey (rank 2)', 'quickstep (rank 5)')
    DEBUFFS = ('unguarded', 'lethargy (bloody chantey)', 'unpleasant sensation (quickstep)')
    LEGEND_BUFFS = ("Bulwark Ballad", "Bloody Chantey", "Quickstep")
    LEGEND_DEBUFFS = ("Unguarded (Bulwark Ballad)", "Lethargy (Bloody Chantey)", "Unpleasant Sensation (Quickstep)")
    COLOR_TABLE_BUFFS = ('royalblue', 'crimson', 'orange')
    COLOR_TABLE_DEBUFFS = ('#3a5cc3', '#b61233', '#cd8500')
    fig, axis = plt.subplots()
    
    if len(container) == 0:
        return None
    elif len(container) < y_limit:
        y_limit = len(container)
    
    if buff_or_debuff:
        songs_buff_or_debuff = BUFFS
        color_buff_or_debuff = COLOR_TABLE_BUFFS
        legend_buff_or_debuff = LEGEND_BUFFS
    else: 
        songs_buff_or_debuff = DEBUFFS
        color_buff_or_debuff = COLOR_TABLE_DEBUFFS
        legend_buff_or_debuff = LEGEND_DEBUFFS

    y_pos = BAR_HEIGHT
    for k in container:
        for n in songs_buff_or_debuff:
            container[k].setdefault(n, 0) # dicts are mutable! but this is ok side effect
        container[k] = dict(sorted(tuple(container[k].items()), key=customSongSort)) 
        color_num = 0
        for s in container[k]:
            axis.barh(y_pos, container[k][s], label=s, color=color_buff_or_debuff[color_num], height=BAR_HEIGHT)
            color_num += 1
            y_pos += BAR_HEIGHT
        y_pos += BAR_SEPARATION_MODIFIER

    y_tick_pos = []
    y_tick_labels = []
    
    for n in range(y_limit):
        y_tick_pos.append((BAR_HEIGHT * 2) + ((BAR_HEIGHT * 3 + BAR_SEPARATION_MODIFIER) * n))
        key = tuple(container.keys())[n]
        key = truncate_string(key, 14)
        y_tick_labels.append(key)

    y_tick_pos.append(y_tick_pos[-1] + BAR_HEIGHT + 0.4) # ghost tick
    y_tick_labels.append('') 

    axis.set_ylabel(y_label)
    axis.set_ylim(0, y_limit)
    axis.set_xlabel('Seconds')
    axis.set_title(title)
    axis.set_yticks(y_tick_pos, labels=y_tick_labels)
    axis.legend(legend_buff_or_debuff, loc='lower right', fontsize='x-small')
    plt.tight_layout()
    fig.set_facecolor('gainsboro')
    plt.grid(axis='x')
    axis.set_axisbelow(True)
    plt.gca().invert_yaxis()
    fig.savefig(filename)
    fig.clear()
    axis.clear()
    
    return filename


def move_to_folder(files_to_move: list, folder: str) -> (str | None):
    """Move list of files in first argument to folder in second argument, both always relative to CWD
    
    A numbered subfolder will be created inside the chosen folder if the folder already contains the requested files.
    Returns string of subfolder's name if this happens, else None
    """
    for f in files_to_move:
        if os.path.isabs(f):
            raise ValueError('move_to_folder() argument 1 is using an absolute path: %s' % (f))
    if os.path.isabs(folder):
        raise ValueError('move_to_folder() argument 2 is using an absolute path: %s' % (folder))
    
    if not os.path.isdir(folder):
        os.makedirs(folder)

    base_folder_occupied = False
    for n in files_to_move:
        if os.path.isfile(folder + '\\' + n):
            base_folder_occupied = True
    
    if not base_folder_occupied:
        for n in files_to_move:
            shutil.move(n, folder)
        return None

    n = 0
    while True: # find n of subfolder to use
        n += 1
        if os.path.isdir(folder + '\\' + str(n)):
            continue
        else:
            break
    
    os.mkdir(folder + '\\' + str(n))
    for m in files_to_move:
        shutil.move(m, folder + '\\' + str(n))
    return str(n)


def user_prompt_file() -> (str | None):
    """Prompts user for file to use.
    
    Returns the absolute directory of the location of the prompted combat.log. If nothing picked, return None.
    """
    print('Pick a valid file.')
    allowed_ext = ('.log', '.txt')
    user_file = filedialog.askopenfilename(filetypes = [('Plaintext file', allowed_ext)])
    
    if user_file == "":
        print('Picked nothing, returning.')
        return None

    return user_file


def user_prompt_copy_log(file:str) -> bool:
    """Ask wether to copy a file to output folder. Doesn't actually copy. Argument will be the name used to refer to file."""
    while True:
        print('''Do you want to copy the %s to the output folder?
(Y) for Yes, (N) for No.''' % (file))
        user_input = input().lower()
        if user_input == 'y':
            print('Picked Yes.')
            return True
        elif user_input == 'n':
            print('Picked No.')
            return False
        else:
            print('Unknown command, looping')


def write_to_txt(custom: bool, custom_message='', dict_container={}, title='', filename='Output.txt'):
    """Appends to a given plaintext file. Has two modes, depending on argument 1, which must be a boolean.
    Keyword arguments:
    
    custom_message -- used if custom is True, appends only this string to file (default '')
    
    dict_container -- used if custom is False, writes its contents (key, value pair) to the file. If empty, writes "NO DATA" : "IN DICT"
    
    title -- used if custom is False, appears once above the contents of dict_container (default '')
    
    filename -- the file to write to, must be relative path (default 'Output.txt')
    """
    if type(custom) is not bool:
        raise TypeError('Argument "custom" is not boolean')
    
    if os.path.isabs(filename):
        raise ValueError('Argument "filename" is an absolute path')
    
    if not custom:
        if len(dict_container) == 0:
            dict_container.setdefault("NO DATA" , "IN DICT")
        
        with open(filename, 'a', encoding='utf-8') as f:
            f.write('   ----- ' + title + ' -----    \n')
            for k in dict_container.keys():
                f.write('%s : %s\n' % (k, dict_container[k]))
            f.write('\n')
    else:
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(custom_message + '\n')


def truncate_string(string:str, limit:int) -> str:
    '''Given a string, truncates the max length it can have by a given integer, then returns the new string. Limit is inclusive.
    The given string will never go over length given by limit: if the string is truncated, the last 3 characters before limit will be "...".
    '''
    if limit <= 3:
        raise ValueError('"limit (of value %s)" must be value > 3.' % (limit))

    if len(string) > limit:
        string = string[:limit - 3] + "..."

    return string


def build_simple_dict(dictionary):
    """Return a new dict from argument dict that contains only the key and that key's "total" value: {"key" : total}"""
    dictionary_simple = {}
    for k in dictionary:
        dictionary_simple.setdefault(k, dictionary[k]["total"])
    
    return dictionary_simple


def fix_dict_formatting(line) -> dict:
    """Fix formatting of dicts directly written as strings.
    Currently loses double quotes inside keys or values, writing them as '' """
    for i, char in enumerate(line):
        if char == " " and line[i+1] == ":" and line[i+2] == " ":
            i += 1
            break
    line = "{\"" + line[0:i-1] + "\"" + line[i-1:] + "}"
    
    if "\"" in line: # some values have ' in them, in which case python delimits them with "" instead of '' when writing to txt.
        single_quote_pos = []
        double_quote_pos_temp = []
        double_quote_pos = []
        double_quote = False
        for i, char in enumerate(line):
            if char == "\"":
                double_quote += 1
                double_quote_pos_temp.append(i)
            
            elif char == ":":
                m = 0
                o = False
                while True:
                    m += 1
                    if line[i+m] == " ":
                        o = True
                        continue
                    elif o and line[i+m] in (",", "}", "{"):
                        break
                    elif line[i+m] in ("\"", "\'"):
                        m = -1
                        break
                        
                if m == -1:
                    continue
                
                elif len(double_quote_pos_temp) > 2:
                    double_quote_pos.append(double_quote_pos_temp[1:-1][0])
                double_quote_pos_temp.clear()
                double_quote = 0
            
            elif double_quote != 0 and char == "\'":
                single_quote_pos.append(i)
            
        line = list(line)
        for i, n in enumerate(line):
            if n == "\'" and i not in single_quote_pos:
                line[i] = "\""
            elif n == "\"" and i in double_quote_pos:
                line[i] = "\'\'"
        line = "".join(line)

    else:
        line = line.replace("'", "\"")
    line = json.loads(line)
    return line


def error_traceback_print():
    """Print error using traceback.print_exception()"""
    traceback.print_exception(sys.exception(), file=sys.stdout)
    print("Script recovered from error\n")


############################## module end


user_prompt_main()