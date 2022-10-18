
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

        this.boilerStateBar = new StatusBar('bolier_state', 3);

        this.leds = {'power': new Led('led_power', 'green', 3),
                     'air_fun': new Led('led_air_fun', 'green', 3),
                     'fuel_pump': new Led('led_fuel_pump', 'green', 3),
                     'ignition': new Led('led_ignition', 'red', 3),
                     'water_pump': new Led('led_water_pump', 'green', 3),
                     'flame': new Led('led_flame', 'green', 3),
                     'heater': new Led('led_heater', 'red', 3),
                     'no_pressure': new Led('led_no_pressure', 'red', 3),
                     'overheat': new Led('led_overheat', 'red', 3)};

        this.sevenSegs = {'target_t':  new SevenSeg("ss_target_t", "lime", 3, 3),
                          'room_t':  new SevenSeg("ss_room_t", "lime", 3, 3),
                          'boiler_box_t':  new SevenSeg("ss_boiler_box_t", "red", 3, 3),
                          'boiler_t':  new SevenSeg("ss_boiler_t", "red", 3, 3),
                          'return_t':  new SevenSeg("ss_return_t", "red", 3, 3),
                          'ignition_counter':  new SevenSeg("ss_ignition_counter", "orange", 3, 3),
                          'fuel_consumption':  new SevenSeg("ss_fuel_consumption", "orange", 3, 3)}
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
        switch (type) {
        case 'boilerStatus':
            this.updateStatus(data);
            return;

        case 'error':
            this.logErr(data)
            return

        case 'info':
            this.logInfo(data)
            return

        case 'boilerFuelConsumption':
            this.updateBoilerFuelConsumption(data);
            return

        default:
            this.logErr("Incorrect event type: " + type)
        }
    }

    actualizeSevenSeg(data, field) {
        if (field in data)
            var val = data[field].toString()
            val = Math.round(val * 10) / 10
            this.sevenSegs[field].set(val)
    }

    updateStatus(data) {
        if (typeof data !== 'object') {
            this.logErr("Incorrect event status")
            return;
        }

        if ('state' in data)
            this.boilerStateBar.set(data['state']);

        this.leds['power'].actualize(data, 'power', 'True');
        this.leds['air_fun'].actualize(data, 'air_fun', 'True');
        this.leds['fuel_pump'].actualize(data, 'fuel_pump', 'True');
        this.leds['ignition'].actualize(data, 'ignition', 'True');
        this.leds['water_pump'].actualize(data, 'water_pump', 'True');
        this.leds['flame'].actualize(data, 'flame', 'True');
        this.leds['heater'].actualize(data, 'heater', 'True');
        this.leds['no_pressure'].actualize(data, 'no_pressure', 'True');
        this.leds['overheat'].actualize(data, 'overheat', 'True');

        this.actualizeSevenSeg(data, 'target_t');
        this.actualizeSevenSeg(data, 'room_t');
        this.actualizeSevenSeg(data, 'boiler_box_t');
        this.actualizeSevenSeg(data, 'boiler_t');
        this.actualizeSevenSeg(data, 'return_t');
        this.actualizeSevenSeg(data, 'ignition_counter');
        this.actualizeSevenSeg(data, 'fuel_consumption');
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




