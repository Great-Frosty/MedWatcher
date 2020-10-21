import dbworker as db
from telebot import types


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
        return markup
    if req_type == 'sub':
        if keyb_type == 'days':
            markup = types.InlineKeyboardMarkup()
            button_state = db.get_keyboard(user_id, keyb_type, req_type)
            buttons_text = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

            buttons = []
            for i, text in enumerate(buttons_text):
                buttons.append(
                    types.InlineKeyboardButton(
                                text='text',
                                callback_data=f'{text.lower()}_{button_state[i]}')
                )
            continue_button = types.InlineKeyboardButton(
                        text='Continue',
                        callback_data=f'cont_sub_days')
            markup.row(*buttons[:4])
            markup.row(*buttons[4:])
            markup.row(continue_button)
            return markup
        if keyb_type == 'journals':
            markup = types.InlineKeyboardMarkup()
            button_state = db.get_keyboard(user_id, keyb_type, req_type)
            print(button_state)
            lancet_button = types.InlineKeyboardButton(
                                    text='The Lancet',
                                    callback_data=f'lanc_sub_{button_state}')
            continue_button = types.InlineKeyboardButton(
                                    text='Continue',
                                    callback_data=f'cont_sub_journals')
            markup.row(lancet_button)
            markup.row(continue_button)
            return markup


def update_keyboard_markup(user_id, callback):
    callback = callback.split('_')
    if callback[0] == 'lanc':
        db.set_keyboard(user_id, 'journals',  callback[1], ['lanc_', int(callback[2])])


markup = generate_keyboard_markup('123', 'journals', 'sub')
update_keyboard_markup('123', 'lanc_sub_0')