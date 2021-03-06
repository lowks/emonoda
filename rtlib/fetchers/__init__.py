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


from .. import plugin

from . import fmod_rutor
from . import fmod_rutracker
from . import fmod_nnmclub
from . import fmod_ponytracker
from . import fmod_pravtor


##### Public constants #####
FETCHERS_MAP = plugin.mapObjects(
    fmod_rutor.Fetcher,
    fmod_rutracker.Fetcher,
    fmod_nnmclub.Fetcher,
    fmod_ponytracker.Fetcher,
    fmod_pravtor.Fetcher,
)

