from enum import Enum


token = '1196869629:AAGWmpWV3hO8D-WCZKK4dz-ryew00XDCkTg'
db_file = 'database.db'


class States(Enum):
    S_START = '0'
    S_SUB = '1'
    S_SUB_JOURNALS = '2'
    S_SUB_KEYWORDS = '3'
    S_SUB_DAYS = '4'
    S_SUB_TIME = '5'
    S_SEARCH = '6'
    S_SEARCH_JOURNALS = '7'
    S_SEARCH_KEYWORDS = '8'
