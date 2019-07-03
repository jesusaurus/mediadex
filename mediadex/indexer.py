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

from mediadex import AudioStream
from mediadex import Movie
from mediadex import Song
from mediadex import StreamCounts
from mediadex import TextStream
from mediadex import VideoStream


class Indexer:
    def __init__(self, host):
        self.log = logging.getLogger('mediadex.indexer')
        connections.create_connection(hosts=[host], timeout=10)
        Song.init()
        Movie.init()

    def build(self, data):
        gen = [t for t in data if t['track_type'] == 'General']
        if len(gen) > 1:
            raise Exception("More than one General track found")
        elif len(gen) == 0:
            raise Exception("No General track found")
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
        else:
            raise Exception("Unknown media type")

    def index(self):
        filename = self.general['complete_name']

        if self.dex_type is None:
            raise Exception("Media type unset")

        elif self.dex_type == 'song':
            s = Song.search()
            r = s.query('match', filename=filename).execute()

            if r.hits.total.value == 0:
                self.index_song()
                self.log.info("Indexed new record for {}".format(filename))
            elif r.hits.total.value == 1:
                song = r.hits[0]
                self.index_song(song)
                self.log.info("Updated existing record for {}".format(
                              song.filename))
            else:
                self.log.warning("Found {} existing records for {}".format(
                                 r.hits.total.value, filename))
                for h in r.hits:
                    self.log.debug(h.filename)

        elif self.dex_type == 'movie':
            s = Movie.search()
            r = s.query('match', filename=filename).execute()

            if r.hits.total.value == 0:
                self.index_movie()
                self.log.info("Indexed new record for {}".format(filename))
            elif r.hits.total.value == 1:
                movie = r.hits[0]
                self.index_movie(movie)
                self.log.info("Updated existing record for {}".format(
                              movie.filename))
            else:
                self.log.warning("Found {} existing records for {}".format(
                                 r.hits.total.value, filename))
                self.log.debug(r.hits[0])
                self.log.debug(r.hits[1])

    def index_song(self, song=None):
        if song is None:
            song = Song()
        stream_counts = StreamCounts()

        song_track = self.audio_tracks.pop()
        stream = AudioStream()

        if 'format_profile' in song_track:
            stream.codec = "{0} {1}".format(song_track['format'],
                                            song_track['format_profile'])
        else:
            stream.codec = song_track.format
        if 'channel_s' in song_track:
            stream.channels = song_track['channel_s']
        if 'bit_rate' in song_track:
            stream.bit_rate = song_track['bit_rate']
        if 'language' in song_track:
            stream.language = song_track['language']
        if 'duration' in song_track:
            stream.duration = song_track['duration']
        if 'sampling_rate' in song_track:
            stream.sample_rate = song_track['sampling_rate']
        if 'internet_media_type' in song_track:
            stream.mime_type = song_track['internet_media_type']

        song.audio_stream = stream
        song.filename = self.general['complete_name']

        stream_counts.audio_stream_count = 1
        stream_counts.video_stream_count = 0
        stream_counts.text_stream_count = 0

        song.save()

    def index_movie(self, movie=None):
        if movie is None:
            movie = Movie()
        stream_counts = StreamCounts()

        vstreams = []
        for track in self.video_tracks:
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
                stream.resolution = "{0}x{1}".format(track['width'],
                                                     track['height'])
                stream.width = track['width']
                stream.height = track['height']
            if 'internet_media_type' in track:
                stream.mime_type = track['internet_media_type']
            vstreams.append(stream)
        movie.video_streams = vstreams
        stream_counts.video_stream_count = len(vstreams)
        self.log.info("Processed {} video streams".format(len(vstreams)))

        tstreams = []
        for track in self.text_tracks:
            stream = TextStream()
            if 'codec_id' in track:
                stream.codec = track['codec_id']
            if 'duration' in track and float(track['duration']) > 0:
                stream.duration = track['duration']
            if 'language' in track:
                stream.language = track['language']
            if 'internet_media_type' in track:
                stream.mime_type = track['internet_media_type']
            tstreams.append(stream)
        if tstreams:
            movie.text_streams = tstreams
        stream_counts.text_stream_count = len(tstreams)
        self.log.info("Processed {} text streams".format(len(tstreams)))

        astreams = []
        for track in self.audio_tracks:
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
            astreams.append(stream)
        movie.audio_streams = astreams
        stream_counts.audio_stream_count = len(astreams)
        self.log.info("Processed {} audio streams".format(len(astreams)))

        movie.stream_counts = stream_counts
        movie.filename = self.general['complete_name']

        movie.save()
