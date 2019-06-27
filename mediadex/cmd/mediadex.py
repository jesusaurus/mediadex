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

from mediadex.indexer import Indexer

from pymediainfo import MediaInfo


class Scanner:
    def __init__(self):
        self.args = None

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-p', dest='path')
        parser.add_argument('-dr', dest='dry_run', action='store_true')

        self.args = parser.parse_args()

    def get_info(self, f):
        info = MediaInfo.parse(f).to_data()

        if self.args.dry_run:
            print(yaml.dump(info))

        else:
            try:
                dex = Indexer()
                dex.populate(info['tracks'])
                dex.index()
            except Exception as exc:
                print(exc)
                print(yaml.dump(info))

    def walk(self):
        if self.args and 'path' in self.args:
            for (_top, _dirs, _files) in os.walk(self.args.path):
                for _file in _files:
                    fp = os.path.join(_top, _file)
                    try:
                        self.get_info(fp)
                    except FileNotFoundError as exc:
                        pass  # probably a bad symlink


def main():
    app = Scanner()
    app.parse_args()
    app.walk()
