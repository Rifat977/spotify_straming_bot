from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import requests
import webbrowser
import random
import pytz
import time
import os
import zipfile
import string
from colorama import Fore, init
from pystyle import Center, Colors, Colorate

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException
import threading
from concurrent.futures import ThreadPoolExecutor

# Initialize colorama
init(autoreset=True)

url = "https://github.com/Kichi779/Spotify-Streaming-Bot/"

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass, scheme='http', plugin_path='proxy_auth_plugin.zip'):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = string.Template(
        """
        var config = {
            mode: "fixed_servers",
            rules: {
                singleProxy: {
                    scheme: "${scheme}",
                    host: "${proxy_host}",
                    port: parseInt(${proxy_port})
                },
                bypassList: ["localhost"]
            }
        };

        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "${proxy_user}",
                    password: "${proxy_pass}"
                }
            };
        }

        chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {urls: ["<all_urls>"]},
            ["blocking"]
        );
        """
    ).substitute(
        proxy_host=proxy_host,
        proxy_port=proxy_port,
        proxy_user=proxy_user,
        proxy_pass=proxy_pass,
        scheme=scheme,
    )

    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return plugin_path

def get_current_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except Exception as e:
        print(Fore.RED + "Failed to get current IP address:", str(e))
        return None

# def play_song_and_wait(driver, playmusic_xpath, next_button_xpath, min_play_time=20):
#     while True:
#         try:
#             time.sleep(min_play_time)

#             next_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, next_button_xpath)))
#             next_button.click()

#             print(Fore.GREEN + "Next song started.")

#         except NoSuchElementException:
#             print(Fore.RED + "Could not find the play button or next button.")
#             break
#         except ElementClickInterceptedException:
#             print(Fore.RED + "Click intercepted while trying to click play or next button. Retrying...")
#             time.sleep(3)
#         except TimeoutException:
#             print(Fore.RED + "Timeout waiting for the next button. Trying again...")
#             continue
#         except Exception as e:
#             print(Fore.RED + "An error occurred while playing the song:", str(e))
#             break

supported_timezones = pytz.all_timezones

def set_random_timezone(driver):
    random_timezone = random.choice(supported_timezones)
    driver.execute_script(f"""
        Services.prefs.setStringPref("intl.timezone.override", "{random_timezone}");
        """)

def set_fake_geolocation(driver, latitude, longitude):
    driver.execute_script(f"""
        navigator.geolocation.getCurrentPosition = function(success) {{
            var position = {{ "coords" : {{ "latitude": "{latitude}", "longitude": "{longitude}" }} }};
            success(position);
        }};
        """)

def play_song_and_wait(driver, playmusic_xpath, next_button_xpath, min_play_time):
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, playmusic_xpath))).click()
    time.sleep(min_play_time)
    next_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, next_button_xpath)))
    next_button.click()

