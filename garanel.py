import config
from auth import Auth
import asyncio
import logging
import logging.config
import discord
from discord import File
import lineparser
from raid import Raid
import utils
import messagecomposer as mc
import dkp
import timehandler as timeh
import helper


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

    def run(self):
        self.client.loop.create_task(self.minute_digest())
        self.client.loop.create_task(self.eqdkp_sync())
        self.client.event(self.on_ready)
        self.client.event(self.on_message)
        self.client.run(config.DISCORD_TOKEN)

    async def on_ready(self):
        log.info(f"Garanel connected to Discord ({config.DISCORD_TOKEN})")
        self.guild = self.client.get_guild(config.GUILD_ID)
        self.my_auth.load_roles(config.ROLES_FILE)

    async def on_message(self, msg):
        # Assign temporary variables
        self.input_author = msg.author
        self.input_channel = msg.channel

        lp = lineparser.LineParser(msg.content)
        interpreter = lp.process()

        if interpreter == 'ABOUT':
            await self.get_about(msg.author)
        if interpreter == 'HELP':
            await self.get_help(msg.author, lp.param)
        if interpreter == 'GET_DKP':
            await self.get_dkp(msg.channel, msg.author, lp.param)
        if interpreter == 'ADD_MAIN':
            await self.add_char_main(lp.param)
            self.dkp.last_rest_error = ""
        if interpreter == 'ADD_CHAR':
            await self.add_char(lp.split_words)
            self.dkp.last_rest_error = ""
        if interpreter == 'RAID_STATUS':
            await self.raid_status(msg.channel)
        if interpreter == 'RAID_ADD':
            await self.raid_add(msg.channel, lp.raid_name_id, timeh.now().strftime("%b-%d"), msg.author.name)
        if interpreter == 'RAID_CLOSE':
            await self.raid_close(msg.channel.id)
        if interpreter == 'RAID_SEND':
            await self.raid_send()
        if interpreter == 'RAID_ARCHIVE':
            await self.raid_archive(msg.channel.id)
        if interpreter == 'ADD_LOG':
            await self.add_log(lp.players_to_add, msg.channel.id, lp.log_date)
        if interpreter == 'ADD_PLAYER':
            await self.add_raid_player(lp.players_to_add, lp.players_to_remove, msg.channel)
        if interpreter == 'DEL_PLAYER':
            await self.del_raid_player(lp.players_to_remove, msg.channel)
        if interpreter == 'KILL':
            await self.set_kill(True, msg.channel.id)
        if interpreter == 'NOKILL':
            await self.set_kill(False, msg.channel.id)
        if interpreter == 'SET_RAID_POINTS':
            await self.set_raid_points(lp.param)
        if interpreter == 'ITEM_ADD':
            await self.item_add(msg.channel, lp.item_name, lp.item_dkp, lp.item_winner)
        if interpreter == 'ITEM_WIPE':
            await self.item_wipe(msg.channel)
        if interpreter == 'ROLES':
            await self.roles(lp.split_words)

        # Clear temporary variables
        self.auth = False
        self.input_author = msg.author
        self.input_channel = msg.channel

    ####
    # ABOUT
    ####
    async def get_about(self, author):
        await author.send(self.help.get_about())

    ####
    # GET HELP
    ####
    async def get_help(self, author, param):
        await author.send(self.help.get_help(param))

    ####
    # GET DKP
    ####
    async def get_dkp(self, channel, author, param):
        # if not self.my_auth.check("member", self.input_author):
        #     return False
        # Can't use this command on raid channels
        if utils.get_raid_by_channel_input_id(self.raid_list, channel.id):
            return False

        if not self.dkp.points_last_read:
            await channel.send(mc.prettify("DKP website was unreachable, no data available", "MD"))
            return False

        if param:
            if "#" in param:
                main_name = param
                find_name = main_name
            else:
                main_name = self.dkp.get_user_by_char_name(param)
                find_name = param
        else:
            main_name = str(author)
            find_name = main_name

        points = self.dkp.get_points_by_user_name(main_name)
        chars = self.dkp.get_chars_by_user_name(main_name)

        if not chars:
            if self.dkp.get_user_by_name(main_name):
                await channel.send(mc.prettify(f"+ {find_name} has no characters", "MD"))
            else:
                await channel.send(mc.prettify(f"+ {find_name} not found", "MD"))
            return False

        recap = f"[{main_name}]\n"
        recap += mc.header_sep(recap) + "\n"
        for char in chars:
            recap += f"+ {char.name}\n"
        recap += f"\nTotal DKP: {points}"
        recap = mc.prettify(recap, "CSS")
        recap += f"_Last Read: {timeh.countdown(self.dkp.points_last_read, timeh.now())} ago_"

        await channel.send(recap)

    ####
    # ADD MAIN CHAR
    ####
    async def add_char_main(self, param):
        if not self.my_auth.check("officer", self.input_author):
            return False

        if not param:
            await self.input_channel.send(mc.prettify("Missing parameter. Please use $add-main name#1234", "YELLOW"))
            return False
        if self.dkp.get_chars_by_user_name(param):
            await self.input_channel.send(mc.prettify(f"Main {param} is already present. To add a char "
                                                      f"please type '$add-char {param} char_name'", "YELLOW"))
            return False
        player_id = await self.dkp.add_remote_char(param, 0)
        if player_id:
            self.dkp.add_new_user(player_id, param, dkp_points=0)
            await self.input_channel.send(mc.prettify(f"Main {param} added!", "YELLOW"))
        else:
            await self.input_channel.send(mc.prettify(f"Failed to add {param}: {self.dkp.last_rest_error}", "YELLOW"))
        return False

    ####
    # ADD CHAR
    ####
    async def add_char(self, words):
        if not self.my_auth.check("officer", self.input_author):
            return False

        try:
            user_name = words[0].capitalize()
            char_name = words[1].capitalize()
        except IndexError:
            await self.input_channel.send(mc.prettify("Wrong Syntax. Type $add-char user_name player_name", "YELLOW"))
            return False
        except TypeError:
            await self.input_channel.send(mc.prettify("Missing Parameters. Type $add-char user_name player_name", "YELLOW"))
            return False

        user = self.dkp.get_user_by_user_name(user_name)

        if not user:
            await self.input_channel.send(mc.prettify(f"Main {user_name} not found", "YELLOW"))
            return False
        player_id = await self.dkp.add_remote_char(char_name, user['user_id'])
        if player_id:
            self.dkp.add_new_char(player_id, char_name, user_name)
            await self.input_channel.send(mc.prettify(f"{char_name} added to {user_name}", "YELLOW"))
            # Refresh Chars in raids
            for raid in self.raid_list:
                raid.refresh_dkp_status(self.dkp.get_all_chars())
        else:
            await self.input_channel.send(mc.prettify(f"Failed to add {char_name}: {self.dkp.last_rest_error}", "YELLOW"))

    ####
    # RAID STATUS
    ####
    async def raid_status(self, channel):
        if not self.my_auth.check("member", self.input_author):
            return False

        raid = utils.get_raid_by_channel_input_id(self.raid_list, channel.id)
        if not raid:

            return False
        if raid.close:
            await channel.send(mc.prettify("Raid is closed!", "YELLOW"))
            return False

        # Refresh the DKP status of players
        raid.refresh_dkp_status(self.dkp.get_all_chars())

        current_attendees = mc.print_raid_attendees(raid, filter="ALL")
        current_attendees_not_in_dkp = mc.print_raid_attendees(raid, filter="NO_DKP")
        current_items = mc.print_raid_items(raid)

        if not raid.log_loaded:
            await channel.send(mc.prettify("No log inserted yet!", "YELLOW"))
            return False
        if current_attendees:
            await channel.send("**Current Attendees**\n" + mc.prettify(current_attendees, "MD"))
        if current_attendees_not_in_dkp:
            await channel.send("**Players not in DKP**\n" + mc.prettify(current_attendees_not_in_dkp, "YELLOW"))
        if current_items:
            await channel.send("**Items**\n" + mc.prettify(current_items, "MD"))

    ####
    # ADD A RAID
    ####
    async def raid_add(self, channel, name_id, date, author):
        if not self.my_auth.check("member", self.input_author):
            return False

        in_raid = utils.get_raid_by_channel_input_id(self.raid_list, channel.id)
        if in_raid:
            return False

        check_raid = utils.get_raid_by_name_id(self.raid_list, name_id)
        if check_raid:
            await channel.send(mc.prettify(f"Raid already present!", "YELLOW") + f"<#{check_raid.discord_channel_id}>")
            return False

        category = self.guild.get_channel(config.RAID_CATEGORY_ID)
        raid_channel = await self.guild.create_text_channel(name_id, category=category, position=(100-len(self.raid_list)))
        await raid_channel.send(mc.prettify(f"+ Raid created by {author}", "MD"))
        await raid_channel.send(mc.prettify(config.TEXT_WELCOME_TO_RAID, "YELLOW"))

        self.raid_list.append(Raid(name_id, date, raid_channel.id, False, None, 0, False, "", [], []))
        await channel.send(mc.prettify(f"Raid created", "YELLOW") + f"<#{raid_channel.id}>")
        self.raid_list[-1].save()

    ####
    # CLOSE A RAID
    ####
    async def raid_close(self, channel_id):
        if not self.my_auth.check("officer", self.input_author):
            return False

        raid = utils.get_raid_by_channel_input_id(self.raid_list, channel_id)
        if not raid or raid.close:
            return False

        # Refresh the DKP status of players
        raid.refresh_dkp_status(self.dkp.get_all_chars())

        channel = self.client.get_channel(raid.discord_channel_id)
        final_attendees = mc.print_raid_attendees(raid, filter="ONLY_DKP")
        final_attendees_not_in_dkp = mc.print_raid_attendees(raid, filter="NO_DKP")
        final_items = mc.print_raid_items(raid)


        # If the raid is empty, closing will delete
        if not final_attendees:
            await channel.delete(reason="Done!")
            utils.remove_json_raid(raid)
            self.raid_list.remove(raid)
            return False

        if final_attendees:
            await channel.send("**Final Attendees**\n" + mc.prettify(final_attendees, "MD"))
        if final_attendees_not_in_dkp:
            await channel.send("**Players not in DKP**\n" + mc.prettify(final_attendees_not_in_dkp, "YELLOW"))
        if final_items:
            await channel.send("**Items**\n" + mc.prettify(final_items, "MD"))

        log_file = raid.create_log_file()
        raid.close = True
        await channel.send(file=File(config.PATH_HISTORY+log_file))
        await channel.send(mc.prettify("Please type $raid-archive when done", "MD"))
        return True

    ####
    # SEND A RAID TO EQDKP
    ####
    async def raid_send(self):
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
    # ARCHIVE A RAID
    ####
    async def raid_archive(self, channel_id):
        if not self.my_auth.check("officer", self.input_author):
            return False

        raid = utils.get_raid_by_channel_input_id(self.raid_list, channel_id)
        if not raid:
            return False
        channel = self.client.get_channel(raid.discord_channel_id)

        if not raid.close:
            await channel.send(mc.prettify("Close the raid with $raid-close before archiving it", "MD"))
            return False

        history_channel = self.client.get_channel(config.HISTORY_CHANNEL_ID)

        if not raid.log_final:
            raid.create_log_file()

        await history_channel.send(file=File(config.PATH_HISTORY + raid.log_final))
        items = mc.print_raid_items(raid)
        if items:
            await history_channel.send(mc.prettify(items, "MD"))

        if channel:
            await channel.delete(reason="Done!")
        utils.remove_json_raid(raid)
        utils.remove_log_raid(raid)
        log.info(f"Raid {raid.name_id} was archived. Log file: {raid.log_final}")
        self.raid_list.remove(raid)

    ####
    # ADD A LOG
    ####
    async def add_log(self, players: list, channel_id, date):
        if not self.my_auth.check("member", self.input_author):
            return False
        raid = utils.get_raid_by_channel_input_id(self.raid_list, channel_id)
        counter = 0
        if not raid or raid.close:
            return False

        raid.log_loaded = True
        raid.date = date
        for player in players:
            dkp_char = self.dkp.get_char_by_name(player.name)
            if dkp_char:
                player.eqdkp_id = dkp_char.id
            if raid.add_raid_player(player):
                counter = counter + 1


        channel = self.guild.get_channel(raid.discord_channel_id)
        await channel.send(mc.prettify(f"+ Log Parsed. {counter} players added", "MD"))

        missing_msg = ""
        for player in raid.players:
            if not player.eqdkp_id:
                missing_msg += f"{player.name} "
        if missing_msg:
            missing_msg = f"Chars missing in eqdkp database: " + missing_msg
            await channel.send(mc.prettify(missing_msg, "MD"))

        raid.save()

    ####
    # ADD RAID PLAYER
    ####
    async def add_raid_player(self, player_to_add, player_to_remove, channel):
        if not self.my_auth.check("member", self.input_author):
            return False

        raid = utils.get_raid_by_channel_input_id(self.raid_list, channel.id)
        if not raid or raid.close:
            return False

        if not len(player_to_add):
            await channel.send(mc.prettify("No player inserted", "YELLOW"))
            return False

        player_to_add = player_to_add[0]

        if raid.has_player_by_name(player_to_add.name):
            await channel.send(mc.prettify(f"{player_to_add.name} is already present", "YELLOW"))
            return False

        dkp_id = self.dkp.get_char_id_by_name(player_to_add.name)
        if dkp_id:
            player_to_add.eqdkp_id = dkp_id

        raid.add_raid_player(player_to_add)
        if player_to_add.eqdkp_id:
            await channel.send(mc.prettify(f"+ {player_to_add.name} was added to this raid", "MD"))
        else:
            await channel.send(mc.prettify(f"+ {player_to_add.name} was added to this raid but missing from EQDKP", "MD"))

        if player_to_remove:
            if not raid.has_player_by_name(player_to_remove[0].name):
                await channel.send(mc.prettify(f"{player_to_remove[0].name} is not present", "YELLOW"))
                return False
            raid.del_raid_player(player_to_remove[0])
            await channel.send(mc.prettify(f"+ {player_to_remove[0].name} was removed from this raid", "MD"))

        raid.save()

    ####
    # DEL RAID PLAYER
    ####
    async def del_raid_player(self, player_to_remove, channel):
        if not self.my_auth.check("member", self.input_author):
            return False

        raid = utils.get_raid_by_channel_input_id(self.raid_list, channel.id)
        if not raid or raid.close:
            return False

        if not len(player_to_remove):
            await channel.send(mc.prettify("No player inserted", "YELLOW"))
            return False

        player_to_remove = player_to_remove[0]
        channel = self.guild.get_channel(raid.discord_channel_id)

        if not raid.has_player_by_name(player_to_remove.name):
            await channel.send(mc.prettify(f"{player_to_remove.name} is not present", "YELLOW"))
            return False

        raid.del_raid_player(player_to_remove)

        await channel.send(mc.prettify(f"- {player_to_remove.name} was removed from this raid", "MD"))
        raid.save()

    ####
    # SET A KILL
    ####
    async def set_kill(self, mode, channel_id):
        if not self.my_auth.check("member", self.input_author):
            return False

        raid = utils.get_raid_by_channel_input_id(self.raid_list, channel_id)
        if not raid or raid.close:
            return False

        raid.kill = mode
        raid.save()

        channel = self.guild.get_channel(raid.discord_channel_id)
        # Change name of channel
        if mode:
            new_name = f"{raid.name_id}-kill"
            await channel.send(mc.prettify("Awesome!", "YELLOW"))
        else:
            new_name = f"{raid.name_id}-nokill"
            await channel.send(mc.prettify(":(", "YELLOW"))
        await channel.edit(name=new_name)

    ####
    # SET POINTS
    ####
    async def set_raid_points(self, points):
        if not self.my_auth.check("member", self.input_author):
            return False

        raid = utils.get_raid_by_channel_input_id(self.raid_list, self.input_channel.id)
        if not raid or raid.close:
            return False

        raid.points = points
        raid.save()
        await self.input_channel.send(mc.prettify(f"DKP Points: {points}", "YELLOW"))

    ####
    # ADD AN ITEM
    ####
    async def item_add(self, channel, name, points, winner):
        if not self.my_auth.check("member", self.input_author):
            return False

        raid = utils.get_raid_by_channel_input_id(self.raid_list, channel.id)
        if not raid or raid.close:
            return False

        help_text = "Please type $help item-add"
        channel = self.guild.get_channel(raid.discord_channel_id)

        if not name:
            await channel.send(mc.prettify(f"Wiki url missing or not recognized. {help_text}", "YELLOW"))
            return False
        if not points:
            await channel.send(mc.prettify(f"Missing dkp value. {help_text}", "YELLOW"))
            return False
        if not winner:
            await channel.send(mc.prettify(f"Missing winner name. {help_text}", "YELLOW"))
            return False

        winner_player = self.dkp.get_user_by_char_name(winner.capitalize())
        if not winner_player:
            await channel.send(mc.prettify(f"Char {winner.capitalize()} is missing from EQDKP website\n", "YELLOW"))
            return False

        raid.add_item(name, points, winner.capitalize())
        await channel.send(mc.prettify(f"+ {name} won by {winner} for {points} DKP. Grats!", "MD"))
        raid.save()

    ####
    # WIPE ALL ITEMS
    ####
    async def item_wipe(self, channel):
        if not self.my_auth.check("member", self.input_author):
            return False

        raid = utils.get_raid_by_channel_input_id(self.raid_list, channel.id)
        if not raid or raid.close:
            return False

        raid.wipe_items()
        channel = self.guild.get_channel(raid.discord_channel_id)
        await channel.send(mc.prettify("Cleared all items", "MD"))

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

    async def roles(self, words):
        if not self.my_auth.check_owner(self.input_author.id):
            return False

        if not words:
            bot_roles_list = ""
            for bot_role in self.my_auth.roles:
                bot_roles_list += f"+ {bot_role} = {self.my_auth.roles[bot_role]}\n"
            bot_roles_list = "**Bot Roles**\n" + mc.prettify(bot_roles_list, "MD")

            discord_roles_list = ""
            for discord_role in self.guild.roles:
                discord_roles_list += f"+ {discord_role.name} = {discord_role.id}\n"
            discord_roles_list = "**Discord Roles**\n" + mc.prettify(discord_roles_list, "MD")

            await self.input_author.send(bot_roles_list + discord_roles_list)
        else:
            bot_role = discord_id = None
            for word in words:
                if word.isdigit():
                    discord_id = int(word)
                if word.lower() in self.my_auth.roles:
                    bot_role = word

            if bot_role and discord_id:
                self.my_auth.roles[bot_role] = discord_id
                self.my_auth.save_roles()
                await self.input_author.send(mc.prettify(f"{bot_role} assigned to {discord_id}", "YELLOW"))
            else:
                await self.input_author.send(mc.prettify("Error interpreting the line. "
                                                         "Use '$role bot_role discord_id'", "YELLOW"))


    async def minute_digest(self):
        tic = 60
        while True:
            await asyncio.sleep(tic)
            await self.clean_if_deleted_channel()

    # Coroutine to sync with eqdkp website
    async def eqdkp_sync(self):
        tic = 60*60
        while True:
            await self.dkp.load_chars()
            await self.dkp.get_raids()
            for raid in self.raid_list:
                # Refresh the DKP status of players
                raid.refresh_dkp_status(self.dkp.get_all_chars())
            await asyncio.sleep(tic)



def main():

    garanel = Garanel()
    garanel.run()


if __name__ == "__main__":
    # Generic logger
    log = setup_logger('Garanel', config.LOG_FILE, logging.INFO)

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
    })


    main()
