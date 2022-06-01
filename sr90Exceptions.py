
class AppError(Exception):
    def __init__(s, log, msg):
        super().__init__(s, msg)
        log.err("MBIO Exception: %s" % msg)


# Configuration parser errors

class ConfigError(AppError):
    pass


# Gpio errors

class GpioError(AppError):
    pass

class GpioNotRegistredError(GpioError):
    pass

class GpioNotConfiguredError(GpioError):
    pass

class GpioNumberIsBusyError(GpioError):
    pass

class GpioIncorrectStateError(GpioError):
    pass


# Telegram client errors

class TelegramError(AppError): # Telegram client errors
    pass

class TelegramClientError(TelegramError):
    pass

