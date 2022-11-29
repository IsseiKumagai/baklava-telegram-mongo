import json
import datetime
import os
import bisect
import math
import requests

# hostname = socket.gethostname()
# IPAddr = socket.gethostbyname(hostname)

# telegram bot ---
# TELEGRAM_TOKEN_ID = "5760680368:AAHLf-ZTdshgYLExYgiqrx60altD02k11Kg"  # token-id
# TELEGRAM_CHAT_ID = "5331052190" # chat-id
# # ----------------
#
# # parser = argparse.ArgumentParser(description='Notifier.')
# # parser.add_argument("--message", type=str, help='Message for the notifier.', default='hello from issei')
# # parser.add_argument("--token_id", type=str, help='Token ID for the chat bot.', default=TELEGRAM_TOKEN_ID)
# # parser.add_argument("--chat_id", type=str, help='Chat ID for the chat bot.', default=TELEGRAM_CHAT_ID)
# # parser.add_argument("--hostname", type=str, help='Name of the server running the task.', default=hostname)
# # parser.add_argument("--ip", type=str, help='IP address of the server running the task.', default=IPAddr)
#
# def main(text):
#
#     #args = parser.parse_args()
#     msg = text
#     # hostname = args.hostname
#     # ip = args.ip
#
#     # telegram bot:
#     token_id = TELEGRAM_TOKEN_ID
#     chat_id = TELEGRAM_CHAT_ID
#
#     # - - - - - - - - - -
#     # Telegram notification:
#     # msg = "Automatic message from host: '{hostname}', at: {ip}\n{separator}\n" \
#     #       "<b>MESSAGE: </b>\n<pre> {text} </pre>".format(separator=' -' * 10, text=text, hostname=hostname, ip=ip)
#
#     telegram_notifier.basic_notifier(logger_name='training_notifier',
#                                      token_id=token_id,
#                                      chat_id=chat_id,
#                                      message=msg,
#                                      level=logging.INFO)
# # just calls the `main` function above


STABLE_COIN_ADDRESSES = {
    "USDC.e": "0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664",
    "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
}


def send_to_telegram(message):

    apiToken = "5760680368:AAHLf-ZTdshgYLExYgiqrx60altD02k11Kg"
    chatID = "5331052190"
    apiURL = f'https://api.telegram.org/bot{apiToken}/sendMessage'

    try:
        response = requests.post(apiURL, json={'chat_id': chatID, 'text': message})
        print(response.text)
    except Exception as e:
        print(e)


def obtain_data_from_json_files():
    try:
        stable_coin_reserve = open("stable_coin_reserve.json")
        stable_coin_distribution = open("stable_coin_distribution.json")
        stable_coin_reserve_data = json.load(stable_coin_reserve)
        stable_coin_distribution_data = json.load(stable_coin_distribution)
        return True, stable_coin_reserve_data, stable_coin_distribution_data
    except Exception as e:
        print("Issue occurred whilst retrieving data from the json files", e)
        return False, None, None


def create_message_to_send():
    (file_successfully_loaded, stable_coin_reserve_data, stable_coin_distribution_data) = obtain_data_from_json_files()
    if file_successfully_loaded:
        try:
            total_sum_stable_coin = {
                key: sum(sum_in_contract for address, sum_in_contract in value.items())
                for key, value in stable_coin_reserve_data.items()
            }
            # will always return ==> {'USDC.e': 1618.385437, 'USDC': 1759.808441} or {'USDC.e': 0, 'USDC': 0}
            today_date = datetime.datetime.today()
            message_to_send = ""

            for day in range(0, 7):

                date_object = (today_date + datetime.timedelta(days=day)).date()
                new_date = str(date_object.strftime('%Y-%m-%d'))
                name_of_new_date = str(date_object.strftime('%A'))
                message_to_send += "\n" + "-------- " + new_date + " [" + name_of_new_date + "]" + " --------" + "\n"

                for stable_coin_name, stable_coin_address in STABLE_COIN_ADDRESSES.items():

                    amount_to_distribute_for_date = stable_coin_distribution_data["accumulative"][stable_coin_address]
                    # {
                    #     "2022-11-01": 999000,
                    #     "2022-12-07": 4995000
                    # }
                    # OR {} is returned

                    money_in_the_contract = total_sum_stable_coin[stable_coin_name]

                    if new_date in amount_to_distribute_for_date:
                        total_money_left = money_in_the_contract - amount_to_distribute_for_date[new_date]
                        if total_money_left < 0:
                            message_to_send += f"{stable_coin_name}: Please deposit => ${math.ceil(total_money_left * 100.0) / 100.0} \u274C \n"
                        else:
                            message_to_send += f"{stable_coin_name}: Enough Funds => ${math.ceil(money_in_the_contract * 100.0) / 100.0} \u2705 \n"
                    elif day == 0:  # first date we are looking at
                        # do a binary search and look for the previous date that is due
                        if stable_coin_address in stable_coin_distribution_data:
                            distribution_date_amount = stable_coin_distribution_data[stable_coin_address] # returns a list
                            #distribution_date_amount = [["2022-11-30", 10000000000], ["2023-11-11", 1], ["2023-11-12", 1], ["2023-12-11", 1], ["2023-12-12", 1]]
                            print(new_date)
                            index_date = bisect.bisect(distribution_date_amount, [new_date, 0])
                            if index_date == 0:
                                message_to_send += f"{stable_coin_name}: Enough funds => ${math.ceil(money_in_the_contract * 100.0) / 100.0} \u2705 \n"
                            else:
                                index_date -= 1
                                date_in_consideration = distribution_date_amount[index_date][0]
                                total_money_left = money_in_the_contract - (amount_to_distribute_for_date[date_in_consideration]) / 10**6
                                if total_money_left < 0:
                                    message_to_send += f"{stable_coin_name}: Please deposit => ${math.ceil(total_money_left * 100.0) / 100.0} \u274C \n"
                                    print(f"{stable_coin_name}: Please deposit => ${math.ceil(total_money_left * 100.0) / 100.0} \u274C \n")
                                else:
                                    message_to_send += f"{stable_coin_name}: Enough funds => ${math.ceil(money_in_the_contract * 100.0) / 100.0} \u2705 \n"
                        else:
                            message_to_send += f"{stable_coin_name}: Enough funds => ${math.ceil(money_in_the_contract * 100.0) / 100.0} \u2705 \n"
                    else:
                        message_to_send += f"{stable_coin_name}: Enough funds => ${math.ceil(money_in_the_contract * 100.0) / 100.0} \u2705 \n"
            return message_to_send
        except Exception as e:
            print("Issue occurred whilst processing data.", e)
            return "Issue occurred whilst processing data. Please troubleshoot the issue. \u274C"
    else:
        print("Json files were not successfully loaded.")
        return "Json files were not successfully loaded. \u274C"



if __name__ == '__main__':

    message = create_message_to_send()
    send_to_telegram(message)
