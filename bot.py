import os

import telebot
import openai

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

BOT_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)

chat_history = []

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Hey")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_message(message):
    print('ehy')
    chat_id = message.chat.id
    chat_history.append({"user": message.from_user.first_name, "message": message.text})
    print(str(chat_history))
   
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

        messages = chat_history[:-1]  # Exclude the last message (command message)
        summary = generate_summary(messages, num_messages)
        bot.send_message(chat_id, summary)

def generate_summary(messages, num_messages):
    history = str(messages[-num_messages:])
    prompt = """
    Your task is generate a summary of the chat history contained between the triple backticks in the same language the chat history is in.
    
    Chat history: ```%s```
    """ % (prompt)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    print(response)
    summary = response.choices[0].message.content
    return summary

bot.polling()