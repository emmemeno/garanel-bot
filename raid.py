import os
import logging
import config
import json
from datetime import datetime

log = logging.getLogger("Garanel")


class Player:
    def __init__(self, name, anon=False, lvl=None, role=None, race=None, afk=False, eqdkp=None):
        self.name = name
        self.lvl = lvl
        self.role = role
        self.race = race
        self.anon = anon
        self.afk = afk
        self.eqdkp_id = eqdkp

    def __repr__(self):
        return f"OBJ Player: {self.name}"

    def get_log_line(self):
        output = ""

        if self.afk:
            output += " AFK "
        if self.anon:
            output += f"[ANONYMOUS] {self.name}  "
        else:
            output += f"[{self.lvl} {self.role}] {self.name} ({self.race}) "

        output += f"<{config.GUILD_NAME}>"

        return output

    def serialize(self):
        return {"name": self.name,
                "anon": self.anon,
                "lvl": self.lvl,
                "role": self.role,
                "race": self.race,
                "afk": self.afk,
                'eqdkp_id': self.eqdkp_id
                }


class Item:
    def __init__(self, name, char_winner, points):
        self.name = name
        self.char_winner = char_winner
        self.points = points

    def serialize(self):
        return {"name": self.name,
                "char_winner": self.char_winner,
                "points": self.points}


class Raid:

    def __init__(self,
                 name_id: str,
                 date: str,
                 event_name: str,
                 event_id,
                 discord_channel_id: int,
                 close: bool,
                 kill,
                 points,
                 log_loaded: bool,
                 log_final: str,
                 players: list,
                 items: list,
                 ):
        self.name_id = name_id
        try:
            self.date = datetime.strptime(date, config.DATE_EQDKP_FORMAT)
        except ValueError as e:
            log.error(f"RAID: Error loading Date: {e}")
            self.date = datetime.utcnow()

        self.event_name = event_name
        self.event_id = event_id

        self.players = players
        self.items = items
        self.discord_channel_id = discord_channel_id
        self.discord_attenders_preview_message_id = None
        self.log_loaded = log_loaded
        self.kill = kill
        self.points = points
        self.log_final = log_final
        self.close = close
        self.status_save = False

    def __repr__(self):
        if self.event_name:
            return self.event_name
        return self.name_id

    def add_raid_player(self, player: Player, dkp):
        if self.has_player_by_name(player.name):
            return False
        else:
            # Add player to raid
            self.players.append(player)
            # Add pending raid to user
            user = dkp.get_user_by_char_name(player.name)
            if user:
                dkp.users[user]['pending_raids'].append(self)
                log.info(f"ADD PENDING RAID TO USER: {user}")
            self.players.sort(key=lambda x: x.name, reverse=False)
            self.status_save = True
            return True

    # def add_player_by_name(self, player_name: str):
    #     self.players.append(Player(player_name, anon=True))

    def del_raid_player(self, player: Player, dkp):
        get_char = self.has_player_by_name(player.name)
        if get_char:
            self.players.remove(get_char)
            # Remove pending raid to user
            user = dkp.get_user_by_char_name(player.name)
            if user:
                dkp.users[user]['pending_raids'].remove(self)
                log.info(f"REMOVE PENDING RAID TO USER: {user}")
                self.status_save = True
            return True
        else:
            return False

    def add_item(self, name: str, points, char_winner: Player, user_winner):
        item = Item(name, char_winner, points)
        self.items.append(item)
        self.status_save = True

    def wipe_items(self):
        del self.items[:]
        self.status_save = True

    def close(self):
        self.close = True
        self.status_save = True

    def has_player(self, player: Player):
        if player in self.players:
            return True
        return False

    def has_player_by_name(self, name: str):
        for char in self.players:
            if char.name.lower() == name.lower():
                return char
        return False

    def get_players(self, filter="ALL"):
        output_players = []
        for player in self.players:
            if filter == "NO_DKP" and not player.eqdkp_id:
                output_players.append(player)
            elif filter == "ONLY_DKP" and player.eqdkp_id:
                output_players.append(player)
            elif filter == "ALL":
                output_players.append(player)

        return output_players

    def get_item_by_user(self, user):
        pending_items = []
        for item in self.items:
            for char in user['chars']:
                if item.char_winner == char.name:
                    pending_items.append(item)
        return pending_items

    def get_player_eqdkp_id_list(self):
        output = []
        for player in self.players:
            if player.eqdkp_id:
                output.append(player.eqdkp_id)
        return output

    def get_log_format_date(self):
        return self.date.strftime(config.DATE_EQ_LOG_FORMAT)

    def refresh_dkp_status(self, dkp_users):
        log.info(f"RAID SYNC: {self.name_id} refreshing...")
        for user in dkp_users:
            for char in dkp_users[user]['chars']:
                for player in self.players:
                    if char.name == player.name:
                        # Update the player
                        if not player.eqdkp_id == char.id:
                            player.eqdkp_id = char.id
                            self.status_save = True
                        # Update the user
                        if self not in dkp_users[user]['pending_raids']:
                            dkp_users[user]['pending_raids'].append(self)
                        log.debug(f"RAID SYNC: {user} added to pending raid")
                    else:
                        char.eqdkp_id = False
                for item in self.items:
                    pass

        log.info(f"RAID SYNC: {self.name_id}: Done!")

    def delete_pending_raids_from_user(self, dkp_users):
        log.info(f"RAID SYNC: Deleting Pending Raids from Users")
        for user in dkp_users:
            for char in dkp_users[user]['chars']:
                for player in self.players:
                    # Update the user
                    if char.name == player.name:
                        try:
                            dkp_users[user]['pending_raids'].remove(self)
                        except Exception as e:
                            pass

                        log.debug(f"RAID SYNC: Deleting {user} from pending raid")


    def set_kill(self, mode):
        self.kill = mode
        self.status_save = True
        return True

    def create_log_file(self):
        status = ""
        if self.kill is True:
            status = "-kill"
        if self.kill is False:
            status = "-nokill"

        file_name = f"{self.name_id}{status}.txt"
        file_url = config.PATH_HISTORY+file_name
        if os.path.isfile(file_url):
            mode = "w"
        else:
            mode = "a"
        with open(file_url, mode) as output_file:
            for char in self.players:
                output_file.write(f"[{self.get_log_format_date()}] {char.get_log_line()}\n")
        self.log_final = file_name
        self.status_save = True
        return file_name

    def serialize(self):
        player_list = []
        item_list = []
        for item in self.items:
            item_list.append(item.serialize())
        for char in self.players:
            player_list.append(char.serialize())
        return {'name_id': self.name_id,
                'date': self.date.strftime(config.DATE_EQDKP_FORMAT),
                'event_name': self.event_name,
                'event_id': self.event_id,
                'discord_channel_id': self.discord_channel_id,
                'close': self.close,
                'kill': self.kill,
                'points': self.points,
                'log_loaded': self.log_loaded,
                'log_final': self.log_final,
                'players': player_list,
                'items': item_list
                }

    def autosave(self):
        if self.status_save:
            log.info(f"Auto-saving {self}")
            self.save()
            self.status_save = False
            return True
        return False

    def save(self):
        file_url = config.PATH_RAIDS + self.name_id + '.json'
        if os.path.isfile(file_url):
            mode = "w"
        else:
            mode = "a"
        with open(file_url, mode) as outfile:
            json.dump(self.serialize(), outfile, indent=4)
        log.info(f"RAID: {self.name_id} saved.")
        return True


