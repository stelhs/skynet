
class Io extends ModuleBase {
    constructor(ui) {
        super(ui, 'io');
        this.ioNames = ['mbio1', 'sbio2', 'mbio3', 'mbio4'];
        this.pagesNumber = this.ioNames.length;
        this.boardDivs = {};
        this.portsInfo = {};
        this.watcherTimeoutHandler = {}
        this.ioInfoLoaded = false
    }

    title() {
        return 'Модули I/O';
    }

    description() {
        return 'Панель управления платами ввода-вывода';
    }

    init() {
        super.init();
        for (var i in this.ioNames) {
            var ioName = this.ioNames[i];
            this.boardDivs[ioName] = $$('mod_io_mbio_' + ioName);
            this.watcherTimeoutHandler[ioName] = NaN
        }

        this.requestToUpdateBoardsIO();

        for (var i in this.ioNames) {
            var ioName = this.ioNames[i];
            this.restartEventTimeoutWatcher(ioName);
        }
    }

    eventHandler(type, data) {
        switch (type) {
        case 'boardsInfo':
            this.updateBoardsInfo(data)
            return;

        case 'boardsBlokedPortsList':
            if (!this.ioInfoLoaded)
                return;
            this.updateBlokedPorts(data);
            return;

        case 'error':
            this.logErr(data)
            return

        case 'info':
            this.logInfo(data)
            return

        case 'ioStatus':
            if (!this.ioInfoLoaded)
                return;
            this.updatePortStates(data)
            return

        default:
            this.logErr("Incorrect event type: " + type)
        }
    }


    logErr(msg) {
        this.ui.logErr("IO: " + msg)
    }


    logInfo(msg) {
        this.ui.logInfo("IO: " + msg)
    }


    onPageChanged(pageNum) {
    }

    html(pageNum) {
        var tpl = this.ui.teamplates.openTpl('mod_io_mbio');
        tpl.assign('mbio_page', {'name': this.ioNames[pageNum - 1]});
        return tpl.result();
    }

    requestToUpdateBoardsIO() {
        this.logInfo('Request to sr90 to obtain board IO info')
        this.sr90Request('io/request_mbio_ui_update')
    }

    updateBoardsInfo(data) {
        this.portNamesList = [];
        for (var i in this.ioNames) {
            var ioName = this.ioNames[i];
            if (!(ioName in data)) {
                this.logErr('updateBoardsInfo: board "' + ioName + '" is absent in update event');
                continue;
            }

            var boardInfo = data[ioName];
            var tpl = this.ui.teamplates.openTpl('mbio');
            if ('in' in boardInfo) {
                tpl.assign('inputs', {'io_name': ioName});
                for (var portNum in boardInfo['in']) {
                    var portInfo = boardInfo['in'][portNum];
                    tpl.assign('input',
                               {'port_num': portNum,
                                'port_name': portInfo['name'],
                                'io_name': ioName});

                    this.portsInfo[portInfo['name']] = {'ioName': ioName};
                }
            }

            if ('out' in boardInfo) {
                tpl.assign('outputs', {'io_name': ioName});
                for (var portNum in boardInfo['out']) {
                    var pName = boardInfo['out'][portNum];
                    tpl.assign('output',
                               {'port_num': portNum,
                                'port_name': pName,
                                'io_name': ioName});

                    this.portsInfo[pName] = {'ioName': ioName};
                }
            }
            this.boardDivs[ioName].innerHTML = tpl.result();
        }

        for (var pName in this.portsInfo) {
            var ledBlocked = $$('led_io_port_' + pName + '_blocked');
            var ledEmulate = $$('led_io_port_' + pName + '_emulate');
            var ledState = $$("led_port_" + pName + "_state");
            var ledBlink = $$("led_port_" + pName + "_blink");
            var labelBlink = $$("label_port_" + pName + "_blink_info");

            this.portsInfo[pName]['ledBlocked'] = ledBlocked;
            this.portsInfo[pName]['ledEmulate'] = ledEmulate;
            this.portsInfo[pName]['ledState'] = ledState;
            this.portsInfo[pName]['ledBlink'] = ledBlink;
            this.portsInfo[pName]['labelBlink'] = labelBlink;
        }

        for (var i in this.ioNames) {
            var ioName = this.ioNames[i];
            this.ioResetStates(ioName);
        }
        this.ioInfoLoaded = true
    }


    restartEventTimeoutWatcher(ioName) {
        if (this.watcherTimeoutHandler[ioName]) {
            clearTimeout(this.watcherTimeoutHandler[ioName]);
            this.watcherTimeoutHandler[ioName] = NaN;
        }

        var handler = function() {
            this.logErr('UI does not receive a signal from "' + ioName + '" more then 3 second');
            this.ioResetStates(ioName);
        }

        this.watcherTimeoutHandler[ioName] = setTimeout(handler.bind(this), 3000);
    }

