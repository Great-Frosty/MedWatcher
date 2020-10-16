import logging
import telebot
import config
import schedule
import dbworker
import parser_lancet


logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(config.token)


# Handle '/start'
@bot.message_handler(commands=['start'])
def send_welcome(message):

    if not dbworker.check_if_user_exists(message.chat.id):
        dbworker.add_user(message.chat.id)

    dbworker.set_user_state(message.chat.id, config.States.S_START.value)

    bot.reply_to(message,
                 ('Hi there, I am MedWatcher Bot.\n'
                  'I follow several major medical journals and enjoy spreading'
                  ' the knowledge. Get it? Spread. Where was I? Right. '
                  'Heres\'s what I can do for you.\n'
                  'If you need a quick fix of science — just send me\n'
                  '/search command.\n'
                  'If you are more of a'
                  ' \"constant stream of knowledge in my face\"'
                  ' type of person — it\'s fine.\n'
                  '/subscribe will hook you up.\n'
                  '/help\n might also come in handy, '
                  'but you\'ve probaby figured that one out already...'))


# We need a scheduling command as soon as possible.
@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    bot.send_message(message.chat.id, 'работает!')


@bot.message_handler(commands=['search'])
def search(message):
    bot.send_message(
                    message.chat.id,
                    'Ait. Now just type in keywords you want me to look for.'
                    )

    dbworker.set_user_state(message.chat.id, config.States.S_SEARCH.value)
    mes = f'User state is now at {dbworker.get_user_state(message.chat.id)}'
    bot.send_message(message.chat.id, mes)

@bot.message_handler(
    func=lambda message: dbworker.get_user_state(message.chat.id) == config.States.S_SEARCH.value
    and message.text.strip().lower() not in ('/search', '/subscribe', '/reset', '/help')
    )
def get_keywords(message):
    dbworker.set_user_terms(message.chat.id, message.text, 'SEARCH', 'KEYWORDS')
    bot.send_message(message.chat.id,
                     ('Nice! Now send me the names of the journals you want'
                      ' me to search in.')
                     )
    dbworker.set_user_state(
                            message.chat.id,
                            config.States.S_SEARCH_KEYWORDS.value
                            )


@bot.message_handler(
    func=lambda message: dbworker.get_user_state(message.chat.id) == config.States.S_SEARCH_KEYWORDS.value
    and message.text.strip().lower() not in ('/search', '/subscribe', '/reset', '/help'))
def get_journals(message):
    dbworker.set_user_terms(message.chat.id, message.text, 'SEARCH', 'JOURNALS')
    dbworker.set_user_state(
        message.chat.id,
        config.States.S_SEARCH_JOURNALS.value
    )
    user_keywords = dbworker.get_user_keywords(message.chat.id, 'SEARCH')
    collected_data = dbworker.select_by_keywords(user_keywords, message.text)
    bot.send_message(message.chat.id, collected_data)
    dbworker.set_user_state(
        message.chat.id, config.States.S_START.value
    )

# Минутка архитектуры: Бот должен запоминать пользователя, его предыдущие
# поиски, его предыдущие подписки. В диалоге будет что-то типа 'Welcome back'.
# Подписаться заново - пришли время, подписаться как раньше - пришли /ок.


# schedule.every(6).hours.do(parser_lancet.check_updates)

if __name__ == "__main__":
    bot.infinity_polling()

