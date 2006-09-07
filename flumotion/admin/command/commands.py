# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.GPL" in the source distribution for more information.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.
import os

from flumotion.twisted.defer import defer_generator
from flumotion.admin.command import utils
from flumotion.common.planet import moods
from flumotion.common import errors
from flumotion.twisted import flavors
from flumotion.twisted.compat import implements
from twisted.internet import defer

__all__ = ['commands']

# copied from flumotion/twisted/integration.py
class CommandNotFoundException(Exception):
    def __init__(self, command):
        Exception.__init__(self)
        self.command = command
    def __str__(self):
        return 'Command %r not found in the PATH.' % self.command

def _which(executable):
    if os.sep in executable:
        if os.access(os.path.abspath(executable), os.X_OK):
            return os.path.abspath(executable)
    elif os.getenv('PATH'):
        for path in os.getenv('PATH').split(os.pathsep):
            if os.access(os.path.join(path, executable), os.X_OK):
                return os.path.join(path, executable)
    raise CommandNotFoundException(executable)


# it's probably time to move this stuff into classes...

# command-list := (command-spec, command-spec...)
# command-spec := (command-name, command-desc, arguments, command-proc)
# command-name := str
# command-desc := str
# command-proc := f(model, quit, *args) -> None
# arguments := (arg-spec, arg-spec...)
# arg-spec := (arg-name, arg-parser, arg-default?)
# arg-name := str
# arg-parser := f(x) -> Python value or exception
# arg-default := any python value


def do_getprop(model, quit, avatarId, propname):
    d = utils.get_component_uistate(model, avatarId)
    yield d
    uistate = d.value()
    if uistate:
        if uistate.hasKey(propname):
            print uistate.get(propname)
        else:
            print ('Component %s in flow %s has no property called %s'
                   % (avatarId[1], avatarId[0], propname))
    quit()
do_getprop = defer_generator(do_getprop)

def do_listprops(model, quit, avatarId):
    d = utils.get_component_uistate(model, avatarId)
    yield d
    uistate = d.value()
    if uistate:
        for k in uistate.keys():
            print k
    quit()
do_listprops = defer_generator(do_listprops)

def do_showplanet(model, quit):
    d = model.callRemote('getPlanetState')
    yield d
    planet = d.value()

    for f in planet.get('flows'):
        print 'flow: %s' % f.get('name')
        for c in f.get('components'):
            print '  %s' % c.get('name')

    a = planet.get('atmosphere')
    print 'atmosphere: %s' % a.get('name')
    for c in a.get('components'):
        print '  %s' % c.get('name')

    quit()
do_showplanet = defer_generator(do_showplanet)

def do_getmood(model, quit, avatarId):
    d = model.callRemote('getPlanetState')
    yield d
    planet = d.value()
    c = utils.find_component(planet, avatarId)
    if c:
        mood = c.get('mood')
        try:
            _which('cowsay')
            os.spawnlp(os.P_WAIT, 'cowsay', 'cowsay',
                       "%s is %s" % (c.get('name'), moods[mood].name))
        except CommandNotFoundException:
            print "%s is %s" % (c.get('name'), moods[mood].name)

    quit()
do_getmood = defer_generator(do_getmood)

def do_showcomponent(model, quit, avatarId):
    d = model.callRemote('getPlanetState')
    yield d
    planet = d.value()
    c = utils.find_component(planet, avatarId)
    if c:
        print 'Component state:'
        keys = c.keys()
        keys.sort()
        for k in keys:
            print '    %s: %r' % (k, c.get(k))
        d = utils.get_component_uistate(model, avatarId, c, quiet=True)
        yield d
        ui = d.value()
        if ui:
            print '\nUI state:'
            keys = ui.keys()
            keys.sort()
            for k in keys:
                print '    %s: %r' % (k, ui.get(k))
    quit()
do_showcomponent = defer_generator(do_showcomponent)


def do_invoke(model, quit, avatarId, methodName):
    d = model.callRemote('getPlanetState')
    yield d
    planet = d.value()
    c = utils.find_component(planet, avatarId)
    if not c:
        print "Could not find component %r" % avatarId
        yield None

    d = model.componentCallRemote(c, methodName)
    yield d

    try:
        d.value()
        print "Invoke of %s on %s was successful." % (methodName, 
            avatarId[1])
    except errors.NoMethodError:
        print "No method '%s' on component '%s'" % (methodName, avatarId)
    except Exception, e:
        raise

    quit()
do_invoke = defer_generator(do_invoke)

def do_loadconfiguration(model, quit, confFile, saveAs):
    print 'Loading configuration from file: %s' % confFile

    f = open(confFile, 'r')
    configurationXML = f.read()
    f.close()

    d = model.callRemote('loadConfiguration', configurationXML,
                         saveAs=saveAs)
    yield d
    d.value()
    print 'Configuration loaded successfully.'
    if saveAs:
        print 'Additionally, the configuration XML was saved on the manager.'

    quit()
do_loadconfiguration = defer_generator(do_loadconfiguration)

