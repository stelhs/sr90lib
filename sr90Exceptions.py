
class AppError(Exception):
    def __init__(s, log, msg):
        super().__init__(s, msg)
        log.err("Error %s: %s" % (s.__class__, msg))


# Tasks

class TaskAlreadyExistException(AppError):
    pass


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


# Settings Errors

class SettingsError(AppError):
    pass

class SettingsSaveError(SettingsError):
    pass


# Subprocess Errors

class SubProcessError(AppError):
    pass

class SubProcessRegisterError(SubProcessError):
    pass

class SubProcessNotStartedError(SubProcessError):
    pass

class SubProcessCantStopError(SubProcessError):
    pass

class SubProcessCantStartError(SubProcessError):
    pass
