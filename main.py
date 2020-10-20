import logging
import config
import schedule
import time
import dbworker
import parser_lancet
import threading
import re
import telebot
from telebot import types

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(config.token)

# Extends shedule, allows running jobs in parralel with infinity polling.
class JobRunner(schedule.Scheduler):

    def run_continuously(self, interval=1):
        """Continuously run, while executing pending jobs at each elapsed
        time interval.
        @return cease_continuous_run: threading.Event which can be set to
        cease continuous run."""
        cease_continuous_run = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                while not cease_continuous_run.is_set():
                    self.run_pending()
                    time.sleep(interval)

        continuous_thread = ScheduleThread(daemon=True)
        continuous_thread.start()
        return cease_continuous_run

job_keeper = JobRunner()

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

        self.markup = types.InlineKeyboardMarkup()
        self.keys = [types.InlineKeyboardButton(text=day,
                                    callback_data=day) for day in self.days]
        self.cont_key = types.InlineKeyboardButton(text='Continue',
                                    callback_data='Continue')
        self.markup.row(*self.keys[:4])
        self.markup.row(*self.keys[4:])
        self.markup.row(self.cont_key)
        return self.markup

    def switch_button(self, day):
        day_no = self.days.index(day)

        if self.days[day_no] == self.days[-1]:
            if self.days[-1].startswith('Select'):
                for i, day in enumerate(self.days[:-1]):
                    self.days[i] = day.strip(self.tick)
                    self.days[i] = self.days[i] + self.tick
                self.days[-1] = 'Deselect All'
            else:
                for i, day in enumerate(self.days[:-1]):
                    self.days[i] = day.strip(self.tick)
                self.days[-1] = 'Select All'

        elif self.days[day_no].endswith(self.tick):
            self.days[day_no] = self.days[day_no][:-1]
        else:
            self.days[day_no] = day + self.tick
    
    def selected_days(self):
        selected = []
        for day in self.days[:-1]:
            if day.endswith(self.tick):
                selected.append(day[:].strip(self.tick))
        return selected


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
                    '/unsub if you don\'t want to recieve articles'
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

    # Starting a function name with an underscore disables "Unused variable"
    # warnings. Thank you, stackoverflow!
    @bot.callback_query_handler(func=lambda call: True and call.data != 'Continue')
    def _switch_button(call):
        day = call.data
        keyboard.switch_button(day)
        new_markup = keyboard.generate_markup()
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=new_markup)

    @bot.callback_query_handler(func=lambda call: True and call.data == 'Continue')
    def _cont(call):
        selected_days = keyboard.selected_days()
        if selected_days:
            dbworker.set_user_state(call.message.chat.id, config.States.S_SUB_DAYS.value)
            dbworker.set_mailing_days(call.message.chat.id, ','.join(selected_days))
            bot.send_message(call.message.chat.id, 'We are on track! '
                                                   'Next order of business - time. '
                                                   'To simplify the whole ordeal - '
                                                   'just send me one number from 0 to 23 '
                                                   '- that would be the hour of day at '
                                                   'which you would want to recieve your '
                                                   'articles.')
        else:
            bot.send_message(call.message.chat.id, 'Please select at least one day.')


@bot.message_handler(
    func=lambda message: dbworker.get_user_state(message.chat.id) == config.States.S_SUB_DAYS.value
    and message.text.strip().lower() not in ('/search', '/subscribe', '/help', '/unsub')
)
def get_time(message):
    time = message.text.strip()
    if not time.isnumeric():
        bot.send_message(message.chat.id, 'That\'s not a very good input. '
                                          'I only need a time of day '
                                          'right now. One number from 0 to 23 '
                                          'will do nicely.')
    elif int(time) not in range(24):
        bot.send_message(message.chat.id, 'So close! It\'s now a number, '
                                          'but it\'s still not in 0-23 range. '
                                          'Another try maybe?')
    else:
        dbworker.set_user_delivery_time(message.chat.id, time)
        bot.send_message(message.chat.id, 'Great! Now send me the keywords, '
                                          'you want to track.')
        dbworker.set_user_state(message.chat.id, config.States.S_SUB_TIME.value)


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
    or dbworker.get_user_state(message.chat.id) == config.States.S_SUB_TIME.value 
    and message.text.strip().lower() not in ('/search', '/subscribe', '/help', '/unsub')
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
        user_state = dbworker.get_user_state(message.chat.id)
        keywords_type = ''
        if user_state == config.States.S_SEARCH.value:
            keywords_type = 'SEARCH'
        elif user_state == config.States.S_SUB_TIME.value:
            keywords_type = 'SUB'
        
        dbworker.set_user_terms(message.chat.id, strpd_text, keywords_type, 'KEYWORDS')
        bot.send_message(message.chat.id,
                        ('Nice! Now send me the names of the journals you want'
                        ' me to search in. Sadly at moment I can only look for'
                        ' things in one journal - \'Lancet\'. But I promise to '
                        'become more diligent in the future. ')
                        )
        next_state = f'config.States.S_{keywords_type}_KEYWORDS.value'
        exec(f'dbworker.set_user_state(message.chat.id, {next_state})')


