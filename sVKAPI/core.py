from bs4 import BeautifulSoup
from requests import Session, Response
from datetime import datetime
from PIL import Image
from pickle import dump, load
from os import path
from base64 import b64encode, b64decode

class API:
    __mAccessToken = ""
    __mAuthPassed = False
    __mCustomToken = "N"

    __mAPIClientID = 7249628
    __mAPIVersion = 5.103
    __mAPIBaseUrl = "https://api.vk.com/method/"

    __mSession = Session()

    __mLongPollInit = False
    __mLongPollTs = 0
    __mLongPollServer = ""
    __mLongPollKey = ""

    #Private

    def __del__(self):
        self.__saveSession()
        if self.__mAccessToken != "":
            self.__saveToken()

    def __saveSession(self):
        with open("sVKAPI/data/currentSession.encrypted", "wb") as f:
            dump(self.__mSession, f)
        print("SESSION SAVED")
        return True

    def __loadSession(self) -> bool:
        if path.isfile("sVKAPI/data/currentSession.encrypted"):
            with open("sVKAPI/data/currentSession.encrypted", "rb") as f:
                self.__mSession = load(f)
            print("SESSION LOADED")
            return True
        else:
            print("CAN'T LOAD SESSION, TRYING TO LOG IN...")
            return False

    def __saveToken(self):
        with open("sVKAPI/data/currentToken.encrypted", "wb") as f:
            encryptedData = self.__mAccessToken + "\n"
            if self.__mCustomToken == "Y":
                encryptedData += "CUSTOM_TOKEN_Y"
            else:
                encryptedData += "CUSTOM_TOKEN_N"
            encryptedData = b64encode(b64encode(b64encode(encryptedData.encode("utf-8"))))
            f.write(encryptedData)

    def __loadToken(self) -> bool:
        if path.isfile("sVKAPI/data/currentToken.encrypted"):
            with open("sVKAPI/data/currentToken.encrypted", "rb") as f:
                lines = b64decode(b64decode(b64decode(f.read()))).decode("utf-8").split("\n")
                self.__mAccessToken = lines[0]
                self.__mCustomToken = lines[1][13]
            print("TOKEN LOADED (", end="")
            if self.__mCustomToken == "Y":
                print("CUSTOM) ", end="")
            else:
                print("USUAL) ", end="")
            print(self.__mAccessToken[0:4] + "***")
            return True
        else:
            print("CAN'T LOAD TOKEN, TRYING TO AUTHENTICATE...")
            return False

    def __checkAuth(self):
        if not self.__mAuthPassed:
            raise RuntimeError("CANT CALL THIS METHOD: authenticate() WASN'T CALLED")

    #Public

    def authenticate(self, **kwargs):

        def input2FA() -> str:
            return input("Code: ")

        def inputCaptcha() -> str:
            return input("Captcha: ")

        def sendAuthRequest(header: dict) -> Response:
            params = {
                "client_id": self.__mAPIClientID,
                "display": "mobile",
                "redirect_uri": "blank.html",
                "scope": "notify,friends,photos,audio,video,stories,pages,status,notes,"
                         "wall,offline,docs,groups,notifications,stats,email",
                "response_type": "token",
                "v": self.__mAPIVersion
            }
            return self.__mSession.get("https://oauth.vk.com/authorize", params = params, headers = header)

        def sendAuthData(authPage: Response, login: str, password: str, header: dict) -> Response:
            soup = BeautifulSoup(authPage.text, features = "html.parser")
            inputFields = soup.select("form input")
            data = {
                "_origin": inputFields[0].attrs["value"],
                "ip_h": inputFields[1].find_all("input")[0].attrs["value"],
                "lg_h": inputFields[2].attrs["value"],
                "to": inputFields[3].attrs["value"],
                "email": login,
                "pass": password,
            }
            return self.__mSession.post("https://login.vk.com/?act=login&soft=1&utf8=1", data = data, headers = header)

        def send2FA(authPage: Response, header: dict) -> Response:
            soup = BeautifulSoup(authPage.text, features = "html.parser")
            url = "https://m.vk.com" + soup.find_all("form")[0].attrs["action"]
            data = {
                "code": input2FA(),
                "checked": "checked",
                "remember": 1
            }
            return self.__mSession.post(url, data = data, headers = header)

        def sendCaptcha(authPage: Response, header: dict) -> Response:
            soup = BeautifulSoup(authPage.text, features = "html.parser")
            captcha = soup.select("img.captcha_img")[0]
            captchaResponse = self.__mSession.get("https://m.vk.com/" + captcha.attrs["src"])
            fileName = "sVKAPI/_captchaLog/Captcha_" + str(datetime.now().strftime("%Y.%m.%d_%H.%M")) + ".jpg"
            with open(fileName, 'wb') as f:
                f.write(captchaResponse.content)

            img = Image.open(fileName)
            img.show()

            url = soup.select("div form")[0].attrs["action"]
            inputFields = soup.select("form input")
            data = {
                "captcha_sid": inputFields[0].attrs["value"],
                "code": inputFields[1].attrs["value"],
                "checked": "checked",
                "remember": 1,
                "captcha_key": inputCaptcha()
            }
            return self.__mSession.post("https://m.vk.com" + url, data = data, headers = header)

        def sendConfirmation(confPage: Response, header: dict) -> Response:
            soup = BeautifulSoup(confPage.text, features = "html.parser")
            url = soup.find_all("form")[0].attrs["action"]
            data = {
                "email_denied": 0,
            }
            return self.__mSession.post(url, data = data, headers = header)

        def getPageType(page: Response) -> str:
            soup = BeautifulSoup(page.text, features = "html.parser")
            inputFields = soup.select("form input")
            if inputFields[0].attrs["name"] == "code":
                return "2FA"
            if inputFields[0].attrs["name"] == "captcha_sid":
                return "CAP"
            if inputFields[0].attrs["name"] == "email_denied":
                return "CON"
            else:
                raise TypeError

        if self.__loadToken():
            if len(kwargs) > 0:
                print("PROVIDED DATA WAS IGNORED")
        elif "token" in kwargs:
            self.__mAccessToken = kwargs["token"]
            self.__mCustomToken = "Y"
            print("CUSTOM TOKEN RECEIVED: " + self.__mAccessToken[0:4] + "***")
        elif "username" in kwargs and "password" in kwargs:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}
            if self.__loadSession() :
                tmp = sendAuthRequest(headers)
                result = sendConfirmation(tmp, headers)
                self.__mAccessToken = result.url[45:130]
            else:
                result = None
                tmp = sendAuthRequest(headers)
                tmp = sendAuthData(tmp, kwargs["username"], kwargs["password"], headers)
                if getPageType(tmp) == "2FA":
                    tmp = send2FA(tmp, headers)
                    if getPageType(tmp) == "CAP":
                        tmp = sendCaptcha(tmp, headers)
                        result = sendConfirmation(tmp, headers)
                    elif getPageType(tmp) == "CON":
                        result = sendConfirmation(tmp, headers)
                elif getPageType(tmp) == "CON":
                    result = sendConfirmation(tmp, headers)
                self.__mAccessToken = result.url[45:130]
            print("USUAL TOKEN RECEIVED " + self.__mAccessToken[0:4] + "***")
        else:
            raise AttributeError("NO REQUIRED DATA PASSED (token OR username & password)")
        self.__mAuthPassed = True

    def setToken(self, newToken: str):
        self.__mAuthPassed = True
        self.__mCustomToken = "Y"
        self.__mAccessToken = newToken
        print("TOKEN CHANGED " + self.__mAccessToken[0:4] + "***")

    def call(self, method:str, **kwargs) -> dict:
        self.__checkAuth()
        data = {
            "access_token": self.__mAccessToken,
            "v": self.__mAPIVersion
        }

        for key, value in kwargs.items():
            data[key] = value

        return self.__mSession.post(self.__mAPIBaseUrl + method, data = data).json()

    def setLongPollServer(self, needPts: int = 1, lp_version: int = 3):
        self.__checkAuth()
        serverData = self.call("messages.getLongPollServer", needPts = needPts, lp_version = lp_version)
        if "error" in serverData and serverData["error"]["error_code"] == 15:
            raise Exception("CANT ACCESS MESSAGES WITH CURRENT TOKEN (CONSIDER RECEIVING YOUR OWN AND CALL setToken() )")
        self.__mLongPollInit = True
        self.__mLongPollTs = serverData["response"]["ts"]
        self.__mLongPollKey = serverData["response"]["key"]
        self.__mLongPollServer = serverData["response"]["server"]

    def longPoll(self, mode: int = 234, wait: int = 25, version: int = 3) -> dict:
        self.__checkAuth()
        if not self.__mLongPollInit:
            raise Exception("YOU NEED TO CALL setLongPollServer() BEFORE USING LONGPOLL")
        data = {
            "act": "a_check",
            "key": self.__mLongPollKey,
            "ts": self.__mLongPollTs,
            "wait": wait,
            "mode": mode,
            "version": version
        }
        updates = self.__mSession.post("https://"+self.__mLongPollServer, data = data).json()
        if "failed" in updates:
            print("BAD LONGPOLL RESPONSE, TRYING FIX...")
            if updates["failed"] == 2:
                print("BAD LONGPOLL KEY, TRYING RECEIVE NEW ONE...")
                self.setLongPollServer()
                data["key"] = self.__mLongPollKey
                data["ts"] = self.__mLongPollTs
                print("NEW KEY RECEIVED, REBOOTING...")
                updates = self.__mSession.post("https://" + self.__mLongPollServer, data=data).json()
                if not "failed" in updates:
                    print("SUCCESS")
                else:
                    raise Exception("LONGPOLL ERROR")

        self.__mLongPollTs = updates["ts"]
        return updates



