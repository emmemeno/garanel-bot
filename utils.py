import config
import os
import glob
import aiohttp
import json
from raid import Raid
from raid import Player
import logging

log = logging.getLogger("Garanel")


def load_raids(path):
    json_raids = []
    raid_list = []
    for file in glob.glob(os.path.join(path, '*.json')):
        with open(file) as f:
            json_raids.append(json.load(f))

    for raid in json_raids:

        player_list = []
        item_list = []
        for char in raid['players']:
            player_list.append(Player(char['name'],
                                      char['anon'],
                                      char['lvl'],
                                      char['role'],
                                      char['race'],
                                      char['afk'],
                                      char['eqdkp_id']))
        for item in raid['items']:
            item_list.append(item)
        raid_list.append(Raid(raid['name_id'],
                              raid['date'],
                              raid['discord_channel_id'],
                              raid['close'],
                              raid['kill'],
                              raid['points'],
                              raid['log_loaded'],
                              raid['log_final'],
                              player_list,
                              item_list,
                              ))
        log.debug(f"Raid Loaded: {raid['name_id']}")
    return raid_list


def get_raid_by_name_id(raid_list, name_id):
    for raid in raid_list:
        if raid.name_id == name_id:
            return raid
    return False


def get_raid_by_category_id(raid_list, cat_id):
    pass


def get_raid_by_channel_input_id(raid_list, channel_id):
    for raid in raid_list:
        if raid.discord_channel_id == channel_id:
            return raid
    return False


async def load_remote_json(url, params):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                return await resp.json()
    except Exception as exc:
        log.error(f"Error on Fetching data from {config.EQDKP_API_URL}: {exc}")
        return False


def load_local_json(path):
    with open(path) as f:
        return json.load(f)


def save_local_json(path, json_data):
    with open(path, "w") as f:
        json.dump(json_data, f, indent=4)
        return True


def update_raid_attendees_dkp_status(raid_list, dkp):
    updated_players = []
    for raid in raid_list:
        players = raid.get_players(filter="NO_DKP")
        for player in players:
            if dkp.get_user_by_char_name(player.name):
                player.eqdkp = True
                updated_players.append(player)
                log.debug(f"EQDKP Player updated: {player.name} in {raid.name_id}")

    return updated_players


def remove_json_raid(raid: Raid):
    file_url = config.PATH_RAIDS + raid.name_id + ".json"
    os.remove(file_url)
    log.debug(f"{file_url} REMOVED")

def remove_log_raid(raid: Raid):
    file_url = config.PATH_HISTORY + raid.log_final
    os.remove(file_url)
    log.debug(f"{file_url} REMOVED")


def check_if_channel(raid: Raid, client):
    if client.get_channel(raid.discord_channel_id):
        return True
    else:
        return False
