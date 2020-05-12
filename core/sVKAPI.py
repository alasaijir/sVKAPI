from requests import *

class VkAPI:

    __mAccessToken: str
    __mAPIBaseUrl: str = "https://api.vk.com/method/"
    __mAPIClientID: int = 7249628
    __mAPIVersion: float = 5.103

    __mSession = Session()

    def __init__(self, login: str, password: str):

        def input2FA() -> str:
            return input("Code: ")

        def inputCaptcha() -> str:
            return input("Captcha: ")

        headers: dict = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                                       " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}

