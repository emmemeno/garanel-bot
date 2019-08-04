from html import unescape

class Item:

    def __init__(self, name, eqdkp_id):
        self.name = name
        self.eqdkp_id = eqdkp_id


class Items:

    def __init__(self):
        self.items_dict = {}
        self.items_by_points = {}
        self.items_by_user = {}

    def add(self, eqdkp_dict, winner):

        if len(eqdkp_dict):
            for entry in eqdkp_dict:
                item_name = unescape(eqdkp_dict[entry]['name'])
                item_value = eqdkp_dict[entry]['value']

                item = {'winner': winner, "value": item_value}
                # Add to main Dict
                if item_name not in self.items_dict:
                    self.items_dict[item_name] = []
                self.items_dict[item_name].append(item)

                # Add to dict by points
                if eqdkp_dict[entry]['value'] not in self.items_by_points:
                    self.items_by_points[eqdkp_dict[entry]['value']] = []
                self.items_by_points[item_value].append({"name": item_name, "winner": winner})

                # Add to dict by users
                if winner not in self.items_by_user:
                    self.items_by_user[winner] = []
                self.items_by_user[winner].append({"name": item_name, "value": item_value})

    def get_items_by_user(self, user_name):
        return self.items_by_user[user_name]


