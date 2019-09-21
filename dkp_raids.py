from datetime import datetime
from datetime import timedelta
import timehandler as timeh
import logging



log = logging.getLogger("Garanel")

class Raid:

    def __init__(self, raid_id, event_id, event_name, note, date, attendees):
        self.raid_id = raid_id
        self.event_id = event_id
        self.event_name = event_name
        self.note = note
        self.date = date
        self.attendees = attendees

    def __repr__(self):
        return f"{self.date} - {self.event_name}"


class Raids:

    def __init__(self):
        self.raid_list = list()
        self.raid_dict = {}
        self.raid_last_seven_days = list()
        self.raid_last_thirty_days = list()
        self.raid_last_ninety_days = list()
        self.raids_by_user_id = {}

    def load(self, eqdkp_dict, dkp):
        if not eqdkp_dict:
            return False

        for entry in eqdkp_dict:
            if entry == 'status':
                continue

            try:

                raid_id = eqdkp_dict[entry]['id']
                raid_event_id = eqdkp_dict[entry]['event_id']
                raid_event_name = eqdkp_dict[entry]['event_name']
                raid_note = eqdkp_dict[entry]['note']
                raid_date_str = eqdkp_dict[entry]['date']
                raid_date = datetime.strptime(raid_date_str, "%Y-%m-%d %H:%M:%S")
                raid_attendees = eqdkp_dict[entry]['raid_attendees']

                raid = Raid(raid_id, raid_event_id, raid_event_name, raid_note, raid_date, raid_attendees)

                # print(f"{raid_event_name} - {raid_date} vs {timeh.now()}")
                if raid_date + timedelta(days=7) > timeh.now():
                    self.raid_last_seven_days.append(raid)
                if raid_date + timedelta(days=30) > timeh.now():
                    self.raid_last_thirty_days.append(raid)
                if raid_date + timedelta(days=90) > timeh.now():
                    self.raid_last_ninety_days.append(raid)

                self.raid_dict.update({int(raid_id): raid})
                self.raid_list.append(raid)
                # Add to dict by users
                for attendee_id in raid_attendees:
                    if attendee_id not in self.raids_by_user_id:
                        self.raids_by_user_id[attendee_id] = []
                    self.raids_by_user_id[attendee_id].append(raid)

            except Exception as e:
                log.debug(f"LOAD RAID: Error {e}")

    def get_raids(self, timeframe, limit=100):
        raid_list = self.raid_list
        if timeframe == 'week':
            raid_list = self.raid_last_seven_days
        if timeframe == 'month':
            raid_list = self.raid_last_thirty_days

        output = list()
        counter = 0
        for raid in raid_list:
            output.append({'name': raid.event_name,
                           'date': raid.date,
                           'attendees': len(raid.attendees),
                           'note': raid.note
                           })
            counter += 1
            if counter == limit:
                break

        return output

