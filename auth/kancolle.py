"""This class handles authenitcaton specific to the PC version of Kantai Collection hosted on dmm.com"""

import aiohttp
import asyncio
import json
import re
import time
from urllib.parse import urlparse, parse_qs

from base import config
from auth.exceptions import OOIAuthException


class KancolleAuth:
    """This class handles authenitcaton specific to the PC version of Kantai Collection hosted on dmm.com"""

    # Define URLs used for auth
    urls = {'login': 'https://www.dmm.com/my/-/login/',
            'ajax': 'https://www.dmm.com/my/-/login/ajax-get-token/',
            'auth': 'https://www.dmm.com/my/-/login/auth/',
            'game': 'http://www.dmm.com/netgame/social/-/gadgets/=/app_id=854854/',
            'make_request': 'http://osapi.dmm.com/gadgets/makeRequest',
            'get_world': 'http://203.104.209.7/kcsapi/api_world/get_id/%s/1/%d',
            'get_flash': 'http://%s/kcsapi/api_auth_member/dmmlogin/%s/1/%d',
            'flash': 'http://%s/kcs/mainD2.swf?api_token=%s&amp;api_starttime=%d'}

    # IP address of game servers
    world_ip_list = (
        "203.104.209.71",
        "203.104.209.87",
        "125.6.184.16",
        "125.6.187.205",
        "125.6.187.229",
        "125.6.187.253",
        "125.6.188.25",
        "203.104.248.135",
        "125.6.189.7",
        "125.6.189.39",
        "125.6.189.71",
        "125.6.189.103",
        "125.6.189.135",
        "125.6.189.167",
        "125.6.189.215",
        "125.6.189.247",
        "203.104.209.23",
        "203.104.209.39",
        "203.104.209.55",
        "203.104.209.102",
    )

    # Define user-agent, default is IE11.0 on Windows 7 x64
    user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko'

    # RegEx patterns for parsing auth messages
    patterns = {'dmm_token': re.compile(r'"DMM_TOKEN", "([\d|\w]+)"'),
                'token': re.compile(r'"token": "([\d|\w]+)"'),
                'reset': re.compile(r'認証エラー'),
                'osapi': re.compile(r'URL\W+:\W+"(.*)",')}

    def __init__(self, login_id, password):
        """ Define auth function __init__() with `login_id`和`password`
        'login_id' can be the email address used for registration or the unique dmm.com account ID

        :param login_id: str
        :param password: str
        :return: none
        """

        # Initialise auth variables
        self.login_id = login_id
        self.password = password

        # Init aiohttp session, use proxy if configured
        if config.proxy:
            self.connector = aiohttp.ProxyConnector(proxy=config.proxy, force_close=False)
        else:
            self.connector = None
        self.session = aiohttp.ClientSession(connector=self.connector)
        self.headers = {'User-Agent': self.user_agent}

        # Re-init all variables for auth
        self.dmm_token = None
        self.token = None
        self.idKey = None
        self.pwdKey = None
        self.owner = None
        self.osapi_url = None
        self.world_id = None
        self.world_ip = None
        self.api_token = None
        self.api_starttime = None
        self.flash = None

    def __del__(self):
        """Define function to close this session

        :return: none
        """
        self.session.close()

    @asyncio.coroutine
    def _request(self, url, method='GET', data=None, timeout_message='Connection timed out', timeout=10):
        """Query remote server via asyncio.wait_for, 'timeout' defined in seconds

        :param url: str
        :param method: str
        :param data: dict
        :param timeout_message: str
        :param timeout: int
        :return: generator
        """
        try:
            response = yield from asyncio.wait_for(self.session.request(method, url, data=data, headers=self.headers),
                                                   timeout)
            return response
        except asyncio.TimeoutError:
            raise OOIAuthException(timeout_message)

    @asyncio.coroutine
    def _get_dmm_tokens(self):
        """Parse login response and obtain dmm_token and token, return values to function

        :return: tuple
        """
        response = yield from self._request(self.urls['login'], method='GET', data=None,
                                            timeout_message='Error: Cannot connect to dmm.com')
        html = yield from response.text()

        m = self.patterns['dmm_token'].search(html)
        if m:
            self.dmm_token = m.group(1)
        else:
            raise OOIAuthException('Error: Failed to query dmm_token')

        m = self.patterns['token'].search(html)
        if m:
            self.token = m.group(1)
        else:
            raise OOIAuthException('Error: Failed to query token')

        return self.dmm_token, self.token

    @asyncio.coroutine
    def _get_ajax_token(self):
        """Raise an AJAX query for 'token', 'idKey' and 'pwdKey'

        :return: tuple
        """
        self.headers.update({'Origin': 'https://www.dmm.com',
                             'Referer': self.urls['login'],
                             'DMM_TOKEN': self.dmm_token,
                             'X-Requested-With': 'XMLHttpRequest'})
        data = {'token': self.token}
        response = yield from self._request(self.urls['ajax'], method='POST', data=data,
                                       timeout_message='Error: AJAX query failed')
        j = yield from response.json()
        self.token = j['token']
        self.idKey = j['login_id']
        self.pwdKey = j['password']

        return self.token, self.idKey, self.pwdKey

    @asyncio.coroutine
    def _get_osapi_url(self):
        """Game auth using dmm.com login tokens

        :return: str
        """
        del self.headers['DMM_TOKEN']
        del self.headers['X-Requested-With']
        data = {'login_id': self.login_id,
                'password': self.password,
                'token': self.token,
                self.idKey: self.login_id,
                self.pwdKey: self.password}
        response = yield from self._request(self.urls['auth'], method='POST', data=data,
                                       timeout_message='Error: Authentication Timed Out')
        html = yield from response.text()
        m = self.patterns['reset'].search(html)
        if m:
            raise OOIAuthException('Error: Password Reset Prompt Detected - Please visit dmm.com to reset your password')

        response = yield from self._request(self.urls['game'],
                                       timeout_message='Error: Connection Timed Out')
        html = yield from response.text()
        m = self.patterns['osapi'].search(html)
        if m:
            self.osapi_url = m.group(1)
        else:
            raise OOIAuthException('Wrong Username or Password')

        return self.osapi_url

    @asyncio.coroutine
    def _get_world(self):
        """Query osapi.dmm.com for the current user's game server information

        :return: tuple
        """
        qs = parse_qs(urlparse(self.osapi_url).query)
        self.owner = qs['owner'][0]
        self.st = qs['st'][0]
        url = self.urls['get_world'] % (self.owner, int(time.time()*1000))
        self.headers['Referer'] = self.osapi_url
        response = yield from self._request(url, timeout_message='Error: Server list is unavailable')
        html = yield from response.text()
        svdata = json.loads(html[7:])
        if svdata['api_result'] == 1:
            self.world_id = svdata['api_data']['api_world_id']
            self.world_ip = self.world_ip_list[self.world_id-1]
        else:
            raise OOIAuthException('Error: Server information is unavailable')

        return self.world_id, self.world_ip, self.st

    @asyncio.coroutine
    def _get_api_token(self):
        """Construct an API link to the game

        :return: tuple
        """
        url = self.urls['get_flash'] % (self.world_ip, self.owner, int(time.time()*1000))
        data = {'url': url,
                'httpMethod': 'GET',
                'authz': 'signed',
                'st': self.st,
                'contentType': 'JSON',
                'numEntries': '3',
                'getSummaries': 'false',
                'signOwner': 'true',
                'signViewer': 'true',
                'gadget': 'http://203.104.209.7/gadget.xml',
                'container': 'dmm'}
        response = yield from self._request(self.urls['make_request'], method='POST', data=data,
                                       timeout_message='Error: make_request timed out')
        html = yield from response.text()
        svdata = json.loads(html[27:])
        if svdata[url]['rc'] != 200:
            raise OOIAuthException('Error: API token unavailable')
        svdata = json.loads(svdata[url]['body'][7:])
        if svdata['api_result'] != 1:
            raise OOIAuthException('Error: API token unavailable')
        self.api_token = svdata['api_token']
        self.api_starttime = svdata['api_starttime']
        self.flash = self.urls['flash'] % (self.world_ip, self.api_token, self.api_starttime)

        return self.api_token, self.api_starttime, self.flash

    @asyncio.coroutine
    def get_osapi(self):
        """Fetch osapi URL and return

        :return: str
        """
        yield from self._get_dmm_tokens()
        yield from self._get_ajax_token()
        yield from self._get_osapi_url()
        return self.osapi_url

    @asyncio.coroutine
    def get_flash(self):
        """Fetch flash URL and return

        :return: str
        """
        yield from self.get_osapi()
        yield from self._get_world()
        yield from self._get_api_token()
        return self.flash
