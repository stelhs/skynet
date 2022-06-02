from sr90Exceptions import *

# Database errors:

class DatabaseConnectorError(AppError):
    pass


# errors in subsystem event handler

class EventHandlerError(AppError):
    pass



# IO boars errors

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


# Thermosensors errors

class TermosensorError(AppError):
    pass

class TermosensorConfiguringError(TermosensorError):
    pass

class TermosensorNotRegistredError(TermosensorError):
    pass

class TermosensorNoDataError(TermosensorError):
    pass



# Boiler errors:

class BoilerError(AppError):
    pass
