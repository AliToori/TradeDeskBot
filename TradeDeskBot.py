#!/usr/bin/env python3
"""
    *******************************************************************************************
    TradeDeskBot: A TradeDesk Ticket Checkout Bot
    Developer: Ali Toori, Full-Stack Python Developer
    Founder: https://boteaz.com/
    *******************************************************************************************
"""
import os
import pickle
import re
import json
import random
import logging.config
import threading
import time
from time import sleep
import pandas as pd
import requests
import pyfiglet
import ntplib
from datetime import datetime
from pathlib import Path
from multiprocessing import freeze_support
import concurrent.futures
from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory, PNOperationType
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

pnconfig = PNConfiguration()

pnconfig.subscribe_key = 'sub-06059d87-ebbe-11e1-8247-37c456d16340'
pnconfig.publish_key = 'pub-f59b296a-9c78-45fc-b592-d5e6f9e839b4'
pnconfig.user_id = "Channel-TradeDeskBot"
pubnub = PubNub(pnconfig)
PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))


# Publishes a message to a pubnub channel with channel name
def my_publish_callback(envelope, status):
    # Check whether request successfully completed or not
    if not status.is_error():
        pass  # Message successfully published to specified channel.
    else:
        pass  # Handle message publish error. Check 'category' property to find out possible issue
        # because of which request did fail.
        # Request can be resent using: [status retry];


# Event listener to subscribe to the channel events
class EventURLHandler(SubscribeCallback):

    def presence(self, pubnub, presence):
        pass  # handle incoming presence data

    def status(self, pubnub, status):
        if status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            pass  # This event happens when radio / connectivity is lost

        elif status.category == PNStatusCategory.PNConnectedCategory:
            # Connect event. You can do stuff like publish, and know you'll get it.
            # Or just use the connected event to confirm you are subscribed for
            # UI / internal notifications, etc
            # pubnub.publish().channel('Channel-Machine2').message('Ali pubnub publisher test!').pn_async(my_publish_callback)
            pass
        elif status.category == PNStatusCategory.PNReconnectedCategory:
            pass
            # Happens as part of our regular operation. This event happens when
            # radio / connectivity is lost, then regained.
        elif status.category == PNStatusCategory.PNDecryptionErrorCategory:
            pass
            # Handle message decryption error. Probably client configured to
            # encrypt messages and on live data feed it received plain text.

    def message(self, pubnub, message):
        file_event_urls = PROJECT_ROOT / 'BotRes/EventURLs.csv'
        # Handle new message stored in message.message
        # Get EventURLs from the dictionary format: {'purchaseURLs': [], 'instances': 1}
        if "purchaseURLs" in message.message:
            event_url = message.message["purchaseURLs"][0]
            data_dict = {"EventURL": event_url, "Processed": "No"}
            # self.LOGGER.info(data_dict)
            df = pd.DataFrame([data_dict])
            # if file does not exist write headers
            if not os.path.isfile(file_event_urls):
                df.to_csv(file_event_urls, index=False)
            else:  # else if exists, append without writing the headers
                df.to_csv(file_event_urls, mode='a', header=False, index=False)
            # self.LOGGER.info(f'EVentURL saved successfully')


