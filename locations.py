"""Location rule from profile.json: home area, fully remote US, and (only when relocate_min_salary is set) other US
locations, whose pay rank_queue.py then checks against that floor. Non-US postings never pass."""
import re
from jobprofile import load, home_regex

US_HINT = re.compile(r"united states|\busa?\b|remote|anywhere|, ?(al|ak|az|ar|ca|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|"
                     r"mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy|dc)\b|california|"
                     r"new york|nyc|seattle|boston|austin|chicago|denver|atlanta|los angeles|san diego|miami|dallas|houston|"
                     r"philadelphia|washington|portland|phoenix|minneapolis|pittsburgh", re.I)
NON_US = re.compile(r"canada|toronto|vancouver|montreal|ontario|united kingdom|\buk\b|london|india|bangalore|bengaluru|"
                    r"hyderabad|germany|berlin|ireland|dublin(?!, ca)|poland|singapore|japan|tokyo|israel|mexico|brazil|australia|"
                    r"netherlands|amsterdam|paris|france|spain|philippines|emea|apac|latam|europe|argentina|colombia|italy|milan|rome|"
                    r"bulgaria|sofia|romania|bucharest|portugal|lisbon|greece|czech|prague|hungary|budapest|serbia|croatia|ukraine|kyiv|"
                    r"turkey|istanbul|sweden|stockholm|norway|oslo|denmark|copenhagen|finland|helsinki|switzerland|zurich|austria|vienna|"
                    r"belgium|brussels|estonia|latvia|lithuania|chile|peru|uruguay|costa rica|china|shanghai|beijing|hong kong|taiwan|"
                    r"korea|seoul|vietnam|thailand|malaysia|indonesia|pakistan|egypt|nigeria|kenya|south africa|new zealand|armenia|yerevan", re.I)
REMOTE = re.compile(r"remote|anywhere|distributed", re.I)

_P = None


def location_ok(loc: str) -> bool:
    global _P
    _P = _P or load()
    if not loc:
        return False
    if NON_US.search(loc):  # "Toronto or SF": keep only if something US-specific (not just "remote") remains
        loc = NON_US.sub(" ", loc)
        if not (home_regex(_P).search(loc) or US_HINT.search(REMOTE.sub(" ", loc))):
            return False
    if home_regex(_P).search(loc):
        return True
    if REMOTE.search(loc) and _P['location'].get('remote_us_ok', True):
        return True
    return bool(_P['location'].get('relocate_min_salary')) and bool(US_HINT.search(loc))
