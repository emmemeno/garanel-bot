import re
import urllib.parse
from raid import Player


class LineParser:

    def __init__(self, line: str):
        self.line = line
        self.low_line = self.line.lower()
        self.result = {'action': '', 'params': {}}

    def consume_line(self, string):
        if string:
            try:
                split_line = self.line.split(string)
                self.line = split_line[0] + split_line[1]
                self.line = self.line.strip()
                self.low_line = self.line.lower()
            except IndexError:
                pass

    def parse_command(self, cmd_list):
        for cmd in cmd_list:
            if self.low_line.startswith(cmd):
                self.result['action'] = cmd_list[cmd]
                # Consume the line
                self.line = self.line[len(cmd):].strip()
                self.low_line = self.low_line[len(cmd):].strip()
        return False

    def get_action(self):
        if self.result['action']:
            return self.result['action']
        return False

    def get_params(self):
        return self.result['params']

    def set_param(self, name, value):
        if name and value:
            self.result['params'][name] = value
            return True
        return False

    def parse_first_word(self):
        first_word = self.low_line.split(' ', 1)[0]
        if first_word:
            self.consume_line(first_word)
            return first_word
        return False

    def parse_snippet(self):
        reg = re.search(r"(['\"](.*?)['\"])", self.line)
        if reg:
            print(f"reg1 {reg.group(1)} - reg2 {reg.group(2)}")
            self.consume_line(reg.group(1))
            return reg.group(2)
        return False

    def parse_squares(self):
        reg = re.search(r"([\(](.*?)[\)])", self.line)
        if reg:
            print(f"reg1 {reg.group(1)} - reg2 {reg.group(2)}")
            self.consume_line(reg.group(1))
            return reg.group(2)
        return False

    def process(self):
        if not self.line:
            return False

        command_list = {'$about': 'about',
                        '$help': 'help',
                        '$raid-status': 'raid_status',
                        '$raid-add': 'raid_add',
                        '$raid-close': 'raid_close',
                        '$raid-open': 'raid_open',
                        '$raid-send': 'raid_send',
                        '$raid-archive': 'raid_archive',
                        '$raid-list': 'raid_list',
                        '[': 'raid_add_log',
                        '+': 'raid_add_player',
                        '-': 'raid_del_player',
                        '?': 'raid_search_player',
                        '$item-add': 'raid_item_add',
                        '$item-wipe': 'raid_item_wipe',
                        '$kill': 'raid_kill',
                        '$nokill': 'raid_nokill',
                        '$points': 'raid_set_points',
                        '$mainchar-add': 'dkp_mainchar_add',
                        '$char-add': 'dkp_char_add',
                        '$dkp': 'dkp',
                        '$who': 'who',
                        '$sync': 'sync',
                        '$dkp-adj': 'dkp_adjust',
                        '$roles': 'roles'
                        }

        self.action = self.parse_command(command_list)

        ##
        # PARSING COMMAND SPECIFIC PARAMS
        ##
        if self.get_action() == 'help':
            self.set_param("help_command", self.parse_first_word())

        if self.get_action() == 'get_dkp':
            self.set_param("dkp_target", self.parse_first_word())

        if self.get_action() == 'who':
            self.set_param("who", self.parse_first_word().capitalize())

        if self.get_action() == 'raid_add':
            self.set_param("event_name", self.parse_squares())
            self.set_param("raid_name", self.line)

        if self.get_action() == 'raid_add_log':
            self.parse_log()

        if self.get_action() == 'raid_add_player':
            reg = re.search(r"^(([A-Za-z]+)([^A-Za-z]+)?)(on (\w+))?", self.low_line)
            if reg:
                if reg.group(2):
                      self.set_param('player_to_add', reg.group(2).capitalize())
                if reg.group(5):
                       self.set_param('player_to_remove', reg.group(5).capitalize())

        if self.get_action() == 'raid_del_player':
            self.set_param('player_to_remove', self.parse_first_word().capitalize())

        if self.get_action() == 'raid_search_player':
            self.set_param('player_to_search', self.parse_first_word().capitalize())

        if self.get_action() == 'raid_item_add':

            self.parse_item()

        if self.get_action() == 'raid_set_points':
            points = re.findall(r'\d+', self.line)
            if len(points):
                self.set_param('raid_points', int(points[0]))

        if self.get_action() == 'dkp_mainchar_add':
            self.set_param('main_char', self.parse_first_word().capitalize())

        if self.get_action() == 'dkp_char_add':
            self.set_param('char', self.parse_first_word().capitalize())

        if self.get_action() == 'dkp_adjust':
            reg = re.search(r"([A-Za-z#]+[0-9]{4,4}\b) (\+|-)?([0-9]{1,3}) ['\"](.*?)['\"]", self.line)
            if reg:
                self.set_param('user', reg.group(1).capitalize())
                if not reg.group(2):
                    sign = "+"
                else:
                    sign = reg.group(2)
                self.set_param('points', float(sign + reg.group(3)))
                self.set_param('reason', reg.group(4))

        if self.get_action() == 'roles':
            self.set_param('bot_role', self.parse_first_word())
            self.set_param('discord_role_id', self.parse_first_word())

        return self.result

    def parse_log(self):
        self.line = "[" + self.line
        print(self.line)
        lines = self.line.split('\n')
        players = []
        for line in lines:
            reg = re.search(r"\[(.*?)\]\s*(AFK)? \[(.*?)\] (\w+) (\(.*?\))? <Riot>", line)
            if reg:
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

                players.append(Player(reg.group(4), anon, lvl, role, race, afk))

        self.set_param('players_to_add', players)

    def parse_item(self):
        item_name = item_winner = item_dkp = None
        reg = re.search(r"(http(s)?:\/\/)?wiki.project1999.com\/([-a-zA-Z0-9@:%_\+',.~#?&//=]*)", self.line)
        if reg:
            try:
                item_name = reg.group(0).rsplit("/", 1)[1]
            except:
                return False
        self.consume_line(reg.group(0))
        item_name = urllib.parse.unquote(item_name).replace("_", " ")
        self.set_param("item_name", item_name)

        # Find DKP
        reg = re.search(r"\b(\d+) ?(dkp|dkps)?", self.low_line)
        if reg:
            self.set_param('item_dkp', reg.group(1))
            self.consume_line(reg.group(0))
            if len(self.low_line) > 2:
                self.set_param('item_winner', self.low_line.strip(" ").capitalize())



