import config


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
            output += "  AFK "
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
