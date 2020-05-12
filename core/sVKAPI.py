from requests import *

class VkAPI:

    __mAccessToken: str
    __mAPIBaseUrl: str = "https://api.vk.com/method/"
    __mAPIClientID: int = 7249628
    __mAPIVersion: float = 5.103

    __mSession = Session()