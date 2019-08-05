import os
import logging
import config
import json
from datetime import datetime

class Player:
    def __init__(self, name, anon=False, lvl=None, role=None, race=None, afk=False, eqdkp=None):
        self.name = name
        self.lvl = lvl
        self.role = role
        self.race = race
        self.anon = anon
        self.afk = afk
        self.eqdkp_id = eqdkp

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

    def __repr__(self):
        return self.name

    def serialize(self):
        return {"name": self.name,
                "anon": self.anon,
                "lvl": self.lvl,
                "role": self.role,
                "race": self.race,
                "afk": self.afk,
                'eqdkp_id': self.eqdkp_id
                }


log = logging.getLogger("Garanel")


class Raid:

    def __init__(self,
                 name_id: str,
                 date: str,
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

        self.players = players
        self.items = items
        self.discord_channel_id = discord_channel_id
        self.discord_attenders_preview_message_id = None
        self.log_loaded = log_loaded
        self.kill = kill
        self.points = points
        self.log_final = log_final
        self.close = close

    def __repr__(self):
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
            return True
        else:
            return False

    def add_item(self, name: str, points, winner: Player):
        if name in self.items:
            return False

        self.items.append({'name': name, 'points': points, 'winner': winner})

    def wipe_items(self):
        del self.items[:]

    def close(self):
        self.close = True

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
                        player.eqdkp_id = char.id
                        # Update the user
                        if self not in dkp_users[user]['pending_raids']:
                            dkp_users[user]['pending_raids'].append(self)
                        log.debug(f"RAID SYNC: {user} added to pending raid")
                    else:
                        char.eqdkp_id = False
        log.info(f"RAID SYNC: {self.name_id}: Done!")
        self.save()

    def delete_pending_raids_from_user(self, dkp_users):
        log.info(f"RAID SYNC: Deleting Pending Raids from Users")
        for user in dkp_users:
            for char in dkp_users[user]['chars']:
                for player in self.players:
                    # Update the user
                    if char.name == player.name:
                        dkp_users[user]['pending_raids'].remove(self)
                        log.debug(f"RAID SYNC: Deleting {user} from pending raid")

    def create_log_file(self):
        status = ""
        if self.kill is True:
            status = "-kill"
        if self.kill is False:
            status = "-nokill"

        file_name = f"{self.name_id}{status}.txt"
        with open(config.PATH_HISTORY+file_name, 'a') as output_file:
            for char in self.players:
                output_file.write(f"[{self.get_log_format_date()}] {char.get_log_line()}\n")
        self.log_final = file_name
        return file_name

    def serialize(self):
        player_list = []
        for char in self.players:
            player_list.append(char.serialize())
        return {'name_id': self.name_id,
                'date': self.date.strftime(config.DATE_EQDKP_FORMAT),
                'discord_channel_id': self.discord_channel_id,
                'close': self.close,
                'kill': self.kill,
                'points': self.points,
                'log_loaded': self.log_loaded,
                'log_final': self.log_final,
                'players': player_list,
                'items': self.items
                }

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


