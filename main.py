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
from collections import defaultdict, Counter
from pymongo.errors import ConnectionFailure
from pymongo import MongoClient
from datetime import datetime
import urllib.parse

# https://www.mongodb.com/languages/python

# brew tap mongodb/brew
# brew update
# brew install mongodb-community@4.2
# https://www.mongodb.com/docs/v4.2/tutorial/install-mongodb-on-os-x/

# # Creating a client
# client = MongoClient('localhost', 27020)
#
# # Creating a database name GFG
# db = client['GFG']
# print("Database is created !!")
# print(client.list_database_names())


load_dotenv()


class Baklava:
    AVALANCHE_RPC = "https://api.avax.network/ext/bc/C/rpc"
    CHAIN_ID = 43114
    # USB_LIQUIDITY_POOL_ADDRESS = "0xCC10F41Bf412839e651a32C42EFE497B9320fa76"
    USB_LIQUIDITY_POOL_ADDRESS = "0x1578D79ab9777f8f1B9A5fE8abd593835492f21A" # proxy
    # USB_SWAP_LOCKER_ADDRESS = "0x4e5138EbD881608EcB9769e5be61F0C6155417D7"
    USB_SWAP_LOCKER_ADDRESS = "0xD2c6e7892F3131e22d05E37E9B22bA79f8C74bA0" # proxy

    STABLE_COIN_ADDRESSES = {
        "USB": "0xc3fdd1652dD28b0b1D3401CC6fa50B4d8C45e7Ad",
        "USDC.e": "0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664",
        "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
    }

    def __init__(self):
        self.web3 = Web3(Web3.HTTPProvider(Baklava.AVALANCHE_RPC))
        self.USB_liquidity_pool_contract = self.create_USB_liquidity_pool_contract()
        self.USB_swap_locker_contract = self.create_USB_swap_locker_contract()
        self._non_vested_funds_total = Counter()
        self._vested_funds_total = Counter()
        self._stable_coin_distribution_schedule = dict()
        self._user_vesting_schedule = dict()
        self.time_last_refreshed = None
        # count of the tokens in $

        self._USDC_token_contract = self.create_USDC_token_contract()
        self._USDC_E_token_contract = self.create_USDC_E_token_contract()
        self.USDC_E_reserve = {Baklava.USB_LIQUIDITY_POOL_ADDRESS: 0, Baklava.USB_SWAP_LOCKER_ADDRESS: 0}
        self.USDC_reserve = {Baklava.USB_LIQUIDITY_POOL_ADDRESS: 0, Baklava.USB_SWAP_LOCKER_ADDRESS: 0}
        self.stable_coin_reserve = {"USDC.e": self.USDC_E_reserve, "USDC": self.USDC_reserve} # US dollars
        self.update_stable_coin_reserves()
        print("self._USDC_E_reserve", self.USDC_E_reserve)
        print("self._USDC_reserve", self.USDC_reserve)

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

    def create_USDC_token_contract(self):
        if not self.is_connected_to_avax_rpc:
            self.connect_to_avax_rpc()
        try:
            usdc_json = open("./ABI/usdc.json")
            usdc_json_loaded = json.load(usdc_json)
            usb_token_contract = self.web3.eth.contract(Baklava.STABLE_COIN_ADDRESSES["USDC"],
                                                                 abi=usdc_json_loaded)
            return usb_token_contract
        except Exception as e:
            print("Unable to access the USDC_contract")
            logging.error(e)

    def create_USDC_E_token_contract(self):
        if not self.is_connected_to_avax_rpc:
            self.connect_to_avax_rpc()
        try:
            usdc_e_json = open("./ABI/usdc_e.json")
            usdc_e_json_loaded = json.load(usdc_e_json)
            usdc_e_token_contract = self.web3.eth.contract(Baklava.STABLE_COIN_ADDRESSES["USDC.e"],
                                                                 abi=usdc_e_json_loaded)
            return usdc_e_token_contract
        except Exception as e:
            print("Unable to access the USDC_E_contract")
            logging.error(e)

    def create_USB_liquidity_pool_contract(self):
        if not self.is_connected_to_avax_rpc:
            self.connect_to_avax_rpc()
        try:
            usb_liquidity_json = open("./ABI/usb_liquidity_pool.json")
            usb_liquidity_json_loaded = json.load(usb_liquidity_json)
            usb_liquidity_pool_contract = self.web3.eth.contract(Baklava.USB_LIQUIDITY_POOL_ADDRESS,
                                                                 abi=usb_liquidity_json_loaded)
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
            usb_swap_locker_contract = self.web3.eth.contract(Baklava.USB_SWAP_LOCKER_ADDRESS,
                                                              abi=usb_swap_locker_json_loaded)
            return usb_swap_locker_contract
        except Exception as e:
            print("Unable to access the USB_swap_locker_contract")
            logging.error(e)

    def get_all_stable_coins(self):
        # Master_Farm_Contract.functions.poolLength().call()
        try:
            stable_coin_count = self.USB_liquidity_pool_contract.functions.getUSPeggedCoinsLength().call()
            stable_coin = dict()
            for stable_coin_index in range(stable_coin_count):
                address_stable_coin, vesting_days, swap_enabled = self.USB_liquidity_pool_contract.functions.getUSPeggedCoin(
                    stable_coin_index).call()
                # (addrress of stable coin, 21 days, boolean)
                stable_coin[address_stable_coin] = [vesting_days, swap_enabled]
            print(stable_coin)
            return stable_coin
        except Exception as e:
            logging.error(e)

    def get_user_address_list(self):
        # Master_Farm_Contract.functions.poolLength().call()
        try:
            all_stable_coins = self.get_all_stable_coins()
            user_addresses = dict()
            for stable_coin_address in all_stable_coins:
                user_addresses[stable_coin_address] = set(
                    self.USB_swap_locker_contract.functions.getUserAddressesList(stable_coin_address).call()
                )
            print(user_addresses)
            return user_addresses
        except Exception as e:
            logging.error(e)

    def _calculate_vesting_schedules(self):
        # {'0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664': {'0x4e3DA49cc22694D53F4a71e4d4BfdFB2BF272887', '...'}, ... }
        try:
            user_addresses = self.get_user_address_list()
            print(user_addresses)
            for stable_coin_address, unique_user_address in user_addresses.items():
                total_sum_for_a_coin = Counter()  # {date1: sum1, date2: sum2, ... }
                # Below always gives us a unique user address
                for user_address in unique_user_address:
                    # returns a list [(startTime, endTime, quantity, vestedQuantity), (), ...]
                    #    struct VestingSchedule {
                    #         uint64 startTime;
                    #         uint64 endTime;
                    #         uint128 quantity;
                    #         uint128 vestedQuantity;
                    #    }
                    print("stable_coin_address", stable_coin_address)
                    print('user_address', user_address)
                    schedules = self.USB_swap_locker_contract.functions.getVestingSchedules(user_address, stable_coin_address).call()
                    print("VestingSchedule", schedules)

                    ########## TEST #############
                    # stable_coin_address = "stable_coin_1"
                    # user_address = "user_address_1"
                    # schedules = [
                    #     (1, "1667316203", 10, 0),
                    #     (1, "1667316204", 10, 0),
                    #     (10, "1667402603", 100, 0),
                    #     (100, "1667402604", 1000, 0),
                    #     (1000, "1667575403", 10000, 0)
                    # ]
                    ########## TEST #############

                    self._process_vesting_schedules(total_sum_for_a_coin, stable_coin_address, user_address, schedules)
                self._stable_coin_distribution_schedule[stable_coin_address] = total_sum_for_a_coin
        except Exception as e:
            logging.error(e)

    def _process_vesting_schedules(self, total_sum_for_a_coin, stable_coin_address, user_address, vesting_schedules):

        if stable_coin_address not in self._user_vesting_schedule:
            self._user_vesting_schedule[stable_coin_address] = dict()

        self._user_vesting_schedule[stable_coin_address][user_address] = Counter()

        for start_time, end_time, quantity, vested_quantity in vesting_schedules:
            # start_time_number = int(start_time)
            # end_time_number = int(end_time)
            # quantity_number = int(quantity)
            # vested_quantity_number = int(vested_quantity)
            if vested_quantity == 0:
                end_time_formatted = datetime.utcfromtimestamp(end_time).strftime('%Y-%m-%d')
                total_sum_for_a_coin[end_time_formatted] += quantity
                self._non_vested_funds_total[stable_coin_address] += quantity
                self._user_vesting_schedule[stable_coin_address][user_address][end_time_formatted] += quantity
            elif quantity == vested_quantity:
                self._vested_funds_total[stable_coin_address] += vested_quantity

    def calculate_all_vesting_schedule_data(self):

        self._non_vested_funds_total = Counter()
        self._vested_funds_total = Counter()
        self._stable_coin_distribution_schedule = dict()
        self._user_vesting_schedule = dict()
        self._calculate_vesting_schedules()
        self.update_stable_coin_reserves()
        self.time_last_refreshed = datetime.now()

        print("self.__non_vested_funds_total:", self._non_vested_funds_total)
        print("self.__vested_funds_total:", self._vested_funds_total)
        print("self.__stable_coin_distribution_schedule:", self._stable_coin_distribution_schedule)
        print("self.__user_vesting_schedule", self._user_vesting_schedule)

        self._write_all_data_to_external_json()

    def _write_all_data_to_external_json(self):

        """Overwrites everything in the file due to "w" in the open command
        Also important to note that the name of the json corresponds to the name
        of the collections in the MongoDB"""


        with open("non_vested_funds_total.json", "w") as non_vested_funds:
            json.dump(self._non_vested_funds_total, non_vested_funds, indent=4)

        with open("vested_funds_total.json", "w") as vested_funds:
            json.dump(self._vested_funds_total, vested_funds, indent=4)

        with open("stable_coin_distribution.json", "w") as stable_coin_distribution:
            json.dump(self._stable_coin_distribution_schedule, stable_coin_distribution, indent=4)

        with open("user_vesting_schedule.json", "w") as user_vesting_schedule:
            json.dump(self._user_vesting_schedule, user_vesting_schedule, indent=4)

        with open("stable_coin_reserve.json", "w") as stable_coin_reserve:
            json.dump(self.stable_coin_reserve, stable_coin_reserve, indent=4)

    def update_stable_coin_reserves(self):
        """This calculates the amount of USDC/USDC.e tokens in the smart contracts"""
        if not self.is_connected_to_avax_rpc:
            self.connect_to_avax_rpc()
        try:
            USDC_balance_USB_pool = self._USDC_token_contract.functions.balanceOf(Baklava.USB_LIQUIDITY_POOL_ADDRESS).call()
            USDC_balance_swap_pool = self._USDC_token_contract.functions.balanceOf(Baklava.USB_SWAP_LOCKER_ADDRESS).call()
            USDC_E_balance_USB_pool = self._USDC_E_token_contract.functions.balanceOf(Baklava.USB_LIQUIDITY_POOL_ADDRESS).call()
            USDC_E_balance_swap_pool = self._USDC_E_token_contract.functions.balanceOf(Baklava.USB_SWAP_LOCKER_ADDRESS).call()
            self.USDC_reserve[Baklava.USB_LIQUIDITY_POOL_ADDRESS] = USDC_balance_USB_pool / 10**6
            self.USDC_reserve[Baklava.USB_SWAP_LOCKER_ADDRESS] = USDC_balance_swap_pool / 10**6
            self.USDC_E_reserve[Baklava.USB_LIQUIDITY_POOL_ADDRESS] = USDC_E_balance_USB_pool / 10**6
            self.USDC_E_reserve[Baklava.USB_SWAP_LOCKER_ADDRESS] = USDC_E_balance_swap_pool / 10**6
            self.stable_coin_reserve = {"USDC.e": self.USDC_E_reserve, "USDC": self.USDC_reserve}

        except Exception as e:
            print("Unable to calculate the balance of the stable coins")
            logging.error(e)

