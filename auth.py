import json
import discord
import config
import logging

log = logging.getLogger("Garanel")

class Auth:
    def __init__(self):
        self.roles = []
        self.file_url = ""

    def load_roles(self, file_url):
        with open(file_url) as f:
            self.roles = json.load(f)
            self.file_url = file_url
            return True

    def save_roles(self):
        with open(self.file_url, "w") as f:
            json.dump(self.roles, f, indent=4)
            return True

    def check(self, bot_role, member: discord.Member):
        roles_to_check = bot_role.split(":")
        # If input is done privately dont do anything
        if type(member).__name__ == "Member":
            for m_role in member.roles:
                for b_role in roles_to_check:
                    try:
                        if self.roles[b_role] == m_role.id:
                            return True
                    except KeyError:
                        log.info(f"MYAUTH: Bot Role {b_role} not found")
        log.info(f"MYAUTH: {bot_role} not found in {member}")
        return False

    def check_owner(self, discord_id):
        if discord_id == config.OWNER_ID:
            return True
        else:
            return False

    def set_role(self, bot_role, discord_id):
        if bot_role not in self.roles:
            return False
        self.roles[bot_role] = int(discord_id)
        self.save_roles()
        return True
