"""OOI3 API handler - asynch forward proxy for game API requests
"""

import aiohttp
import aiohttp.web
import asyncio
from aiohttp_session import get_session

from base import config


class APIHandler:
    """ This class handles the forward proxy for API calls in game"""

    def __init__(self):
        """ Init the proxy service

        :return: none
        """
        if config.proxy:
            self.connector = aiohttp.ProxyConnector(proxy=config.proxy, force_close=False)
        else:
            self.connector = None

        # Re-init server banner and api_start2 cache
        self.api_start2 = None
        self.worlds = {}

    @asyncio.coroutine
    def world_image(self, request):
        """ Special handling for server banner
		URLs for server banner are generated dynamically by the flash client based on the domain hosting OOI
		This function is necessary or the banner will not be displayed properly
		
        :param request: aiohttp.web.Request
        :return: aiohttp.web.HTTPFound or aiohttp.web.HTTPBadRequest
        """
        size = request.match_info['size']
        session = yield from get_session(request)
        world_ip = session['world_ip']
        if world_ip:
            ip_sections = map(int, world_ip.split('.'))
            image_name = '_'.join([format(x, '03') for x in ip_sections]) + '_' + size
            if image_name in self.worlds:
                body = self.worlds[image_name]
            else:
                url = 'http://203.104.209.102/kcs/resources/image/world/' + image_name + '.png'
                coro = aiohttp.get(url, connector=self.connector)
                try:
                    response = yield from asyncio.wait_for(coro, timeout=5)
                except asyncio.TimeoutError:
                    return aiohttp.web.HTTPBadRequest()
                body = yield from response.read()
                self.worlds[image_name] = body
            return aiohttp.web.Response(body=body, headers={'Content-Type': 'image/png', 'Cache-Control': 'no-cache'})
        else:
            return aiohttp.web.HTTPBadRequest()

    @asyncio.coroutine
    def api(self, request):
        """ Forward API requests between game client and server

        :param request: aiohttp.web.Request
        :return: aiohttp.web.Response or aiohttp.web.HTTPBadRequest
        """
        action = request.match_info['action']
        session = yield from get_session(request)
        world_ip = session['world_ip']
        if world_ip:
            if action == 'api_start2' and self.api_start2 is not None:
                return aiohttp.web.Response(body=self.api_start2,
                                            headers=aiohttp.MultiDict({'Content-Type': 'text/plain'}))
            else:
                referrer = request.headers.get('REFERER')
                referrer = referrer.replace(request.host, world_ip)
                referrer = referrer.replace('https://', 'http://')
                url = 'http://' + world_ip + '/kcsapi/' + action
                headers = aiohttp.MultiDict({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
                    'Origin': 'http://' + world_ip + '/',
                    'Referer': referrer,
                    'X-Requested-With': 'ShockwaveFlash/18.0.0.232'
                })
                data = yield from request.post()
                coro = aiohttp.post(url, data=data, headers=headers, connector=self.connector)
                try:
                    response = yield from asyncio.wait_for(coro, timeout=5)
                except asyncio.TimeoutError:
                    return aiohttp.web.HTTPBadRequest()
                body = yield from response.read()
                if action == 'api_start2' and len(body) > 100000:
                    self.api_start2 = body
                return aiohttp.web.Response(body=body, headers=aiohttp.MultiDict({'Content-Type': 'text/plain'}))
        else:
            return aiohttp.web.HTTPBadRequest()
