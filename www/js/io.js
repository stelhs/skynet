
class Io extends ModuleBase {
    constructor(ui) {
        super(ui, 'io');
        this.conf = ui.configs['io'];
        this.termosensorsConf = ui.configs['termosensors'];
        this.pagesNumber = 1 + Object.keys(this.conf['boards']).length;
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
                    this.ui.ledRegister("ledIoPortState_" + pName, 'red');
                    this.ui.ledRegister("ledIoPortBlocked_" + pName, 'green', 'mini', 0);
                    this.ui.ledRegister("ledIoPortEmulate_" + pName, 'green', 'mini', 0);
                }
            }
            if ('out' in boardInfo) {
                for (var portNum in boardInfo['out']) {
                    pName = boardInfo['out'][portNum];
                    this.ui.ledRegister("ledIoPortState_" + pName, 'green');
                    this.ui.ledRegister("ledIoPortBlocked_" + pName, 'green', 'mini', 0);
                    this.ui.ledRegister("ledIoPortBlink_" + pName, 'green', 'mini');
                    this.ui.labelBarRegister("labelIoPortBlink_" + pName)
                }
            }
        }

        for (var name in this.termosensorsConf['sensors'])
            this.ui.sevenSegRegister("ssTermosensor_" + name, "red", 4);

        this.requestIoBlockedPortsInfo();
    }

    eventHandler(source, type, data) {
        this.ledAct();
    }

    logErr(msg) {
        this.ui.logErr("IO: " + msg)
    }


    logInfo(msg) {
        this.ui.logInfo("IO: " + msg)
    }

    onPageChanged() {
        this.requestIoBlockedPortsInfo();
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