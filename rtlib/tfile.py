#####
#
#    rtfetch -- Update rtorrent files from popular trackers
#    Copyright (C) 2012  Devaev Maxim <mdevaev@gmail.com>
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


import sys
import os
import base64
import hashlib
import urllib.parse
import itertools

from ulib import ui
import ulib.ui.term # pylint: disable=W0611

from .thirdparty import bcoding


##### Public constants #####
ALL_MAGNET_FIELDS = ("dn", "tr", "xl")


##### Public methods #####
encodeStruct = bcoding.bencode # pylint: disable=C0103
decodeData = bcoding.bdecode # pylint: disable=C0103


###
def torrents(src_dir_path, extension = ".torrent", abs_flag = False) :
    torrents_dict = {}
    for name in os.listdir(src_dir_path) :
        if not name.endswith(extension) :
            continue
        try :
            path = os.path.join(src_dir_path, name)
            if abs_flag :
                path = os.path.abspath(path)
            torrent = Torrent(path)
        except TypeError :
            torrent = None
        torrents_dict[name] = torrent
    return torrents_dict

def indexed(src_dir_path, prefix = "") :
    files_dict = {}
    for torrent in filter(None, torrents(src_dir_path).values()) :
        for path in torrent.files() :
            full_path = os.path.join(prefix, path)
            files_dict.setdefault(full_path, set())
            files_dict[full_path].add(torrent)
    return files_dict

def isValidTorrentData(data) :
    try :
        return isinstance(decodeData(data), dict) # Must be True
    except TypeError :
        return False


###
def diff(old_torrent, new_torrent) :
    assert isinstance(old_torrent, (Torrent, dict))
    assert isinstance(new_torrent, (Torrent, dict))
    old_dict = ( old_torrent.files() if isinstance(old_torrent, Torrent) else old_torrent )
    new_dict = ( new_torrent.files() if isinstance(new_torrent, Torrent) else new_torrent )

    old_set = set(old_dict)
    new_set = set(new_dict)

    modified_set = set()
    modified_type_set = set()
    for path in old_set.intersection(new_set) :
        old_attrs_dict = old_dict[path]
        new_attrs_dict = new_dict[path]

        real = len(tuple(filter(None, (new_attrs_dict, old_attrs_dict))))
        if real == 0 :
            continue
        elif real == 1 :
            modified_type_set.add(path)
            continue

        if old_attrs_dict["size"] != new_attrs_dict["size"] :
            modified_set.add(path)

    return (
        new_set.difference(old_set), # Added
        old_set.difference(new_set), # Removed
        modified_set,
        modified_type_set,
    )

def printDiff(diff_tuple, prefix = "", use_colors_flag = True, force_colors_flag = False, output = sys.stdout) :
    # XXX: See man 4 console_codes
    (added_set, removed_set, modified_set, modified_type_set) = diff_tuple
    for (sign, color, files_set) in (
            ("-", (31, 1), removed_set),
            ("+", (32, 1), added_set),
            ("~", (36, 1), modified_set),
            ("?", (33, 1), modified_type_set),
        ) :
        for item in sorted(files_set) :
            if use_colors_flag :
                sign = ui.term.colored(color, sign, force_colors_flag=force_colors_flag, output=output)
            print("%s%s %s" % (prefix, sign, item), file=output)


###
def isSingleFile(bencode_dict) :
    return ( "files" not in bencode_dict["info"] )

def torrentSize(bencode_dict) :
    if isSingleFile(bencode_dict) :
        return bencode_dict["info"]["length"]
    else :
        size = 0
        for file_dict in bencode_dict["info"]["files"] :
            size += file_dict["length"]
        return size

def torrentHash(bencode_dict) :
    return hashlib.sha1(encodeStruct(bencode_dict["info"])).hexdigest().lower()


###
def scrapeHash(torrent_hash) :
    scrape_hash = ""
    for index in range(0, len(torrent_hash), 2) :
        scrape_hash += "%{0}".format(torrent_hash[index:index + 2])
    return scrape_hash

