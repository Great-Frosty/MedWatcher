import logging
import telebot
import config
import schedule
import parser_lancet

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(config.token)


# Handle '/start' and '/help'
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(message,
                 ('Hi there, I am MedWatcher Bot.\n'
                  'I follow several major medical journals and enjoy spreading'
                  ' the knowledge. Get it? Spread. Where was I? Right. '
                  'I was about to explain what I can do for you.\n'
                  'If you need a quick fix of science — just send me\n'
                  '/search command.\n'
                  'If you are more of a'
                  ' \"constant stream of knowledge in my face\"'
                  ' type of person — it\'s fine.\n'
                  '/subscribe will hook you up.\n'
                  '/help\n might also come in handy, '
                  'but you probaby knew that already...'))


# Handle all other messages
@bot.message_handler(func=lambda message: True, content_types=['text'])
def echo_message(message):
    bot.reply_to(message, message.text)


# We need a scheduling command as soon as possible.
@bot.message_handler(commands=['subscribe'])
def sub(message):
    pass


schedule.every(6).hours.do(parser_lancet.check_updates())

if __name__ == "__main__":
    bot.infinity_polling()
    schedule.run_pending()
