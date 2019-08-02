import datetime
import pytz


def now():
    return datetime.datetime.utcnow().replace(second=0, microsecond=0)


def next_future(hours=1):
    return now() + datetime.timedelta(hours=hours)


def now_local(timezone):
    tz = pytz.timezone(timezone)
    return datetime.datetime.now(tz)


def from_mins_ago(mins):
    date_new = datetime.datetime.utcnow().replace(second=0, microsecond=0)
    return date_new - datetime.timedelta(minutes=int(mins))


def convert24(time, meridian):
    if time["hour"] > 12:
        return False

    if meridian == "am":
        if time["hour"] == 12:
            time["hour"] = 00
    elif meridian == "pm":
        if not time["hour"] == 12:
            time["hour"] = time["hour"] + 12

    return time

def naive_to_tz(naive_date, tz_to="UTC"):
    local = pytz.timezone(tz_to)
    return local.localize(naive_date)


def tz_to_naive(tz_date):
    return tz_date.replace(tzinfo=None)


def change_tz(mydate, target_timezone="CET"):
    tz_convert_to = pytz.timezone(target_timezone)
    return mydate.astimezone(tz_convert_to)


def change_naive_to_tz(mydate, ttz):
    mydate = naive_to_tz(mydate, "UTC")
    return change_tz(mydate, ttz)


def countdown(past, future):
    output = ""
    date_diff = future - past
    seconds_diff = date_diff.total_seconds()
    days = int(seconds_diff // (60 * 60 * 24))
    hours = int((seconds_diff - days*86400) // (60 * 60))
    minutes = int((seconds_diff // 60) % 60)
    if days == 1:
        output += "1 day "
    if days > 1:
        output += str(days) + " days "
    if hours == 1:
        output += "1 hour "
    if hours > 1:
        output += str(hours) + " hours "
    if hours and minutes:
        output += "and "
    if minutes == 1:
        output += "1 minute"
    if minutes > 1 or minutes == 0:
        output += str(minutes) + " minutes"

    return output