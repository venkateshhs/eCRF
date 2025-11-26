from datetime import datetime
def local_now():
    # Local system time with tzinfo
    return datetime.now().astimezone()