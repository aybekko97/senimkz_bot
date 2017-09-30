
import json

from aiohttp import web
import ssl
import telebot
from telebot import types

import apiai_agent
from config import token, OPERATORS
from helper import get_distance, Message

step = {}
users = {}
replied = {}

bot = telebot.TeleBot(token)

WEBHOOK_HOST = '95.85.35.196'
WEBHOOK_PORT = 443  # 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr

WEBHOOK_SSL_CERT = './webhook_cert.pem'  # Path to the ssl certificate
WEBHOOK_SSL_PRIV = './webhook_pkey.pem'  # Path to the ssl private key


# Quick'n'dirty SSL certificate generation:
#
# openssl genrsa -out webhook_pkey.pem 2048
# openssl req -new -x509 -days 3650 -key webhook_pkey.pem -out webhook_cert.pem
#
# When asked for "Common Name (e.g. server FQDN or YOUR name)" you should reply
# with the same value in you put in WEBHOOK_HOST

WEBHOOK_URL_BASE = "https://{}:{}".format(WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/{}/".format(token)

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

# Load data

data = open('static/points.json', encoding='utf-8')
points = json.load(data)

for i in range(len(points)):
    points[i]['i'] = i

data = open('static/category.json', encoding='utf-8')
categories = json.load(data)


# Callback ids
callback_ctg1 = {}
callback_ctg2 = {}
r_callback_ctg1 = []
r_callback_ctg2 = []
i = 0
j = 0
for key in categories.keys():
    callback_ctg1[key] = i
    r_callback_ctg1.append(key)
    i += 1
    for subkey in categories[key]:
        callback_ctg2[subkey] = j
        r_callback_ctg2.append(subkey)
        j += 1

# Keyboards
categories_keyboard = {}
category_keyboard = types.InlineKeyboardMarkup()

for key in list(categories.keys()):
    if len(category_keyboard.keyboard) == 0 or len(category_keyboard.keyboard[-1]) == 2:
        category_keyboard.keyboard.append([])
    category_keyboard.keyboard[-1].append(types.InlineKeyboardButton(text=key, callback_data="f"+str(callback_ctg1[key])).to_dic())

    categories_keyboard[key] = types.InlineKeyboardMarkup()
    for skey in categories[key]:
        categories_keyboard[key].add(types.InlineKeyboardButton(text=skey, callback_data="s"+str(callback_ctg2[skey])))
    categories_keyboard[key].add(types.InlineKeyboardButton(text="Назад", callback_data="Назад"))


location_button = types.KeyboardButton(text="Send location", request_location=True)
keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
keyboard.add(location_button)


def in_step_handler(message):
    return step.get(message.chat.id, None) is not None


@bot.message_handler(func=lambda message: in_step_handler(message) is False, commands=['near'])
def get_nearest(message):
    if step.get(message.chat.id, None) is None:
        msg = bot.send_message(message.chat.id, text="Чтобы отправить свою геолокацию, нажмите кнопку внизу.",
                               reply_markup=keyboard, parse_mode="Markdown")
        step[message.chat.id] = 0
        bot.register_next_step_handler(msg, get_nearest)
        return
    elif step[message.chat.id] == 0:
        if message.location is None:
            msg = bot.send_message(message.chat.id,
                                   "*Вам нужно отправить текущую геолокацию.*",
                                   parse_mode="Markdown")
            bot.register_next_step_handler(msg, get_nearest)
            return

        sorted_points = sorted(points, key=lambda point: get_distance(message.location.longitude,
                                                                      message.location.latitude,
                                                                      point['longitude'],
                                                                      point['latitude']))

        inline_keyboard = types.InlineKeyboardMarkup()
        for point in sorted_points[:10]:
            inline_keyboard.add(types.InlineKeyboardButton(text="{0} - {1}".format(point['name'], point['category']),
                                                           callback_data=str(point['i'])))
        bot.send_message(message.chat.id, text="Отлично!", reply_markup=inline_keyboard)
        bot.send_message(message.chat.id, text="Вот список 10 ближайших точек Senim 📍",
                         reply_markup=types.ReplyKeyboardRemove())
        step[message.chat.id] = None


@bot.message_handler(func=lambda message: in_step_handler(message) is False, commands=['nearc'])
def get_nearest_ctg(message):
    if step.get(message.chat.id, None) is None:
        msg = bot.send_message(message.chat.id, text="Выберите, одну из категории.",
                               reply_markup=category_keyboard, parse_mode="Markdown")
        #step[message.chat.id] = 0
        #bot.register_next_step_handler(msg, get_nearest_ctg)
        return
    else:
        if message.location is None:
            msg = bot.send_message(message.chat.id,
                                   "*Вам нужно отправить текущую геолокацию.*",
                                   parse_mode="Markdown")
            bot.register_next_step_handler(msg, get_nearest_ctg)
            return

        new_points = []
        for point in points:
            if point['category'] == step[message.chat.id]:
                new_points.append(point)
        sorted_points = sorted(new_points, key=lambda point: get_distance(message.location.longitude,
                                                                          message.location.latitude,
                                                                          point['longitude'],
                                                                          point['latitude']))

        inline_keyboard = types.InlineKeyboardMarkup()
        for point in sorted_points[:10]:
            inline_keyboard.add(types.InlineKeyboardButton(text="{0} - {1}".format(point['name'], point['category']),
                                                           callback_data=str(point['i'])))
        bot.send_message(message.chat.id, text="Отлично!", reply_markup=inline_keyboard)
        bot.send_message(message.chat.id, text="Вот список 10 ближайших точек Senim по категории '%s' 📍" % step[message.chat.id],
                         reply_markup=types.ReplyKeyboardRemove())
        step[message.chat.id] = None


@bot.message_handler(func=lambda message: in_step_handler(message) is False, commands=['ask'])
def ask(message):
    if step.get(message.chat.id, None) is None:
        msg = bot.send_message(message.chat.id, text="Напишите свой вопрос, который хотите задать оператору.",
                               parse_mode="Markdown")
        step[message.chat.id] = 0
        bot.register_next_step_handler(msg, ask)
        return
    else:
        if message.from_user.username is None:
            for OPERATOR_CHAT_ID in OPERATORS:
                bot.send_message(OPERATOR_CHAT_ID, "User-{0} [{2}] задал вопрос:\n{1}".format(message.chat.id, message.text, message.message_id))
        else:
            for OPERATOR_CHAT_ID in OPERATORS:
                bot.send_message(OPERATOR_CHAT_ID, "@{0} [{2}]: {1}".format(message.from_user.username, message.text, message.message_id))
            users[message.from_user.username] = message.chat.id
        bot.send_message(message.chat.id, "Рахмет, ожидайте ответа оператора!")
        step[message.chat.id] = None


@bot.message_handler(func=lambda message: in_step_handler(message) is False, commands=['help'])
def help(message):
    bot.send_message(message.chat.id, "*Вы можете воспользоваться этими командами, \nчтобы:*\n\n"
                                      "[/near](tg://bot_command?command=near&bot=senimkz_bot) - получить список 10 ближайших точек Senim\n"
                                      "[/nearc](tg://bot_command?command=nearc&bot=senimkz_bot) - получить список 10 ближайших точек по категории\n"
                                      "[/ask](tg://bot_command?command=ask&bot=senimkz_bot) - задать вопрос оператору\n"
                                      "[/help](tg://bot_command?command=help&bot=senimkz_bot) - получить список команд бота и их описание\n"
                                      "[/about](tg://bot_command?command=about&bot=senimkz_bot) - Чтобы получить информацию о сервисе",parse_mode="Markdown")



@bot.message_handler(func=lambda message: in_step_handler(message) is False, commands=['start'])
def help(message):
    if message.from_user.first_name is not None:
        hello = "Здравствуйте, %s!\nПеред вами бот Senim. Я помогу вам найти наши  более быстро и удобно.\n\n" % message.from_user.first_name
    else:
        hello = "Здравствуйте!"
    bot.send_message(message.chat.id, hello + "*Вы можете воспользоваться этими командами, \nчтобы:*\n\n"
                                      "[/near](tg://bot_command?command=near&bot=senimkz_bot) - получить список 10 ближайших точек Senim\n"
                                      "[/nearc](tg://bot_command?command=nearc&bot=senimkz_bot) - получить список 10 ближайших точек по категории\n"
                                      "[/ask](tg://bot_command?command=ask&bot=senimkz_bot) - задать вопрос оператору\n"
                                      "[/help](tg://bot_command?command=help&bot=senimkz_bot) - получить список команд бота и их описание\n"
                                      "[/about](tg://bot_command?command=about&bot=senimkz_bot) - Чтобы получить информацию о сервисе",parse_mode="Markdown")


@bot.message_handler(func=lambda message: in_step_handler(message) is False, commands=['about'])
def about(message):
    bot.send_message(message.chat.id, "*О компании*\n\n"
                                      "Оператором программы лояльности Senim является ТОО «Казахстанский Дисконтный Центр». " 
                                      "Основная миссия компании – содействие развитию казахстанского бизнеса путем создания уникальной бизнес-среды, "
                                      "в которой все участники получают широкий спектр возможностей для развития своего бизнеса.\n\n"
                                      "[Подробнее](https://senim.kz/about.html)",
                     parse_mode="Markdown")


@bot.message_handler(func=lambda message: in_step_handler(message) is False, content_types=['text'])
def echo_message(message):
    if message.chat.id in OPERATORS:
        if message.reply_to_message is not None and (message.reply_to_message.text[0] == '@' or message.reply_to_message.text[:4] == 'User'):
            reply_text = message.reply_to_message.text
            dot_i = reply_text.index(' ')

            if reply_text[0] == '@':
                chat_id = users[reply_text[1:dot_i]]
            else:
                chat_id = int(reply_text[5:dot_i])

            message_id = int(reply_text[reply_text.index('[') + 1:reply_text.index(']')])
            if chat_id not in replied:
                replied[chat_id] = {}

            if replied[chat_id].get(message_id, None) is None:
                try:
                    bot.reply_to(Message(chat=bot.get_chat(chat_id), message_id=message_id),
                                 "Ответ оператора: %s" % message.text)
                except:
                    bot.send_message(chat_id, "Вопрос: {0}\nОтвет оператора: {1}".format(reply_text[reply_text.index(']')+1:], message.text))
                replied[chat_id][message_id] = True
            else:
                bot.reply_to(message, "Спасибо за ответ! Но, на этот вопрос уже ответил другой оператор.")
            return

    try:
        bot.reply_to(message, apiai_agent.get_response(message.text))
    except Exception as e:
        bot.reply_to(message, 'Что-то пошло не так.')


# @bot.message_handler(func=lambda message: in_step_handler(message) is False, content_types=['voice'])
# def echo_message(message):
#     file_info = bot.get_file(message.voice.file_id)
#     file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(token, file_info.file_path))
#     bot.reply_to(message, apiai_agent.get_response_voice(file))

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        if call.data.isdigit():
            bot.send_location(call.message.chat.id, points[int(call.data)]['latitude'], points[int(call.data)]['longitude'])
        else:
            if call.data == "Назад":
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=category_keyboard)

            else:
                if call.data[0] == 'f':
                    category_name = r_callback_ctg1[int(call.data[1:])]
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                                  reply_markup=categories_keyboard[category_name])
                else:
                    msg = bot.send_message(call.message.chat.id,
                                           text="Чтобы отправить свою геолокацию, нажмите кнопку внизу.",
                                           reply_markup=keyboard, parse_mode="Markdown")
                    step[call.message.chat.id] = r_callback_ctg2[int(call.data[1:])]
                    bot.register_next_step_handler(msg, get_nearest_ctg)


bot.skip_pending = True
#bot.polling(none_stop=True)


# Remove webhook, it fails sometimes the set if there is a previous webhook
bot.remove_webhook()

# Set webhook
bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))

# Build ssl context
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)

# Start aiohttp server
web.run_app(
    app,
    host=WEBHOOK_LISTEN,
    port=WEBHOOK_PORT,
    ssl_context=context,
)
