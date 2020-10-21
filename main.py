import logging
import schedule
import time
import parser_lancet
import threading
import re
import telebot
import logging
import ssl
from creds import token

from aiohttp import web
from telebot import types
from config import States as sts

import dbworker as db


API_TOKEN = token

WEBHOOK_HOST = '35.199.188.65'
WEBHOOK_PORT = 8443  # 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr

WEBHOOK_SSL_CERT = 'ssh/url_cert.pem'  # Path to the ssl certificate
WEBHOOK_SSL_PRIV = 'ssh/url_private.key'  # Path to the ssl private key

WEBHOOK_URL_BASE = "https://{}:{}".format(WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/{}/".format(API_TOKEN)

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(API_TOKEN, threaded=False)

app = web.Application()


# Process webhook calls
async def handle(request):
    if request.match_info.get('token') == bot.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return web.Response()
    else:
        return web.Response(status=403)


app.router.add_post('/{token}/', handle)


class JobRunner(schedule.Scheduler):
    """Extends shedule, allows running jobs in parralel
       with infinity polling.

    """

    def run_continuously(self, interval=1):
        """Continuously run, while executing pending jobs at each elapsed
           time interval.
           @return cease_continuous_run: threading.Event which can be set to
           cease continuous run.

        """
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
    """Keyboard is responsible for creating markups, switching buttons on/off
    and passing selected buttons further down the line.

    """
    tick = '✓'
    id = 0

    def __init__(self, passed_buttons, keyb_type='day selection'):
        self.button_names = passed_buttons
        self.button_names = [*self.button_names, 'Select All']
        self.keyb_type = keyb_type
        self.id = Keyboard.id
        Keyboard.id += 1
        print(f'created instance {self.id}')

    def generate_markup(self):
        self.markup = types.InlineKeyboardMarkup()

        # generates keys from key names passed during __init__.
        self.keys = []
        for button_name in self.button_names:
            self.keys.append(types.InlineKeyboardButton(
                                                    text=button_name,
                                                    callback_data=button_name)
                             )
        self.cont_key = types.InlineKeyboardButton(text='Continue',
                                                   callback_data='Continue'
                                                   )

        if self.keyb_type == 'days':
            self.markup.row(*self.keys[:4])
            self.markup.row(*self.keys[4:])
            self.markup.row(self.cont_key)
            return self.markup
        elif self.keyb_type == 'journals':
            self.markup.row(*self.keys)
            self.markup.row(self.cont_key)
            return self.markup

    def switch_button(self, text):
        """Marks button with passed [text] on/off, uses tick sign as a mark."""
        print(f'current buttons = {self.button_names[0]}. call = {text}. instance = {self.id}')
        key_number = self.button_names.index(text)
        # This first clause checks if the key 'Select All'
        # was pressed. This key is last on the list of key names.
        if self.button_names[key_number] == self.button_names[-1]:
            # This case handles the 'Select All' state.
            if self.button_names[-1].startswith('Select'):
                for i, text in enumerate(self.button_names[:-1]):
                    self.button_names[i] = text.strip(self.tick)
                    self.button_names[i] = self.button_names[i] + self.tick
                self.button_names[-1] = 'Deselect All'
            # This one is for 'Deselect All'.
            else:
                for i, text in enumerate(self.button_names[:-1]):
                    self.button_names[i] = text.strip(self.tick)
                self.button_names[-1] = 'Select All'

        elif self.button_names[key_number].endswith(self.tick):
            self.button_names[key_number] = self.button_names[key_number][:-1]
        else:
            self.button_names[key_number] = text + self.tick

    def selected_buttons(self):
        selected = []
        for btn in self.button_names[:-1]:
            if btn.endswith(self.tick):
                selected.append(btn[:].strip(self.tick))
        return selected


@bot.message_handler(commands=['start'])
def send_welcome(message):

    if not db.check_if_user_exists(message.chat.id):
        db.add_user(message.chat.id)

        db.set_user_state(message.chat.id, sts.S_START.value)

        bot.send_message(message.chat.id,
                         'Hi there, I am MedWatcher Bot.\n'
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
                         'but you\'ve probaby figured that one out already...'
                         )
    else:
        db.set_user_state(message.chat.id, sts.S_START.value)
        bot.send_message(
            message.chat.id, 'Welcome back! How can I be of service today?'
        )


@bot.message_handler(commands=['unsub'])
def unsub(message):
    job_keeper.clear(message.chat.id)
    bot.send_message(message.chat.id,
                     'You\'re unsubbed. Hope we\'ll talk again:)')
    db.set_user_state(message.chat.id, sts.S_START.value)


@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    kbd_buttons = ['Lancet']
    sub_keyboard = Keyboard(kbd_buttons, keyb_type='journal selection')
    markup = sub_keyboard.generate_markup()
    bot.send_message(message.chat.id,
                     'Select relevant journals.\nP.S. I can only look in The '
                     'Lancet at the moment, but I promise to become more'
                     ' diligent in the future.',
                     reply_markup=markup)
    db.set_user_state(message.chat.id, sts.S_SUB.value)

    # Starting a function name with an underscore disables "Unused variable"
    # warnings. Thank you, stackoverflow!
    @bot.callback_query_handler(func=lambda call: True
                                and call.data != 'Continue')
    def _switch_button_sub(call):
        day = call.data
        sub_keyboard.switch_button(day)
        new_markup = sub_keyboard.generate_markup()
        bot.edit_message_reply_markup(call.message.chat.id,
                                      call.message.message_id,
                                      reply_markup=new_markup)

    @bot.callback_query_handler(func=lambda call: True
                                and call.data == 'Continue')
    def _cont_sub(call):
        selected_journals = sub_keyboard.selected_buttons()
        if not selected_journals:
            bot.send_message(call.message.chat.id,
                             'Please select at least one journal.')
        else:
            db.set_user_state(call.message.chat.id,
                              sts.S_SUB_JOURNALS.value)
            db.set_user_terms(call.message.chat.id,
                              ','.join(selected_journals),
                              'SUB', 'JOURNALS')
            bot.send_message(call.message.chat.id,
                             'We are on track! '
                             'Now let\'s figure out what keywords we\'re '
                             'looking for. You can send me more that one '
                             'keyword, just separate them with spaces.')


@bot.message_handler(
    func=lambda message: db.get_state(message.chat.id) == sts.S_SUB_DAYS.value
    and message.text.strip().lower() not in ('/search',
                                             '/subscribe',
                                             '/help',
                                             '/unsub'))
def get_time(message):
    user_id = message.chat.id
    time = message.text.strip()
    if not time.isnumeric():
        bot.send_message(user_id, 'That\'s not a very good input. '
                                  'I only need a time of day '
                                  'right now. One number from 0 to 23 '
                                  'will do nicely.')
    elif int(time) not in range(24):
        bot.send_message(user_id, 'So close! It\'s now a number, '
                                  'but it\'s still not in 0-23 range. '
                                  'Another try maybe?')
    else:
        db.set_user_delivery_time(user_id, time)
        exec(f'job_keeper.clear({user_id})')
        schedule_job(user_id)
        bot.send_message(user_id, 'Great! You have '
                                  'successfully subscribed!')


def generate_keyboard_markup(user_id, keyb_type, req_type):
    if req_type == 'search':
        markup = types.InlineKeyboardMarkup()
        button_state = db.get_keyboard(user_id, keyb_type, req_type)
        lancet_button = types.InlineKeyboardButton(
                                text='The Lancet',
                                callback_data=f'lanc_search_{button_state}')
        continue_button = types.InlineKeyboardButton(
                                text='Continue',
                                callback_data=f'cont_search')
        markup.row(lancet_button)
        markup.row(continue_button)
    if req_type == 'sub':
        if keyb_type == 'days':
            markup = types.InlineKeyboardMarkup()
            button_state = db.get_keyboard(user_id, keyb_type, req_type)
            print(button_state)
            

@bot.message_handler(commands=['search'])
def search(message):
    markup = generate_journal_markup()
    bot.send_message(message.chat.id,
                     'Select relevant journals.\nP.S. I can only look in The '
                     'Lancet at the moment, but I promise to become more'
                     ' diligent in the future.',
                     reply_markup=markup)
    db.set_user_state(message.chat.id, sts.S_SEARCH.value)

    @bot.callback_query_handler(func=lambda call: True
                                and call.data != 'Continue')
    def _switch_button(call):
        print(f'call data = {call.data} instance = {search_keyboard.id}')
        search_keyboard.switch_button(call.data)
        new_markup = search_keyboard.generate_markup()
        bot.edit_message_reply_markup(call.message.chat.id,
                                      call.message.message_id,
                                      reply_markup=new_markup)

    @bot.callback_query_handler(func=lambda call: True
                                and call.data == 'Continue')
    def _cont(call):
        selected_journals = search_keyboard.selected_buttons()
        if selected_journals:
            db.set_user_state(call.message.chat.id,
                              sts.S_SEARCH_JOURNALS.value)
            db.set_user_terms(call.message.chat.id,
                              ','.join(selected_journals),
                              'SEARCH', 'JOURNALS')
            bot.send_message(call.message.chat.id,
                             'Great!\n'
                             'Now send me the keywords you want to '
                             'look for.')
        else:
            bot.send_message(call.message.chat.id,
                             'Please select at least one journal.')


@bot.message_handler(
    func=lambda message: db.get_state(message.chat.id) == sts.S_SEARCH_JOURNALS.value
    or db.get_state(message.chat.id) == sts.S_SUB_JOURNALS.value
    and message.text.strip().lower() not in ('/search',
                                             '/subscribe',
                                             '/help',
                                             '/unsub'))
def get_keywords(message):
    strpd_text = message.text.strip(',;_\'"')
    user_id = message.chat.id

    if not re.search('[a-z A-z]', strpd_text):
        bot.send_message(
                    user_id, 'Sorry, I won\'t be able to find those keywords, '
                             'try leaning more towards letters, not numbers.\n'
                             'For example: instead of "covid-19 try "covid".\n'
                             'If you\'re somehow stuck - just do a new /search'
                             ' or even /start, I promise, I will still '
                             ' remember you.'
        )
    else:
        user_state = db.get_state(user_id)
        keywords_type = ''
        if user_state == sts.S_SEARCH_JOURNALS.value:
            keywords_type = 'SEARCH'
        elif user_state == sts.S_SUB_JOURNALS.value:
            keywords_type = 'SUB'

        db.set_user_terms(user_id,
                          strpd_text,
                          keywords_type,
                          'KEYWORDS')
        next_state = f'sts.S_{keywords_type}_KEYWORDS.value'
        exec(f'db.set_user_state(user_id, {next_state})')

        if keywords_type == 'SEARCH':
            collected_articles = collect_articles(user_id, keywords_type)
            send_articles(user_id, collected_articles, keywords_type)
            db.set_user_state(user_id, sts.S_START.value)

        elif keywords_type == 'SUB':
            user_keywords = db.get_user_keywords(user_id, 'SUB').split()
            user_journals = db.get_user_journals(user_id, 'SUB').split()

            collected_data = db.articles_by_keywords(user_keywords,
                                                     user_journals)
            if not collected_data:
                bot.send_message(user_id, 'Fair warning:\nI have no  '
                                          'matches with those keywords'
                                          ' in my archive. Your '
                                          'subscription probably won\'t'
                                          'yield any results.')
            else:
                kbd_buttons = ['Monday',
                               'Tuesday',
                               'Wednesday',
                               'Thursday',
                               'Friday',
                               'Saturday',
                               'Sunday']

                days_keyboard = Keyboard(kbd_buttons, keyb_type='days')
                markup = days_keyboard.generate_markup()
                bot.send_message(user_id,
                                 'Select delivery days',
                                 reply_markup=markup)
                db.set_user_state(user_id, sts.S_SUB_DAYS.value)

                @bot.callback_query_handler(func=lambda call: True
                                            and call.data != 'Continue')
                def _switch_button(call):
                    day = call.data
                    days_keyboard.switch_button(day)
                    new_markup = days_keyboard.generate_markup()
                    bot.edit_message_reply_markup(user_id,
                                                  call.message.message_id,
                                                  reply_markup=new_markup)

                @bot.callback_query_handler(func=lambda call: True
                                            and call.data == 'Continue')
                def _cont(call):
                    selected_days = days_keyboard.selected_buttons()
                    if selected_days:
                        db.set_user_state(call.message.chat.id,
                                          sts.S_SUB_DAYS.value)
                        db.set_mailing_days(user_id, selected_days)
                        bot.send_message(call.message.chat.id,
                                         'Great!\n'
                                         'Now let\'s deal with delivery time.'
                                         'I\'ll accept the number from 0 to 23'
                                         'representing an hour of day '
                                         'at which you want to recieve the '
                                         'delivery.')
                    else:
                        bot.send_message(call.message.chat.id,
                                         'Please select at least'
                                         ' one delivery day.')


@bot.message_handler(
    func=lambda message: db.get_state(message.chat.id) == sts.S_START.value
    and message.text.strip().lower() not in ('/search',
                                             '/subscribe',
                                             '/help',
                                             '/unsub'))
def handle_random_message(message):
    bot.reply_to(
        message, 'Well, this was rather random. At this point of '
                 'our conversation it would be more fruitful to use'
                 ' either /search or /subscribe. You can /unsub if I get'
                 ' too much.'
                )


def collect_articles(user_id, op_type):
    user_keywords = db.get_user_keywords(user_id, op_type).split()
    user_journals = db.get_user_journals(user_id, op_type).split()

    collected_data = db.articles_by_keywords(user_keywords, user_journals)
    return collected_data


def send_articles(user_id, articles, op_type):
    data_to_send = articles
    if not data_to_send:
        bot.send_message(user_id,
                         'Sorry, i can\'t find what you you\'re looking for.')
    else:
        formatted_data = format(data_to_send)
        for part in formatted_data:
            text = '\n\n'.join(part)
            bot.send_message(user_id, text,
                             parse_mode='html',
                             disable_web_page_preview=False)


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
    articles = collect_articles(user_id, 'SUB')
    send_articles(user_id, articles, 'SUB')


def schedule_job(user_id):
    days = db.get_mailing_days(user_id).split(',')
    delivery_time = db.get_user_delivery_time(user_id)

    if len(delivery_time) == 1:
        delivery_time = '0' + delivery_time + ':00'
    else:
        delivery_time = delivery_time + ':00'

    for d in days:

        day = d.lower()
        job_string = f'job_keeper.every().{day}.at("{delivery_time}").do(mailing_job, user_id={user_id}).tag("{user_id}")'
        exec(job_string)


# Remove webhook, it fails sometimes the set if there is a previous webhook
bot.remove_webhook()

# Set webhook
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))

# Build ssl context
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)
# Start aiohttp server


parsing_thread = threading.Thread(target=parser_lancet.check_updates,
                                  daemon=True)
job_keeper.every(6).hours.do(parsing_thread.start)
running_keeper = job_keeper.run_continuously()
try:
    web.run_app(
                app,
                host=WEBHOOK_LISTEN,
                port=WEBHOOK_PORT,
                ssl_context=context,
                )
except KeyboardInterrupt:
    running_keeper.set()
    parsing_thread.join()
    print("threads successfully closed")

# TODO: schedule mailing in a separate thread probably??? scheduling workks,
# mailing = broken

# TODO: db would probably handle easier as a class.
# TODO: /search with journals selected kills the bot.
 