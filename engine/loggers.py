from injector import singleton

from nexus_kit.logging import NamedLogger


@singleton
class ManagerLogger(NamedLogger):
    name = "ls.manager"


@singleton
class SwitcherLogger(NamedLogger):
    name = "ls.switcher"


@singleton
class HookLogger(NamedLogger):
    name = "ls.hook"
