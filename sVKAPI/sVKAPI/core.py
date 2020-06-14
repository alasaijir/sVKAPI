from bs4 import BeautifulSoup
from requests import Session, Response
from datetime import datetime
from PIL import Image
from pickle import dump, load
from os import path
from base64 import b64encode, b64decode


class API:
    __mAccessToken = ""

    __mAPIClientID = 7249628
    __mAPIVersion = 5.103
    __mAPIBaseUrl = "https://api.vk.com/method/"

    __mSession = Session()

    __mLongPollTs = 0
    __mLongPollServer = ""
    __mLongPollKey = ""

    #Private

    def __saveSession(self):
        with open("curSession.enc", "wb") as f:
            dump(self.__mSession, f)
        return True

    def __loadSession(self) -> bool:
        if path.isfile("curSession.enc"):
            with open("curSession.enc", "rb") as f:
                self.__mSession = load(f)
            return True
        else:
            return False

    def __saveToken(self):
        with open("curToken.enc", "wb") as f:
            encryptedData = self.__mAccessToken + "\n"
            encryptedData += "CUSTOM_TOKEN_*_Lorem ipsum dolor sit amet, consectetur adipiscing elit, " \
                             "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim " \
                             "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo " \
                             "consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum " \
                             "dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, " \
                             "sunt in culpa qui officia deserunt mollit anim id est laborum."
            encryptedData = b64encode(b64encode(b64encode(encryptedData.encode("utf-8"))))
            f.write(encryptedData)

    def __loadToken(self) -> bool:
        if path.isfile("curToken.enc"):
            with open("curToken.enc", "rb") as f:
                lines = b64decode(b64decode(b64decode(f.read()))).decode("utf-8").split("\n")
                self.__mAccessToken = lines[0]
            return True
        else:
            return False

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
            fileName = "Captcha_" + str(datetime.now().strftime("%Y.%m.%d_%H.%M")) + ".jpg"
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
            pass
        elif "token" in kwargs:
            self.__mAccessToken = kwargs["token"]
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
        else:
            raise RuntimeError("NO REQUIRED DATA PASSED (token OR username & password)")
        self.__saveSession()
        self.__saveToken()

    def setToken(self, newToken: str):
        self.__mAccessToken = newToken
        self.__saveToken()

    def call(self, method:str, **kwargs) -> dict:
        data = {
            "access_token": self.__mAccessToken,
            "v": self.__mAPIVersion
        }

        for key, value in kwargs.items():
            data[key] = value

        return self.__mSession.post(self.__mAPIBaseUrl + method, data = data).json()

    def uploadDoc(self, fileType: str, fileName: str) -> dict:
        url = self.call("docs.getUploadServer", type=fileType)["response"]["upload_url"]
        files = {"file": open(fileName, "rb")}
        fileObj = self.__mSession.post(url, files=files).json()
        try:
            fileObj["file"]
        except KeyError:
            raise RuntimeError("FILE WAS NOT UPLOADED")
        return self.call("docs.save", file=fileObj["file"])

    def setLongPollServer(self, needPts: int = 0, lp_version: int = 3):
        serverData = self.call("messages.getLongPollServer", needPts = needPts, lp_version = lp_version)
        if "error" in serverData and serverData["error"]["error_code"] == 15:
            raise Exception("CANT ACCESS MESSAGES WITH CURRENT TOKEN (CONSIDER RECEIVING YOUR OWN AND CALL setToken() )")
        self.__mLongPollTs = serverData["response"]["ts"]
        self.__mLongPollKey = serverData["response"]["key"]
        self.__mLongPollServer = serverData["response"]["server"]

    def longPoll(self, mode: int = 202, wait: int = 25, version: int = 3) -> dict:
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
            if updates["failed"] == 2:
                self.setLongPollServer()
                data["key"] = self.__mLongPollKey
                data["ts"] = self.__mLongPollTs
                updates = self.__mSession.post("https://" + self.__mLongPollServer, data=data).json()
                if "failed" in updates:
                    raise RuntimeError("LONGPOLL ERROR")

        self.__mLongPollTs = updates["ts"]
        return updates

    def handleLongPollMessage(self, eventObj: dict) -> dict:
        if eventObj[0] != 4:
            raise RuntimeError("HANDLING NON-MESSAGE EVENT (EVENT CODE SHOULD BE 4)")
        return self.call("messages.getById", message_ids=eventObj[1], extended=1)["response"]["items"][0]