@bot.message_handler(
    func=lambda message: dbworker.get_user_state(message.chat.id) == config.States.S_START.value
    and message.text.strip().lower() not in ('/search', '/subscribe', '/help', '/unsub'))
def handle_random_message(message):
    bot.reply_to(
        message, 'Well, this was rather random. At this point of '
                 'our conversation it would be more fruitful to use'
                 ' either /search or /subscribe.'
    )


@bot.message_handler(commands=['unsub'])
def unsub(message):
    job_keeper.clear(message.chat.id)


@bot.message_handler(
    func=lambda message: dbworker.get_user_state(message.chat.id) == config.States.S_SEARCH_KEYWORDS.value
    or dbworker.get_user_state(message.chat.id) == config.States.S_SUB_KEYWORDS.value 
    and message.text.strip().lower() not in ('/search', '/subscribe', '/help', '/unsub'))
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
        user_state = dbworker.get_user_state(message.chat.id)
        keywords_type = ''
        if user_state == config.States.S_SEARCH_KEYWORDS.value:
            keywords_type = 'SEARCH'
        elif user_state == config.States.S_SUB_KEYWORDS.value:
            keywords_type = 'SUB'

        dbworker.set_user_terms(message.chat.id, strpd_text, keywords_type, 'JOURNALS')
        next_state = f'config.States.S_{keywords_type}_JOURNALS.value'
        exec(f'dbworker.set_user_state(message.chat.id, {next_state})')

        if dbworker.get_user_state(message.chat.id) == config.States.S_SEARCH_JOURNALS.value:
            collect_and_send(message.chat.id, keywords_type)
        elif dbworker.get_user_state(message.chat.id) == config.States.S_SUB_JOURNALS.value:
            schedule_job(message.chat.id)

def collect_and_send(user_id, op_type):
    user_keywords = dbworker.get_user_keywords(user_id, op_type).split()
    user_journals = dbworker.get_user_journals(user_id, op_type).split()

    collected_data = dbworker.select_by_keywords(user_keywords,user_journals)

    if not collected_data:
        bot.send_message(
            user_id, 'Sorry, i can\'t find what you you\'re looking for.'
            )
        dbworker.set_user_state(
            user_id,
            config.States.S_START.value)
    else:
        formatted_data = format(collected_data)

        for part in formatted_data:
            text = '\n\n'.join(part)
            bot.send_message(user_id, text, parse_mode='html', disable_web_page_preview=False)


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


def mailing_job(user_id):
    # collect_and_send(user_id, 'SUB')
    bot.send_message(user_id, 'Working!')
    print('working')


def schedule_job(user_id):

    days = dbworker.get_mailing_days(user_id).split(',')
    delivery_time = dbworker.get_user_delivery_time(user_id)

    if len(delivery_time) == 1:
        delivery_time = '0' + delivery_time + ':00'
    else:
        delivery_time = delivery_time + ':00'

    for d in days:

        day = d.lower()
        job_string = f'job_keeper.every().{day}.at("{delivery_time}").do(job, user_id={user_id}).tag("{user_id}")'
        # exec(job_string)
        exec(f'job_keeper.every().second.do(mailing_job, user_id={user_id}).tag("{user_id}")')


if __name__ == "__main__":

    parsing_thread = threading.Thread(target=parser_lancet.check_updates, daemon=True)
    parsing_thread.start()
    running_keeper = job_keeper.run_continuously()
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        running_keeper.set()
        parsing_thread.join()
        print ("threads successfully closed")

    #TODO: schedule mailing in a separate thread probably??? scheduling workks, mailing = broken
