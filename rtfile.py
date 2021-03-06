#!/usr/bin/env python3
#
#    rtfile -- Show torrents metadata
#    Copyright (C) 2013  Devaev Maxim <mdevaev@gmail.com>
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


import socket
import operator
import itertools
import datetime

from ulib import fmt

from rtlib import tfile
from rtlib import fs
from rtlib import clients
from rtlib import clientlib
from rtlib import config



##### Public methods #####
def makeFilesList(files_dict, depth = 0, prefix = "\t") :
    text = ""
    for (key, value_dict) in sorted(files_dict.items(), key=operator.itemgetter(0)) :
        text += prefix + "*   " * depth + key + "\n"
        text += makeFilesList(value_dict, depth + 1)
    return text


###
def formatSizePretty(torrent) :
    return fmt.formatSize(torrent.size())

def formatAnnounce(torrent) :
    return ( torrent.announce() or "" )

def formatAnnounceList(torrent) :
    return list(itertools.chain.from_iterable(torrent.announceList()))

def formatAnnounceListPretty(torrent) :
    return " ".join(formatAnnounceList(torrent))

def formatCreationDate(torrent) :
    return ( torrent.creationDate() or "" )

def formatCreationDatePretty(torrent) :
    return str( datetime.datetime.utcfromtimestamp(torrent.creationDate()) if torrent.creationDate() is not None else "" )

def formatCreatedBy(torrent) :
    return ( torrent.createdBy() or "" )

def formatProvides(torrent) :
    return sorted(torrent.files())

def formatIsPrivate(torrent) :
    return str(int(torrent.isPrivate()))

def formatIsPrivatePretty(torrent) :
    return ( "yes" if torrent.isPrivate() else "no" )

def formatComment(torrent) :
    return ( torrent.comment() or "" )

def formatClientPath(torrent, client) :
    assert client is not None, "Required client"
    try :
        return client.fullPath(torrent)
    except clientlib.NoSuchTorrentError :
        return ""

def formatClientPrefix(torrent, client) :
    assert client is not None, "Required client"
    try :
        return client.dataPrefix(torrent)
    except clientlib.NoSuchTorrentError :
        return ""

def formatFilesList(torrent) :
    return makeFilesList(fs.treeListToDict(torrent.files()))

def printPrettyMeta(torrent, client) :
    print("Path:         ", torrent.path())
    print("Name:         ", torrent.name())
    print("Hash:         ", torrent.hash())
    print("Size:         ", formatSizePretty(torrent))
    print("Announce:     ", formatAnnounce(torrent))
    print("Announce list:", formatAnnounceListPretty(torrent))
    print("Creation date:", formatCreationDatePretty(torrent))
    print("Created by:   ", formatCreatedBy(torrent))
    print("Private:      ", formatIsPrivatePretty(torrent))
    print("Comment:      ", formatComment(torrent))
    if client is not None :
        print("Client path:  ", formatClientPath(torrent, client))
    if torrent.isSingleFile() :
        print("Provides:     ", tuple(torrent.files())[0])
    else :
        print("Provides:\n%s" % (formatFilesList(torrent)), end=' ')


##### Main #####
def main() :
    parser = config.makeParser(description="Show torrents metadata")
    print_options_list = []
    for (print_option, print_dest, print_method) in (
            ("--path",                 "print_path_flag",                 lambda torrent : torrent.path()),
            ("--name",                 "print_name_flag",                 lambda torrent : torrent.name()),
            ("--hash",                 "print_hash_flag",                 lambda torrent : torrent.hash()),
            ("--comment",              "print_comment_flag",              formatComment),
            ("--size",                 "print_size_flag",                 lambda torrent : str(torrent.size())),
            ("--size-pretty",          "print_size_pretty_flag",          formatSizePretty),
            ("--announce",             "print_announce_flag",             formatAnnounce),
            ("--announce-list",        "print_announce_list_flag",        formatAnnounceList),
            ("--announce-list-pretty", "print_announce_list_pretty_flag", formatAnnounceListPretty),
            ("--creation-date",        "print_creation_date_flag",        formatCreationDate),
            ("--creation-date-pretty", "print_creation_date_pretty_flag", formatCreationDatePretty),
            ("--created-by",           "print_created_by_flag",           formatCreatedBy),
            ("--provides",             "print_provides_flag",             formatProvides),
            ("--is-private",           "print_is_private_flag",           formatIsPrivate),
            ("--is-private-pretty",    "print_is_private_pretty_flag",    formatIsPrivatePretty),
            ("--client-path",          "print_client_path_flag",          lambda torrent : formatClientPath(torrent, client)),
            ("--client-prefix",        "print_client_prefix_flag",        lambda torrent : formatClientPrefix(torrent, client)),
            ("--make-magnet",          "print_magnet_flag",               lambda torrent : torrent.magnet(options.magnet_fields_list)),
        ) :
        print_options_list.append((
                parser.addRawArgument(print_option, dest=print_dest, action="store_true"),
                print_method,
            ))
    parser.addRawArgument("--without-headers", dest="without_headers_flag", action="store_true")
    parser.addRawArgument("--magnet-fields",   dest="magnet_fields_list",   nargs="+",  default=None, metavar="<fields>", choices=tfile.ALL_MAGNET_FIELDS)
    parser.addArguments(
        config.ARG_TIMEOUT,
        config.ARG_CLIENT,
        config.ARG_CLIENT_URL,
    )
    parser.addRawArgument("torrents_list", type=str, nargs="+")
    options = parser.sync((config.SECTION_MAIN, config.SECTION_RTFILE))[0]

    socket.setdefaulttimeout(options.timeout)

    torrents_list = [ tfile.Torrent(item) for item in options.torrents_list ]

    client = None
    if options.client_name is not None :
        client_class = clients.CLIENTS_MAP[options.client_name]
        client = client_class(options.client_url)

    to_print_list = [
        (print_option.option_strings[0][2:], print_method)
        for (print_option, print_method) in print_options_list
        if getattr(options, print_option.dest)
    ]
    for torrent in torrents_list :
        if len(to_print_list) == 0 :
            printPrettyMeta(torrent, client)
        else :
            for (header, print_method) in to_print_list :
                prefix = ( "" if options.without_headers_flag else header + ": " )
                retval = print_method(torrent)
                if isinstance(retval, (list, tuple)) :
                    for item in retval :
                        print(prefix + item)
                else :
                    print(prefix + retval)
        if len(torrents_list) > 1 :
            print()


###
if __name__ == "__main__" :
    main()