def run_bot(username, password, playlists, use_proxy=False, proxy_info=None):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36",
    ]
    supported_languages = [
        "en-US", "en-GB", "en-CA", "en-AU", "en-NZ", "fr-FR", "fr-CA", "fr-BE", "fr-CH", "fr-LU",
        "de-DE", "de-AT", "de-CH", "de-LU", "es-ES", "es-MX", "es-AR", "es-CL", "es-CO", "es-PE",
        "it-IT", "it-CH", "ja-JP", "ko-KR", "pt-BR", "pt-PT", "ru-RU", "tr-TR", "nl-NL", "nl-BE",
        "sv-SE", "da-DK", "no-NO"
    ]

    random_user_agent = random.choice(user_agents)
    random_language = random.choice(supported_languages)

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--head")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"user-agent={random_user_agent}")
    chrome_options.add_argument(f"--lang={random_language}")

    if use_proxy and proxy_info:
        proxy_host, proxy_port, proxy_user, proxy_pass = proxy_info.split(':')
        plugin_path = create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass)
        chrome_options.add_extension(plugin_path)

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    account_stats = {
        "username": username,
        "songs_played": 0,
        "proxy_used": proxy_info if use_proxy else "None"
    }

    try:
        if use_proxy:
            print(Fore.BLUE + f"Connecting to proxy: {proxy_info}")
            initial_ip = get_current_ip(driver)
            print(Fore.BLUE + f"Initial IP: {initial_ip}")

            final_ip = get_current_ip(driver)
            print(Fore.BLUE + f"Final IP: {final_ip}")

            if initial_ip != final_ip:
                print(Fore.GREEN + f"Proxy {proxy_info} is working correctly.")
            else:
                print(Fore.RED + f"Proxy {proxy_info} is not working. Trying next proxy.")
                return False

        driver.get("https://www.spotify.com/us/login/")

        username_input = driver.find_element(By.CSS_SELECTOR, "input#login-username")
        password_input = driver.find_element(By.CSS_SELECTOR, "input#login-password")

        username_input.send_keys(username)
        password_input.send_keys(password)

        driver.find_element(By.CSS_SELECTOR, "button[data-testid='login-button']").click()

        time.sleep(random.uniform(2, 6))

        for playlist_url in playlists:
            driver.get(playlist_url)
            time.sleep(10)

            try:
                cookie = driver.find_element(By.XPATH, "//button[text()='Accept Cookies']")
                cookie.click()
            except NoSuchElementException:
                try:
                    button = driver.find_element(By.XPATH, "//button[contains(@class,'onetrust-close-btn-handler onetrust-close-btn-ui')]")
                    button.click()
                except NoSuchElementException:
                    time.sleep(random.uniform(5, 14))

            playmusic_xpath = "/html/body/div[4]/div/div[2]/div[3]/div[1]/div[2]/div[2]/div[2]/main/section/div[3]/div[2]/div/div/div[1]/button"
            next_button_xpath = "//button[contains(@aria-label, 'Next')]"
            mute_button_xpath = "/html/body/div[4]/div/div[2]/div[2]/footer/div/div[3]/div/div[3]/button"
            song_base_xpath = "/html/body/div[4]/div/div[2]/div[3]/div[1]/div[2]/div[2]/div[2]/main/section/div[4]/div[1]/div[2]/div[2]/div[{index}]/div/div/div[2]"

            min_play_time = 40

            print(Fore.GREEN + f"Username: {username} - Listening process has started.")
            
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, mute_button_xpath))).click()
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, playmusic_xpath))).click()
            
            print(Fore.GREEN + f"Song is playing. Waiting for at least {min_play_time} seconds...")

            song_count = 0
            while True:
                try:
                    driver.find_element(By.XPATH, song_base_xpath.format(index=song_count + 1))
                    song_count += 1
                except NoSuchElementException:
                    break

            print(Fore.GREEN + f"Found {song_count} songs in the playlist {playlist_url} for account {username}.")

            for i in range(song_count):
                play_song_and_wait(driver, playmusic_xpath, next_button_xpath, min_play_time)
                account_stats["songs_played"] += 1
                print(Fore.GREEN + f"Played song number {account_stats['songs_played']} for account {username}")

                try:
                    next_button = driver.find_element(By.XPATH, next_button_xpath)
                    next_button.click()
                    time.sleep(random.uniform(2, 6))
                except NoSuchElementException:
                    print(Fore.YELLOW + f"No more songs to play in playlist {playlist_url} for account {username}. Moving to next playlist.")
                    break

            time.sleep(2)

    except Exception as e:
        print(Fore.RED + "An error occurred in the bot system:", str(e))
        return False
    finally:
        driver.quit()
        print(Fore.BLUE + f"Account {username} played {account_stats['songs_played']} songs. Proxy used: {account_stats['proxy_used']}")

    return True

def main():
    print(Fore.RED + "RM Digital")
    print(Fore.YELLOW + "Spotify Streaming Bot")
    print("")

    with open('accounts.txt', 'r') as file:
        accounts = file.readlines()

    use_proxy = input("Do you want to use proxies? (y/n): ")

    proxies = []
    if use_proxy.lower() == 'y':
        with open('proxy.txt', 'r') as file:
            proxies = file.readlines()

    with open('list.txt', 'r') as file:
        playlists = [line.strip() for line in file.readlines()]

    def run_account(account):
        username, password = account.strip().split(':')
        proxy_info = None
        if use_proxy.lower() == 'y' and proxies:
            proxy_info = proxies.pop(0).strip()

        success = run_bot(username, password, playlists, use_proxy.lower() == 'y', proxy_info)
        if not success and proxies:
            proxies.append(proxy_info)

        time.sleep(random.uniform(5, 14))

    with ThreadPoolExecutor(max_workers=len(accounts)) as executor:
        executor.map(run_account, accounts)

    print(Fore.YELLOW + "Stream operations are completed. You can stop all transactions by closing the program.")

    while True:
        pass

if __name__ == "__main__":
    main()