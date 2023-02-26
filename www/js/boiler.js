
class Boiler extends ModuleBase {
    constructor(ui) {
        super(ui, 'boiler');
        this.watcherTimeoutHandler = NaN;
        this.pagesNumber = 2;
    }

    title() {
        return 'Котёл';
    }

    description() {
        return 'Панель управления котлом';
    }

    eventSources() {
        return ['boiler'];
    }

    setContentPageTotal(content) {
        this.setPageContent(1, content)
    }

    setContentPageStatistics(content) {
        this.setPageContent(2, content)
    }

    init() {
        super.init();

        var tpl = this.tplOpen('mod_boiler_1')
        tpl.assign();
        this.setContentPageTotal(tpl.result())

        this.boilerStateBar = this.ui.statusBarRegister('sbBolierState');

        this.ui.ledRegister('ledBoilerPower', 'green');
        this.ui.ledRegister('ledBoilerAirFun', 'green');
        this.ui.ledRegister('ledBoilerFuelPump', 'green');
        this.ui.ledRegister('ledBoilerIgnition', 'red');
        this.ui.ledRegister('ledBoilerWaterPump', 'green');
        this.ui.ledRegister('ledBoilerFlame', 'green');
        this.ui.ledRegister('ledBoilerHeater', 'red');
        this.ui.ledRegister('ledBoilerNoPressure', 'green');
        this.ui.ledRegister('ledBoilerOverheat', 'green');

        this.ui.sevenSegRegister("ssBoilerTarget_t", "lime", 3)
        this.ui.sevenSegRegister("ssBoilerRoom_t", "lime", 4)
        this.ui.sevenSegRegister("ssBoilerBox_t", "red", 4)
        this.ui.sevenSegRegister("ssBoilerWater_t", "red", 4)
        this.ui.sevenSegRegister("ssBoilerRetWater_t", "red", 4)
        this.ui.sevenSegRegister("ssBoilerIgnitionCounter", "orange", 3)
        this.ui.sevenSegRegister("ssBoilerFuelConsumption", "orange", 3)
    }


    onPageChanged(pageNum) {
        if (pageNum == 2)
            this.requestBoilerFuelConsumption()
    }

    logErr(msg) {
        this.ui.logErr("Boiler: " + msg)
    }

    logInfo(msg) {
        this.ui.logInfo("Boiler: " + msg)
    }


    eventHandler(source, type, data) {
        this.ledAct();
        switch (type) {
        case 'boilerFuelConsumption':
            this.updateBoilerFuelConsumption(data);
            return
        }
    }


    boilerRequest(method, args) {
        var success = function(responceText) {
            var resp = JSON.parse(responceText)

            if (resp.status == 'error') {
                this.logErr("boiler method 'boiler/" + method + "'" +
                            "return error: " + resp.reason)
                return;
            }
            this.logInfo("to boiler 'boiler/" + method + "' success finished")
        }

        var error = function(reason, errCode) {
            this.logErr('Can`t send request "boiler/' + method + '" to boiler: ' + reason)
        }
        asyncAjaxReq('GET', 'boiler/' + method, args,
                     success.bind(this), error.bind(this))
    }

    boilerSetTarget_t(t) {
        this.ui.logInfo('Request to set target temperature ' + t);
        this.boilerRequest('set_target_t', {'t': t.toString()})
    }

    onClickSetTarget_t() {
        var cb = function(results) {
            var t = results['t'];
            this.boilerSetTarget_t(t);
        }

        var numberBox = new NumberBox(this.ui, cb.bind(this),
                                      'Установить температуру',
                                      [['t', 't°', 2, 30, 'lime', false]]);
        this.ui.showDialogBox(numberBox)
    }

    boilerStart() {
        this.ui.logInfo('Request to start boiler');
        this.boilerRequest('boiler_start')
    }

    boilerEnableHeater() {
        this.ui.logInfo('Request to enable heater');
        this.boilerRequest('heater_enable')
    }

    boilerDisableHeater() {
        this.ui.logInfo('Request to disable heater');
        this.boilerRequest('heater_disable')
    }

    updateBoilerFuelConsumption(data) {
        var months = ['Январь',
                      'Февраль',
                      'Март',
                      'Апрель',
                      'Май',
                      'Июнь',
                      'Июль',
                      'Август',
                      'Сентябрь',
                      'Октябрь',
                      'Ноябрь',
                      'Декабрь'];

        if (typeof data !== 'object') {
            this.logErr("Incorrect event boilerFuelConsumption")
            return;
        }

        var tpl = this.tplOpen('mod_boiler_2');

        if (!data.length) {
            tpl.assign('no_data');
            this.setContentPageStatistics(tpl.result())
            this.logErr('Received list of fuel consumption is empty');
            return;
        }

        for (var i in data) {
            var row = data[i];

            if (!('year' in row)) {
                this.logErr('Incorrect boiler fuel consumption event: field "year" is absent');
                return;
            }

            if (!('total' in row)) {
                this.logErr('Incorrect boiler fuel consumption event: field "total" is absent');
                return;
            }

            if (!('months' in row)) {
                this.logErr('Incorrect boiler fuel consumption event: field "months" is absent');
                return;
            }

            tpl.assign('year', {'year': row['year'],
                                'total': row['total']});

            for (var i in row['months']) {
                var subrow = row['months'][i];

                if (!('month' in subrow)) {
                    this.logErr('Incorrect boiler fuel consumption event: sub field "month" is absent in months list');
                    return;
                }

                if (!('liters' in subrow)) {
                    this.logErr('Incorrect boiler fuel consumption event: sub field "liters" is absent in months list');
                    return;
                }

                tpl.assign('month',
                           {'month': months[subrow['month'] - 1],
                            'liters': subrow['liters']});
            }
        }
        this.setContentPageStatistics(tpl.result())
    }

    requestBoilerFuelConsumption() {
        this.logInfo('Request to skynet to obtain fuel consumption report')
        this.skynetGetRequest('boiler/request_fuel_compsumption_stat')
    }
}