class MongoDB:
    USER_NAME = os.getenv("MONGODB_USERNAME")
    PASSWORD = os.getenv("MONGODB_PASSWORD")
    # below are the only collection names - corresponding to the json file names - this is a must
    MONGO_DB_COLLECTIONS = {
        "non_vested_funds_total",
        "stable_coin_distribution",
        "user_vesting_schedule",
        "vested_funds_total",
        "stable_coin_reserve"
    }

    def __init__(self):
        self.connection_string = (
                "mongodb+srv://" +
                MongoDB.USER_NAME +
                ":" +
                urllib.parse.quote(MongoDB.PASSWORD) +
                "@cluster0.9ibig9g.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
        )
        self.mongo_client = None

    def create_mongo_client(self):
        print("creating a mongo client")
        try:
            self.mongo_client = MongoClient(self.connection_string, tls=True, tlsAllowInvalidCertificates=True)
            self.mongo_client.server_info()
            print("Successfully created a mongo client")
            return True
        except ConnectionFailure as err:
            print("connection error has occurred")
            logging.error(err)
            return False
        except Exception as err:
            print("error occurred whilst creating a mongo client")
            logging.error(err)
            return False

    def check_client_connection(self):
        print("checking mongo client connection to the server")
        try:
            self.mongo_client.admin.command('ping')
            print("no issue with mongo client connection")
            return True
        except AttributeError:
            print("self.mongo_client is set to None")
            return False
        except ConnectionFailure:
            print("Mongo client not connected to the server")
            return False
        except Exception as err:
            print("error occurred whilst checking connection to mongo server")
            logging.error(err)
            return False

    def connect_and_get_database(self, database_name="Baklava"):
        while not self.check_client_connection():
            if not self.create_mongo_client():
                time.sleep(60)

        print("mongo client successfully created")

        try:
            database = self.mongo_client[database_name]  # create/get the "Baklava" database
            print("database successfully accessed")
            return database
        except ConnectionFailure as err:
            logging.error(err)
        except Exception as err:
            print(f"could not get the database {database_name}")
            logging.error(err)

    def update_database_add_collection(self, collection_name):

        if collection_name not in MongoDB.MONGO_DB_COLLECTIONS:
            raise ValueError("This collection is not defined in the class variable 'MONGO_DB_COLLECTIONS'")

        try:
            database_instance = self.connect_and_get_database()  # create and get the database
            collection = database_instance[collection_name]  # create collection named "....."
            with open(f"{collection_name}.json") as collection_data:
                collection_json_data = json.load(collection_data)
                collection.delete_many({})
                collection.insert_one(collection_json_data)
            print(f"{collection_name} collection added")
        except Exception as err:
            print(f"Was not able to update the mongodb database - collection: {collection_name}")
            logging.error(err)

    def update_database_add_all_collections(self):

        try:
            database_instance = self.connect_and_get_database()  # create and get the database
            for collection_name in MongoDB.MONGO_DB_COLLECTIONS:
                collection = database_instance[collection_name]  # get collection named "....."
                with open(f"{collection_name}.json") as collection_data:
                    collection_json_data = json.load(collection_data)
                    collection.delete_many({})
                    collection.insert_one(collection_json_data)
            print("all collections added")
        except Exception as err:
            print(f"Was not able to update the mongodb database - add all collections")
            logging.error(err)

    def update_database_delete_collection(self, collection_name):

        if collection_name not in MongoDB.MONGO_DB_COLLECTIONS:
            raise ValueError("This collection is not defined in the class variable 'MONGO_DB_COLLECTIONS'")

        try:
            database_instance = self.connect_and_get_database()  # create and get the database
            collection = database_instance[collection_name]
            collection.drop()
            print(f"{collection_name} collection deleted")
        except Exception as err:
            print(f"Was not able to update the mongodb database - drop collection {collection_name}")
            logging.error(err)

    def update_database_delete_all_collections(self):
        try:
            database_instance = self.connect_and_get_database()  # create and get the database
            for collection_name in MongoDB.MONGO_DB_COLLECTIONS:
                collection = database_instance[collection_name]  # create collection named "....."
                collection.drop()
            print("all collections deleted")
        except Exception as err:
            print(f"Was not able to update the mongodb database - delete all collections")
            logging.error(err)



    # def update_database_add_collection_stable_coin_distribution(self):
    #     database_instance = self.connect_and_get_database()  # create and get the database
    #     collection = database_instance["stable_coin_distribution"]  # create collection named "....."
    #
    #     with open("stable_coin_distribution.json") as stable_coin_distribution:
    #         stable_coin_distribution_data = json.load(stable_coin_distribution)
    #         collection.delete_many({})
    #         collection.insert_one(stable_coin_distribution_data)
    #
    # def update_database_add_collection_user_vesting_schedule(self):
    #     database_instance = self.connect_and_get_database()  # create and get the database
    #     collection = database_instance["user_vesting_schedule"]  # create collection named "....."
    #
    #     with open("user_vesting_schedule.json") as user_vesting_schedule:
    #         user_vesting_schedule_data = json.load(user_vesting_schedule)
    #         collection.delete_many({})
    #         collection.insert_one(user_vesting_schedule_data)
    #
    # def update_database_add_collection_vested_funds_total(self):
    #     database_instance = self.connect_and_get_database()  # create and get the database
    #     collection = database_instance["vested_funds_total"]  # create collection named "....."
    #
    #     with open("vested_funds_total.json") as vested_funds_total:
    #         vested_funds_total_data = json.load(vested_funds_total)
    #         collection.delete_many({})
    #         collection.insert_one(vested_funds_total_data)


try:
    with open('user_token_vesting.json', 'r+') as f:
        json_data = json.load(f)
        json_data['a']['b'].append(200)
        json_data['c'] = dict()
        json_data['c']['e'] = 2
        f.seek(0)
        f.write(json.dumps(json_data))
        f.truncate()
except Exception as e:
    logging.error(e)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    baklava = Baklava()
    baklava.calculate_all_vesting_schedule_data()


    m = MongoDB()
    db = m.connect_and_get_database()
    m.update_database_add_all_collections()




