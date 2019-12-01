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

from mediadex import AudioStream
from mediadex import Movie
from mediadex import StreamCounts
from mediadex import TextStream
from mediadex import VideoStream


class MovieIndexer:
    def __init__(self):
        self.log = logging.getLogger('mediadex.indexer.movie')

    def index(self, item, movie=None):
        if movie is None:
            movie = Movie()
        stream_counts = StreamCounts()

        vstreams = []
        for track in item.video_tracks:
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
            vstreams.append(stream)
        movie.video_streams = vstreams
        stream_counts.video_stream_count = len(vstreams)
        self.log.info("Processed {} video streams".format(len(vstreams)))

        tstreams = []
        for track in item.text_tracks:
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
        for track in item.audio_tracks:
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
        movie.filename = item.general['complete_name']

        movie.save()
