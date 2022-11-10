import json
import web3
from web3 import Web3
from web3.logs import STRICT, IGNORE, DISCARD, WARN
import time
import os
from dotenv import load_dotenv
import logging
import schedule
import requests
import random
from collections import defaultdict
from pymongo import MongoClient
#brew tap mongodb/brew
#brew update
#brew install mongodb-community@4.2
#https://www.mongodb.com/docs/v4.2/tutorial/install-mongodb-on-os-x/

# Creating a client
client = MongoClient('localhost', 27020)

# Creating a database name GFG
db = client['GFG']
print("Database is created !!")
print(client.list_database_names())


class Baklava:

    AVALANCHE_RPC = "https://api.avax.network/ext/bc/C/rpc"
    CHAIN_ID = 43114
    # USB_LIQUIDITY_POOL_ADDRESS = "0xCC10F41Bf412839e651a32C42EFE497B9320fa76"
    USB_LIQUIDITY_POOL_ADDRESS = "0x1578D79ab9777f8f1B9A5fE8abd593835492f21A"
    # USB_SWAP_LOCKER_ADDRESS = "0x4e5138EbD881608EcB9769e5be61F0C6155417D7"
    USB_SWAP_LOCKER_ADDRESS = "0xD2c6e7892F3131e22d05E37E9B22bA79f8C74bA0"

    STABLE_COIN_ADDRESSES = {
        "USB": "0xc3fdd1652dD28b0b1D3401CC6fa50B4d8C45e7Ad",
        "USDC.e": "0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664",
        "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
    }

    def __init__(self):
        self.web3 = Web3(Web3.HTTPProvider(Baklava.AVALANCHE_RPC))
        self.USB_liquidity_pool_contract = self.create_USB_liquidity_pool_contract()
        self.USB_swap_locker_contract = self.create_USB_swap_locker_contract()

    def is_connected_to_avax_rpc(self):
        return self.web3.isConnected()

    def connect_to_avax_rpc(self):
        try:
            while not self.is_connected_to_avax_rpc():
                self.web3 = Web3(Web3.HTTPProvider(Baklava.AVALANCHE_RPC))
                time.sleep(30)
        except Exception as e:
            print("Unable to connect to the avax rpc endpoint")
            logging.error(e)

    def create_USB_liquidity_pool_contract(self):
        if not self.is_connected_to_avax_rpc:
            self.connect_to_avax_rpc()
        try:
            usb_liquidity_json = open("./ABI/usb_liquidity_pool.json")
            usb_liquidity_json_loaded = json.load(usb_liquidity_json)
            usb_liquidity_pool_contract = self.web3.eth.contract(Baklava.USB_LIQUIDITY_POOL_ADDRESS, abi=usb_liquidity_json_loaded)
            return usb_liquidity_pool_contract
        except Exception as e:
            print("Unable to access the USB_liquidity_pool_contract")
            logging.error(e)

    def create_USB_swap_locker_contract(self):
        if not self.is_connected_to_avax_rpc:
            self.connect_to_avax_rpc()
        try:
            usb_swap_locker_json = open("./ABI/usb_swap_locker.json")
            usb_swap_locker_json_loaded = json.load(usb_swap_locker_json)
            usb_swap_locker_contract = self.web3.eth.contract(Baklava.USB_SWAP_LOCKER_ADDRESS, abi=usb_swap_locker_json_loaded)
            return usb_swap_locker_contract
        except Exception as e:
            print("Unable to access the USB_swap_locker_contract")
            logging.error(e)

    def get_all_stable_coins(self):
        #Master_Farm_Contract.functions.poolLength().call()
        try:
            stable_coin_count = self.USB_liquidity_pool_contract.functions.getUSPeggedCoinsLength().call()
            stable_coin = dict()
            for stable_coin_index in range(stable_coin_count):
                address_stable_coin, vesting_days, swap_enabled = self.USB_liquidity_pool_contract.functions.getUSPeggedCoin(stable_coin_index).call()
                # (addrress of stable coin, 21 days, boolean)
                stable_coin[address_stable_coin] = [vesting_days, swap_enabled]
            #print(stable_coin)
            return stable_coin
        except Exception as e:
            logging.error(e)

    def get_user_address_list(self):
        #Master_Farm_Contract.functions.poolLength().call()
        try:
            all_stable_coins = self.get_all_stable_coins()
            user_addresses = dict()
            for stable_coin_address in all_stable_coins:
                user_addresses[stable_coin_address] = set(
                    self.USB_swap_locker_contract.functions.getUserAddressesList(stable_coin_address).call()
                )
            #print(user_addresses)
            return user_addresses
        except Exception as e:
            logging.error(e)

    def get_vesting_schedules(self):
        # {'0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664': {'0x4e3DA49cc22694D53F4a71e4d4BfdFB2BF272887', '...'}, ... }
        try:
            user_addresses = self.get_user_address_list()
            print(user_addresses)
            user_vesting_schedule = defaultdict(dict)
            for stable_coin_address, user_address_list in user_addresses.items():
                for user_address in user_address_list:
                    # returns a list [(startTime, endTime, quantity, vestedQuantity), (), ...]
                    #    struct VestingSchedule {
                    #         uint64 startTime;
                    #         uint64 endTime;
                    #         uint128 quantity;
                    #         uint128 vestedQuantity;
                    #    }
                    schedules = self.USB_swap_locker_contract.functions.getVestingSchedules(stable_coin_address, user_address).call()
                    schedules_updated = [
                        [int(start_time), int(end_time), int(quantity), int(vested_quantity)]
                        for start_time, end_time, quantity, vested_quantity in schedules
                        if int(end_time) > time.time() and int(vested_quantity) == 0
                    ] # for a specific user address and stable coin
                    user_vesting_schedule[stable_coin_address][user_address] = schedules_updated
            #print(user_vesting_schedule)
            return user_vesting_schedule
        except Exception as e:
            logging.error(e)

    def create_external_json_vesting_schedules(self):
        user_vesting_schedule = self.get_vesting_schedules()
        print(user_vesting_schedule)
        with open("all_data.json", "w") as tvl_file:
            json.dump(user_vesting_schedule, tvl_file, indent=4)

class MongoDB:

    def __init__(self):
        try:
            self.db_client = pymongo.MongoClient("mongodb://localhost:2707/")
            self.db = self.db_client["mydatabase"]
            print(self.db_client.list_database_names())
        except Exception as e:
            logging.error(e)

    def connect_to_local_mongo_server(self):
        pass




# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    baklava = Baklava()
    print(baklava.create_external_json_vesting_schedules())
    m = MongoDB()
    print(m.db)
    print(m.db_client.server_info())





# See PyCharm help at https://www.jetbrains.com/help/pycharm/