# Main TradeDeskBot class
class TradeDeskBot:
    def __init__(self):
        self.PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
        self.file_settings = str(self.PROJECT_ROOT / 'BotRes/Settings.json')
        self.file_event_urls = self.PROJECT_ROOT / 'BotRes/EventURLs.csv'
        # self.proxies = self.get_proxies()
        self.user_agents = self.get_user_agents()
        self.settings = self.get_settings()
        self.LOGGER = self.get_logger()
        self.logged_in = False
        self.driver = None

    # Loads LOGGER
    @staticmethod
    def get_logger():
        """
        Get logger file handler
        :return: LOGGER
        """
        logging.config.dictConfig({
            "version": 1,
            "disable_existing_loggers": False,
            'formatters': {
                'colored': {
                    '()': 'colorlog.ColoredFormatter',  # colored output
                    # --> %(log_color)s is very important, that's what colors the line
                    'format': '[%(asctime)s,%(lineno)s] %(log_color)s[%(message)s]',
                    'log_colors': {
                        'DEBUG': 'green',
                        'INFO': 'cyan',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'bold_red',
                    },
                },
                'simple': {
                    'format': '[%(asctime)s,%(lineno)s] [%(message)s]',
                },
            },
            "handlers": {
                "console": {
                    "class": "colorlog.StreamHandler",
                    "level": "INFO",
                    "formatter": "colored",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "simple",
                    "filename": "TradeDeskBot.log",
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 1
                },
            },
            "root": {"level": "INFO",
                     "handlers": ["console", "file"]
                     }
        })
        return logging.getLogger()

    # Enables CMD color
    @staticmethod
    def enable_cmd_colors():
        # Enables Windows New ANSI Support for Colored Printing on CMD
        from sys import platform
        if platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    # Prints ASCII Art Banner
    @staticmethod
    def banner():
        pyfiglet.print_figlet(text='____________ TradeDeskBot\n', colors='RED')
        print('TradeDeskBot: A TradeDesk Ticket Checkout Bot\n'
              'Developer: Ali Toori, Full-Stack Python Developer\n'
              'Founder: https://boteaz.com/\n'
              '************************************************************************')

    # Trial version logic
    @staticmethod
    def trial(trial_date):
        ntp_client = ntplib.NTPClient()
        try:
            response = ntp_client.request('pool.ntp.org')
            local_time = time.localtime(response.ref_time)
            current_date = time.strftime('%Y-%m-%d %H:%M:%S', local_time)
            current_date = datetime.strptime(current_date, '%Y-%m-%d %H:%M:%S')
            return trial_date > current_date
        except:
            return False

    # Loads Setting from local file
    def get_settings(self):
        """
        Creates default or loads existing settings file.
        :return: settings
        """
        if os.path.isfile(self.file_settings):
            with open(self.file_settings, 'r') as f:
                settings = json.load(f)
            return settings
        settings = {"Settings": {
            "Email": "Enter Your Email ID"
        }}
        with open(self.file_settings, 'w') as f:
            json.dump(settings, f, indent=4)
        with open(self.file_settings, 'r') as f:
            settings = json.load(f)
        return settings

    # Loads event URL
    def get_event_url_txt(self):
        file_proxies = str(self.PROJECT_ROOT / 'BotRes/EventURL.txt')
        with open(file_proxies) as f:
            content = f.readlines()
        return [x.strip() for x in content]

    # Loads proxies
    def get_proxies(self):
        file_proxies = str(self.PROJECT_ROOT / 'BotRes/proxies.txt')
        with open(file_proxies) as f:
            content = f.readlines()
        return [x.strip() for x in content]

    # Loads user agents
    def get_user_agents(self):
        file_uagents = str(self.PROJECT_ROOT / 'BotRes/user_agents.txt')
        with open(file_uagents) as f:
            content = f.readlines()
        return [x.strip() for x in content]

    # Get web driver
    def get_driver(self, proxy=False, headless=False):
        driver_bin = str(self.PROJECT_ROOT / "BotRes/bin/chromedriver.exe")
        service = Service(executable_path=driver_bin)
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        prefs = {"directory_upgrade": True,
                 "credentials_enable_service": False,
                 "profile.password_manager_enabled": False,
                 "profile.default_content_settings.popups": False,
                 "profile.managed_default_content_settings.images": 2,
                 # f"download.default_directory": f"{self.directory_downloads}",
                 "profile.default_content_setting_values.geolocation": 2
                 }
        options.add_experimental_option("prefs", prefs)
        options.add_argument(F'--user-agent={random.choice(self.user_agents)}')
        if proxy:
            options.add_argument(f"--proxy-server={self.get_proxy()}")
        if headless:
            options.add_argument('--headless')
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    # Waits until an element is present on the DOM
    @staticmethod
    def wait_until_present(driver, css_selector=None, element_id=None, name=None, class_name=None, tag_name=None, duration=10000, frequency=0.01):
        if css_selector:
            WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
        elif element_id:
            WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.ID, element_id)))
        elif name:
            WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.NAME, name)))
        elif class_name:
            WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))
        elif tag_name:
            WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.TAG_NAME, tag_name)))

    # Waits until an element is visible on the DOM
    @staticmethod
    def wait_until_visible(driver, css_selector=None, element_id=None, name=None, class_name=None, tag_name=None, duration=10000, frequency=0.01):
        if css_selector:
            WebDriverWait(driver, duration, frequency).until( EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
        elif element_id:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.ID, element_id)))
        elif name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.NAME, name)))
        elif class_name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.CLASS_NAME, class_name)))
        elif tag_name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.TAG_NAME, tag_name)))

    # Gets you sign-in to the website
    def login_trade_desk(self, driver, email_id, password):
        self.LOGGER.info(f"Signing in to the website")
        base_url = "https://tradedesk.ticketmaster.com/"
        # Try to sign-in with saved cookies from previous session
        cookies = 'cookies_' + email_id + '.pkl'
        file_path_cookies = self.PROJECT_ROOT / 'BotRes' / cookies
        driver.get(base_url)
        # if os.path.isfile(file_path_cookies):
        #     self.LOGGER.info(f"Loading cookies for: {email_id}")
        #     with open(file_path_cookies, 'rb') as cookies_file:
        #         cookies = pickle.load(cookies_file)
        #         for cookie in cookies:
        #             driver.add_cookie(cookie)
        #     try:
        #         self.LOGGER.info(f"Waiting for profile")
        #         driver.refresh()
        #         # Wait for Upload button to confirm that we are logged-in
        #         self.wait_until_visible(driver=driver, css_selector='[id="tmp_header_menu_left"]', duration=3)
        #         self.LOGGER.info(f"Cookies login successful")
        #         return True
        #     except:
        #         self.LOGGER.info(f"Cookies login failed")
        #         os.remove(file_path_cookies)

        # Signing-in using Email or Username
        try:
            self.LOGGER.info(f"Signing in using email id")
            self.wait_until_visible(driver=driver, css_selector='[name="username"]')
            # Filling signup fields
            self.LOGGER.info(f"Filling username")
            driver.find_element(By.CSS_SELECTOR, '[name="username"]').send_keys(email_id)
            self.LOGGER.info(f"Filling password")
            driver.find_element(By.CSS_SELECTOR, '[name="password"]').send_keys(password)
        except:
            self.LOGGER.info(f"Error while filling username and password")
            pass

        # Submitting sign-in form
        try:
            self.LOGGER.info(f"Submitting form")
            # Clicking button signin
            self.wait_until_visible(driver=driver, css_selector='[class="header_signup"]')
            driver.find_element(By.CSS_SELECTOR, '[class="header_signup"]').click()
        except:
            self.LOGGER.info(f"Error while submitting sign-in form")
            pass
        try:
            self.LOGGER.info(f"Waiting for profile")
            driver.get(base_url)
            # Wait for Upload button to confirm that we are logged-in
            self.wait_until_visible(driver=driver, css_selector='[id="tmp_header_menu_left"]', duration=30)
            self.LOGGER.info(f"Email login successful")
        except:
            self.LOGGER.info(f"Email login failed")

        # Store user cookies with cookies_email.pkl for later use
        try:
            self.LOGGER.info(f"Saving cookies for: {email_id}")
            cookies = 'cookies_' + email_id + '.pkl'
            file_path_cookies = self.PROJECT_ROOT / 'BotRes' / cookies
            with open(file_path_cookies, 'wb') as cookies_file:
                pickle.dump(driver.get_cookies(), cookies_file)
            self.LOGGER.info(f"Cookies have been saved")
            return True
        except:
            self.LOGGER.info(f"Error while saving cookies")

    # Checkout a ticket after matching
    def checkout_ticket(self, driver, section_to_buy, row_to_buy, seats_to_buy):
        # Wait and check till the tickets gets available
        wait_for_ticket = self.settings["Settings"]["WaitForTicket"]
        # 5 minutes from now
        timeout = time.time() + wait_for_ticket * 60
        tickets_checked = 0
        while True:
            try:
                # self.LOGGER.info(f"Waiting for the tickets list")
                # Waiting for the tickets table
                self.wait_until_visible(driver=driver, css_selector='tr[id*="ticket_"]', duration=1)
                # self.LOGGER.info(f"Tickets list is visible")

                # Check if ticket list has new tickets came in
                ticket_list = driver.find_elements(By.CSS_SELECTOR, 'tr[id*="ticket_"]')
                if ticket_list > tickets_checked:
                    tickets_checked = ticket_list
                    # Checking out a ticket based on the price and other information provided
                    for ticket in driver.find_elements(By.CSS_SELECTOR, 'tr[id*="ticket_"]'):
                        qty, section, row, seats, cost, price = '', '', '', '', '', ''

                        # Scroll ticket into view
                        driver.execute_script("arguments[0].scrollIntoView();", ticket)

                        # Get ticket ID
                        ticket_id = ticket.get_attribute('id')[7:]

                        # Get tickets quantity
                        # try:
                        #     self.LOGGER.info(f"Getting quantity")
                        #     qty = ticket.find_element(By.CSS_SELECTOR, '[class*="column_quantity"]').text
                        #     # tickets_available = qty.split('/')[0].strip()
                        #     # tickets_total = qty.split('/')[1].strip()
                        # except:
                        #     self.LOGGER.info(f'Error while getting quantity')

                        # Get section
                        try:
                            # self.LOGGER.info(f"Getting section")
                            # Waiting for the tickets table
                            # self.wait_until_visible(driver=ticket, css_selector='[class*="column_section"]', duration=3)
                            section = str(
                                ticket.find_element(By.CSS_SELECTOR, '[class*="column_section"]').text).strip()
                        except:
                            self.LOGGER.info(f'Error while getting section')

                        # Get row
                        try:
                            # self.LOGGER.info(f"Getting row")
                            row = str(ticket.find_element(By.CSS_SELECTOR, '[class*="column_row"]').text).strip()
                        except:
                            self.LOGGER.info(f'Error while getting row')

                        # Get seats
                        try:
                            # self.LOGGER.info(f"Getting seats")
                            seats = str(ticket.find_element(By.CSS_SELECTOR, '[class*="column_seats"]').text).strip()
                        except:
                            self.LOGGER.info(f'Error while getting seats')

                        # # Get cost
                        # try:
                        #     self.LOGGER.info(f"Getting cost")
                        #     cost = str(ticket.find_element(By.CSS_SELECTOR, '[class*="column_cost"]').text).strip()
                        # except:
                        #     self.LOGGER.info(f'Error while getting cost')

                        try:
                            # Get price
                            # self.LOGGER.info(f"Getting price")
                            price = float(
                                str(ticket.find_element(By.CSS_SELECTOR, '[class*="column_price"]').text).strip("$"))
                        except:
                            self.LOGGER.info(f'Error while getting price')

                        # Print ticket information
                        ticket_dict = {"Qty": qty, "Section": section, "Row": row, "Seats": seats, "Cost": cost,
                                       "Price": price}
                        self.LOGGER.info(
                            f"Ticket: {ticket_id} | {ticket_dict} | Ticket matched: {(section_to_buy in section) and (row_to_buy in row) and (seats_to_buy in seats)}")
                        # sleep(5000)
                        # Checkout ticket if it matches the section_to_buy, row_to_buy, seats_to_buy and price is between price_from and price_to
                        if (section_to_buy in section) and (row_to_buy in row) and (seats_to_buy in seats):
                            # Checkout the ticket
                            self.LOGGER.info(f"Checking out ticket")
                            # Click buy button
                            try:
                                # self.LOGGER.info(f"Clicking buy button")
                                ticket.find_element(By.CSS_SELECTOR,
                                                    '[class="button special no__border to__cart clickable"]').click()
                                # self.LOGGER.info(f"Buy button clicked")
                            except:
                                self.LOGGER.info(f'Error while clicking buy button')
                            # # Add to the cart
                            # self.LOGGER.info(f"Clicking buy button")
                            #
                            # # Add ticket to the cart
                            # try:
                            #     # Click Add to cart button
                            #     self.LOGGER.info(f"Adding ticket {ticket_id} to the cart")
                            #     self.wait_until_visible(driver=driver, css_selector='[class="button special purchase_send"]')
                            #     driver.find_element(By.CSS_SELECTOR, '[class="button special purchase_send"]').click()
                            #     self.LOGGER.info(f"Ticket {ticket_id} has been added to the cart")
                            # except:
                            #     self.LOGGER.info(f"Error while adding ticket {ticket_id} to the cart")

                            # Click checkout button
                            try:
                                # self.LOGGER.info(f"Clicking checkout button")
                                self.wait_until_visible(driver=driver,
                                                        css_selector='[class="button positive purchase_send_checkout"]')
                                driver.find_element(By.CSS_SELECTOR,
                                                    '[class="button positive purchase_send_checkout"]').click()
                                # self.LOGGER.info(f"Checkout button has been clicked")
                            except:
                                self.LOGGER.info(f"Error while clicking checkout button")

                            # wait and check for pop-up error message, if any
                            # try:
                            #     self.LOGGER.info(f"Waiting for pop-up message")
                            #     self.wait_until_visible(driver=driver, css_selector='[id="messages-popup-content"]', duration=3)
                            #     msg_text = driver.find_element(By.CSS_SELECTOR, '[id="messages-popup-content"]').text
                            #
                            #     # If error message says: "Quantity not selected", close the pop-up and select quantity
                            #     if 'Quantity not selected' in msg_text:
                            #         self.LOGGER.info(f"Error while checking out ticket: {ticket_id}, Msg: {msg_text}")
                            #
                            #         # Close the error message
                            #         try:
                            #             self.LOGGER.info(f"Closing the error message")
                            #             self.wait_until_visible(driver=driver, css_selector='[id="messages-close"]')
                            #             driver.find_element(By.CSS_SELECTOR, '[id="messages-close"]').click()
                            #             self.LOGGER.info(f"Error message closed")
                            #         except:
                            #             self.LOGGER.info(f"Error while closing the error message")
                            #
                            #         # Select ticket quantity
                            #         try:
                            #             self.LOGGER.info(f"Selecting tickets quantity: {qty_to_buy}")
                            #             # Select ticket quantity to buy
                            #             self.wait_until_visible(driver=driver, css_selector=f'[id*="ticket_quantity"]', duration=3)
                            #             selector = Select(webelement=driver.find_element(By.CSS_SELECTOR, f'[id*="ticket_quantity"]'))
                            #             selector.select_by_visible_text(text=qty_to_buy)
                            #             self.LOGGER.info(f"Tickets quantity has been selected: {qty_to_buy}")
                            #         except:
                            #             self.LOGGER.info(f"Error while selecting tickets quantity")
                            #             self.LOGGER.info(f"Selecting next ticket")
                            #             continue
                            #
                            #     # If error message says: "Could not add ticket to cart", just pass
                            #     if 'Could not add ticket to cart' in msg_text or 'Quantity not selected' in msg_text:
                            #         self.LOGGER.info(f"Error while checking out: {ticket_id}")
                            #         self.LOGGER.info(f"{msg_text}: {ticket_id}")
                            #         self.LOGGER.info(f"Selecting next ticket")
                            #         continue
                            #     else:
                            #         self.LOGGER.info(f"Ticket has been added to the cart: {ticket_id}")
                            # except:
                            #     self.LOGGER.info(f"Error while waiting for pup-up message: {ticket_id}")

                            # Handle the checkout page
                            # Wait for the cart page
                            try:
                                # self.LOGGER.info(f"Waiting for the cart page")
                                self.wait_until_visible(driver=driver, css_selector='[id="purchase"]')
                                # self.LOGGER.info(f"Cart page has been visible")
                            except:
                                self.LOGGER.info(f"Error while waiting for the cart page")

                            # Get the ticket price in the cart page
                            try:
                                # self.LOGGER.info(f"Waiting for the ticket price")
                                # self.LOGGER.info(f"Getting price")
                                price = float(
                                    str(driver.find_element(By.CSS_SELECTOR, '[dataformat="price"]').text).strip("$"))
                            except:
                                self.LOGGER.info(f'Error while getting price')

                            # Scroll to the end of the cart page
                            try:
                                # self.LOGGER.info(f"Scrolling to the end of the cart")
                                driver.find_element(By.TAG_NAME, 'html').send_keys(Keys.END)
                                driver.find_element(By.TAG_NAME, 'html').send_keys(Keys.END)
                                driver.find_element(By.TAG_NAME, 'html').send_keys(Keys.END)
                                # self.LOGGER.info(f"Scrolled to the end")
                            except:
                                self.LOGGER.info(f"Error while scrolling")

                            # Cancel the order if the ticket price is not in range of priceFrom - priceTo
                            if price_from <= price <= price_to:
                                # Cancel the order
                                try:
                                    # Click on cancel button
                                    # self.LOGGER.info(f"Cancelling order of the ticket: {ticket_id}")
                                    self.wait_until_visible(driver=driver, css_selector='[id="cancel"]')
                                    cancel_order_btn = driver.find_element(By.CSS_SELECTOR, '[id="cancel"]')
                                    driver.execute_script("arguments[0].click();", cancel_order_btn)
                                    # self.LOGGER.info(f"Ticket order has been cancelled: {ticket_id}")
                                except WebDriverException as exc:
                                    self.LOGGER.info(
                                        f"Error while cancelling order of the ticket: {ticket_id}, {exc.msg}")

                                # Click Yes to confirm cancellation of the order
                                try:
                                    # Click on cancel button
                                    # self.LOGGER.info(f"Cancelling order of the ticket: {ticket_id}")
                                    self.wait_until_visible(driver=driver, css_selector='[class="action yes"]')
                                    cancel_order_btn = driver.find_element(By.CSS_SELECTOR, '[class="action yes"]')
                                    driver.execute_script("arguments[0].click();", cancel_order_btn)
                                    # self.LOGGER.info(f"Ticket order has been cancelled: {ticket_id}")
                                    sleep(20)
                                except WebDriverException as exc:
                                    self.LOGGER.info(
                                        f"Error while cancelling order of the ticket: {ticket_id}, {exc.msg}")
                                    sleep(20)

                            # Wait for the "Paying with card" to be visible on the cart page
                            try:
                                # self.LOGGER.info(f"Waiting for the card to be loaded")
                                self.wait_until_visible(driver=driver,
                                                        css_selector='[class="braintree-methods braintree-methods-initial"]')
                                # self.LOGGER.info(f"Card has been loaded")
                            except:
                                self.LOGGER.info(f"Error while waiting for the card to load")

                            # Complete the transaction
                            try:
                                # Click on Complete Transaction button
                                # self.LOGGER.info(f"Completing the transaction for the ticket: {ticket_id}")
                                self.wait_until_visible(driver=driver, css_selector='[id="proceed"]')
                                cancel_order_btn = driver.find_element(By.CSS_SELECTOR, '[id="proceed"]')
                                driver.execute_script("arguments[0].click();", cancel_order_btn)
                                # actions.move_to_element(complete_transaction_btn).click()
                                # self.LOGGER.info(f"Ticket has been successfully checked out: {ticket_id}")
                                sleep(60)
                                # Break from the loop
                            except WebDriverException as exc:
                                self.LOGGER.info(f"Error while completing the transaction for the ticket: {ticket_id}, {exc.msg}")
                                sleep(60)

                # Refresh Inventory if ticket_list is smaller than the checked tickets
                else:
                    self.LOGGER.info(f"No New tickets found, selecting all Inventory")
                    driver.find_element(By.CSS_SELECTOR, '[class*="filter_tm"]').click()
                    driver.find_element(By.CSS_SELECTOR, '[class*="filter_tm"]').click()
                    sleep(0.5)
            except:
                self.LOGGER.info(f"Tickets are not yet available, selecting all Inventory")
                driver.find_element(By.CSS_SELECTOR, '[class*="filter_tm"]').click()
                driver.find_element(By.CSS_SELECTOR, '[class*="filter_tm"]').click()
                sleep(0.5)

            # If wait_for_ticket time expires, exit the round
            if time.time() > timeout:
                self.LOGGER.info(f"Timeout while waiting for the ticket !")
                break

    # Get tickets via driver
    def get_ticket(self, driver, event_url):
        self.LOGGER.info(f"Checking out tickets from event: {event_url}")
        base_url = "https://tradedesk.ticketmaster.com/"
        cart_url = "https://tradedesk.ticketmaster.com/purchase"

        actions = ActionChains(driver=driver)

        qty_to_buy = 1

        # Extract event ID from event_url
        # event_id = event_url[53:70].split('?')[0]

        # Extract section, row and seats values from the event URL
        section_to_buy = re.findall(r'(?<=section=)(.+)(?=&row)', event_url)[0]
        row_to_buy = re.findall(r'(?<=row=)(.+)(?=&seats)', event_url)[0]
        seats_to_buy = re.findall(r'(?<=seats=)(.+)(?=&all_inv)', event_url)[0]
        price_from = float(re.findall(r'(?<=priceFrom=)(.+)(?=&priceTo)', event_url)[0])
        price_to = float(re.findall(r'(?<=priceTo=)(.+)', event_url)[0])

        # # Get to the event page and click All Events
        # try:
        #     # Click All Events
        #     self.LOGGER.info(f"Waiting for the event")
        #     self.wait_until_visible(driver=driver, css_selector='[name="filter_all_events"]')
        #     driver.find_element(By.CSS_SELECTOR, '[name="filter_all_events"]').click()
        #     self.LOGGER.info(f"All Events selected")
        # except:
        #     self.LOGGER.info(f"Error while selecting All Events")

        # Get to the event page and click All Inventory
        try:
            driver.get(event_url)
            # Click All Inventory
            # self.LOGGER.info(f"Waiting for the Inventory")
            self.wait_until_visible(driver=driver, css_selector='[class*="filter_tm"]')
            # sleep(1)
            driver.find_element(By.CSS_SELECTOR, '[class*="filter_tm"]').click()
            # driver.find_element(By.CSS_SELECTOR, '[class*="filter_tm"]').click()
            # self.LOGGER.info(f"All Inventory selected")
        except:
            self.LOGGER.info(f"Error while selecting all inventory")

        # Filling filter: Section
        try:
            # self.LOGGER.info(f"Filling filter: Section")
            # Waiting for the tickets table
            self.wait_until_visible(driver=driver, css_selector='[name="filter_ticket_section"]')
            driver.find_element(By.CSS_SELECTOR, '[name="filter_ticket_section"]').send_keys(section_to_buy)
            # self.LOGGER.info(f"Filled filter: Section")
        except:
            self.LOGGER.info(f"Error while filling filter: Section")

        # Filling filter: Row
        try:
            # self.LOGGER.info(f"Filling filter: Row")
            # Waiting for the tickets table
            self.wait_until_visible(driver=driver, css_selector='[name="filter_ticket_row"]')
            driver.find_element(By.CSS_SELECTOR, '[name="filter_ticket_row"]').send_keys(row_to_buy)
            # self.LOGGER.info(f"Filled filter: Row")
        except:
            self.LOGGER.info(f"Error while filling filter: Row")

        # Filling filter: Seats
        try:
            # self.LOGGER.info(f"Filling filter: Seats")
            # Waiting for the tickets table
            self.wait_until_visible(driver=driver, css_selector='[name="filter_ticket_seat"]')
            driver.find_element(By.CSS_SELECTOR, '[name="filter_ticket_seat"]').send_keys(seats_to_buy)
            # self.LOGGER.info(f"Filled filter: Seats")
        except:
            self.LOGGER.info(f"Error while filling filter: Seats")

        # Waiting for the tickets inventory
        # try:
        #     # self.LOGGER.info(f"Waiting for the marketplace list")
        #     # Waiting for the tickets table
        #     self.wait_until_visible(driver=driver, css_selector='[id="marketplace_list"]')
        #     # self.LOGGER.info(f"Marketplace list is visible")
        # except:
        #     self.LOGGER.info(f"Error while waiting for the marketplace list")

        # Constantly click All Inventory until there are tickets in the inventory
        while True:
            try:
                # self.LOGGER.info(f"Waiting for the tickets list")
                # Waiting for the tickets table
                self.wait_until_visible(driver=driver, css_selector='tr[id*="ticket_"]', duration=1)
                # Exit from loop when tickets get available
                # driver.find_element(By.CSS_SELECTOR, 'tr[id*="ticket_"]').click()
                # self.LOGGER.info(f"Tickets list is visible")

                # Break if the tickets get available
                break
            except:
                self.LOGGER.info(f"Tickets are not yet available, selecting all Inventory")
                driver.find_element(By.CSS_SELECTOR, '[class*="filter_tm"]').click()
                driver.find_element(By.CSS_SELECTOR, '[class*="filter_tm"]').click()
                sleep(0.5)

        # Try to checkout a ticket
        self.checkout_ticket(driver=driver, section_to_buy=section_to_buy, row_to_buy=row_to_buy, seats_to_buy=seats_to_buy, price_from=price_from, price_to=price_to)

    # Subscribes and listens to pubnub channel to get EventURL
    def start_pubnub_listener(self):
        channel_machine = self.settings["Settings"]["PubNubKeyChannelInstance_2"]
        self.LOGGER.info(f'Starting PubNub Listener for: {channel_machine}')
        # Add EventURLHandler as an event listener
        pubnub.add_listener(EventURLHandler())
        # Subscribe to the channel to get messages i.e. EventURLs
        pubnub.subscribe().channels(channel_machine).execute()

    # Gets EventURL from local file
    def get_event_url(self):
        event_df = pd.read_csv(self.file_event_urls, index_col=None)
        last_url = event_df.iloc[-1]
        if last_url["Processed"] == "No":
            event_df.loc[event_df.Processed == "No", "Processed"] = "Yes"
            event_df.to_csv(self.file_event_urls, index=False)
            return last_url["EventURL"]
        else:
            return None

    def start_tradedesk_instance(self, instance_id):
        self.LOGGER.info(f"Launching Instance: {instance_id}")

        # Initialize driver
        driver = self.get_driver(headless=False)

        # Get email_id and password for TradeDesk
        email_id = self.settings["Settings"]["Email"]
        password = self.settings["Settings"]["Password"]


        # Check if already logged in
        if not self.logged_in:
            self.login_trade_desk(driver=driver, email_id=email_id, password=password)
            self.logged_in = True
        # Continuously wait for the event url to be pasted and checked out
        self.LOGGER.info(f"Waiting for event URL")
        while True:
            event_url = self.get_event_url()
            if event_url is not None:
                self.LOGGER.info(f"EvenURL Received: {event_url}")
                self.get_ticket(driver=driver, event_url=event_url)
                self.LOGGER.info(f"Waiting for next event URL")
            else:
                sleep(1)

    def main(self):
        freeze_support()
        self.enable_cmd_colors()
        self.banner()
        trial_date = datetime.strptime('2023-02-05 23:59:59', '%Y-%m-%d %H:%M:%S')
        if self.trial(trial_date=trial_date):
            self.LOGGER.info(f'TradeDeskBot launched')
            # Start pubnub listener in a separate thread
            threading.Thread(target=self.start_pubnub_listener).start()

            number_of_instances = self.settings["Settings"]["NumberOfInstancesToRun"]
            instance_ids = [instance_id for instance_id in range(number_of_instances)]
            # Launch TradeDeskBot instances in scalable way, each in a thread
            with concurrent.futures.ThreadPoolExecutor(max_workers=number_of_instances) as executor:
                results = executor.map(self.start_tradedesk_instance, instance_ids)
                try:
                    for x, result in results:
                        self.LOGGER.info(f'Results: {result}')
                except Exception as e:
                    self.LOGGER.info(e)


if __name__ == '__main__':
    TradeDeskBot().main()
