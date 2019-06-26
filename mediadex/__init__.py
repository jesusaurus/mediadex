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

from elasticsearch_dsl import Document, InnerDoc, Date, Integer, Keyword, Text, Nested


class _Index:
    settings = {
        'number_of_shards': 2,
        'number_of_replicas': 2,
    }


class _Info(InnerDoc):
    pass


class Media(Document):
    title = Text()
    year = Integer()
    info = Nested(_Info)
    genre = Keyword()

    class Index(_Index):
        name = 'media'


class Song(Media):
    artist = Text()
    album = Text()

    class Index(_Index):
        name = 'music'


class Movie(Media):
    class Index(_Index):
        name = 'movies'


class Show(Media):
    class Index(_Index):
        name = 'series'
