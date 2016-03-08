"""OOI3 Frontend Handler - Interactive User Interface
"""

import asyncio
import aiohttp.web
import aiohttp_jinja2
from aiohttp_session import get_session

from auth.kancolle import KancolleAuth, OOIAuthException


class FrontEndHandler:
    """This class handles browser requests"""

    def clear_session(self, session):
        if 'api_token' in session:
            del session['api_token']
        if 'api_starttime' in session:
            del session['api_starttime']
        if 'world_ip' in session:
            del session['world_ip']

    @aiohttp_jinja2.template('form.html')
    @asyncio.coroutine
    def form(self, request):
        """Display login form

        :param request: aiohttp.web.Request
        :return: dict
        """
        session = yield from get_session(request)
        if 'mode' in session:
            mode = session['mode']
        else:
            session['mode'] = 1
            mode = 1

        return {'mode': mode}

    @asyncio.coroutine
    def login(self, request):
        """Submit the request and return responses

        :param request: aiohttp.web.Request
        :return: aiohttp.web.HTTPFound or aiohttp.web.Response
        """
        post = yield from request.post()
        session = yield from get_session(request)

        login_id = post.get('login_id', None)
        password = post.get('password', None)
        mode = int(post.get('mode', 1))

        session['mode'] = mode

        if login_id and password:
            kancolle = KancolleAuth(login_id, password)
            if mode in (1, 2, 3):
                try:
                    yield from kancolle.get_flash()
                    session['api_token'] = kancolle.api_token
                    session['api_starttime'] = kancolle.api_starttime
                    session['world_ip'] = kancolle.world_ip
                    if mode == 2:
                        return aiohttp.web.HTTPFound('/kcv')
                    elif mode == 3:
                        return aiohttp.web.HTTPFound('/poi')
                    else:
                        return aiohttp.web.HTTPFound('/kancolle')

                except OOIAuthException as e:
                    context = {'errmsg': e.message, 'mode': mode}
                    return aiohttp_jinja2.render_template('form.html', request, context)
            elif mode == 4:
                try:
                    osapi_url = yield from kancolle.get_osapi()
                    session['osapi_url'] = osapi_url
                    return aiohttp.web.HTTPFound('/connector')
                except OOIAuthException as e:
                    context = {'errmsg': e.message, 'mode': mode}
                    return aiohttp_jinja2.render_template('form.html', request, context)
            else:
                raise aiohttp.web.HTTPBadRequest()
        else:
            context = {'errmsg': 'Please enter your login name and password', 'mode': mode}
            return aiohttp_jinja2.render_template('form.html', request, context)

    @asyncio.coroutine
    def normal(self, request):
        """Standard game page with a 800x480 flash embed. 
		Auto-redirect to front page if one or more parameters are missing from: 
		api_token、api_starttime or world_ip

        :param request: aiohttp.web.Request
        :return: aiohttp.web.Response or aiohttp.web.HTTPFound
        """
        session = yield from get_session(request)
        token = session.get('api_token', None)
        starttime = session.get('api_starttime', None)
        world_ip = session.get('world_ip', None)
        if token and starttime and world_ip:
            context = {'scheme': request.scheme,
                       'host': request.host,
                       'token': token,
                       'starttime': starttime}
            return aiohttp_jinja2.render_template('normal.html', request, context)
        else:
            self.clear_session(session)
            return aiohttp.web.HTTPFound('/')

    @asyncio.coroutine
    def kcv(self, request):
        """iFrame wrapper for viewers

        :param request: aiohttp.web.Request
        :return: aiohttp.web.Response or aiohttp.web.HTTPFound
        """
        session = yield from get_session(request)
        token = session.get('api_token', None)
        starttime = session.get('api_starttime', None)
        world_ip = session.get('world_ip', None)
        if token and starttime and world_ip:
            return aiohttp_jinja2.render_template('kcv.html', request, context={})
        else:
            self.clear_session(session)
            return aiohttp.web.HTTPFound('/')

    @asyncio.coroutine
    def flash(self, request):
        """iFrame embed for viewers

        :param request: aiohttp.web.Request
        :return: aiohttp.web.Response or aiohttp.web.HTTPFound
        """
        session = yield from get_session(request)
        token = session.get('api_token', None)
        starttime = session.get('api_starttime', None)
        world_ip = session.get('world_ip', None)
        if token and starttime and world_ip:
            context = {'scheme': request.scheme,
                       'host': request.host,
                       'token': token,
                       'starttime': starttime}
            return aiohttp_jinja2.render_template('flash.html', request, context)
        else:
            self.clear_session(session)
            return aiohttp.web.HTTPFound('/')

    @asyncio.coroutine
    def poi(self, request):
        """Fullscreen flash embed for poi and mobile

        :param request: aiohttp.web.Request
        :return: aiohttp.web.Response or aiohttp.web.HTTPFound
        """
        session = yield from get_session(request)
        token = session.get('api_token', None)
        starttime = session.get('api_starttime', None)
        world_ip = session.get('world_ip', None)
        if token and starttime and world_ip:
            context = {'scheme': request.scheme,
                       'host': request.host,
                       'token': token,
                       'starttime': starttime}
            return aiohttp_jinja2.render_template('poi.html', request, context)
        else:
            self.clear_session(session)
            return aiohttp.web.HTTPFound('/')

    @asyncio.coroutine
    def connector(self, request):
        """Direct connection via osapi.dmm.com url

        :param request: aiohttp.web.Request
        :return: aiohttp.web.Response or aiohttp.web.HTTPFound
        """
        session = yield from get_session(request)
        osapi_url = session.get('osapi_url', None)
        if osapi_url:
            context = {'osapi_url': osapi_url}
            return aiohttp_jinja2.render_template('connector.html', request, context)
        else:
            self.clear_session(session)
            return aiohttp.web.HTTPFound('/')

    @asyncio.coroutine
    def logout(self, request):
        """ Log out the current user
        clear all session information and redirect to front page

        :return: aiohttp.web.HTTPFound
        """
        session = yield from get_session(request)
        self.clear_session(session)
        return aiohttp.web.HTTPFound('/')
