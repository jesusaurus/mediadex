#!/usr/bin/python3

# Mediadex: Index media metadata into elasticsearch
# Copyright (C) 2019  K Jonathan Harker
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging

from elasticsearch_dsl import connections

from mediadex import Movie
from mediadex import Song
from mediadex.exc import IndexerException
from mediadex.indexer.movie import MovieIndexer
from mediadex.indexer.song import SongIndexer


class Item:
    def __init__(self, data):
        self.log = logging.getLogger('mediadex.indexer')
        gen = [t for t in data if t['track_type'] == 'General']
        if len(gen) > 1:
            raise IndexerException("More than one General track found")
        elif len(gen) == 0:
            raise IndexerException("No General track found")
        self.general = gen.pop()

        atracks = [t for t in data if t['track_type'] == 'Audio']
        self.audio_tracks = atracks
        acount = len(atracks)

        vtracks = [t for t in data if t['track_type'] == 'Video']
        self.video_tracks = vtracks
        vcount = len(vtracks)

        ttracks = [t for t in data if t['track_type'] == 'Text']
        self.text_tracks = ttracks
        tcount = len(ttracks)

        if vcount > 0 and acount > 0:
            self.dex_type = 'movie'
        elif vcount > 0:
            self.dex_type = 'image'
        elif acount == 1:
            self.dex_type = 'song'
        elif tcount == 1:
            self.dex_type = 'text'
        elif acount == 0 and vcount == 0 and tcount == 0:
            self.dex_type = 'empty'
        else:
            self.dex_type = 'unknown'


class Indexer:
    def __init__(self, host):
        self.item = None
        self.log = logging.getLogger('mediadex.indexer')
        connections.create_connection(hosts=[host], timeout=10)
        Song.init()
        Movie.init()

    def index(self, data):
        item = Item(data)

        filename = item.general['complete_name']

        if item.dex_type == 'empty':
            return

        elif item.dex_type == 'unknown':
            self.log.warning("Unknown format ({}, {}, {}), skipping {}".format(
                    len(item.video_tracks),
                    len(item.audio_tracks),
                    len(item.text_tracks),
                    filename)
            )

        elif item.dex_type == 'song':
            s = Song.search()
            r = s.query('match', filename=filename).execute()

            if r.hits.total.value == 0:
                self.index_song(item)
                self.log.info("Indexed new record for {}".format(filename))
            elif r.hits.total.value == 1:
                song = r.hits[0]
                self.index_song(item, song)
                self.log.info("Updated existing record for {}".format(
                        song.filename))
            else:
                self.log.warning("Found {} existing records for {}".format(
                        r.hits.total.value, filename))
                for h in r.hits:
                    self.log.debug(h.filename)

        elif item.dex_type == 'movie':
            s = Movie.search()
            r = s.query('match', filename=filename).execute()

            if r.hits.total.value == 0:
                self.index_movie(item)
                self.log.info("Indexed new record for {}".format(filename))
            elif r.hits.total.value == 1:
                movie = r.hits[0]
                self.index_movie(item, movie)
                self.log.info("Updated existing record for {}".format(
                        movie.filename))
            else:
                self.log.warning("Found {} existing records for {}".format(
                        r.hits.total.value, filename))
                self.log.debug(r.hits[0])
                self.log.debug(r.hits[1])

    def index_song(self, item, song=None):
        si = SongIndexer()
        si.index(item, song)

    def index_movie(self, item, movie=None):
        mi = MovieIndexer()
        mi.index(item, movie)
