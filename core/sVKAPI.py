from bs4 import BeautifulSoup, element
from requests import *
from datetime import datetime
from PIL import Image, PngImagePlugin
from pickle import dump, load
from os import path
from base64 import b64encode, b64decode

class VkAPI:
    __mAccessToken: str = ""
    __mCustomToken: str = "N"

    __mAPIClientID: int = 7249628
    __mAPIVersion: float = 5.103
    __mAPIBaseUrl: str = "https://api.vk.com/method/"

    __mSession: sessions.Session = Session()

    __mLongPollInit: bool = False
    __mLongPollTs: int = 0
    __mLongPollServer: str = ""
    __mLongPollKey: str = ""


    def __saveSession(self) -> bool:
        with open("core/data/currentSession.encrypted", "wb") as f:
            dump(self.__mSession, f)
        with open("core/data/currentToken.encrypted", "wb") as f:
            f.write(b64encode(self.__mAccessToken.encode("utf-8")))
            f.write("\n".encode("utf-8"))
            if self.__mCustomToken == "Y":
                f.write(b64encode("CUSTOM_TOKEN_Y".encode("utf-8")))
            else:
                f.write(b64encode("CUSTOM_TOKEN_N".encode("utf-8")))
        print("SESSION SAVED")
        return True


    def __loadSession(self) -> bool:
        if path.isfile("core/data/currentSession.encrypted"):
            with open("core/data/currentSession.encrypted", "rb") as f:
                self.__mSession = load(f)
            print("SESSION LOADED")
            return True
        else:
            print("CANT LOAD SESSION, TRYING TO LOGGING-IN")
            return False


    def __loadToken(self) -> bool:
        if path.isfile("core/data/currentToken.encrypted"):
            with open("core/data/currentToken.encrypted", "rb") as f:
                lines = []
                for line in f:
                    lines.append(line)
                self.__mAccessToken = b64decode(lines[0]).decode("utf-8")
                self.__mCustomToken = b64decode(lines[1]).decode("utf-8")[13]
            print("SECRET TOKEN LOADED (", end="")
            if self.__mCustomToken == "Y":
                print("CUSTOM)")
            else:
                print("USUAL)")
            return True
        else:
            print("CANT LOAD SECRET TOKEN, TRYING TO LOAD SESSION")
            return False


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
            fileName: str = "core/captchaLog/Captcha_" + str(datetime.now().strftime("%Y.%m.%d_%H.%M")) + ".jpg"
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


        if not self.__loadToken():
            if self.__loadSession() :
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

        print("LOG IN SUCCESSFUL WITH TOKEN " + self.__mAccessToken[0:4] + "***")


    def __del__(self):
        self.__saveSession()


    def setToken(self, newToken: str):
        self.__mCustomToken = "Y"
        self.__mAccessToken = newToken
        print("TOKEN CHANGED " + self.__mAccessToken[0:4] + "***")

    #=====================================BASE API REQUESTS=====================================

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


    def friendsGet(self, **kwargs) -> dict:
        data = self.__prepareAPIRequest(kwargs)
        return self.__mSession.post(self.__mAPIBaseUrl + "friends.get", data = data).json()


    def messagesSend(self, **kwargs) -> dict:
        if self.__mCustomToken == "N":
            print("WARNING: MESSAGES CANT BE ACCESSED WITH USUAL TOKEN")
        data = self.__prepareAPIRequest(kwargs)
        return self.__mSession.post(self.__mAPIBaseUrl + "messages.send", data = data).json()


    def messagesGetById(self, **kwargs) -> dict:
        if self.__mCustomToken == "N":
            print("WARNING: MESSAGES CANT BE ACCESSED WITH USUAL TOKEN")
        data = self.__prepareAPIRequest(kwargs)
        return self.__mSession.post(self.__mAPIBaseUrl + "messages.getById", data = data).json()


    def messagesGetLongPollServer(self, **kwargs) -> dict:
        if self.__mCustomToken == "N":
            print("WARNING: MESSAGES CANT BE ACCESSED WITH USUAL TOKEN")
        data = self.__prepareAPIRequest(kwargs)
        return self.__mSession.post(self.__mAPIBaseUrl + "messages.getLongPollServer", data = data).json()

    #============================================================================================

    def setLongPollServer(self, needPts: int = 1, lp_version: int = 3):
        serverData: dict = self.messagesGetLongPollServer(needPts = needPts, lp_version = lp_version)
        self.__mLongPollInit = True
        self.__mLongPollTs = serverData["response"]["ts"]
        self.__mLongPollKey = serverData["response"]["key"]
        self.__mLongPollServer = serverData["response"]["server"]


    def longPoll(self, mode: int = 234, wait: int = 25, version: int = 3) -> dict:
        if not self.__mLongPollInit:
            raise Exception("YOU NEED TO CALL setLongPollServer() BEFORE USING LONGPOLL")
        data: dict = {
            "act": "a_check",
            "key": self.__mLongPollKey,
            "ts": self.__mLongPollTs,
            "wait": wait,
            "mode": mode,
            "version": version
        }
        updates: dict = self.__mSession.post("https://"+self.__mLongPollServer, data = data).json()
        self.__mLongPollTs = updates["ts"]
        return updates

