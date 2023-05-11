import datetime


class TimeRange():
    class ParseError(Exception):
        pass

    def __init__(s, rangeStr):
        try:
            start, end = list(map(lambda p: p.strip(), rangeStr.split('-')))
        except ValueError as e:
            raise TimeRange.ParseError('Wrong interval format "from - to": %s' % e) from e

        try:
            startHour, startMin = list(map(lambda t: int(t.strip()), start.split(':')))
        except ValueError as e:
            raise TimeRange.ParseError('Wrong start time format "hh:mm": %s' % e) from e

        try:
            endHour, endMin = list(map(lambda t: int(t.strip()), end.split(':')))
        except ValueError as e:
            raise TimeRange.ParseError('Wrong end time format "hh:mm": %s' % e) from e

        s.start = TimeRange.Time(startHour, startMin)
        s.end = TimeRange.Time(endHour, endMin)


    def isInEntry(s, date):
        time = TimeRange.Time(date.hour, date.minute, date.second)
        if time >= s.start and time <= s.end:
            return True
        if s.start < s.end:
            return False
        if time >= s.start and time <= TimeRange.Time(24):
            return True
        if time >= TimeRange.Time(0) and time <= s.end:
            return True
        return False


    def __repr__(s):
        return "%s - %s" % (s.start, s.end)


    class Time():
        class Error(Exception):
            pass

        def __init__(s, hour, min = 0, sec = 0):
            if hour > 24 or hour < 0:
                raise TimeRange.Time.Error('incorrect hour')
            if min > 59 or hour < 0:
                raise TimeRange.Time.Error('incorrect minute')
            if sec > 59 or hour < 0:
                raise TimeRange.Time.Error('incorrect seconds')
            s.hour = hour
            s.min = min
            s.sec = sec


        def __ge__(s, other):
            if s.hour < other.hour:
                return False
            if s.hour > other.hour:
                return True
            if s.hour != other.hour:
                return False
            if s.min < other.min:
                return False
            return True


        def __gt__(s, other):
            if s.hour < other.hour:
                return False
            if s.hour > other.hour:
                return True
            if s.hour != other.hour:
                return False
            if s.min <= other.min:
                return False
            return True


        def __le__(s, other):
            if s.hour > other.hour:
                return False
            if s.hour < other.hour:
                return True
            if s.hour != other.hour:
                return False
            if s.min > other.min:
                return False
            return True


        def __lt__(s, other):
            if s.hour > other.hour:
                return False
            if s.hour < other.hour:
                return True
            if s.hour != other.hour:
                return False
            if s.min >= other.min:
                return False
            return True


        def __repr__(s):
            return "Time:%02d:%02d:%02d" % (s.hour, s.min, s.sec)

        def __str__(s):
            return "%02d:%02d:%02d" % (s.hour, s.min, s.sec)



