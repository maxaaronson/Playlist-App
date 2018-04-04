#!/usr/bin/python
####################################
# Created by Max Aaronson
# 3/26/18
####################################

import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from flask import jsonify

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


class Playlists(Base):
    __tablename__ = 'playlists'
    name = Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }



class Songs(Base):
    __tablename__ = 'songs'
    title = Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    artist = Column(String(80), nullable = False)
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
            'title' : self.title,
            'artist' : self.artist,
            'album' : self.album,
            'duration' : self.duration,
            'youtubeId' : self.youtubeId,
            'playlistId' : self.playlistId
            }
  
                                            
engine = create_engine('postgresql:///playlistdb')

Base.metadata.create_all(engine)
