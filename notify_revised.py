import json
import datetime
import bisect
import math
import requests

STABLE_COIN_ADDRESSES = {
    "USDC.e": "0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664",
    "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
}
apiToken = "5760680368:AAHLf-ZTdshgYLExYgiqrx60altD02k11Kg"
chatID = "5331052190"
apiURL = f'https://api.telegram.org/bot{apiToken}/sendMessage'

def send_to_telegram(message):
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
            today_date_for_title = str(today_date.strftime('%Y-%m-%d'))
            date_object = (today_date + datetime.timedelta(days=6)).date() # today and 6 days into the future
            end_date = str(date_object.strftime('%Y-%m-%d'))
            name_of_new_date = str(date_object.strftime('%A'))
            message_to_send = "\U0001F4B0 Baklava Stable Coin Reserve \U0001F4B0"
            message_to_send += "\n" + "        " + today_date_for_title + " ~ " + end_date + "\n" + "\n"

            for stable_coin_name, stable_coin_address in STABLE_COIN_ADDRESSES.items():
                amount_to_distribute_for_date = stable_coin_distribution_data["accumulative"][stable_coin_address]
                # {
                #     "2022-11-01": 999000,
                #     "2022-12-07": 4995000
                # }
                # OR {} is returned
                money_in_the_contract = total_sum_stable_coin[stable_coin_name]
                if end_date in amount_to_distribute_for_date:
                    total_money_left = money_in_the_contract - amount_to_distribute_for_date[end_date]
                    if total_money_left < 0:
                        # 1 % more than required to count for floating numbers
                        message_to_send += f"{stable_coin_name}: Please deposit => ${math.ceil((total_money_left * -1) + 1)} \u274C \n"
                    else:
                        message_to_send += f"{stable_coin_name}: Funds remaining => ${math.ceil(total_money_left)} \u2705 \n"
                else:
                    # do a binary search and look for the previous date that is due
                    if stable_coin_address in stable_coin_distribution_data:
                        distribution_date_amount = stable_coin_distribution_data[stable_coin_address] # returns a list
                        # distribution_date_amount = [["2022-11-30", 10000000000], ["2023-11-11", 1], ["2023-11-12", 1], ["2023-12-11", 1], ["2023-12-12", 1]]
                        print(end_date)
                        index_date = bisect.bisect(distribution_date_amount, [end_date, 0])
                        if index_date == 0:
                            message_to_send += f"{stable_coin_name}: Funds remaining => ${math.ceil(money_in_the_contract)} \u2705 \n"
                        else:
                            index_date -= 1
                            date_in_consideration = distribution_date_amount[index_date][0]
                            # due to 6 decimals stable coin
                            total_money_left = money_in_the_contract - (amount_to_distribute_for_date[date_in_consideration]) / 10**6
                            if total_money_left < 0:
                                # 1 added because of floating numbers
                                message_to_send += f"{stable_coin_name}: Please deposit => ${math.ceil((total_money_left * -1) + 1)} \u274C \n"
                            else:
                                message_to_send += f"{stable_coin_name}: Funds remaining => ${math.ceil(total_money_left)} \u2705 \n"
                    else:
                        message_to_send += f"{stable_coin_name}: Funds remaining => ${math.ceil(money_in_the_contract)} \u2705 \n"

            return message_to_send

        except Exception as e:

            print("Issue occurred whilst processing data.", e)
            return "Issue occurred whilst processing data. Please troubleshoot the issue. \u274C"
    else:

        print("Json files were not successfully loaded.")
        return "Json files were not successfully loaded. \u274C"


def create_message_and_send_to_telegram():
    message = create_message_to_send()
    send_to_telegram(message)


if __name__ == '__main__':
    pass