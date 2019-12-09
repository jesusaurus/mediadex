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

from mediadex import AudioStream
from mediadex import Movie
from mediadex import StreamCounts
from mediadex import TextStream
from mediadex import VideoStream

LOG = logging.getLogger('mediadex.indexer.movie')


class MovieIndexer:
    def __init__(self):
        self.imdb = IMDb()

    def astream(self, track):
        stream = AudioStream()
        if 'codec_id' in track:
            stream.codec = track['codec_id']
        if 'duration' in track and float(track['duration']) > 0:
            stream.duration = track['duration']
        if 'language' in track:
            stream.language = track['language']
        if 'channel_s' in track:
            stream.channels = track['channel_s']
        if 'bit_rate' in track:
            stream.bit_rate = track['bit_rate']
        if 'internet_media_type' in track:
            stream.mime_type = track['internet_media_type']
        return stream

    def tstream(self, track):
        stream = TextStream()
        if 'codec_id' in track:
            stream.codec = track['codec_id']
        if 'duration' in track and float(track['duration']) > 0:
            stream.duration = track['duration']
        if 'language' in track:
            stream.language = track['language']
        if 'internet_media_type' in track:
            stream.mime_type = track['internet_media_type']
        return stream

    def vstream(self, track):
        stream = VideoStream()
        if 'codec_id' in track:
            stream.codec = track['codec_id']
        if 'bit_rate' in track:
            stream.bit_rate = track['bit_rate']
        if 'bit_depth' in track:
            stream.bit_depth = track['bit_depth']
        if 'duration' in track and float(track['duration']) > 0:
            stream.duration = track['duration']
        if 'language' in track:
            stream.language = track['language']
        if 'height' in track and 'width' in track:
            stream.height = track['height']
            stream.width = track['width']
            stream.resolution = "{0}x{1}".format(
                    track['height'],
                    track['width'],
            )
        if 'internet_media_type' in track:
            stream.mime_type = track['internet_media_type']
        return stream

    def index(self, item, movie=None):
        if movie is None:
            movie = Movie()
        stream_counts = StreamCounts()

        vstreams = []
        for track in item.video_tracks:
            stream = self.vstream(track)
            vstreams.append(stream)
        movie.video_streams = vstreams
        stream_counts.video_stream_count = len(vstreams)
        LOG.info("Processed {} video streams".format(len(vstreams)))

        tstreams = []
        for track in item.text_tracks:
            stream = self.tstream(track)
            tstreams.append(stream)
        if tstreams:
            movie.text_streams = tstreams
        stream_counts.text_stream_count = len(tstreams)
        LOG.info("Processed {} text streams".format(len(tstreams)))

        astreams = []
        for track in item.audio_tracks:
            stream = self.astream(track)
            astreams.append(stream)

        movie.audio_streams = astreams
        stream_counts.audio_stream_count = len(astreams)
        LOG.info("Processed {} audio streams".format(len(astreams)))

        movie.stream_counts = stream_counts
        movie.filename = item.general['complete_name']

        _imdb = []
        imdb_info = None
        if 'movie_name' in item.general:
            _imdb = self.imdb.search_movie(item.general['movie_name'])
        elif 'title' in item.general:
            _imdb = self.imdb.search_movie(item.general['title'])
        else:
            _imdb = self.imdb.search_movie(item.general['file_name'])

        imdb_count = len(_imdb)
        if imdb_count > 1:
            LOG.warning("Found {} IMDB matches, "
                        "assuming one".format(imdb_count))
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

        movie.save()
