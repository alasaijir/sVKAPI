from bs4 import BeautifulSoup, element
from requests import *
from datetime import datetime
from PIL import Image, PngImagePlugin
from pickle import dump, load
from os import path
from base64 import b64encode, b64decode

class VkAPI:
    __mAccessToken: str
    __mAPIClientID: int = 7249628
    __mAPIVersion: float = 5.103
    __mAPIBaseUrl: str = "https://api.vk.com/method/"

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
            soup: BeautifulSoup = BeautifulSoup(authPage.text, features = "html.parser")
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
            soup: BeautifulSoup = BeautifulSoup(authPage.text, features = "html.parser")
            url: str = "https://m.vk.com" + soup.find_all("form")[0].attrs["action"]
            data: dict = {
                "code": input2FA(),
                "checked": "checked",
                "remember": 1
            }
            return self.__mSession.post(url, data = data, headers = headers)


        def sendCaptcha(authPage: models.Response) -> models.Response:
            soup: BeautifulSoup = BeautifulSoup(authPage.text, features = "html.parser")
            captcha: element.ResultSet = soup.select("img.captcha_img")[0]
            fileName: str = "core/_logCaptcha/Captcha_" + str(datetime.now().strftime("%Y.%m.%d_%H.%M")) + ".jpg"
            with open(fileName, 'wb') as f:
                captchaResponse: models.Response = self.__mSession.get("https://m.vk.com/" + captcha.attrs["src"])
                f.write(captchaResponse.content)

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


        def sendConfirmation(confPage: models.Response) -> models.Response:
            soup: BeautifulSoup = BeautifulSoup(confPage.text, features = "html.parser")
            url: str = soup.find_all("form")[0].attrs["action"]
            data: dict = {
                "email_denied": 0,
            }
            return self.__mSession.post(url, data = data, headers = headers)


        def getPageType(page: models.Response) -> str:
            soup: BeautifulSoup = BeautifulSoup(page.text, features = "html.parser")
            inputFields: element.ResultSet = soup.select("form input")
            if inputFields[0].attrs["name"] == "code":
                return "2FA"
            if inputFields[0].attrs["name"] == "captcha_sid":
                return "CAP"
            if inputFields[0].attrs["name"] == "email_denied":
                return "YES"
            else:
                raise TypeError


        def saveSession() -> bool:
            with open("core/session/currentSession.encrypted", "wb") as f:
                dump(self.__mSession, f)
            with open("core/session/currentToken.encrypted", "wb") as f:
                f.write(b64encode(self.__mAccessToken.encode("utf-8")))
            print("SESSION SAVED")
            return True


        def loadSession() -> bool:
            if path.isfile("core/session/currentSession.encrypted"):
                with open("core/session/currentSession.encrypted", "rb") as f:
                    self.__mSession = load(f)
                print("SESSION LOADED")
                return True
            else:
                print("CANT LOAD SESSION, TRYING TO LOGGING-IN")
                return False


        def loadToken() -> bool:
            if path.isfile("core/session/currentToken.encrypted"):
                with open("core/session/currentToken.encrypted", "rb") as f:
                    self.__mAccessToken = b64decode(f.read()).decode("utf-8")
                print("SECRET TOKEN LOADED")
                return True
            else:
                print("CANT LOAD SECRET TOKEN, TRYING TO LOAD SESSION")
                return False

        if not loadToken():
            if loadSession() :
                tmp = sendAuthRequest()
                result = sendConfirmation(tmp)
                self.__mAccessToken = result.url[45:130]
            else:
                tmp = sendAuthRequest()
                tmp = sendAuthData(tmp)
                if getPageType(tmp) == "2FA":
                    tmp = send2FA(tmp)
                    if getPageType(tmp) == "CAP":
                        tmp = sendCaptcha(tmp)
                        result = sendConfirmation(tmp)
                    elif getPageType(tmp) == "YES":
                        result = sendConfirmation(tmp)
                elif getPageType(tmp) == "YES":
                    result = sendConfirmation(tmp)
                self.__mAccessToken = result.url[45:130]
            saveSession()

        print("LOG IN SUCCESSFUL WITH TOKEN " + self.__mAccessToken[0:4] + "***")
        print("-"*170+"|")

    def __prepareAPIRequest(self, rawData: dict) -> dict:
        data: dict = {
            "access_token": self.__mAccessToken,
            "v": self.__mAPIVersion
        }
        for key, value in rawData.items():
            data[key] = value
        return data

    def usersGet(self, **kwargs) -> dict:
        data: dict = self.__prepareAPIRequest(kwargs)
        return self.__mSession.post(self.__mAPIBaseUrl + "users.get", data = data).json()


