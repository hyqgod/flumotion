# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a video streaming server
# Copyright (C) 2004 Fluendo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from ConfigParser import ConfigParser

from flumotion.utils import log

class ConfigError(Exception):
    pass

class ConfigComponent:
    nice = 0
    def __init__(self, name):
        self.name = name

    def set(self, arg, kwargs):
        if arg == 'name':
            raise AssertionError
        setattr(self, arg, kwargs)
        
class FlumotionConfig(ConfigParser):
    def __init__(self, filename):
        ConfigParser.__init__(self)

        self.components = {}
        self.msg('Loading configuration file `%s\'' % filename)
        self.read(filename)
        self.parse()

    def msg(self, *args):
        log.msg('config', *args)
        
    def add_component(self, name, **kwargs):
        component = ConfigComponent(name)
        for kwarg in kwargs:
            component.set(kwarg, kwargs[kwarg])
        self.components[name] = component

    def get_pipeline(self, section):
        assert self.has_option(section, 'pipeline')
        return self.get(section, 'pipeline')

    def get_feeds(self, section):
        if self.has_option(section, 'feeds'):
            return self.get(section, 'feeds').split(',')
        else:
            return ['default']

    def get_sources(self, section):
        assert (self.has_option(section, 'source') or
                self.has_option(section, 'sources'))
        if self.has_option(section, 'source'):
            return [self.get(section, 'source')]
        else:
            return self.get(section, 'sources').split(',')

    def get_protocol(self, section):
        assert self.has_option(section, 'protocol')
        return self.get(section, 'protocol')

    def parse_streamer(self, section, **kwargs):
        protocol = self.get_protocol(section)
        if not protocol in ('http', 'file'):
            raise AssertionError, "unknown protocol: %s" % protocol
        kwargs['protocol'] = protocol
        if protocol == 'http':
            if self.has_option(section, 'port'):
                kwargs['port'] = self.getint(section, 'port')
            if self.has_option(section, 'logfile'):
                kwargs['logfile'] = self.get(section, 'logfile')

            self.add_component(section,
                               feeds=self.get_feeds(section),
                               sources=self.get_sources(section),
                               **kwargs)
        elif protocol == 'file':
            if self.has_option(section, 'location'):
                kwargs['location'] = self.get(section, 'location')
            if self.has_option(section, 'port'):
                kwargs['port'] = self.getint(section, 'port')

            self.add_component(section,
                               feeds=self.get_feeds(section),
                               sources=self.get_sources(section),
                               **kwargs)
        
    def parse_globals(self):
        if not self.has_option('global', 'username'):
            return
        
        username = conf.get('global', 'username')
        entry = pwd.getpwnam(username)
        self.uid = entry[2]

    def parse_component(self, kind, section):
        kwargs = {}
        kwargs['kind'] = kind
        if self.has_option(section, 'nice'):
            kwargs['nice'] = self.getint(section, 'nice')

        if kind == 'producer':
            self.add_component(section, pipeline=self.get_pipeline(section),
                               feeds=self.get_feeds(section),
                               **kwargs)
        elif kind == 'converter':
            self.add_component(section, pipeline=self.get_pipeline(section),
                               feeds=self.get_feeds(section),
                               sources=self.get_sources(section),
                               **kwargs)
        elif kind == 'streamer':
            self.parse_streamer(section, **kwargs)
            
    def parse(self):
        sections = self.sections()
        if not sections:
            raise ConfigError("Need at least one section")
            
        for section in sections:
            if section == 'global':
                self.parse_globals(c)
            else:
                if not self.has_option(section, 'kind'):
                    raise ConfigError("section %s needs a kind field" % section)
            
                kind = self.get(section, 'kind')
                if not kind in ('producer', 'converter', 'streamer'):
                    raise ConfigError("Unsupported component kind: %s" % kind)
                self.parse_component(kind, section)
