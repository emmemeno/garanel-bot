import config
from auth import Auth
import asyncio
import logging
import logging.config
import discord
from discord import File
import lineparser
from raid import Raid
from raid import Player
import utils
import messagecomposer as mc
import dkp
import timehandler as timeh
import helper
from datetime import datetime
from pprint import pprint


##############
# LOGGER SETUP
##############
def setup_logger(name, log_file, level):

    formatter = logging.Formatter('[%(asctime)s] - %(message)s')

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger

class Garanel:

    def __init__(self):
        log.info("####################")
        log.info("Initializing Garanel")
        log.info("####################")
        self.client = discord.Client(loop=asyncio.get_event_loop())
        self.raid_list = utils.load_raids(config.PATH_RAIDS)
        self.guild = None
        self.dkp = dkp.Dkp()
        self.help = helper.Helper(config.PATH_HELP)
        # Temporary variables
        self.my_auth = Auth()
        self.input_author = None
        self.input_channel = None
        self.input_params = None
        self.connected = False

    async def call_function(self, name):
        fn = getattr(self, 'cmd_' + name, None)
        if fn is not None:
            await fn()

    def run(self):
        self.client.loop.create_task(self.minute_digest())
        self.client.loop.create_task(self.eqdkp_sync())
        self.client.event(self.on_ready)
        self.client.event(self.on_message)
        self.client.run(config.DISCORD_TOKEN)

    async def on_ready(self):
        log.info(f"Garanel connected to Discord ({config.DISCORD_TOKEN})")
        self.connected = True
        self.guild = self.client.get_guild(config.GUILD_ID)
        self.my_auth.load_roles(config.ROLES_FILE)
        await self.reorder_raid_channels()

    async def on_message(self, msg):
        # Assign temporary variables
        self.input_author = msg.author
        self.input_channel = msg.channel

        # Skip self messages
        if self.input_author == self.client.user:
            return False

        lp = lineparser.LineParser(msg.content)
        lp.process()
        if lp.get_action():
            log.debug(f"INPUT: {str(self.input_author)} - {msg.content}")

        action = lp.get_action()
        if action:
            self.input_params = lp.get_params()
            await self.call_function(action)

        # Clear temporary variables
        self.auth = False
        self.input_author = None
        self.input_channel = None
        self.input_params = None

    ####
    # ABOUT
    ####
    async def cmd_about(self):
        await self.input_author.send(self.help.get_about())

    ####
    # GET HELP
    ####
    async def cmd_help(self):
        cmd = ""
        if "help_command" in self.input_params:
            cmd = self.input_params["help_command"]
        await self.input_author.send(self.help.get_help(cmd))

    ####
    # GET DKP
    ####
    async def cmd_dkp(self):
        # if not self.my_auth.check("member:applicant", self.input_author):
        #     return False
        # Can't use this command on raid channels

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        if utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id):
            return False

        if not self.dkp.points_last_read:
            await input_channel.send(mc.prettify("DKP website was unreachable, no data available", "MD"))
            return False

        try:
            dkp_target = input_params['dkp_target']
        except KeyError:
            dkp_target = None
            pass

        if dkp_target:
            user_name = self.dkp.get_user_by_char_name(dkp_target)
            find_name = dkp_target
        else:
            user_name = str(input_author).capitalize()
            find_name = user_name

        user = self.dkp.get_user_by_name(user_name)

        if not user:
            await input_channel.send(mc.prettify(f"+ {find_name} not found", "MD"))
            return False

        points = self.dkp.get_points_by_user_name(user_name)
        chars = self.dkp.get_chars_by_user_name(user_name)

        if not chars:
            await input_channel.send(mc.prettify(f"+ {find_name} has no characters", "MD"))

        chars_recap = mc.print_dkp_char_list(user_name, chars)
        dkp_recap = mc.print_dkp_char_points(points)
        items_recap = mc.print_dkp_user_items(self.dkp.dkp_items.get_items_by_user(user_name))

        raids_recap = mc.print_dkp_user_raids(self.dkp.dkp_raids.raids_by_user_id, chars, self.dkp)
        pending_raids_recap = mc.print_user_pending_raids(user)
        recap = chars_recap + dkp_recap + items_recap + raids_recap + pending_raids_recap + \
                f"_Last Read: {timeh.countdown(self.dkp.points_last_read, timeh.now())} ago_"
        await input_author.send(recap)

    ####
    # WHO
    ####
    async def cmd_who(self):
        # if not self.my_auth.check("member:applicant", self.input_author):
        #     return False
        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        if not self.dkp.points_last_read:
            await input_channel.send(mc.prettify("DKP website was unreachable, no data available", "MD"))
            return False

        try:
            who = input_params['who']
        except KeyError:
            await input_channel.send(mc.prettify("Missing char name", "YELLOW"))
            return False

        user = self.dkp.get_user_by_char_name(who)

        if not user:
            await input_channel.send(mc.prettify(f"+ {who} not found", "MD"))
            return False

        chars = self.dkp.get_chars_by_user_name(user)
        points = self.dkp.get_points_by_user_name(user)

        if not chars:
            await input_channel.send(mc.prettify(f"+ {who} has no characters", "MD"))
        dkp_recap = mc.print_dkp_char_points(points)

        chars_recap = mc.print_dkp_char_list(user, chars)

        recap = chars_recap + dkp_recap + f"_Last Read: {timeh.countdown(self.dkp.points_last_read, timeh.now())} ago_"
        await input_channel.send(recap)

    ####
    # DKP RELOAD
    ####
    async def cmd_sync(self):
        if not self.my_auth.check("officer", self.input_author):
            return False
        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        await self.dkp.load_dkp_chars()
        await self.dkp.load_dkp_raids()
        utils.raid_autosave(self.raid_list)
        await input_channel.send(mc.prettify(f"DKP Chars and Raids Reloaded!\n"
                                             f"Pending Raids saved!", "YELLOW"))

        # Refresh the DKP status of players
        utils.refresh_dkp_status(self.raid_list, self.dkp.users)

    ####
    # DKP ADJUST
    ####
    async def cmd_dkp_adjust(self):
        if not self.my_auth.check("officer", self.input_author):
            return False
        # if not user_name:
        #     await self.input_channel.send(mc.prettify(f"Syntax error. Please Type $help $dkp-adj", "YELLOW"))
        #     return False
        #
        # user = self.dkp.get_user_by_name(user_name)
        # if not user:
        #     await self.input_channel.send(mc.prettify(f"Error: Char not found", "YELLOW"))
        #     return False
        # await self.dkp.add_adjustment(user['user_id'], points, reason)
        # user['user_id'] += points
        # await self.input_channel.send(mc.prettify(f"{user_name} earned {points} DKP = {reason}", "YELLOW"))

    ####
    # ADD MAIN CHAR
    ####
    async def cmd_dkp_mainchar_add(self):
        if not self.my_auth.check("officer", self.input_author):
            return False
        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        try:
            mainchar = input_params['main_char']
        except KeyError:
            await input_channel.send(mc.prettify("Missing char name", "YELLOW"))
            return False

        if self.dkp.get_chars_by_user_name(mainchar):
            await input_channel.send(mc.prettify(f"Char {mainchar} is already present. To add a char ", "YELLOW"))
            return False

        char_id = await self.dkp.add_remote_char(mainchar, 0)
        if not char_id:
            await input_channel.send(mc.prettify(f"Failed to add {mainchar}: {self.dkp.last_rest_error}", "YELLOW"))
            return False

        self.dkp.add_new_user(char_id, mainchar, dkp_current=0)
        await input_channel.send(mc.prettify(f"Main {mainchar} added!", "YELLOW"))

    ####
    # ADD CHAR
    ####
    async def cmd_dkp_char_add(self):
        if not self.my_auth.check("officer", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        discord_user_name = str(self.input_author)
        try:
            char = input_params['char']
        except KeyError:
            await input_channel.send(mc.prettify("Missing char name", "YELLOW"))
            return False

        user = self.dkp.get_user_by_char_name(discord_user_name)


        if not user:
            await input_channel.send(mc.prettify(f"Char {discord_user_name} not found", "YELLOW"))
            return False

        user_id = await self.dkp.add_remote_char(char, self.dkp.users[user]['user_id'])
        if not user_id:
            await input_channel.send( mc.prettify(f"Failed to add {char}: {self.dkp.last_rest_error}", "YELLOW"))

        self.dkp.add_new_char(user_id, char, discord_user_name)
        await input_channel.send(mc.prettify(f"{char} added to {discord_user_name}", "YELLOW"))

        # Refresh Chars in raids
        utils.refresh_dkp_status(self.raid_list, self.dkp.users)

    ####
    # RAID STATUS
    ####
    async def cmd_raid_status(self):
        if not self.my_auth.check("member:applicant", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if not raid:

            return False
        if raid.close:
            await input_channel.send(mc.prettify("Raid is closed!", "YELLOW"))
            return False

        current_attendees = mc.print_raid_attendees(raid, filter="ALL")
        current_attendees_not_in_dkp = mc.print_raid_attendees(raid, filter="NO_DKP")
        current_items = mc.print_raid_items(raid)

        if not current_attendees:
            await input_channel.send(mc.prettify("Empty!", "YELLOW"))
            return False
        if current_attendees:
            await input_channel.send("**Current Attendees**\n" + mc.prettify(current_attendees, "MD"))
        if current_attendees_not_in_dkp:
            await input_channel.send("**Players not in DKP**\n" + mc.prettify(current_attendees_not_in_dkp, "YELLOW"))
        if current_items:
            await input_channel.send("**Items**\n" + mc.prettify(current_items, "MD"))

        await input_channel.send(mc.prettify(mc.print_raid_generals(raid), "BLUE"))

    ####
    # ADD A RAID
    ####
    async def cmd_raid_add(self):
        if not self.my_auth.check("member:applicant", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        in_raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if in_raid:
            return False

        # Raid Name is mandatory
        try:
            raid_name = input_params['raid_name']
        except KeyError:
            return False

        try:
            event_name = input_params['event_name']

        except KeyError:
            event_name = raid_name
            pass
        event_id = 1
        check_raid = utils.get_raid_by_name_id(self.raid_list, raid_name)

        if check_raid:
            await input_channel.send(mc.prettify(f"Raid already present!", "YELLOW") + f"<#{check_raid.discord_channel_id}>")
            return False

        name_id = raid_name + '-' + timeh.now().strftime("%b_%d")
        # Create a Discord Channel First
        category = self.guild.get_channel(config.RAID_CATEGORY_ID)
        raid_channel = await self.guild.create_text_channel(f"{name_id}-new", category=category)
        # Create the Raid
        raid = Raid(name_id,
                    datetime.utcnow().strftime(config.DATE_EQDKP_FORMAT),
                    event_name,
                    event_id,
                    raid_channel.id,
                    close=False,
                    kill=None,
                    points=0,
                    log_loaded=False,
                    log_final="",
                    players=[],
                    items=[])
        # Add it to the list
        self.raid_list.append(raid)
        # And save it on file
        raid.save()
        # Reorder the save channel list
        self.raid_list.sort(key=lambda x: x.date, reverse=True)
        await self.reorder_raid_channels()
        msg_creation = f"+ Raid {event_name} created by {input_author}" \
                       f" at {timeh.now().strftime(config.DATE_EQ_LOG_FORMAT)} UTC"

        # Send output messages
        await input_channel.send(mc.prettify(f"Raid created", "YELLOW") + f"<#{raid_channel.id}>")
        await raid_channel.send(mc.prettify(msg_creation, "MD"))
        await raid_channel.send(mc.prettify(config.TEXT_WELCOME_TO_RAID, "YELLOW"))

    ####
    # CLOSE A RAID
    ####
    async def cmd_raid_close(self):
        if not self.my_auth.check("officer", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if not raid:
            return False
        if raid.close:
            await input_channel.send(mc.prettify("Raid is already close. Please type $raid-archive when done", "YELLOW"))
            return False


        # Refresh the DKP status of players
        raid.refresh_dkp_status(self.dkp.users)

        final_attendees = mc.print_raid_attendees(raid, filter="ALL")
        final_attendees_not_in_dkp = mc.print_raid_attendees(raid, filter="NO_DKP")
        final_items = mc.print_raid_items(raid)

        # If the raid is empty, closing will delete the channel too
        if not final_attendees:
            await input_channel.delete(reason="Done!")
            utils.remove_json_raid(raid)
            self.raid_list.remove(raid)
            return False
        if not raid.log_final:
            log_file = raid.create_log_file()
        else:
            log_file = raid.log_final
        raid.close = True

        if final_attendees:
            await input_channel.send(mc.prettify(mc.print_raid_generals(raid), "BLUE"))

        await input_channel.send(file=File(config.PATH_HISTORY + log_file))

        if final_items:
            await input_channel.send("**Items**\n" + mc.prettify(final_items, "MD"))
        await input_channel.send(mc.prettify("Please type $raid-archive when done", "YELLOW"))
        return True

    ####
    # CLOSE A RAID
    ####
    async def cmd_raid_open(self):
        if not self.my_auth.check("officer", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if not raid:
            return False

        if not raid.close:
            await input_channel.send(mc.prettify("Raid is still open", "MD"))
        else:
            raid.log_final = None
            raid.close = False
            await input_channel.send(mc.prettify("Raid is now open", "MD"))
        return True

    ####
    # ARCHIVE A RAID
    ####
    async def cmd_raid_archive(self):
        if not self.my_auth.check("officer", self.input_author):
            return False
        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, self.input_channel.id)
        if not raid:
            return False

        if not raid.close:
            await input_channel.send(mc.prettify("Close the raid with $raid-close before archiving it", "MD"))
            return False

        await input_channel.delete(reason="Done!")
        history_channel = self.client.get_channel(config.HISTORY_CHANNEL_ID)

        if not raid.log_final:
            raid.create_log_file()
        # Send the Log File
        await history_channel.send(file=File(config.PATH_HISTORY + raid.log_final))
        # Send the Item list
        items = mc.print_raid_items(raid)
        if items:
            await history_channel.send(mc.prettify(items, "MD"))
        await history_channel.send(mc.prettify(f"Total Attendees: {len(raid.players)}", "BLUE"))

        # Delete the Channel

        # Remove the raid
        utils.remove_json_raid(raid)
        utils.remove_log_raid(raid)
        log.info(f"Raid {raid.name_id} was archived. Log file: {raid.log_final}")
        # Remove pending players from raid
        raid.delete_pending_raids_from_user(self.dkp.users)
        self.raid_list.remove(raid)

    ####
    # SEND A RAID TO EQDKP
    ####
    async def cmd_raid_send(self):
        if not self.my_auth.check("officer", self.input_author):
            return False
        await self.input_channel.send(mc.prettify("Command not ready yet", "YELLOW"))
        return False

        # raid = utils.get_raid_by_channel_input_id(self.raid_list, self.input_channel.id)
        # if not raid or raid.close:
        #     await self.input_channel.send(mc.prettify("Close the raid before sending it", "YELLOW"))
        #     return False
        #
        # raid_id = await self.dkp.add_raid(raid)
        # if raid_id:
        #     await self.input_channel.send(mc.prettify(f"Raid ID {raid_id} added to EQDKP. Yeee!", "YELLOW"))
        # else:
        #     await self.input_channel.send(mc.prettify(f"Failed to send this raid: {self.dkp.last_rest_error}", "YELLOW"))

    ####
    # ADD A LOG
    ####
    async def cmd_raid_add_log(self):
        print(self.input_params)
        if not self.my_auth.check("member:applicant", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        counter = 0
        if not raid or raid.close:
            return False
        # If it is first log, toggle off the asterisk from channel name
        if not raid.log_loaded:
            await input_channel.edit(name=raid.name_id)
        raid.log_loaded = True
        for player in input_params['players_to_add']:
            dkp_char = self.dkp.get_char_by_name(player.name)
            if dkp_char:
                player.eqdkp_id = dkp_char.id
            if raid.add_raid_player(player, self.dkp):
                counter = counter + 1

        await input_channel.send(mc.prettify(f"+ Log Parsed. {counter} players added", "MD"))

        missing_msg = ""
        for player in raid.players:
            if not player.eqdkp_id:
                missing_msg += f"{player.name} "
        if missing_msg:
            missing_msg = f"Chars missing in eqdkp database: " + missing_msg
            await input_channel.send(mc.prettify(missing_msg, "MD"))

    ####
    # ADD RAID PLAYER
    ####
    async def cmd_raid_add_player(self):
        if not self.my_auth.check("member:applicant", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        try:
            player_to_add = Player(input_params['player_to_add'], anon=True)
        except KeyError:
            player_to_add = None
        try:
            player_to_remove = Player(input_params['player_to_remove'], anon=True)
        except KeyError:
            player_to_remove = None

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if not raid or raid.close:
            return False
        if not player_to_add:
            await input_channel.send(mc.prettify("No player inserted", "YELLOW"))
            return False

        if raid.has_player_by_name(player_to_add.name):
            await input_channel.send(mc.prettify(f"{player_to_add.name} is already present", "YELLOW"))
            return False

        dkp_id = self.dkp.get_char_id_by_name(player_to_add.name)
        if dkp_id:
            player_to_add.eqdkp_id = dkp_id

        raid.add_raid_player(player_to_add, self.dkp)
        if player_to_add.eqdkp_id:
            await input_channel.send(mc.prettify(f"+ {player_to_add.name} was added to this raid", "MD"))
        else:
            await input_channel.send(mc.prettify(f"+ {player_to_add.name} was added to this raid but missing from EQDKP", "MD"))

        if player_to_remove:
            if not raid.has_player_by_name(player_to_remove.name):
                await input_channel.send(mc.prettify(f"{player_to_remove.name} is not present", "YELLOW"))
                return False
            raid.del_raid_player(player_to_remove, self.dkp)
            await input_channel.send(mc.prettify(f"- {player_to_remove.name} was removed from this raid", "MD"))

    ####
    # DEL RAID PLAYER
    ####
    async def cmd_raid_del_player(self):
        if not self.my_auth.check("member:applicant", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if not raid or raid.close:
            return False

        try:
            player_to_remove = Player(input_params['player_to_remove'], anon=True)
        except KeyError:
            player_to_remove = None

        if not player_to_remove:
            await input_channel.send(mc.prettify("Missing player name", "YELLOW"))
            return False

        if not raid.has_player_by_name(player_to_remove.name):
            await input_channel.send(mc.prettify(f"{player_to_remove.name} is not present", "YELLOW"))
            return False

        raid.del_raid_player(player_to_remove, self.dkp)

        await input_channel.send(mc.prettify(f"- {player_to_remove.name} was removed from this raid", "MD"))

    ####
    # DEL RAID PLAYER
    ####
    async def cmd_raid_search_player(self):
        if not self.my_auth.check("member:applicant", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if not raid or raid.close:
            return False

        try:
            player_to_search = Player(input_params['player_to_search'], anon=True)
        except KeyError:
            player_to_search = None

        if not player_to_search:
            await input_channel.send(mc.prettify("Missing player name", "YELLOW"))
            return False

        if not raid.has_player_by_name(player_to_search.name):
            await input_channel.send(mc.prettify(f"{player_to_search.name} is not present", "YELLOW"))
            return False

        await input_channel.send(mc.prettify(f"{player_to_search.name} found!", "YELLOW"))

    ####
    # SET A KILL
    ####
    async def cmd_raid_kill(self):
        if not self.my_auth.check("member:applicant", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if not raid or raid.close:
            return False

        new_channel_name = f"{raid.name_id}-kill"
        await input_channel.edit(name=new_channel_name)
        raid.set_kill(True)
        await input_channel.send(mc.prettify(":)!", "YELLOW"))

    ####
    # SET A NO KILL
    ####
    async def cmd_raid_nokill(self):
        if not self.my_auth.check("member:applicant", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if not raid or raid.close:
            return False

        new_channel_name = f"{raid.name_id}-nokill"
        await input_channel.edit(name=new_channel_name)
        raid.set_kill(False)
        await input_channel.send(mc.prettify(":(!", "YELLOW"))

    ####
    # SET POINTS
    ####
    async def cmd_raid_set_points(self):
        if not self.my_auth.check("member:applicant", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if not raid or raid.close:
            return False

        try:
            points = input_params['raid_points']
            raid.set_points(points)
            await input_channel.send(mc.prettify(f"DKP Points: {points}", "YELLOW"))
        except KeyError:
            await input_channel.send(mc.prettify(f"Error setting points", "YELLOW"))

    ####
    # ADD AN ITEM
    ####
    async def cmd_raid_item_add(self):

        if not self.my_auth.check("member:applicant", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if not raid or raid.close:
            return False
        help_text = "Please type $help item-add"
        try:
            name = input_params['item_name']
        except KeyError:
            await input_channel.send(mc.prettify(f"Wiki url missing or not recognized. {help_text}", "YELLOW"))
            return False

        try:
            points = input_params['item_dkp']
        except KeyError:
            await input_channel.send(mc.prettify(f"Missing dkp value. {help_text}", "YELLOW"))
            return False

        try:
            winner = input_params['item_winner']
        except KeyError:
            await input_channel.send(mc.prettify(f"Missing winner name. {help_text}", "YELLOW"))
            return False

        winner_player = self.dkp.get_user_by_char_name(winner)
        if not winner_player:
            await input_channel.send(mc.prettify(f"Char {winner} is missing from EQDKP website\n", "YELLOW"))
            return False

        raid.add_item(name, points, winner)
        await input_channel.send(mc.prettify(f"+ {name} won by {winner} for {points} DKP. Grats!", "MD"))

    ####
    # WIPE ALL ITEMS
    ####
    async def cmd_raid_item_wipe(self):
        if not self.my_auth.check("member", self.input_author):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        raid = utils.get_raid_by_channel_input_id(self.raid_list, input_channel.id)
        if not raid or raid.close:
            return False

        raid.wipe_items()

        await input_channel.send(mc.prettify("Cleared all items", "MD"))

    async def cmd_roles(self):
        if not self.my_auth.check_owner(self.input_author.id):
            return False

        input_author = self.input_author
        input_channel = self.input_channel
        input_params = self.input_params

        try:
            bot_role = input_params['bot_role']
        except KeyError:
            bot_role = None

        try:
            discord_role_id = input_params['discord_role_id']
        except KeyError:
            discord_role_id = None

        # Send a recap
        if not bot_role:
            # print Bot roles
            await input_author.send(mc.print_roles_list(self.my_auth.roles, self.guild.roles))
            return True

        if not discord_role_id.isdigit():
            await input_author.send(mc.prettify("Error interpreting the line. "
                                                     "Use '$role bot_role discord_id'", "YELLOW"))
            return False

        if self.my_auth.set_role(bot_role, discord_role_id):
            await input_author.send(mc.prettify("Bot Role updated", "YELLOW"))
        else:
            await input_author.send(mc.prettify("Bot Role not found", "YELLOW"))

    async def clean_if_deleted_channel(self):
        history_channel = self.client.get_channel(config.HISTORY_CHANNEL_ID)

        for raid in self.raid_list:
            # Works only on raid without channels
            if not utils.check_if_channel(raid, self.client):
                # If raid was empty, just delete it
                if len(raid.players) == 0:
                    utils.remove_json_raid(raid)
                    self.raid_list.remove(raid)
                    log.info(f"CLEAN: Empty {raid.name_id} was deleted")
                # else create the log file, send stats to history channel and clean
                else:
                    log.info(f"CLEAN: Creating Log file for {raid.name_id}...")
                    raid.create_log_file()
                    final_items = mc.print_raid_items(raid)
                    await history_channel.send(file=File(config.PATH_HISTORY + raid.log_final))
                    if final_items:
                        await history_channel.send(mc.prettify(final_items, "MD"))
                    utils.remove_json_raid(raid)
                    utils.remove_log_raid(raid)
                    self.raid_list.remove(raid)

                    log.info(f"CLEAN: Raid {raid.name_id} was archived. Log file: {raid.log_final}")

    async def reorder_raid_channels(self):
        for i, raid in enumerate(self.raid_list):
            channel = self.client.get_channel(raid.discord_channel_id)
            await channel.edit(position=i)

    async def minute_digest(self):
        tic = 60
        while True:
            await asyncio.sleep(tic)
            utils.raid_autosave(self.raid_list)
            await self.clean_if_deleted_channel()

    # Coroutine to sync with eqdkp website
    async def eqdkp_sync(self):
        tic = 60*60
        while True:
            if self.connected:
                await self.reorder_raid_channels()
            await self.dkp.load_dkp_chars()
            await asyncio.sleep(10)
            await self.dkp.load_dkp_raids()
            # Refresh the DKP status of players
            utils.refresh_dkp_status(self.raid_list, self.dkp.users)

            await asyncio.sleep(tic)


def main():

    garanel = Garanel()
    garanel.run()


if __name__ == "__main__":
    # Generic logger
    if config.DEBUG:
        log = setup_logger('Garanel', config.LOG_FILE, logging.DEBUG)
    else:
        log = setup_logger('Garanel', config.LOG_FILE, logging.INFO)

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
    })
    main()

