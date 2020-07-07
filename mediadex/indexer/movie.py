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

from imdb import IMDb

from mediadex import Movie
from mediadex import StreamCounts

LOG = logging.getLogger('mediadex.indexer.movie')


class MovieIndexer:
    def __init__(self):
        self.imdb = IMDb()

    def index(self, item, existing=None):
        movie = Movie()

        stream_counts = StreamCounts()

        vstreams = [x for x in item.vstreams()]
        tstreams = [x for x in item.tstreams()]
        astreams = [x for x in item.astreams()]

        movie.video_streams = vstreams
        movie.text_streams = tstreams
        movie.audio_streams = astreams

        stream_counts.video_stream_count = len(vstreams)
        LOG.debug("Processed {} video streams".format(len(vstreams)))
        stream_counts.text_stream_count = len(tstreams)
        LOG.debug("Processed {} text streams".format(len(tstreams)))
        stream_counts.audio_stream_count = len(astreams)
        LOG.debug("Processed {} audio streams".format(len(astreams)))

        movie.stream_counts = stream_counts
        movie.dirname = item.dirname
        movie.filename = item.filename
        movie.filesize = item.general['file_size']

        _imdb = []
        imdb_info = None
        imdb_search = None

        if 'movie_name' in item.general:
            imdb_search = item.general['movie_name']
            _imdb = self.imdb.search_movie(imdb_search)
            LOG.debug("IMDB search: {}".format(imdb_search))

        if 'title' in item.general and not _imdb:
            imdb_search = item.general['title']
            _imdb = self.imdb.search_movie(imdb_search)
            LOG.debug("IMDB search: {}".format(imdb_search))

        if not _imdb:
            imdb_search = item.general['file_name'].replace('.', ' ')
            _imdb = self.imdb.search_movie(imdb_search)
            LOG.debug("IMDB search: {}".format(imdb_search))

        imdb_count = len(_imdb)
        if imdb_count > 1:
            LOG.info("Found {} IMDB matches, assuming one".format(imdb_count))
            # TODO: try to find the right match
            for i in _imdb:
                if i['kind'] == 'movie':
                    imdb_info = i
                    break

        elif imdb_count == 1:
            imdb_info = _imdb[0]

        if imdb_info:
            self.imdb.update(imdb_info)
            LOG.info("IMDB Title: {}".format(imdb_info['title']))

            if 'cast' in imdb_info:
                movie.cast = [x['name'] for x in imdb_info['cast']]
            if 'director' in imdb_info:
                movie.director = [x['name'] for x in imdb_info['director']]
            if 'writer' in imdb_info:
                movie.writer = [x['name'] for x in imdb_info['writer']]

            if 'title' in imdb_info:
                movie.title = imdb_info['title']
            if 'year' in imdb_info:
                movie.year = imdb_info['year']
            if 'genres' in imdb_info:
                movie.genre = imdb_info['genres']
        else:
            LOG.warn("No IMDB match: {}".format(imdb_search))
            LOG.debug(item.general)

        try:
            if existing is None:
                movie.save()
                LOG.debug("Movie added")
            elif existing.to_dict() == movie.to_dict():
                LOG.debug("Movie unchanged")
            else:
                existing.delete()
                movie.save()
                LOG.debug("Movie updated")

        except Exception as exc:
            if LOG.isEnabledFor(logging.INFO):
                LOG.exception(exc)
            else:
                LOG.warn(str(exc))
