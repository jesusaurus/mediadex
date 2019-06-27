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

from elasticsearch_dsl import Document, InnerDoc, Date, Integer, Keyword, Text, Nested, Object, Float


class _Index:
    settings = {
        'number_of_shards': 1,
        'number_of_replicas': 0,
    }


class StreamCounts(InnerDoc):
    audio_stream_count: Integer()
    text_stream_count: Integer()
    video_stream_count: Integer()


class Media(Document):
    title = Text()
    year = Integer()
    genre = Keyword()
    stream_counts = Object(StreamCounts)
    container = Keyword()

    class Index(_Index):
        name = 'media'


class AudioStream(InnerDoc):
    codec = Keyword()
    channels = Integer()
    bit_rate = Integer()
    duration = Float()
    language = Keyword()


class TextStream(InnerDoc):
    codec = Keyword()
    duration = Float()
    language = Keyword()


class VideoStream(InnerDoc):
    codec = Keyword()
    bit_rate = Integer()
    bit_depth = Integer()
    duration = Float()
    language = Keyword()
    resolution = Keyword()


class Song(Media):
    artist = Text()
    album = Text()

    audio_stream = Object(AudioStream)

    class Index(_Index):
        name = 'music'


class Cinema(Media):
    director = Keyword()
    cast = Keyword(multi=True)

    audio_streams = Object(AudioStream, multi=True)
    text_streams = Object(TextStream, multi=True)
    video_streams = Object(VideoStream, multi=True)

    class Index(_Index):
        name = 'cinema'


class Movie(Cinema):
    class Index(_Index):
        name = 'movies'


class Show(Cinema):
    season = Integer()

    class Index(_Index):
        name = 'series'
