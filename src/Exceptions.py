

class AppError(Exception): # Base of all errors
    def __init__(s, log, msg):
        log.err("Skynet Exception: %s" % msg)
#        global skynet
#        skynet.tc.sendToChat('stelhs', "Skynet Error:\n%s" % msg)
        super().__init__(msg)


class DatabaseConnectorError(AppError):
    pass


class EventHandlerError(AppError): # error in subsystem event handler
    pass


class ConfigError(AppError): # Configuration parser errors
    pass




class IoError(AppError): # Base of all IO subsystem errors
    pass

class IoPortNotFound(IoError): # IO port is not found
    pass

class IoBoardNotFound(IoError): # IO board is not found
    pass

class IoBoardError(IoError): # Base of all IO board errors
    pass

class IoBoardPortNotFound(IoBoardError): # IO port is not found on the selected board IO
    pass

class IoBoardEmulatorError(IoBoardError): # IO board emulator errors
    pass

class IoBoardConfigureErr(IoBoardError): # Configuring of all IO boards errors
    pass

class IoBoardMbioError(IoBoardError): # MBIO board errors
    pass




class TermosensorError(AppError):
    pass

class TermosensorConfiguringError(TermosensorError):
    pass

class TermosensorNotRegistredError(TermosensorError):
    pass

class TermosensorNoDataError(TermosensorError):
    pass



class TelegramError(AppError): # Telegram client errors
    pass

class TelegramClientError(TelegramError):
    pass


# Mysql base error: mysql.connector.errors.Error


class BoilerError(AppError):
    pass