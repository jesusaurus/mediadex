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

from elasticsearch_dsl import Document
from elasticsearch_dsl import Float
from elasticsearch_dsl import InnerDoc
from elasticsearch_dsl import Integer
from elasticsearch_dsl import Keyword
from elasticsearch_dsl import Object
from elasticsearch_dsl import Text


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
    title = Keyword()
    year = Integer()
    genre = Keyword()
    stream_counts = Object(StreamCounts)
    container = Keyword()
    filename = Keyword()


class Stream(InnerDoc):
    codec = Keyword()
    duration = Float()
    language = Text()
    mime_type = Keyword()


class TextStream(Stream):
    pass


class AudioStream(Stream):
    channels = Integer()
    bit_rate = Integer()
    sample_rate = Integer()


class VideoStream(Stream):
    bit_rate = Integer()
    bit_depth = Integer()
    resolution = Keyword()
    height = Integer()
    width = Integer()


class Song(Media):
    artist = Keyword()
    album = Keyword()

    audio_stream = Object(AudioStream)

    class Index(_Index):
        name = 'music'


class Cinema(Media):
    director = Keyword()
    cast = Keyword(multi=True)

    audio_streams = Object(AudioStream, multi=True)
    text_streams = Object(TextStream, multi=True)
    video_streams = Object(VideoStream, multi=True)


class Movie(Cinema):
    class Index(_Index):
        name = 'movies'


class Show(Cinema):
    season = Integer()

    class Index(_Index):
        name = 'series'