def makeMagnet(bencode_dict, extra_list = None) :
    # XXX: http://stackoverflow.com/questions/12479570/given-a-torrent-file-how-do-i-generate-a-magnet-link-in-python
    info_sha1 = hashlib.sha1(encodeStruct(bencode_dict["info"]))
    info_digest = info_sha1.digest() # pylint: disable=E1121
    b32_hash = base64.b32encode(info_digest)

    magnet = "magnet:?xt=%s" % (urllib.parse.quote_plus("urn:btih:%s" % (b32_hash)))
    if "dn" in extra_list :
        magnet += "&dn=" + urllib.parse.quote_plus(bencode_dict["info"]["name"])
    if "tr" in extra_list :
        announce_list = bencode_dict.get("announce-list", [])
        if "announce" in bencode_dict :
            announce_list.append([bencode_dict["announce"]])
        for announce in set(itertools.chain.from_iterable(announce_list)) :
            magnet += "&tr=" + urllib.parse.quote_plus(announce)
    if "xl" in extra_list :
        magnet += "&xl=%d" % (torrentSize(bencode_dict))

    return magnet


##### Public classes #####
class Torrent(object) :
    def __init__(self, torrent_file_path = None) :
        # XXX: File format: https://wiki.theory.org/BitTorrentSpecification

        self._torrent_file_path = None
        self._bencode_dict = None
        self._hash = None
        self._scrape_hash = None

        if torrent_file_path is not None :
            self.loadFile(torrent_file_path)


    ### Public ###

    def loadFile(self, torrent_file_path) :
        with open(torrent_file_path, "rb") as torrent_file :
            self.loadData(torrent_file.read(), torrent_file_path)
        return self

    def loadData(self, data, torrent_file_path = None) :
        self._initData(data)
        self._torrent_file_path = torrent_file_path
        return self

    ###

    def path(self) :
        return self._torrent_file_path

    def bencode(self) :
        return self._bencode_dict

    ###

    def name(self) :
        return self._bencode_dict["info"]["name"]

    def comment(self) :
        return self._bencode_dict.get("comment")

    def creationDate(self) :
        return self._bencode_dict.get("creation date")

    def createdBy(self) :
        return self._bencode_dict.get("created by")

    def announce(self) :
        return self._bencode_dict.get("announce")

    def announceList(self) :
        return self._bencode_dict.get("announce-list", [])

    def isPrivate(self) :
        return bool(self._bencode_dict["info"].get("private", 0))

    ###

    def hash(self) :
        if self._hash is None :
            self._hash = torrentHash(self._bencode_dict)
        return self._hash

    def scrapeHash(self) :
        if self._scrape_hash is None :
            self._scrape_hash = scrapeHash(self.hash())
        return self._scrape_hash

    ###

    def magnet(self, extra_list) :
        return makeMagnet(self._bencode_dict, extra_list)

    ###

    def isSingleFile(self) :
        return isSingleFile(self._bencode_dict)

    def files(self, prefix = "") :
        base = os.path.join(prefix, self._bencode_dict["info"]["name"])
        if self.isSingleFile() :
            return { base : self._fileAttrs(self._bencode_dict["info"]) }
        else :
            files_dict = { base : None }
            for f_dict in self._bencode_dict["info"]["files"] :
                name = None
                for index in range(len(f_dict["path"])) :
                    name = os.path.join(base, os.path.sep.join(f_dict["path"][0:index + 1]))
                    files_dict[name] = None
                assert name is not None
                files_dict[name] = self._fileAttrs(f_dict)
            return files_dict

    def size(self) :
        return torrentSize(self._bencode_dict)


    ### Private ###

    def _initData(self, data) :
        self._bencode_dict = decodeData(data)
        self._hash = None
        self._scrape_hash = None

    def _fileAttrs(self, file_dict) :
        return { "size" : file_dict["length"] }

