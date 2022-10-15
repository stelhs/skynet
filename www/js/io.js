
class Io extends ModuleBase {
    constructor(ui) {
        super(ui, 'io');
        this.conf = ui.configs['io'];
        this.termosensorsConf = ui.configs['termosensors'];
        this.pagesNumber = 1 + Object.keys(this.conf['boards']).length;

        this.ledsState = {};
        this.ledsBlocked = {};
        this.ledsEmulate = {};
        this.ledsBlink = {};
        this.ledsEmulate = {};
        this.labelsBlink = {};

        this.termoSensors = {};
    }

    title() {
        return 'Модули I/O';
    }

    description() {
        return 'Панель управления платами ввода-вывода';
    }

    eventSources() {
        return ['io', 'termosensors'];
    }

    setTermoSensorsPageContent(content) {
        this.setPageContent(1, content)
    }

    setMbioPageContent(mbioNum, content) {
        this.setPageContent(1 + mbioNum, content)
    }

    init() {
        super.init();

        var tpl = this.tplOpen('mod_io_1');
        var num = 0;
        tpl.assign('item_columns')
        for (var name in this.termosensorsConf['sensors']) {
            var info = this.termosensorsConf['sensors'][name];
            num ++;

            if (num > 4) {
                tpl.assign('item_columns');
                num = 1;
            }

            tpl.assign('ss_item',
                       {'name': name,
                        'description': info['description']})
        }
        this.setTermoSensorsPageContent(tpl.result())

        // init pages
        var pageNum = 0
        for (var ioName in this.conf['boards']) {
            pageNum += 1
            var boardInfo = this.conf['boards'][ioName];
            var tpl = this.tplOpen('mod_io_mbio');
            if ('in' in boardInfo) {
                tpl.assign('inputs', {'io_name': ioName});
                for (var portNum in boardInfo['in']) {
                    var portInfo = boardInfo['in'][portNum];
                    var pName = portInfo['name']
                    tpl.assign('input',
                               {'port_num': portNum,
                                'port_name': pName,
                                'io_name': ioName});
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
                }
            }
            this.setMbioPageContent(pageNum, tpl.result())
        }

        for (var ioName in this.conf['boards']) {
            var boardInfo = this.conf['boards'][ioName];
            if ('in' in boardInfo) {
                for (var portNum in boardInfo['in']) {
                    pName = boardInfo['in'][portNum]['name'];
                    this.ledsState[pName] = new Led("led_io_port_" + pName + "_state", 'red', 3);
                    this.ledsBlocked[pName] = new Led('led_io_port_' + pName + '_blocked', 'green', 0, 'mini');
                    this.ledsEmulate[pName] = new Led('led_io_port_' + pName + '_emulate', 'green', 0, 'mini');
                }
            }
            if ('out' in boardInfo) {
                for (var portNum in boardInfo['out']) {
                    pName = boardInfo['out'][portNum];
                    this.ledsState[pName] = new Led("led_io_port_" + pName + "_state", 'green', 3);
                    this.ledsBlocked[pName] = new Led('led_io_port_' + pName + '_blocked', 'green', 0, 'mini');
                    this.ledsBlink[pName] = new Led("led_io_port_" + pName + "_blink", 'green', 3, 'mini');
                    this.labelsBlink[pName] = $$("label_io_port_" + pName + "_blink_info");
                }
            }
        }

        for (var name in this.termosensorsConf['sensors']) {
            this.termoSensors[name] = new SevenSeg("ss_" + name, "red", 3, 3)
        }

        this.requestIoBlockedPortsInfo();
    }

    eventHandler(source, type, data) {
        switch (source) {
        case 'io':
            switch (type) {
            case 'boardsBlokedPortsList':
                this.updateBlokedPorts(data);
                return;

            case 'portsStates':
                this.updatePortStates(data)
                return;

            case 'error':
                this.logErr(data)
                return;

            case 'info':
                this.logInfo(data)
                return;

            default:
                this.logErr("Incorrect event type: " + type)
            }

        case 'termosensors':
            switch (type) {
            case 'termosensorsUpdate':
                this.updateTermoSensors(data);
                return;
            }
        }
    }


    logErr(msg) {
        this.ui.logErr("IO: " + msg)
    }


    logInfo(msg) {
        this.ui.logInfo("IO: " + msg)
    }

    updateBlokedPorts(data) {
        this.logInfo('Blocked ports status success updated')
        for (var i in this.ledsBlocked) {
            var led = this.ledsBlocked[i];
            led.set('off');
        }

        for (var i in data) {
            var row = data[i];
            var type = row['type'];
            var pName = row['port_name'];
            var state = parseInt(row['state']);
            var ledBlocked = this.ledsBlocked[pName];

            if (row['isBlocked'])
                ledBlocked.set('on');
            else
                ledBlocked.set('off');
            if (type == 'in')
                this.ledsEmulate[pName].light(state);
        }
    }

    updateTermoSensors(data) {
        for (var name in data)
            if (data[name])
                this.termoSensors[name].set(data[name])
    }

    updatePortStates(data) {
        if (!('io_name' in data)) {
            this.logErr('Can`t updatePortStates(): field "io_name" is absent')
            return
        }

        if (!('ports' in data)) {
            this.logErr('Can`t updatePortStates(): field "ports" is absent')
            return
        }

        var ioName = data['io_name']

        for (var row of data['ports']) {
            var pName = row['port_name'];
            var type = row['type'];
            var state = parseInt(row['state']);
            var labelBlink = this.labelsBlink[pName];
            var ledBlink = this.ledsBlink[pName];
            this.ledsState[pName].light(state)

            if ('blinking' in row) {
                var blinking = row['blinking'];
                ledBlink.set('on');
                labelBlink.innerHTML = '(' + blinking['d1'] + '/' + blinking['d2'] + ':' +blinking['cnt'] + ')';
                labelBlink.style.display = 'block';
                continue;
            }

            if (ledBlink) {
                ledBlink.set('off');
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
            this.skynetGetRequest('io/port/blink',
                             {'port_name': portName,
                              'd1': parseInt(d1 * 1000),
                              'd2': parseInt(d2 * 1000),
                              'number': number});
        }
        var numberBox = new NumberBox(this.ui, cb.bind(this),
                                      'Режим blink для порта ' + portName + '/' + ioName,
                                      [['d1', 'Вкл. время, сек', 0.3, 9999, 'lime', false],
                                       ['d2', 'Выкл. время, сек', 0.3, 9999, 'lime', false],
                                       ['number', 'Количество', 1, 9999, 'red', false]]);
        this.ui.showDialogBox(numberBox)
    }

    onTogglePortLockUnlock(portName) {
        this.logInfo('Request to Lock/Unlock port "' + portName + '"');
        this.skynetGetRequest('io/port/toggle_lock_unlock', {'port_name': portName});
    }

    onTogglePortBlockedState(portName) {
        this.logInfo('Request to change software emulation input state for port "' + portName + '"');
        this.skynetGetRequest('io/port/toggle_blocked_state', {'port_name': portName});
    }

    onTogglePortState(portName) {
        this.logInfo('Request to toggle state for port "' + portName + '"');
        this.skynetGetRequest('io/port/toggle_out_state', {'port_name': portName});
    }

    requestIoBlockedPortsInfo() {
        this.logInfo('Request to skynet for obtain blocked ports info')
        this.skynetGetRequest('io/request_io_blocked_ports')
    }

}