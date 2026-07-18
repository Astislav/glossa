import faulthandler
import sys

from nexus_kit import Root
from nexus_kit.impl import ContainerInjector

from app.application import Application
from app.config.di import DI_CONFIG
from app.config.environment import Environment

if __name__ == "__main__":
    if sys.stderr is not None:  # windowed builds (console=False) have no stderr
        faulthandler.enable(all_threads=True)

    env = Environment(Root.external(".env"))
    container = ContainerInjector(DI_CONFIG)
    container.set(Environment, env)
    Application(env, container).run()
