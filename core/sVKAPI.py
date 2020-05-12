from bs4 import BeautifulSoup, element
from requests import *
from datetime import datetime
from PIL import Image, PngImagePlugin

class VkAPI:

    __mAccessToken: str
    __mAPIBaseUrl: str = "https://api.vk.com/method/"
    __mAPIClientID: int = 7249628
    __mAPIVersion: float = 5.103

    __mSession: sessions.Session = Session()

    def __init__(self, login: str, password: str):

        def input2FA() -> str:
            return input("Code: ")

        def inputCaptcha() -> str:
            return input("Captcha: ")

        headers: dict = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                                       " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}

        def sendAuthRequest() -> models.Response:
            params: dict = {
                "client_id": self.__mAPIClientID,
                "display": "mobile",
                "redirect_uri": "blank.html",
                "scope": "notify,friends,photos,audio,video,stories,pages,status,notes,"
                         "wall,offline,docs,groups,notifications,stats,email",
                "response_type": "token",
                "v": self.__mAPIVersion
            }
            return self.__mSession.get("https://oauth.vk.com/authorize", params = params, headers = headers)


        def sendAuthData(authPage: models.Response) -> models.Response:
            soup: BeautifulSoup = BeautifulSoup(authPage.text, features="html.parser")
            inputFields: element.ResultSet = soup.select("form input")
            data: dict = {
                "_origin": inputFields[0].attrs["value"],
                "ip_h": inputFields[1].find_all("input")[0].attrs["value"],
                "lg_h": inputFields[2].attrs["value"],
                "to": inputFields[3].attrs["value"],
                "email": login,
                "pass": password,
            }
            return self.__mSession.post("https://login.vk.com/?act=login&soft=1&utf8=1", data = data, headers = headers)


        def send2FA(authPage: models.Response) -> models.Response:
            soup: BeautifulSoup = BeautifulSoup(authPage.text, features="html.parser")
            url: str = "https://m.vk.com" + soup.find_all("form")[0].attrs["action"]
            data: dict = {
                "code": input2FA(),
                "checked": "checked",
                "remember": 1
            }
            return self.__mSession.post(url, data=data, headers=headers)


        def sendCaptcha(authPage: models.Response) -> models.Response:
            soup: BeautifulSoup = BeautifulSoup(authPage.text, features="html.parser")
            captcha: element.ResultSet = soup.select("img.captcha_img")[0]

            fileName: str = "core/_logCaptcha/Captcha_" + datetime.now().strftime("%Y.%m.%d %H:%M") + ".jpg"
            with open(fileName, 'wb') as f:
                r: models.Response = self.__mSession.get("https://m.vk.com/" + captcha.attrs["src"])
                f.write(r.content)

            img: PngImagePlugin.PngImageFile = Image.open(fileName)
            img.show()

            url: str = soup.select("div form")[0].attrs["action"]
            inputFields: element.ResultSet = soup.select("form input")
            data: dict = {
                "captcha_sid": inputFields[0].attrs["value"],
                "code": inputFields[1].attrs["value"],
                "checked": "checked",
                "remember": 1,
                "captcha_key": inputCaptcha()
            }
            return self.__mSession.post("https://m.vk.com" + url, data = data, headers = headers)



