# importing the required libraries and functions
import telegram

from telegram.ext.updater import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters

import requests
import logging
import datetime


# adding different functions to the bot
the_updater = Updater("5671359949:AAHRbJDjMPQbzPbJr1UPvUSfQZaODVlolhk", use_context=True)



def the_start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Hi, Welcome to the Baklava helper. Please write /help to see the commands available."
    )


def the_help(update: Update, context: CallbackContext):
    update.message.reply_text(
        """Available Commands :  
        /user_vesting_schdule
        /Stable_Coin_to_Send - How much stable coin to pay out today?
        """
    )


def stable_coin_distribution(update: Update, context: CallbackContext):
    try:
        response = requests.get("https://ap-southeast-1.aws.data.mongodb-api.com/app/baklava-psozi/endpoint/baklava")
        response_json = response.json()
        current_day = datetime.datetime.today().strftime('%Y-%m-%d')
        usd_per_day = response_json["AllData"]["stable_coin_distribution"]["stable_coin_1"]
        if current_day in usd_per_day:
            update.message.reply_text(f"{current_day} - USDC: ${usd_per_day[current_day]}")
            update.message.reply_text("USDC.e")
        else:
            update.message.reply_text(f"{current_day}: $0")
    except Exception as exception:
        print("Could not access the API endpoint from MongoDB")
        logging.error(exception)

def user_vesting_schdule(update: Update, context: CallbackContext):
    try:
        response = requests.get("https://ap-southeast-1.aws.data.mongodb-api.com/app/baklava-psozi/endpoint/baklava")
        response_json = response.json()
        current_day = datetime.datetime.today().strftime('%Y-%m-%d')
        usd_per_day = response_json["AllData"]["user_vesting_schedule"]["stable_coin_1"]
        update.message.reply_text(
            """Available Commands :  
            /USDC - coin1"""
        )
        if current_day in usd_per_day:
            update.message.reply_text(f"{current_day} - USDC: ${usd_per_day[current_day]}")
            update.message.reply_text("USDC.e")
        else:
            update.message.reply_text(f"{current_day}: $0")
    except Exception as exception:
        print("Could not access the API endpoint from MongoDB")
        logging.error(exception)



def unknownCommmand(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Sorry '%s' is an invalid command" % update.message.text
    )

def unknownText(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Unfortunately, the system cannot recognize you, you said '%s'" % update.message.text
    )

# adding the handler to handle the messages and commands
the_updater.dispatcher.add_handler(CommandHandler('start', the_start))
the_updater.dispatcher.add_handler(CommandHandler('user_vesting_schdule', user_vesting_schdule))
the_updater.dispatcher.add_handler(CommandHandler('help', the_help))
the_updater.dispatcher.add_handler(CommandHandler('Stable_Coin_to_Send', stable_coin_distribution))
the_updater.dispatcher.add_handler(MessageHandler(Filters.text, unknownCommmand))
# Filtering out unknown commands
the_updater.dispatcher.add_handler(MessageHandler(Filters.command, unknownCommmand))
# Filtering out unknown messages
the_updater.dispatcher.add_handler(MessageHandler(Filters.text, unknownText))
# running the bot
the_updater.start_polling()