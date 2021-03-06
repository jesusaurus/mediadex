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
import datetime
import logging
import os

import chardet
import yaml
from elasticsearch_dsl import connections
from pymediainfo import MediaInfo

from mediadex.indexer import Indexer
from mediadex.indexer import IndexerException
from mediadex.purger import MoviePurger
from mediadex.purger import SongPurger


class App:
    def __init__(self):
        self.args = None
        self.dex = None
        self.log = None

    def parse_args(self):
        parser = argparse.ArgumentParser()

        parser.add_argument('-p', '--path',
                            dest='path',
                            action='append',
                            help='top directory to search for media')

        parser.add_argument('-v', '--verbose',
                            dest='verbose',
                            action='count',
                            help='output additional log messages')

        parser.add_argument('--purge',
                            dest='purge',
                            action='store_true',
                            help='Scan for deleted files and remove '
                            'their entries from elasticsearch')

        parser.add_argument('--today',
                            dest='today',
                            action='store_true',
                            help='only scan recent files')

        parser.add_argument('-es', '--elasticsearch-host',
                            dest='host',
                            action='store', default='localhost:9200',
                            help='elasticsearch host to connect to')

        parser.add_argument('-dr', '--dry-run',
                            dest='dry_run',
                            action='store_true',
                            help='write to stdout as yaml instead of '
                            'indexing into elasticsearch')

        self.args = parser.parse_args()

    def setup_logging(self, level):
        root_log = logging.getLogger()
        root_log.setLevel(level)
        sh = logging.StreamHandler()
        sh.setLevel(level)
        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        sh.setFormatter(logging.Formatter(fmt))
        root_log.addHandler(sh)

        for lib in ['elasticsearch', 'imdb', 'imdbpy', 'urllib3']:
            log = logging.getLogger(lib)
            log.setLevel(logging.WARNING)

        self.log = logging.getLogger('mediadex')
        self.log.setLevel(level)

    def index(self, data, path):
        if self.args.dry_run:
            self.log.info(yaml.dump(data))
        else:
            try:
                self.dex.index(data['tracks'], path)
            except IndexerException as exc:
                if self.log.isEnabledFor(logging.INFO):
                    self.log.exception(exc)
                else:
                    self.log.warn(str(exc))
                self.log.debug(yaml.dump(data))
                return 1
        return 0

    def open_file(self, f, p):
        info = {}

        if self.args.today:
            _stat = os.stat(f)
            mtime = datetime.datetime.fromtimestamp(_stat.st_mtime)
            diff = datetime.datetime.now() - mtime
            if diff > datetime.timedelta(days=1):
                self.log.debug('Skipping {} due to timestamp'.format(f))
                return 0

        try:
            info = MediaInfo.parse(f).to_data()
        except FileNotFoundError:
            _enc = f.encode('utf-8', 'surrogateescape')
            charset = chardet.detect(f).get('encoding')
            self.log.info("chardet found: {}".format(charset))

            try:
                _f = _enc.decode(charset)
                info = MediaInfo.parse(_f).to_data()
            except FileNotFoundError:
                self.log.warning("chardet failure: {}".format(_f))

        except Exception as exc:
            if self.log.isEnabledFor(logging.INFO):
                self.log.exception(exc)
            else:
                self.log.warn(str(exc))

        finally:
            if not info:
                _f = f.encode('utf-8', 'surrogateescape')
                raise IOError("Could not open {}".format(_f))

        return self.index(info, p)

    def walk_paths(self):
        retval = 0
        for path in self.args.path:
            for (_top, _dirs, _files) in os.walk(path):
                for _file in _files:
                    fp = os.path.join(_top, _file)
                    try:
                        retval += self.open_file(fp, path)
                    except Exception as exc:
                        if self.log.isEnabledFor(logging.INFO):
                            self.log.exception(exc)
                        else:
                            self.log.warn(str(exc))
                        retval += 1
        return retval

    def purge(self):
        retval = 0
        try:
            sp = SongPurger()
            mp = MoviePurger()
            retval += sp.purge() + mp.purge()
        except Exception as exc:
            self.log.exception(exc)
            retval += 1
        return retval

    def run(self):
        self.parse_args()

        if self.args.verbose is None:
            self.setup_logging(level=logging.WARNING)
        elif self.args.verbose == 1:
            self.setup_logging(level=logging.INFO)
        else:
            self.setup_logging(level=logging.DEBUG)

        if not self.args.dry_run:
            connections.create_connection(hosts=[self.args.host], timeout=11)
            self.dex = Indexer()
            if self.args.purge:
                return self.purge()

        return self.walk_paths()


def main():
    app = App()
    return app.run()
