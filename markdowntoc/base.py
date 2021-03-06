import pprint
import sublime
import json
from .util import Util

# for debug
pp = pprint.PrettyPrinter(indent=4)

class Base(object):

    def settings(self, attr):
        DEFAULT = 'Packages/MarkdownTOC/MarkdownTOC.sublime-settings'
        files = sublime.find_resources('MarkdownTOC.sublime-settings')
        files.remove(DEFAULT)
        settings = sublime.decode_value(sublime.load_resource(DEFAULT))
        for f in files:
            user_settings = sublime.decode_value(sublime.load_resource(f))
            if user_settings != None:
                Util.dict_merge(settings, user_settings)
        return settings[attr]

    def defaults(self):
        return self.settings('defaults')

    def log(self, arg):
        if self.settings('logging') is True:
            arg = str(arg)
            sublime.status_message(arg)
            pp.pprint(arg)

    def error(self, arg):
        arg = 'MarkdownTOC Error: '+arg
        arg = str(arg)
        sublime.status_message(arg)
        pp.pprint(arg)
