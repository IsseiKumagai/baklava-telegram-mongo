
import telegram_notifier
import logging
import argparse
import socket
import json
import datetime
import os

hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)

# telegram bot ---
TELEGRAM_TOKEN_ID = "5760680368:AAHLf-ZTdshgYLExYgiqrx60altD02k11Kg"  # token-id
TELEGRAM_CHAT_ID = "5331052190" # chat-id
# ----------------

parser = argparse.ArgumentParser(description='Notifier.')
parser.add_argument("--message", type=str, help='Message for the notifier.', default='hello from issei')
parser.add_argument("--token_id", type=str, help='Token ID for the chat bot.', default=TELEGRAM_TOKEN_ID)
parser.add_argument("--chat_id", type=str, help='Chat ID for the chat bot.', default=TELEGRAM_CHAT_ID)
parser.add_argument("--hostname", type=str, help='Name of the server running the task.', default=hostname)
parser.add_argument("--ip", type=str, help='IP address of the server running the task.', default=IPAddr)

def main(text):

    args = parser.parse_args()
    text = text
    hostname = args.hostname
    ip = args.ip

    # telegram bot:
    token_id = TELEGRAM_TOKEN_ID
    chat_id = TELEGRAM_CHAT_ID

    # - - - - - - - - - -
    # Telegram notification:
    # msg = "Automatic message from host: '{hostname}', at: {ip}\n{separator}\n" \
    #       "<b>MESSAGE: </b>\n<pre> {text} </pre>".format(separator=' -' * 10, text=text, hostname=hostname, ip=ip)
    msg = text
    telegram_notifier.basic_notifier(logger_name='training_notifier',
                                     token_id=token_id,
                                     chat_id=chat_id,
                                     message=msg,
                                     level=logging.INFO)
# just calls the `main` function above


if __name__ == '__main__':

    STABLE_COIN_ADDRESSES = {
        "USDC.e": "0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664",
        "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
    }
    stable_coin_reserve = open("stable_coin_reserve.json")
    stable_coin_distribution = open("stable_coin_distribution.json")
    stable_coin_reserve_data = json.load(stable_coin_reserve)
    stable_coin_distribution_data = json.load(stable_coin_distribution)
    total_sum_stable_coin = {key: sum(sum_in_contract for address, sum_in_contract in value.items()) for key, value in stable_coin_reserve_data.items()}
    today_date = datetime.datetime.today()

    message_to_send = ""

    for day in range(0, 5):
        new_date = (today_date + datetime.timedelta(days=day)).date().strftime('%Y-%m-%d')
        message_to_send += "\n" + "----------" + new_date + "----------" + "\n"
        print(message_to_send)
        for stable_coin_name, stable_coin_address in STABLE_COIN_ADDRESSES.items():
            amount_to_distribute_for_date = stable_coin_distribution_data["accumulative"][stable_coin_address]
            if new_date in amount_to_distribute_for_date:
                total_money_left = total_sum_stable_coin[stable_coin_name] - amount_to_distribute_for_date[new_date]
                if total_money_left < 0:
                    message_to_send += f"{stable_coin_name}: ${total_money_left * -1}\n"
                else:
                    message_to_send += f"{stable_coin_name}: Enough funds available\n"
            else:
                message_to_send += f"{stable_coin_name}: Enough funds available\n"

        print(message_to_send)

    main(message_to_send)
