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

class Baklava:

    AVALANCHE_RPC = "https://api.avax.network/ext/bc/C/rpc"
    CHAIN_ID = 43114
    # USB_LIQUIDITY_POOL_ADDRESS = "0xCC10F41Bf412839e651a32C42EFE497B9320fa76"
    USB_LIQUIDITY_POOL_ADDRESS = "0x1578D79ab9777f8f1B9A5fE8abd593835492f21A"
    # USB_SWAP_LOCKER_ADDRESS = "0x4e5138EbD881608EcB9769e5be61F0C6155417D7"
    USB_SWAP_LOCKER_ADDRESS = "0xD2c6e7892F3131e22d05E37E9B22bA79f8C74bA0"

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
                time.sleep(60)
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
            print(usb_liquidity_pool_contract.functions.getSystemCoin().call())
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
            print(usb_swap_locker_contract.functions.owner().call())
            return usb_swap_locker_contract
        except Exception as e:
            print("Unable to access the USB_swap_locker_contract")
            logging.error(e)









# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    baklava = Baklava()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
