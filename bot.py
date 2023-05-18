import os

import mysql.connector
import telebot
import openai

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

BOT_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)

chat_history = []

BOT_DB_USER=os.environ.get('BOT_DB_USER')
BOT_DB_PASSWORD=os.environ.get('BOT_DB_PASSWORD')


@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Hey")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_message(message):
    chat_id = message.chat.id
    chat_history.append({"user": message.from_user.first_name, "message": message.text})

    if message.text.startswith('/summary'):
        command_parts = message.text.split()
        if len(command_parts) != 2:
            bot.reply_to(message, "Invalid command. Usage: /summary <num_messages>")
            return

        try:
            num_messages = int(command_parts[1])
        except ValueError:
            bot.reply_to(message, "Invalid number of messages. Please provide a valid integer.")
            return

        if num_messages <= 0:
            bot.reply_to(message, "Number of messages should be greater than zero.")
            return

        messages = get_chat_history(chat_id, num_messages)
        summary = generate_summary(messages)
        bot.send_message(chat_id, summary)
    else:
        store_message(chat_id, message.from_user.first_name, message.text)

def store_message(chat_id, user, message):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute('INSERT IGNORE INTO chats (chat_id) VALUES (%s)', (chat_id,))
    conn.commit()

    # Store the message in the "chat_history" table
    cursor.execute('''
        INSERT INTO chat_history (user, message, chat_id)
        VALUES (%s, %s, %s)
    ''', (user, message, chat_id))
    conn.commit()
    conn.close()

    history_size = get_chat_history_size(chat_id)
    conn = connect_to_db()
    cursor = conn.cursor()
    print(f"Chat history size: {history_size}")
    if history_size > 500:
        cursor.execute('''
        DELETE FROM chat_history
        WHERE chat_id = %s
        ORDER BY sent_on ASC
        LIMIT 1;
        ''', (chat_id,))
        conn.commit()
    conn.close()

def get_chat_history(chat_id, num_messages):
    conn = connect_to_db()
    cursor = conn.cursor()

    # Retrieve the last X messages for the given chat_id
    query = '''
        SELECT user, message
        FROM chat_history
        WHERE chat_id = %s
        ORDER BY id DESC
        LIMIT %s
    '''
    cursor.execute(query, (chat_id, num_messages))
    messages = cursor.fetchall()
    conn.close()
    return [{ "user": tpl[0], "message": tpl[1] } for tpl in messages[::-1]]

def get_chat_history_size(chat_id):
    conn = connect_to_db()
    cursor = conn.cursor()

    # Retrieve the last X messages for the given chat_id
    query = '''
        SELECT count(*) as row_count
        FROM chat_history
        WHERE chat_id = %s
    '''
    cursor.execute(query, (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0]

def generate_summary(messages):
    history = str(messages)
    language = find_language(history)
    prompt = f"""
    Your task is generate a summary of the chat history contained between the triple backticks.
    The summary should capture the key points and most relevant information discussed in the conversation.
    Write the summary in {language}

    Chat history: ```{history}```
    """
    summary = get_response(prompt)
    return summary

def find_language(history):
    prompt =  f"""
    Your task is to determine the main language that is used in the chat history that is contained
    between triple backticks. Look only at the "message" keys of the json object.
    If you find more than one languange only answer with the main one that is used.
    Your response will be a single word with the language name.
    ```{history}```
    """
    language = get_response(prompt)
    print(f"Language: {language}")
    return language


def get_response(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content


def connect_to_db():
    conn = mysql.connector.connect(
    host='adori30.mysql.pythonanywhere-services.com',
    user=BOT_DB_USER,
    password=BOT_DB_PASSWORD,
    database='adori30$telegram_summary_bot_db'
    )
    print("Connected to database")
    return conn

print("Bot is running")
bot.polling()