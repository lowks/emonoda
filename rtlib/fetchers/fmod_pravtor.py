#####
#
#    rtfetch -- Plugin for http://pravtor.ru (based on rutracker.py)
#    Copyright (C) 2012  Devaev Maxim <mdevaev@gmail.com>
#    Copyright (C) 2013  Vitaly Lipatov <lav@etersoft.ru>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#####


import urllib.parse
import http.cookiejar
import re

from .. import fetcherlib


##### Public constants #####
FETCHER_NAME = "pravtor"
FETCHER_VERSION = 0

PRAVTOR_DOMAIN = "pravtor.ru"
PRAVTOR_URL = "http://%s" % (PRAVTOR_DOMAIN)
PRAVTOR_LOGIN_URL = "%s/login.php" % (PRAVTOR_URL)
PRAVTOR_VIEWTOPIC_URL = "%s/viewtopic.php" % (PRAVTOR_URL)
PRAVTOR_DL_URL = "%s/download.php" % (PRAVTOR_URL)
PRAVTOR_ENCODING = "cp1251"


##### Public classes #####
class Fetcher(fetcherlib.AbstractFetcher) :
    def __init__(self, *args_tuple, **kwargs_dict) :
        self.__comment_regexp = re.compile(r"http://pravtor\.(ru|spb\.ru)/viewtopic\.php\?p=(\d+)")

        self.__hash_regexp = re.compile(r"<span id=\"tor-hash\">([a-fA-F0-9]+)</span>")
        self.__loginform_regexp = re.compile(r"<!--login form-->")
        self.__torrent_id_regexp = re.compile(r"<a href=\"download.php\?id=(\d+)\" class=\"(leech|seed|gen)med\">")

        self.__cookie_jar = None
        self.__opener = None
        self.__torrent_id = None

        fetcherlib.AbstractFetcher.__init__(self, *args_tuple, **kwargs_dict)


    ### Public ###

    @classmethod
    def plugin(cls) :
        return FETCHER_NAME

    @classmethod
    def version(cls) :
        return FETCHER_VERSION

    ###

    def match(self, torrent) :
        return ( not self.__comment_regexp.match(torrent.comment() or "") is None )

    def ping(self) :
        opener = fetcherlib.buildTypicalOpener(proxy_url=self.proxyUrl())
        data = self.__readUrlRetry(PRAVTOR_URL, opener=opener).decode(PRAVTOR_ENCODING)
        self.assertSite("<img src=\"/images/pravtor_beta1.png\"" in data)

    def login(self) :
        self.assertNonAnonymous()
        self.__cookie_jar = http.cookiejar.CookieJar()
        self.__opener = fetcherlib.buildTypicalOpener(self.__cookie_jar, self.proxyUrl())
        try :
            self.__tryLogin()
        except :
            self.__cookie_jar = None
            self.__opener = None
            raise

    def loggedIn(self) :
        return ( not self.__opener is None )

    def torrentChanged(self, torrent) :
        self.assertMatch(torrent)
        self.__torrent_id = None
        return ( torrent.hash() != self.__fetchHash(torrent) )

    def fetchTorrent(self, torrent) :
        comment_match = self.__comment_regexp.match(torrent.comment() or "")
        self.assertFetcher(not comment_match is None, "No comment match")
        topic_id = comment_match.group(1)

        assert not self.__torrent_id is None, "Programming error, torrent_id == None"

        cookie = http.cookiejar.Cookie(
            version=0,
            name="bb_dl",
            value=topic_id,
            port=None,
            port_specified=False,
            domain="",
            domain_specified=False,
            domain_initial_dot=False,
            path="/",
            path_specified=True,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={ "HttpOnly" : None },
            rfc2109=False,
        )
        self.__cookie_jar.set_cookie(cookie)

        data = self.__readUrlRetry(PRAVTOR_DL_URL+("?id=%d" % (self.__torrent_id)), b"", {
                "Referer" : PRAVTOR_VIEWTOPIC_URL+("?t=%s" % (topic_id)),
                "Origin"  : "http://%s" % (PRAVTOR_DOMAIN),
            })
        self.assertValidTorrentData(data)
        return data


    ### Private ###

    def __tryLogin(self) :
        post_dict = {
            "login_username" : self.userName(),#.decode("utf-8").encode("cp1251"),
            "login_password" : self.passwd(),#.decode("utf-8").encode("cp1251"),
            "login"          : "\xc2\xf5\xee\xe4",
        }
        post_data = urllib.parse.urlencode(post_dict).encode(PRAVTOR_ENCODING)
        data = self.__readUrlRetry(PRAVTOR_LOGIN_URL, post_data).decode(PRAVTOR_ENCODING)
        self.assertLogin(self.__loginform_regexp.search(data) is None, "Invalid login or password")

    def __fetchHash(self, torrent) :
        data = self.__readUrlRetry(torrent.comment()).decode(PRAVTOR_ENCODING)

        hash_match = self.__hash_regexp.search(data)
        self.assertFetcher(not hash_match is None, "Hash is not found")

        torrent_id = self.__torrent_id_regexp.search(data)
        self.assertFetcher(not torrent_id is None, "Torrent ID is not found")
        self.__torrent_id = int(torrent_id.group(1))

        return hash_match.group(1).lower()

    def __readUrlRetry(self, url, data = None, headers_dict = None, opener = None) :
        opener = ( opener or self.__opener )
        assert not opener is None

        headers_dict = ( headers_dict or {} )
        user_agent = self.userAgent()
        if not user_agent is None :
            headers_dict.setdefault("User-Agent", user_agent)

        return fetcherlib.readUrlRetry(opener, url, data,
            headers_dict=headers_dict,
            timeout=self.timeout(),
            retries=self.urlRetries(),
            sleep_time=self.urlSleepTime(),
        )