def do_showworkers(model, quit):
    d = model.callRemote('getWorkerHeavenState')
    yield d
    whs = d.value()

    for worker in whs.get('workers'):
        print "%s: %s" % (worker.get('name'), worker.get('host'))
    quit()
do_showworkers = defer_generator(do_showworkers)

class MoodListener:
    implements(flavors.IStateListener)
    
    def __init__(self):
        self._moodDefer = None
        self._moodFinal = None

    def waitOnMood(self, moods):
        """
        @type moods: tuple of moods
        """
        self._moodDefer = defer.Deferred()
        self._moodsFinal = moods
        return self._moodDefer

    def stateSet(self, object, key, value):
        if self._moodDefer:
            if key == 'mood' and moods[value] in self._moodsFinal:
                self._moodDefer.callback(moods[value])
                
    def stateAppend(self, object, key, value):
        pass

    def stateRemove(self, object, key, value):
        pass

# FIXME: nicer to rewrite do_stop, do_start and do_delete to run some common 
# code
def do_avatar_action(model, quit, avatarPath, action):
    """
    @type action: a tuple of (actionName, remoteCall, moods, checkMoodFunc)
    """
    d = model.callRemote('getPlanetState')
    yield d
    planet = d.value()
    components = []
    if avatarPath[0] == 'flow':
        flows = planet.get('flows')
        flow_to_act = None
        for f in flows:
            if avatarPath[1] == f.get('name'):
                flow_to_act = f
        if flow_to_act == None:
            print "The flow %s is not found." % avatarPath[1]
            quit()
        else:
            components = flow_to_act.get('components')
    elif avatarPath[0] == 'atmosphere':
        components = planet.get('atmosphere').get('components')
    elif avatarPath[0] == 'root':
        flows = planet.get('flows')
        for f in flows:
            components = components + f.get('components')
        components = components + planet.get('atmosphere').get('components')
    else:
        c = utils.find_component(planet, avatarPath[1:])
        components.append(c)

    if len(components) > 0:
        def actionComponent(c):
            if action[3](moods[c.get('mood')]):
                return model.callRemote(action[1], c)
            else:
                print "Cannot %s component /%s/%s, it is in mood: %s." % (
                    action[0],
                    c.get("parent").get("name"), c.get("name"), 
                    moods[c.get("mood")].name)
                return None
        dl = []
        for comp in components:
            actD = actionComponent(comp)
            # maybeDeferred won't work here due to python lexicals
            if actD:
                dl.append(actD)
                if action[2]:
                    # wait for component to be in certain moods
                    listener = MoodListener()
                    waitForMoodD = listener.waitOnMood(action[2])
                    comp.addListener(listener)
                    dl.append(waitForMoodD)
        d = defer.DeferredList(dl)
        yield d
        d.value()
        if avatarPath[0] == 'flow':
            print "Components in flow now completed action %s." % action[0]
        elif avatarPath[0] == 'atmosphere':
            print "Components in atmosphere now completed action %s." % (
                action[0],)
        elif avatarPath[0] == 'root':
            print "Components in / now completed action %s." % action[0]
        else:
            print "Component now completed action %s." % action[0]
    quit()
do_avatar_action = defer_generator(do_avatar_action)

def do_stop(model, quit, avatarPath):
    return do_avatar_action(model, quit, avatarPath, ('stop', 'componentStop',
        (moods.sleeping,), moods.can_stop))

def do_start(model, quit, avatarPath):
    return do_avatar_action(model, quit, avatarPath, ('start', 'componentStart',
        (moods.happy, moods.sad), moods.can_start))

def do_delete(model, quit, avatarPath):
    return do_avatar_action(model, quit, avatarPath, ('delete', 
        'deleteComponent', None, lambda m: not moods.can_stop(m)))

commands = (('getprop',
             'gets a property on a component',
             (('component-path', utils.avatarId),
              ('property-name', str)),
             do_getprop),
            ('listprops',
             'lists the properties a component has',
             (('component-path', utils.avatarId),
              ),
             do_listprops),
            ('showplanet',
             'shows the flows, atmosphere, and components in the planet',
             (),
             do_showplanet),
            ('getmood',
             'gets the mood of a component',
             (('component-path', utils.avatarId),
              ),
             do_getmood),
            ('showcomponent',
             'shows everything we know about a component',
             (('component-path', utils.avatarId),
              ),
             do_showcomponent),
            ('showworkers',
             'shows all the workers that are logged into the manager',
             (),
             do_showworkers),
            ('invoke',
             'invoke a component method',
             (('component-path', utils.avatarId),
              ('method-name', str)),
             do_invoke),
            ('loadconfiguration',
             'load configuration into the manager',
             (('conf-file', str),
              ('save-as', str, None),
              ),
             do_loadconfiguration),
            ('stop',
             'stops a component, flow or all flows',
             (('path', utils.avatarPath),
             ),
             do_stop),
            ('start',
             'starts a componment, all components in a flow or all flows',
             (('path', utils.avatarPath),
             ),
             do_start),
            ('delete',
             'deletes a component, all components in a flow or all flows',
             (('path', utils.avatarPath),
             ),
             do_delete)
            )
