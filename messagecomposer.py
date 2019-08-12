from raid import Raid
import config
import timehandler as timeh
import re

def message_cut(input_text: str, limit: int):
    """
    Function that take a string as argument and breaks it in smaller chunks
    :param input_text: str
    :param limit: int
    :return: output: list()
    """

    output = list()

    while len(input_text) > limit:

        # find a smart new limit based on newline...
        smart_limit = input_text[0:limit].rfind('\n') + 1
        if smart_limit == -1:
            # ...or find a smart new limit based on blank space
            smart_limit = input_text[0:limit].rfind(' ') + 1
        output.append(input_text[0:smart_limit])
        input_text = input_text[smart_limit:]

    output.append(input_text)
    return output


def prettify(text: str, my_type="BLOCK"):

    if my_type == "BLOCK":
        prefix = postfix = "```\n"
    elif my_type == "CSS":
        prefix = "```css\n"
        postfix = "```\n"
    elif my_type == "YELLOW":
        prefix = "```fix\n"
        postfix = "```\n"
    elif my_type == "RED":
        prefix = "```diff\n"
        postfix = "```\n"
    elif my_type == "MD":
        prefix = "```md\n"
        postfix = "```\n"
    elif my_type == "BLUE":
        prefix = "```asciidoc\n= "
        postfix = "```\n"
    elif my_type == "SINGLE":
        prefix = postfix = "`\n"
    else:
        prefix = postfix = ""

    return prefix + text + postfix


def header_sep(header, sep="-"):
    return (sep * len(header.strip())) + "\n"


def print_raid_attendees(raid: Raid, filter="ALL"):
    output = ""
    counter = 0
    for char in raid.get_players(filter=filter):
        counter += 1
        output += f"+ {char.name}\n"
    if counter:
        output += f"\nTotal: {counter} players"
    return output


def print_raid_items(raid: Raid):
    output = ""
    for item in raid.items:

        output += f"+ {item['name']}: {item['points']} DKP to {item['winner']}\n"
    return output


def print_raid_generals(raid: Raid):
    if raid.event_name:
        name = raid.event_name
    else:
        name = raid.name_id
    date = raid.date.strftime(config.DATE_EQDKP_FORMAT)
    time_lapsed = timeh.countdown(raid.date,timeh.now())
    total_attendees = len(raid.players)
    return f"{name} added at {date} UTC ({time_lapsed} ago)\n- Total Attendees: {total_attendees}"


def print_dkp_char_list(user_name, chars):
    header = "**CHARS**"
    recap = ""
    for char in chars:
        # skip discord chars
        if "#" not in char.name:
            recap += f"+ {char.name}\n"
    if not recap:
        recap = "Empty :("
    recap = header + prettify(recap, "MD")
    return recap


def print_dkp_char_points(points):
    header = "**DKP POINTS**"
    recap = f"+ Current: {points['current']}\n+ Spent: {points['spent']}"
    recap = header + prettify(recap, "MD")
    return recap


def print_dkp_user_items(items):
    if not items:
        return ""
    header = "**ITEMS**"
    recap = ""
    for item in items:
        recap += f"+ {item['name']}: {item['value']}\n"
    recap = header + prettify(recap, "MD")
    return recap


def print_dkp_user_raids(raids_by_char, chars, dkp):
    counter = 0
    if not raids_by_char:
        return ""
    header = "**LATEST RAIDS**"
    recap = ""
    for char in chars:
        if str(char.id) in raids_by_char:
            for raid in raids_by_char[str(char.id)]:
                counter += 1
                recap += f"+ {raid.event_name} - {raid.date.strftime('%b %d')}\n"
                if counter == 5:
                    break
        if counter == 5:
            break
    recap = header + prettify(recap, "MD")
    return recap


def print_user_pending_raids(user):
    header = "**PENDING RAIDS**"
    recap = ""
    for raid in user['pending_raids']:
        recap += f"+ {raid} - {raid.date.strftime('%b %d %H:%M')}\n"
    if not recap:
        return ""
    recap = header + prettify(recap, "MD")
    return recap

def print_roles_list(bot_roles, discord_guild_roles):
    bot_roles_list = ""
    for bot_role in bot_roles:
        bot_roles_list += f"+ {bot_role} = {bot_roles[bot_role]}\n"
    bot_roles_list = "**Bot Roles**\n" + prettify(bot_roles_list, "MD")

    discord_roles_list = ""
    for discord_role in discord_guild_roles:
        discord_roles_list += f"+ {discord_role.name} = {discord_role.id}\n"
    discord_roles_list = "**Discord Roles**\n" + prettify(discord_roles_list, "MD")
    return bot_roles_list + discord_roles_list


def username_prettify(name):
    reg = re.search(r"(#\d{4})\b", name)
    if reg:
        return name[0:reg.start()]
    return name



