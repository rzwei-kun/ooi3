"""OOI3 Service Handler
Only POST requests with valid login_id and password are accepted, returns HTTP 400 on error
"""

import asyncio
import aiohttp
import aiohttp.web
import json

from auth.exceptions import OOIAuthException
from auth.kancolle import KancolleAuth


class ServiceHandler:
    """This class defines the login service invoked twice during auth"""

    @asyncio.coroutine
    def get_osapi(self, request):
        """Fetch osapi URL and output in a JSON-format tuple

        :param request: aiohttp.web.Request
        :return: aiohttp.web.Response or aiohttp.web.HTTPBadRequest
        """
        data = yield from request.post()
        login_id = data.get('login_id', None)
        password = data.get('password', None)
        if login_id and password:
            headers = aiohttp.MultiDict({'Content-Type': 'application/json'})
            kancolle = KancolleAuth(login_id, password)
            try:
                osapi_url = yield from kancolle.get_osapi()
                result = {'status': 1,
                          'osapi_url': osapi_url}
            except OOIAuthException as e:
                result = {'status': 0,
                          'message': e.message}
            return aiohttp.web.Response(body=json.dumps(result).encode(), headers=headers)
        else:
            return aiohttp.web.HTTPBadRequest()

    @asyncio.coroutine
    def get_flash(self, request):
        """Fetch flash URL and output in a JSON-format tuple
        Success if status == 1. error if status == 0

        :param request: aiohttp.web.Request
        :return: aiohttp.web.Response or aiohttp.web.HTTPBadRequest
        """
        data = yield from request.post()
        login_id = data.get('login_id', None)
        password = data.get('password', None)
        if login_id and password:
            headers = aiohttp.MultiDict({'Content-Type': 'application/json'})
            kancolle = KancolleAuth(login_id, password)
            try:
                flash_url = yield from kancolle.get_flash()
                result = {'status': 1,
                          'flash_url': flash_url}
            except OOIAuthException as e:
                result = {'status': 0,
                          'message': e.message}
            return aiohttp.web.Response(body=json.dumps(result).encode(), headers=headers)
        else:
            return aiohttp.web.HTTPBadRequest()
