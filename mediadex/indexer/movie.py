#!/usr/bin/python3

# Mediadex: Index media metadata into opensearch
# Copyright (C) 2019-2022  K Jonathan Harker
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
import re

from imdb import Cinemagoer

from mediadex import Movie
from mediadex import StreamCounts

LOG = logging.getLogger('mediadex.indexer.movie')


class MovieIndexer:
    def __init__(self, force=False):
        self.imdb = Cinemagoer()
        self.force = force

    def index(self, item, existing=None):
        movie = Movie()
        force = self.force

        # basic stream info
        stream_counts = StreamCounts()

        vstreams = [x for x in item.vstreams()]
        tstreams = [x for x in item.tstreams()]
        astreams = [x for x in item.astreams()]

        movie.video_streams = vstreams
        if existing and movie.video_streams != existing.video_streams:
            force = True

        movie.text_streams = tstreams
        if existing and movie.text_streams != existing.text_streams:
            force = True

        movie.audio_streams = astreams
        if existing and movie.audio_streams != existing.audio_streams:
            force = True

        stream_counts.video_stream_count = len(vstreams)
        LOG.debug("Processed {} video streams".format(len(vstreams)))
        stream_counts.text_stream_count = len(tstreams)
        LOG.debug("Processed {} text streams".format(len(tstreams)))
        stream_counts.audio_stream_count = len(astreams)
        LOG.debug("Processed {} audio streams".format(len(astreams)))

        movie.stream_counts = stream_counts
        if existing and movie.stream_counts != existing.stream_counts:
            force = True

        movie.dirname = item.dirname
        movie.filename = item.filename
        movie.filesize = item.general['file_size']
        movie.fingerprint = item.fingerprint

        if existing and not force:
            # Assume imdb hasn't changed anything
            movie.cast = existing.cast or None
            movie.director = existing.director or None
            movie.writer = existing.writer or None
            movie.title = existing.title or None
            movie.year = existing.year or None
            movie.genre = existing.genre or None

        else:
            # build a list of potential movie names
            # order matters
            #   title + subtitle (no year)
            #   title + year
            #   filename
            #   subtitle
            #   container movie_name
            #   container title
            search_strings = []

            file_name = item.general['file_name']
            file_sanitized = file_name.replace('.', ' ')

            file_title = None
            file_year = None
            file_subtitle = None
            file_re = re.compile(r'([^.]+ )+(\d{4})( [^.]*)*')
            file_match = file_re.match(file_sanitized)

            # parse re results
            if file_match:
                LOG.debug('filename parts: {}'.format(file_match.groups()))

                file_title = file_match.group(1).strip()
                file_year = file_match.group(2)
                if file_match.group(3):
                    file_subtitle = file_match.group(3).strip()

                LOG.debug("RE Match: {} {} {}".format(
                    file_title,
                    file_year,
                    file_subtitle)
                )

                if file_subtitle:
                    full_title = '{}: {}'.format(file_title, file_subtitle)
                    search_strings.append(full_title)

                title_year = '{} {}'.format(file_title, file_year)
                search_strings.append(title_year)

            search_strings.append(file_sanitized)

            if file_subtitle:
                search_strings.append(file_subtitle)

            # check container metadata
            if 'movie_name' in item.general:
                search_strings.append(item.general['movie_name'])

            if 'title' in item.general:
                search_strings.append(item.general['title'])

            # collate search string results
            best_title = ''
            imdb_info = None

            LOG.debug(f"Searching through: {search_strings}")
            for imdb_search in search_strings:
                LOG.debug("Searching for: {}".format(imdb_search))
                if not imdb_search:
                    continue

                _imdb = self.imdb.search_movie(imdb_search)
                if _imdb:
                    LOG.debug("Found IMDB info: {}".format(_imdb))
                    best_title = imdb_search
                    imdb_info = _imdb[0]
                    break

            if imdb_info is None:
                LOG.warn("No IMDB match: {}".format(search_strings))
                LOG.debug(item.general)
                return

            LOG.info("Found match for: {}".format(best_title))
            LOG.info("IMDB Title: {}".format(imdb_info['title']))
            self.imdb.update(imdb_info)

            try:
                if 'cast' in imdb_info:
                    movie.cast = [
                        x['name'] for x in imdb_info['cast'] if 'name' in x
                    ]
                if 'director' in imdb_info:
                    movie.director = [
                        x['name'] for x in imdb_info['director'] if 'name' in x
                    ]
                if 'writer' in imdb_info:
                    movie.writer = [
                        x['name'] for x in imdb_info['writer'] if 'name' in x
                    ]
                if 'title' in imdb_info:
                    movie.title = imdb_info['title']
                if 'year' in imdb_info:
                    movie.year = imdb_info['year']
                if 'genres' in imdb_info:
                    movie.genre = imdb_info['genres']
            except KeyError as exc:
                LOG.debug(imdb_info.__dict__)
                LOG.exception(exc)

        try:
            if existing is None:
                movie.save()
                LOG.info("Movie added")
            elif force:
                existing.delete()
                movie.save()
                LOG.info("Movie update forced")
            elif existing.to_dict() == movie.to_dict():
                LOG.debug("Movie unchanged")
            else:
                existing.delete()
                movie.save()
                LOG.info("Movie updated")

        except Exception as exc:
            if LOG.isEnabledFor(logging.INFO):
                LOG.exception(exc)
            else:
                LOG.warn(str(exc))
