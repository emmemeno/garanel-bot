from raid import Raid

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
    for char in raid.get_players(filter=filter):
        output += f"+ {char.name}\n"
    return output


def print_raid_items(raid: Raid):
    output = ""
    for item in raid.items:

        output += f"+ {item['name']}: {item['points']} DKP to {item['winner']}\n"
    return output

