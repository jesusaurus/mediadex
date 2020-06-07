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
import os.path

from elasticsearch_dsl import connections
from elasticsearch_dsl import FacetedSearch
from elasticsearch_dsl import TermsFacet

from mediadex import AudioStream
from mediadex import Movie
from mediadex import Song
from mediadex import TextStream
from mediadex import VideoStream
from mediadex.exc import IndexerException
from mediadex.indexer.movie import MovieIndexer
from mediadex.indexer.song import SongIndexer

LOG = logging.getLogger('mediadex.indexer')


class Item:
    def __init__(self, data):
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

    def base_track(self, track, stream):
        if 'duration' in track:
            try:
                stream.duration = float(track['duration'])
            except ValueError as exc:
                if LOG.isEnabledFor(logging.INFO):
                    LOG.exception(exc)
                else:
                    LOG.warn(str(exc))

        if 'format' in track:
            stream.codec = track['format']
        if 'format_profile' in track:
            stream.codec_profile = track['format_profile']
        if 'language' in track:
            stream.language = track['language']
        if 'internet_media_type' in track:
            stream.mime_type = track['internet_media_type']

    def astreams(self):
        for t in self.audio_tracks:
            stream = AudioStream()

            self.base_track(t, stream)

            if 'channel_s' in t:
                stream.channels = t['channel_s']
            if 'bit_rate' in t:
                stream.bit_rate = t['bit_rate']
            if 'sampling_rate' in t:
                stream.sample_rate = t['sampling_rate']

            yield stream

    def tstreams(self):
        for t in self.text_tracks:
            stream = TextStream()

            self.base_track(t, stream)

            yield stream

    def vstreams(self):
        for t in self.video_tracks:
            stream = VideoStream()

            self.base_track(t, stream)

            if 'bit_rate' in t:
                stream.bit_rate = t['bit_rate']

            if 'bit_depth' in t:
                stream.bit_depth = t['bit_depth']

            if 'height' in t and 'width' in t:
                try:
                    stream.height = int(t['height'])
                    stream.width = int(t['width'])

                    stream.resolution = "{0}x{1}".format(
                            t['height'],
                            t['width'],
                    )
                except ValueError as exc:
                    if LOG.isEnabledFor(logging.INFO):
                        LOG.exception(exc)
                    else:
                        LOG.warn(str(exc))

            yield stream


class FileListFacet(FacetedSearch):
    fields = ['filename', ]
    facets = {'filenames': TermsFacet(field='filename')}

    def params(self, **kwargs):
        s = self._s._clone()
        r = s.params(**kwargs)
        self._s = r
        return r

    def execute(self):
        """
        Execute the search and return the response.
        """
        r = self._s.execute(ignore_cache=True)
        r._faceted_search = self
        return r

    def scan(self):
        for hit in self._s.scan():
            yield hit


class MovieListFacet(FileListFacet):
    doc_types = [Movie, ]

    def search(self):
        r = super().search().doc_type(Movie)
        return r.filter('exists', field='filename')


class SongListFacet(FileListFacet):
    doc_types = [Song, ]

    def search(self):
        r = super().search().doc_type(Song)
        return r.filter('exists', field='filename')


class Indexer:
    def __init__(self, host):
        connections.create_connection(hosts=[host], timeout=10)
        Movie.init()
        Song.init()
        self.mi = MovieIndexer()
        self.si = SongIndexer()

    def index(self, data):
        item = Item(data)

        # LOG.debug('keys in item.general: {}'.format(item.general.keys()))
        filename = item.general['file_name']
        dirname = item.general['folder_name']

        if item.dex_type == 'empty':
            return

        elif item.dex_type == 'unknown':
            LOG.warning('Unknown format ({}, {}, {}), '
                        'skipping {}'.format(len(item.video_tracks),
                                             len(item.audio_tracks),
                                             len(item.text_tracks),
                                             filename))

        elif item.dex_type == 'song':
            s = Song.search()
            LOG.info("Processing Song for {}".format(filename))
            r = s.query('match', filename=filename)\
                 .query('match', dirname=dirname).execute()

            if r.hits.total.value == 0:
                LOG.debug("Indexing new Song for {}".format(filename))
                self.index_song(item)
            elif r.hits.total.value == 1:
                LOG.debug("Updating existing Song for {}".format(filename))
                song = r.hits[0]
                self.index_song(item, song)
            else:
                LOG.error("Found {} existing Songs for {}".format(
                        r.hits.total.value, filename))
                for h in r.hits:
                    LOG.debug(h.filename)
                raise IndexerException("Multiple filename matches")

        elif item.dex_type == 'movie':
            s = Movie.search()
            LOG.info("Processing Movie for {}".format(filename))
            r = s.query('match', filename=filename)\
                 .query('match', dirname=dirname).execute()

            if r.hits.total.value == 0:
                LOG.debug("Indexing new Movie for {}".format(filename))
                self.index_movie(item)
            elif r.hits.total.value == 1:
                LOG.debug("Updating existing Movie for {}".format(filename))
                movie = r.hits[0]
                self.index_movie(item, movie)
            else:
                LOG.error("Found {} existing Movies for {}".format(
                        r.hits.total.value, filename))
                for h in r.hits:
                    LOG.debug(h.filename)
                raise IndexerException("Multiple filename matches")

    def index_song(self, item, song=None):
        self.si.index(item, song)

    def index_movie(self, item, movie=None):
        self.mi.index(item, movie)

    def purge_movies(self):
        nef = []  # non-exsistent files
        facet = MovieListFacet()
        fcount = facet.count()
        LOG.debug('MovieListFacet found {} hits'.format(fcount))

        if fcount > 10000:
            LOG.warning('More than 10000 hits, truncating')
            fcount = 10000

        facet.params(size=fcount)
        result = facet.execute()
        for (filename, _, _) in result.facets.filenames:
            if not os.path.exists(filename):
                LOG.info('Found non-existent file: {}'.format(filename))
                nef.append(filename)

        for f in nef:
            LOG.info('Deleting entries for {}'.format(f))
            Movie.search().query('match', filename=f).delete()

    def purge_songs(self):
        nef = []  # non-exsistent files
        facet = SongListFacet()
        fcount = facet.count()
        LOG.debug('SongListFacet found {} hits'.format(fcount))

        if fcount > 10000:
            LOG.warning('More than 10000 hits, truncating')
            fcount = 10000

        facet.params(size=fcount)
        result = facet.execute()
        for (filename, _, _) in result.facets.filenames:
            if not os.path.exists(filename):
                LOG.info('Found non-existent file: {}'.format(filename))
                nef.append(filename)

        for f in nef:
            LOG.info('Deleting entries for {}'.format(f))
            Song.search().query('match', filename=f).delete()

    def purge(self):
        self.purge_movies()
        self.purge_songs()
        return 0
