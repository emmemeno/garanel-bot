import utils
import config
import dicttoxml
import timehandler as timeh
import logging
import os
import datetime
import aiohttp
from raid import Raid
from player import Player

log = logging.getLogger("Garanel")


class DkpChar:

    def __init__(self, char_id, char_name):
        self.id = char_id
        self.name = char_name

class Dkp:

    def __init__(self):
        self.users = {}
        self.raw_points = None
        self.raw_raids = None
        self.points_last_read = None
        self.raids_last_read = None
        self.last_rest_error = None

    async def load_chars(self):
        main_counter = 0
        char_counter = 0

        if await self.load_remote_chars():
            self.points_last_read = timeh.now()
            log.info("EQDKP: Remote Points loaded")
            self.save_local_chars()
            log.info("EQDKP: Saved Points locally.")
        elif self.load_local_chars():
            self.points_last_read = datetime.datetime.fromtimestamp(os.path.getmtime(config.LOCAL_EQDK_POINTS))
            log.info("EQDKP: Local Points loaded")
        else:
            log.info("EQDKP: Error on loading Points")
            return False

        self.users.clear()

        for player in self.raw_points['players']:
            main_name = self.raw_points['players'][player]['main_name'].lower().capitalize()
            char_name = self.raw_points['players'][player]['name'].lower().capitalize()
            char_id = int(self.raw_points['players'][player]['id'])
            main_id = int(self.raw_points['players'][player]['main_id'])
            dkp_total = self.raw_points['players'][player]['points']['multidkp_points:1']['points_current_with_twink']
            dkp_total = int(round(float(dkp_total)))

            # If there is no user, create it!
            if main_name not in self.users:
                if not char_id == main_id:
                    # if the char name is not the main name create a user with main name and add the char name to it
                    main_counter += 1
                    char_counter += 1
                    self.add_new_user(char_id, main_name, dkp_total)
                    self.add_new_char(char_id, char_name, main_name)
                # if this is a main char, just add the user
                else:
                    main_counter += 1
                    self.add_new_user(main_id, main_name, dkp_total)
            # If there is the user and the player name is not the user name, add the char
            else:
                # Don't save main_user as a player_user
                if not main_name == char_name:
                    char_counter += 1
                    log.debug(f"EQDKP: Adding {char_name} to {main_name}")
                    self.add_new_char(char_id, char_name, main_name)
        log.info(f"EQDKP: Points fetched - {main_counter} mains and {char_counter} chars added")
        return True

    def add_new_user(self, user_id, main_name, dkp_points):
        log.debug(f"EQDKP: Adding User {main_name}")
        self.users.update({main_name: {'user_id': user_id, 'dkp': dkp_points,'chars': []}})
        return True

    def add_new_char(self, player_id, char_name, main_name):
        log.debug(f"EQDKP: Adding Char {char_name} to {main_name}")
        self.users[main_name]['chars'].append(DkpChar(player_id, char_name))

    async def get_raids(self):
        if await self.load_remote_raids():
            self.raids_last_read = timeh.now()
            log.info("EQDKP: Remote Raids loaded")
            self.save_local_raids()
            log.info("EQDKP: Saved Raids locally.")
        elif self.load_local_raids():
            self.raids_last_read = datetime.datetime.fromtimestamp(os.path.getmtime(config.LOCAL_EQDK_POINTS))
            log.info("EQDKP: Local Raids loaded")
        else:
            log.info("EQDKP: Error on loading Raids")
            return False

    async def load_remote_chars(self):

        log.info("EQDKP: Loading Remote Points file...")
        params = {'function': "points", 'format': 'json', 'atoken': config.EQDKP_API_KEY, 'atype': 'api'}
        self.raw_points = await utils.load_remote_json(config.EQDKP_API_URL, params=params)
        if self.raw_points:
            return True
        return False

    def load_local_chars(self):
        log.info("EQDKP: Loading Local Points file...")
        self.raw_points = utils.load_local_json(config.LOCAL_EQDK_POINTS)
        if self.raw_points:
            return True
        return False

    def save_local_chars(self):
        log.info("EQDKP: Saving Remote Points file locally...")
        if utils.save_local_json(config.LOCAL_EQDK_POINTS, self.raw_points):
            return True
        return False

    async def load_remote_raids(self):

        log.info("EQDKP: Loading Remote Raids file...")
        params = {'function': "raids", 'format': 'json', 'atoken': config.EQDKP_API_KEY, 'atype': 'api'}
        self.raw_raids = await utils.load_remote_json(config.EQDKP_API_URL, params=params)
        if self.raw_points:
            return True
        return False

    def load_local_raids(self):
        log.info("EQDKP: Loading Local Raids file...")
        self.raw_raids = utils.load_local_json(config.LOCAL_EQDK_RAIDS)
        if self.raw_points:
            return True
        return False

    def save_local_raids(self):
        log.info("EQDKP: Saving Remote Raids file locally...")
        if utils.save_local_json(config.LOCAL_EQDK_RAIDS, self.raw_raids):
            return True
        return False

    def get_all_chars(self):
        output_list = []
        for user in self.users:
            for char in self.users[user]['chars']:
                output_list.append(char)
        return output_list

    def get_user_by_char_name(self, name):
        for user in self.users:
            for char in self.users[user]['chars']:
                if name == char.name:
                    return user
        return False

    def get_user_by_name(self, user_name):
        if user_name in self.users:
            return self.users[user_name]
        return False

    def get_char_by_name(self, find_name):
        for user in self.users:
            for char in self.users[user]['chars']:
                if char.name == find_name:
                    return char
        return False

    def get_chars_by_user_name(self, user_name):
        if user_name in self.users:
            return self.users[user_name]['chars']
        return False

    def get_char_id_by_name(self, char_name):
        for char in self.get_all_chars():
            if char.name == char_name:
                return char.id
        return False

    def get_points_by_user_name(self, user_name):
        if user_name in self.users:
            return self.users[user_name]['dkp']

    async def add_remote_char(self, name, main_id):
        char_data = {'name': name, 'mainid': main_id}
        xml_data = dicttoxml.dicttoxml(char_data, custom_root='request', attr_type=False)
        params = {'function': 'character', 'format': 'json', 'atoken': config.EQDKP_API_KEY, 'atype': 'api'}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(config.EQDKP_API_URL, data=xml_data, params=params) as resp:
                    response = await resp.json()
                    log.debug(f"ADD_REMOTE__CHAR: {response}")
                    if response['status'] == 1:
                        return int(response['character_id'])
                    else:
                        self.last_rest_error = response['error']
                        return False

        except Exception as exc:
            log.error(f"ADD_REMOTE__CHAR: Error on Sending data to {config.EQDKP_API_URL}: {exc}")
            self.last_rest_error = f"ADD_REMOTE__CHAR: Error on Sending data to {config.EQDKP_API_URL}: {exc}"
            return False

    async def add_raid(self, raid: Raid):

        my_item_func = lambda x: 'member'

        raid_data = {'raid_date': raid.date_creation.strftime(config.DATE_EQDKP_FORMAT),
                     'event_name': raid.name_id,
                     'raid_attendees':  raid.get_player_eqdkp_id_list(),
                     'raid_value': raid.points}
        xml_data = dicttoxml.dicttoxml(raid_data, custom_root='request', attr_type=False, item_func=my_item_func)
        params = {'function': 'add_raid', 'format': 'json', 'atoken': config.EQDKP_API_KEY, 'atype': 'api'}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(config.EQDKP_API_URL, data=xml_data, params=params) as resp:
                    response = await resp.json()
                    log.debug(f"ADD_REMOTE__RAID: {response}")
                    if response['status'] == 1:
                        return int(response['raid_id'])
                    else:
                        self.last_rest_error = response['error']
                        return False

        except Exception as exc:
            log.error(f"ADD_REMOTE__RAID: Error on Sending data to {config.EQDKP_API_URL}: {exc}")
            self.last_rest_error = f"ADD_REMOTE__RAID: Error on Sending data to {config.EQDKP_API_URL}: {exc}"
            return False

