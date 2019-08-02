import os
import logging
from player import Player
import config
import json
from datetime import datetime


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
        self.date_log = date
        self.date_creation = datetime.utcnow()
        self.players = players
        self.items = items
        self.discord_channel_id = discord_channel_id
        self.discord_attenders_preview_message_id = None
        self.log_loaded = log_loaded
        self.kill = kill
        self.points = points
        self.log_final = log_final
        self.close = close

    def add_raid_player(self, player: Player):
        if self.has_player_by_name(player.name):
            return False
        else:
            self.players.append(player)
            self.players.sort(key=lambda x: x.name, reverse=False)
            return True

    # def add_player_by_name(self, player_name: str):
    #     self.players.append(Player(player_name, anon=True))

    def del_raid_player(self, player: Player):
        get_char = self.has_player_by_name(player.name)
        if get_char:
            self.players.remove(get_char)
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


    def refresh_dkp_status(self, dkp_chars):
        log.info(f"RAID {self.name_id}: Syncing raid players to eqdkp chars...")
        for char in dkp_chars:
            for player in self.players:
                if char.name == player.name:
                    player.eqdkp_id = char.id
                else:
                    char.eqdkp_id = False
        log.info(f"RAID {self.name_id}: Done!")
        self.save()

    def create_log_file(self):
        status = ""
        if self.kill is True:
            status = "-kill"
        if self.kill is False:
            status = "-nokill"

        file_name = f"{self.name_id}{status}.txt"
        with open(config.PATH_HISTORY+file_name, 'a') as output_file:
            for char in self.players:
                output_file.write(f"[{self.date_log}] {char.get_log_line()}\n")
        self.log_final = file_name
        return file_name

    def serialize(self):
        player_list = []
        for char in self.players:
            player_list.append(char.serialize())
        return {'name_id': self.name_id,
                'date': self.date_log,
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
        log.info(f"Raid {self.name_id} saved.")
        return True


