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

import argparse
import os

import yaml
from pymediainfo import MediaInfo

from mediadex.indexer import Indexer
from mediadex.indexer import Indexer


class App:
    def __init__(self):
        self.args = None
        self.dex = None

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-p', '--path', dest='path', required=True,
            help='top directory to search for media')
        parser.add_argument('-dr', '--dry-run', dest='dry_run',
            action='store_true', help='write yaml to stdout instead of '
            'indexing into Elasticsearch')

        self.args = parser.parse_args()

    def process(self, f):
        try:
            _f = f.encode('utf-8', 'surrogateescape').decode('ISO-8859-1')
            info = MediaInfo.parse(_f).to_data()
        except Exception as exc:
            print(exc)
            return

        if self.args.dry_run:
            print(yaml.dump(info))
        else:
            try:
                self.dex.build(info['tracks'])
                self.dex.index()
            except Exception as exc:
                print(exc)
                print(yaml.dump(info))

    def walk(self):
        for (_top, _dirs, _files) in os.walk(self.args.path):
            for _file in _files:
                fp = os.path.join(_top, _file)
                try:
                    self.process(fp)
                except FileNotFoundError as exc:
                    pass  # probably a bad symlink

    def run(self):
        self.parse_args()

        if not self.args.dry_run:
            self.dex = Indexer()

        self.walk()


def main():
    app = App()
    app.run()
