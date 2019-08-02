import re
import urllib.parse
from datetime import datetime
from player import Player


class LineParser:

    def __init__(self, line: str):
        self.line = line
        self.param = None
        self.action = None
        self.raid_name_id = None
        self.raid_name = None
        self.players_to_add = []
        self.players_to_remove = []
        self.item_url = None
        self.item_name = None
        self.item_dkp = None
        self.item_winner = None
        self.log_date = None
        self.split_words = None
        self.error = None

    def process(self):
        if not self.line:
            return False

        low_line = self.line.lower()

        # About
        if low_line.startswith('$about'):
            self.action = 'ABOUT'

        # Help
        if low_line.startswith('$help'):
            self.action = 'HELP'
            self.param = self.line[5:].lstrip().split(' ', 1)[0]

        if low_line.startswith('$dkp'):
            self.action = 'GET_DKP'
            if len(self.line) > 5:
                self.param = self.line[5:].strip(" ").capitalize()
        # Status of the raid
        if low_line.startswith('$raid-status'):
            self.action = 'RAID_STATUS'

        # Add a Raid
        if low_line.startswith('$raid-add '):
            self.action = 'RAID_ADD'
            self.raid_name = self.line[10:]
            self.raid_name_id = self.raid_name + '-' + datetime.utcnow().strftime("%b_%d")

        # Close a Raid
        if low_line.startswith('$raid-close'):
            self.action = 'RAID_CLOSE'

        # Close a Raid
        if self.line.startswith('$raid-send'):
            self.action = 'RAID_SEND'

        # Archive a Raid
        if self.line.startswith('$raid-archive'):
            self.action = 'RAID_ARCHIVE'

        # Parse a Log
        if low_line.startswith('['):
            self.parse_log()

        # Add a Player
        if low_line.startswith('+') and len(self.line) > 4:
            self.action = 'ADD_PLAYER'
            split_line = self.line[1:].lstrip().split(' ', 1)[0]
            char_name = re.sub('[^A-Za-z]+', '', split_line).capitalize()
            self.players_to_add.append(Player(char_name, anon=True))

            # search for minus
            reg = re.search(r"( on )", self.line)
            if reg:
                char_to_delete = self.line[reg.end():].split(' ', 1)[0]
                char_to_delete = re.sub('[^A-Za-z]+', '', char_to_delete).capitalize()
                self.players_to_remove.append(Player(char_to_delete, anon=True))

        # Remove a Player
        if low_line.startswith('-') and len(self.line) > 4:
            self.action = 'DEL_PLAYER'
            char_name = self.line[1:].lstrip().split(' ', 1)[0]
            char_name = re.sub('[^A-Za-z]+', '', char_name).capitalize()
            if char_name:
                self.players_to_remove.append(Player(char_name, anon=True))

        # Add an Item
        if low_line.startswith('$item-add '):
            self.action = 'ITEM_ADD'
            self.parse_item()

        # Wipe Items
        if low_line.startswith('$item-wipe'):
            self.action = 'ITEM_WIPE'

        if low_line.startswith('$kill'):
            self.action = 'KILL'

        if low_line.startswith('$nokill'):
            self.action = 'NOKILL'

        if low_line.startswith('$points'):
            self.action = 'SET_RAID_POINTS'
            self.param = re.findall(r'\d+', self.line[7:])
            if len(self.param):
                self.param = int(self.param[0])

        if low_line.startswith('$mainchar-add'):
            self.action = 'ADD_MAIN'
            if len(self.line) > 12:
                self.param = self.line[13:].strip(" ")

        if low_line.startswith('$char-add'):
            self.action = 'ADD_CHAR'
            if len(self.line) > 10:
                self.param = self.line[10:].strip(" ")
                self.split_words = self.param.split(" ")

        if low_line.startswith('$roles'):
            self.action = 'ROLES'
            if len(self.line) > 6:
                self.split_words = self.line.split(" ")

        return self.action

    def parse_log(self):
        self.action = 'ADD_LOG'

        lines = self.line.split('\n')
        for line in lines:
            reg = re.search(r"\[(.*?)\]\s*(AFK)? \[(.*?)\] (\w+) (\(.*?\))? <Riot>", line)
            if reg:
                self.log_date = reg.group(1)
                afk = False
                anon = False
                lvl = role = race = None
                if reg.group(3).upper() == "ANONYMOUS":
                    anon = True
                else:
                    details = reg.group(3).split(" ")
                    lvl = int(details[0])
                    role = details[1]
                    race = reg.group(5)[1:-1]
                if reg.group(2):
                    afk = True
                self.players_to_add.append(Player(reg.group(4), anon, lvl, role, race, afk))

    def parse_item(self):
        item_name = item_winner = item_dkp = None
        line = self.line[len("$item-add"):]
        reg = re.search(r"(http(s)?:\/\/)?wiki.project1999.com\/([-a-zA-Z0-9@:%_\+.~#?&//=]*)", line)
        if reg:
            try:
                item_name = reg.group(0).rsplit("/", 1)[1]
            except:
                pass
        if not item_name:
            return False
        item_name = urllib.parse.unquote(item_name)
        self.item_name = item_name.replace("_", " ")

        new_line = line[:reg.start()] + line[reg.end():]

        # Find DKP
        reg = re.search(r"\b(\d+) ?(dkp|dkps)?", new_line)
        if reg:
            self.item_dkp = reg.group(1)
            new_line = (new_line[:reg.start()] + new_line[reg.end():]).strip(" ")
            if len(new_line) > 2:
                self.item_winner = new_line.strip(" ").capitalize()


