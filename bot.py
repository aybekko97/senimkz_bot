import json

import telebot
from telebot import types

from config import token
from helper import get_distance

step = {}

bot = telebot.TeleBot(token)

data = open('static/points.json')
points = json.load(data)

print(len(points))

location_button = types.KeyboardButton(text="Send location", request_location=True)
keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
keyboard.add(location_button)

@bot.message_handler(func=lambda message: True, commands=['near'])
def get_nearests(message):
    if step.get(message.chat.id, None) is None:
        msg = bot.send_message(message.chat.id, text="Чтобы отправить свою геолокацию, нажмите кнопку внизу.", reply_markup=keyboard, parse_mode="Markdown")
        step[message.chat.id] = 0
        bot.register_next_step_handler(msg, get_nearests)
    else:
        if message.location is None:
            msg = bot.send_message(message.chat.id,
                                   "*Вам нужно отправить текущую геолокацию.*",
                                   parse_mode="Markdown")
            bot.register_next_step_handler(msg, get_nearests)

        #bot.send_chat_action(message.chat.id, "ищу ближайшие точки")
        sorted_points = sorted(points, key=lambda point: get_distance(message.location.longitude,
                                                      message.location.latitude,
                                                      point['longitude'],
                                                      point['latitude']))

        inline_keyboard = types.InlineKeyboardMarkup()
        for point in sorted_points[:10]:
            inline_keyboard.add(types.InlineKeyboardButton(text="{0} - {1}".format(point['name'], point['category']),
                                                           callback_data=str(point['id'])))
        bot.send_message(message.chat.id, text="Отлично!", reply_markup=inline_keyboard)
        bot.send_message(message.chat.id, text="Вот список 10 ближайших точек Senim 📍", reply_markup=types.ReplyKeyboardRemove())
        step[message.chat.id] = None

@bot.message_handler(func=lambda message: True, commands=['nearc'])
def get_nearests_ctg(message):
    if step.get(message.chat.id, None) is None:
        msg = bot.send_message(message.chat.id, text="Чтобы отправить свою геолокацию, нажмите кнопку внизу.", reply_markup=keyboard, parse_mode="Markdown")
        step[message.chat.id] = 0
        bot.register_next_step_handler(msg, get_nearests)
    else:
        if message.location is None:
            msg = bot.send_message(message.chat.id,
                                   "*Вам нужно отправить текущую геолокацию.*",
                                   parse_mode="Markdown")
            bot.register_next_step_handler(msg, get_nearests)

        #bot.send_chat_action(message.chat.id, "ищу ближайшие точки")
        sorted_points = sorted(points, key=lambda point: get_distance(message.location.longitude,
                                                      message.location.latitude,
                                                      point['longitude'],
                                                      point['latitude']))

        inline_keyboard = types.InlineKeyboardMarkup()
        for point in sorted_points[:10]:
            inline_keyboard.add(types.InlineKeyboardButton(text="{0} - {1}".format(point['name'], point['category']),
                                                           callback_data=str(point['id'])))
        bot.send_message(message.chat.id, text="Отлично!", reply_markup=inline_keyboard)
        bot.send_message(message.chat.id, text="Вот список 10 ближайших точек Senim 📍", reply_markup=types.ReplyKeyboardRemove())
        step[message.chat.id] = None

@bot.message_handler(func=lambda message: True, commands=['ask'])
def ask(message):
    pass

@bot.message_handler(func=lambda message: True, commands=['help'])
def help(message):
    pass

@bot.message_handler(func=lambda message: True, commands=['about'])
def about(message):
    pass


@bot.message_handler(func=lambda message: True, content_types=['text'])
def echo_message(message):
    bot.reply_to(message,message.text)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        print(call.data)


bot.polling(none_stop=True)

'''
/near - Присылать 10 ближайших точек Senim. Приветствуется использование алгоритма нахождения короткого пути при помощи Яндекс/Google карт.
/nearc - Выбрать категорию и присылать ближайшие 10 точек по данной категории. Приветствуется использование алгоритма нахождения короткого пути при помощи Яндекс/Google карт.
/ask - Задать вопрос в службу поддержки. Данный вопрос автоматически должен отправиться на другой номер телефона, у которого есть телеграмм. Другой номер телефона отправляет может отправлять ответ на заданные вопросы.
/help - выдает список команд бота и их описание
/about - выдает информацию о сервисе. Взять на senim.kz
Входные данные:
Название, координаты, категория продавцов в формате JSON. Файл points.json
Выходные данные:
/near - Присылать 10 ближайших точек Senim. 
/nearc - Выбрать категорию и присылать ближайшие 10 точек по данной категории. 
/ask - ответ от оператора
/help - список команд бота и их описание
/about - информация о сервисе.

'''