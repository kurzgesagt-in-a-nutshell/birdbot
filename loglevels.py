import logging

LDEBUG = 15
logging.addLevelName(15, "LDEBUG")


def ldebug(self, message, *args, **kws):
    if self.isEnabledFor(15):
        self._log(15, message, args, **kws)


def setup():
    logging.Logger.ldebug = ldebug
    logging.LDEBUG = LDEBUG
