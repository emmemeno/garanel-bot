from datetime import datetime
import logging


log = logging.getLogger("Garanel")

class Raid:

    def __init__(self, raid_id, event_id, event_name, note, date, attendees):
        self.raid_id = raid_id
        self.event_id = event_id
        self.event_name = event_name
        self.note = note
        self.date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        self.attendees = attendees

    def __repr__(self):
        return self.raid_id


class Raids:

    def __init__(self):
        self.raids_list = list()
        self.raid_dict = {}
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
                raid_attendees = eqdkp_dict[entry]['raid_attendees']

                raid = Raid(raid_id, raid_event_id, raid_event_name, raid_note, raid_date_str, raid_attendees)
                self.raid_dict.update({int(raid_id): raid})
                self.raids_list.append(raid)
                # Add to dict by users
                for attendee_id in raid_attendees:
                    if attendee_id not in self.raids_by_user_id:
                        self.raids_by_user_id[attendee_id] = []
                    self.raids_by_user_id[attendee_id].append(raid)

            except Exception as e:
                log.debug(f"LOAD RAID: Error {e}")
