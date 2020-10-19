import logging
import config
import schedule
import dbworker
import parser_lancet
import threading
import re
import telebot
from telebot import types

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(config.token)


def makeKeyboard():

    days = [
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday',
        'Select All']

    markup = types.InlineKeyboardMarkup(row_width=4)

    keys = [types.InlineKeyboardButton(text=day,
                                        callback_data=day) for day in days]

    markup.add(*keys)

    return markup


class Keyboard(object):

    tick = '✓'
    def __init__(self):

        self.days = [
                    'Monday',
                    'Tuesday',
                    'Wednesday',
                    'Thursday',
                    'Friday',
                    'Saturday',
                    'Sunday',
                    'Select All'
                    ]

    def generate_markup(self):

        self.markup = types.InlineKeyboardMarkup(row_width=4)
        self.keys = [types.InlineKeyboardButton(text=day,
                                    callback_data=day) for day in self.days]
        self.markup.add(*self.keys)
        return self.markup

    def switch_button(self, day):
        day_no = self.days.index(day)

        if self.days[day_no] == self.days[-1]:
            if self.days[-1].startswith('Select'):
                for i, day in enumerate(self.days[:-1]):
                    self.days[i] = day.strip(self.tick)
                    self.days[i] = day + self.tick
                self.days[-1] = 'Deselect All'
            else:
                for i, day in enumerate(self.days[:-1]):
                    self.days[i] = day.strip(self.tick)
                self.days[-1] = 'Select All'

        elif self.days[day_no].endswith(self.tick):
            self.days[day_no] = self.days[day_no][:-1]
        else:
            self.days[day_no] = day + self.tick


# Handle '/start'
@bot.message_handler(commands=['start'])
def send_welcome(message):

    if not dbworker.check_if_user_exists(message.chat.id):
        dbworker.add_user(message.chat.id)

        dbworker.set_user_state(message.chat.id, config.States.S_START.value)

        bot.send_message(message.chat.id,
                    ('Hi there, I am MedWatcher Bot.\n'
                    'I follow several major medical journals and enjoy '
                    'spreading the knowledge. Get it? Spread. '
                    'Where was I? Right. '
                    'Heres\'s what I can do for you.\n'
                    'If you need a quick fix of science — just send me\n'
                    '/search command.\n'
                    'If you are more of a'
                    ' \"constant stream of knowledge in my face\"'
                    ' type of person — it\'s fine.\n'
                    '/subscribe will hook you up.\n'
                    '/help\n might also come in handy, '
                    'but you\'ve probaby figured that one out already...'))
    else:
        dbworker.set_user_state(message.chat.id, config.States.S_START.value)
        bot.send_message(
            message.chat.id, 'Welcome back! How can I be of service today?'
        )


@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    keyboard = Keyboard()
    markup = keyboard.generate_markup()
    bot.send_message(message.chat.id, 'Select days', reply_markup=markup)
    dbworker.set_user_state(
        message.chat.id, config.States.S_SUB.value
        )

    @bot.callback_query_handler(func=lambda call: True)
    def switch_button(call):

            day = call.data
            keyboard.switch_button(day)
            new_markup = keyboard.generate_markup()
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=new_markup)



@bot.message_handler(commands=['search'])
def search(message):
    bot.send_message(
                    message.chat.id,
                    'Ait. Now just type in keywords you want me to look for.'
                    '\nSend them like you normally would – '
                    'separated by a spacebar.'
                    )

    dbworker.set_user_state(message.chat.id, config.States.S_SEARCH.value)


@bot.message_handler(
    func=lambda message: dbworker.get_user_state(message.chat.id) == config.States.S_SEARCH.value
    and message.text.strip().lower() not in ('/search', '/subscribe', '/help')
    )
def get_keywords(message):
    strpd_text = message.text.strip(',;_\'"')

    if not re.search('[a-zA-z]', strpd_text):
        bot.send_message(
            message.chat.id, 'Sorry, I won\'t be able to find those keywords, '
                             'try leaning more towards letters, not numbers.\n'
                             'If you\'re somehow stuck - just do a new /search'
                             ' or even /start, I promise, I will still '
                             ' remember you.' 
        )
    else:
        dbworker.set_user_terms(message.chat.id, strpd_text, 'SEARCH', 'KEYWORDS')
        bot.send_message(message.chat.id,
                        ('Nice! Now send me the names of the journals you want'
                        ' me to search in. Sadly at moment I can only look for'
                        ' things in one journal - \'Lancet\'. But I promise to '
                        'become more diligent in the future. ')
                        )
        dbworker.set_user_state(
                                message.chat.id,
                                config.States.S_SEARCH_KEYWORDS.value
                                )


@bot.message_handler(
    func=lambda message: dbworker.get_user_state(message.chat.id) == config.States.S_START.value
    and message.text.strip().lower() not in ('/search', '/subscribe', '/help'))
def handle_random_message(message):
    bot.reply_to(
        message, 'Well, this was rather random. At this point of '
                 'our conversation it would be more fruitful to use'
                 ' either /search or /subscribe.'
    )


@bot.message_handler(
    func=lambda message: dbworker.get_user_state(message.chat.id) == config.States.S_SEARCH_KEYWORDS.value
    and message.text.strip().lower() not in ('/search', '/subscribe', '/help'))
def get_journals(message):
    strpd_text = message.text.strip(',;_\'"')

    if not re.search('[a-zA-z]', strpd_text):
        bot.send_message(
            message.chat.id, 'I\'m pretty sure no journal in the world is '
                             'named like that. A letter is worth a thousand '
                             'numbers in this case.\n'
                             'If you\'re somehow stuck - just do a new /search'
                             ' or even /start, I promise, I will still '
                             ' remember you.'
        )
    else:
        dbworker.set_user_terms(message.chat.id, strpd_text, 'SEARCH', 'JOURNALS')
        dbworker.set_user_state(
            message.chat.id,
            config.States.S_SEARCH_JOURNALS.value
        )
        user_keywords = dbworker.get_user_keywords(message.chat.id, 'SEARCH').split()

        collected_data = dbworker.select_by_keywords(user_keywords, message.text.split())

        if not collected_data:
            bot.send_message(
                message.chat.id, 'Sorry, i can\'t find what you you\'ve asked.'
                )
            dbworker.set_user_state(
                message.chat.id,
                config.States.S_START.value)
        else:
            formatted_data = format(collected_data)

            for part in formatted_data:
                text = '\n\n'.join(part)
                bot.send_message(message.chat.id, text, parse_mode='html', disable_web_page_preview=False)

            dbworker.set_user_state(
                message.chat.id, config.States.S_START.value
            )


def format(collected_data):
    '''Recieves a list of article names with links, formats them properly,
     groups them in chunks. Grouping results in several chunks is required
     to keep message size manageable.'''

    formatted_data = []
    for row in collected_data:
        formatted_row = f'{row[0]}.\n<a href="{row[1]}">Read article</a>'
        formatted_data.append(formatted_row)


    formatted_data = parts(formatted_data)

    return formatted_data


def parts(lst, n=5):
    """Yields pieces of the list of the size n."""

    for i in range(0, len(lst), n):
        yield lst[i:i+n]


if __name__ == "__main__":

    parsing_thread = threading.Thread(target=parser_lancet.check_updates, daemon=True)
    parsing_thread.start()
    bot.infinity_polling()
    parsing_thread.join()
