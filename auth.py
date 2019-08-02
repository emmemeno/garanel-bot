import json
import discord
import config


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
        # If input is done privately dont do anything
        if type(member).__name__ == "Member":
            for role in member.roles:
                if self.roles[bot_role] == role.id:
                    return True
        return False

    def check_owner(self, discord_id):
        if discord_id == config.OWNER_ID:
            return True
        else:
            return False