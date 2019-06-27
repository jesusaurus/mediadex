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


from mediadex import Song, AudioStream, Movie, StreamCounts, VideoStream, TextStream

from elasticsearch_dsl import connections
import yaml


class Indexer:
    def __init__(self):
        self.dex_type = None
        self.general = {}
        self.audio_tracks = []
        self.text_tracks = []
        self.video_tracks = []
        self.other_tracks = []

        connections.create_connection(hosts=['localhost'], timeout=5)

    def populate(self, data):
        gen = [ t for t in data if t['track_type'] == 'General' ]
        if len(gen) > 1:
            raise Exception("More than one General track found")
        elif len(gen) == 0:
            raise Exception("No General track found")
        self.general = gen.pop()

        atracks = [ t for t in data if t['track_type'] == 'Audio' ]
        self.audio_tracks = atracks
        acount = len(atracks)

        vtracks = [ t for t in data if t['track_type'] == 'Video' ]
        self.video_tracks = vtracks
        vcount = len(vtracks)

        ttracks = [ t for t in data if t['track_type'] == 'Text' ]
        self.text_tracks = ttracks
        tcount = len(ttracks)

        if vcount > 0:
            self.dex_type = 'movie'
        elif acount == 1:
            self.dex_type = 'song'
        else:
            print("v/t/a count: {}/{}/{}".format(vcount, tcount, acount))
            raise Exception("Unknown media type")


    def index(self):
        if self.dex_type is None:
            raise Exception("Media type unset")

        elif self.dex_type is 'song':
            self.index_song()

        elif self.dex_type is 'movie':
            self.index_movie()

    def index_song(self):
        song_track = self.audio_tracks.pop()
        song = Song()
        stream = AudioStream()

        stream.codec = song_track.format
        stream.channels = song_track.channel_s
        stream.bit_rate = song_track.bit_rate
        stream.language = song_track.language
        stream.duration = song_track.duration

        song.audio_stream = stream
        song.title = self.general['complete_name']  # file name

        song.save()

    def index_movie(self):
        movie = Movie()
        stream_counts = StreamCounts()

        vstreams = []
        for track in self.video_tracks:
            try:
                stream = VideoStream()
                if 'codec_id' in track:
                    stream.codec = track['codec_id']
                if 'bit_rate' in track:
                    stream.bit_rate = track['bit_rate']
                if 'bit_depth' in track:
                    stream.bit_depth = track['bit_depth']
                if 'duration' in track:
                    stream.duration = track['duration']
                if 'language' in track:
                    stream.language = track['language']
                if 'height' in track and 'width' in track:
                    stream.resolution = "{0}x{1}".format(track['width'], track['height'])
                vstreams.append(stream)
            except Exception as exc:
                print(yaml.dump(track))
                print("Could not process VideoStream")
        movie.video_streams = vstreams
        stream_counts.video_stream_count = len(vstreams)
        print("Processed {} video streams".format(len(vstreams)))

        tstreams = []
        for track in self.text_tracks:
            stream = TextStream()
            if 'codec_id' in track:
                stream.codec = track['codec_id']
            if 'duration' in track:
                stream.duration = track['duration']
            if 'language' in track:
                stream.language = track['language']
            tstreams.append(stream)
        if tstreams:
            movie.text_streams = tstreams
        stream_counts.text_stream_count = len(tstreams)
        print("Processed {} text streams".format(len(tstreams)))

        astreams = []
        for track in self.audio_tracks:
            stream = AudioStream()
            if 'codec_id' in track:
                stream.codec = track['codec_id']
            if 'duration' in track:
                stream.duration = track['duration']
            if 'language' in track:
                stream.language = track['language']
            if 'channel_s' in track:
                stream.channels = track['channel_s']
            if 'bit_rate' in track:
                stream.bit_rate = track['bit_rate']
            astreams.append(stream)
        movie.audio_streams = astreams
        stream_counts.audio_stream_count = len(astreams)
        print("Processed {} audio streams".format(len(astreams)))

        movie.stream_counts = stream_counts
        movie.title = self.general['complete_name']  # file name

        movie.save()