    ioResetStates(ioNameForReset) {
        for (var pName in this.portsInfo) {
            var ioName = this.portsInfo[pName]['ioName'];
            if (ioName != ioNameForReset)
                continue;

            var ledState = this.portsInfo[pName]['ledState'];
            var ledBlink = this.portsInfo[pName]['ledBlink'];
            var labelBlink = this.portsInfo[pName]['labelBlink'];

            ledState.className = 'led_big-undefined';
            if (ledBlink) {
                ledBlink.className = 'led_mini-undefined';
                labelBlink.innerHTML = "";
            }
        }
    }


    updateBlokedPorts(data) {
        this.logInfo('Locked ports status sucess updated')
        for (var pName in this.portsInfo) {
            var ledBlocked = this.portsInfo[pName]['ledBlocked'];
            var ledEmulate = this.portsInfo[pName]['ledEmulate'];

            ledBlocked.className = 'led_mini-off';
            if (ledEmulate)
                ledEmulate.className = 'led_mini-off';
        }

        for (var i in data) {
            var row = data[i];
            var type = row['type'];
            var pName = row['port_name'];
            var state = parseInt(row['state']);
            var ledBlocked = this.portsInfo[pName]['ledBlocked'];

            ledBlocked.className = 'led_mini-green';
            if (type == 'in') {
                var ledEmulate = this.portsInfo[pName]['ledEmulate'];
                if (state)
                    ledEmulate.className = 'led_mini-green';
                else
                    ledEmulate.className = 'led_mini-off';
            }
        }
    }

    updatePortStates(data) {
        if (!('io_name' in data)) {
            this.logErr('Can`t updatePortStates(): field "io_name" is absent')
            return
        }

        if (!('list' in data)) {
            this.logErr('Can`t updatePortStates(): field "list" is absent')
            return
        }

        var ioName = data['io_name']
        this.restartEventTimeoutWatcher(ioName);

        for (var i in data['list']) {
            var row = data['list'][i];
            var pName = row['port_name'];
            var type = row['type'];
            var state = parseInt(row['state']);
            var ledState = this.portsInfo[pName]['ledState'];
            var ledBlink = this.portsInfo[pName]['ledBlink'];
            var labelBlink = this.portsInfo[pName]['labelBlink'];
            var color = (type == 'in') ? 'red' : 'green';

            if (state)
                ledState.className = 'led_big-' + color;
            else
                ledState.className = 'led_big-off';

            if ('blinking' in row) {
                var blinking = row['blinking'];
                ledBlink.className = 'led_mini-green';
                labelBlink.innerHTML = '(' + blinking['d1'] + '/' + blinking['d2'] + ':' +blinking['cnt'] + ')';
                labelBlink.style.display = 'block';
                continue;
            }

            if (ledBlink) {
                ledBlink.className = 'led_mini-off';
                labelBlink.style.display = 'none';
                labelBlink.innerHTML = "";
            }
        }
    }

    onSetPortBlink(ioName, portName) {
        var cb = function(results) {
            var d1 = results['d1']
            var d2 = results['d2']
            var number = results['number']
            this.logInfo('Request to blinking port ' + portName + '"');
            this.sr90Request('io/port/blink',
                             {'port_name': portName,
                              'd1': parseInt(d1 * 1000),
                              'd2': parseInt(d2 * 1000),
                              'number': number});
        }
        var numberBox = new NumberBox(this.ui, cb.bind(this),
                                      'Режим blink для порта ' + portName + '/' + ioName,
                                      [['d1', 'Вкл. время, сек', 0.3, 9999, 'lime'],
                                       ['d2', 'Выкл. время, сек', 0.3, 9999, 'lime'],
                                       ['number', 'Количество', 1, 9999, 'red']]);
        this.ui.showDialogBox(numberBox)
    }

    onTogglePortLockUnlock(portName) {
        this.logInfo('Request to Lock/Unlock port "' + portName + '"');
        this.sr90Request('io/port/toggle_lock_unlock', {'port_name': portName});
    }

    onTogglePortBlockedState(portName) {
        this.logInfo('Request to change software emulation input state for port "' + portName + '"');
        this.sr90Request('io/port/toggle_blocked_state', {'port_name': portName});
    }

    onTogglePortState(portName) {
        this.logInfo('Request to toggle state for port "' + portName + '"');
        this.sr90Request('io/port/toggle_state', {'port_name': portName});
    }

}