#!/usr/bin/python
####################################
# Created by Max Aaronson
# 3/26/18
####################################

import sys
from sqlalchemy import (Column,
                        ForeignKey,
                        Integer,
                        String,
                        create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from flask import jsonify

Base = declarative_base()


class Playlists(Base):
    __tablename__ = 'playlists'
    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    user_id = Column(String(40))
    songs = relationship('Songs', cascade='all, delete-orphan')

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }


class Songs(Base):
    __tablename__ = 'songs'
    title = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    artist = Column(String(80), nullable=False)
    album = Column(String(80))
    duration = Column(String(80))
    artwork = Column(String(80))
    youtubeId = Column(String(80))
    playlistId = Column(Integer, ForeignKey('playlists.id'))
    playlists = relationship(Playlists)

    # returns serialized format of the data
    @property
    def serialize(self):
        return {
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'duration': self.duration,
            'youtubeId': self.youtubeId,
            'playlistId': self.playlistId
            }


engine = create_engine('postgresql:///playlistdb')
Base.metadata.create_all(engine)
