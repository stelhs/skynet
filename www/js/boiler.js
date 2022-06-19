
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

        this.boilerStateDiv = $$('bolier_state');


        this.leds = {'led_power': new Led('led_power', 'green', 3),
                     'led_air_fun': new Led('led_air_fun', 'green', 3),
                     'led_fuel_pump': new Led('led_fuel_pump', 'green', 3),
                     'led_ignition': new Led('led_ignition', 'green', 3),
                     'led_water_pump': new Led('led_water_pump', 'red', 3),
                     'led_flame': new Led('led_flame', 'green', 3),
                     'led_heater': new Led('led_heater', 'red', 3),
                     'led_no_pressure': new Led('led_no_pressure', 'red', 3),
                     'led_overheat': new Led('led_overheat', 'red', 3)};

        this.sevenSegs = {
                     'ss_target_t': [$("#ss_target_t"), 3, "lime"],
                     'ss_room_t': [$("#ss_room_t"), 3, "lime"],
                     'ss_boiler_box_t': [$("#ss_boiler_box_t"), 3, "red"],
                     'ss_boiler_t': [$("#ss_boiler_t"), 3, "red"],
                     'ss_return_t': [$("#ss_return_t"), 3, "red"],
                     'ss_ignition_counter': [$("#ss_ignition_counter"), 3, "orange"],
                     'ss_fuel_consumption': [$("#ss_fuel_consumption"), 3, "orange"],
                     'ss_fuel_consumption_month': [$("#ss_fuel_consumption_month"), 4, "orange"],
                     'ss_fuel_consumption_year': [$("#ss_fuel_consumption_year"), 4, "orange"]};


        this.uiReset();

        for (var name in this.sevenSegs)
            this.showSevenSegVal(name, "");

        this.restartEventTimeoutWatcher();
    }


    onPageChanged(pageNum) {
        if (pageNum == 2)
            this.requestBoilerFuelConsumption()
    }

    showBoilerState(state) {
        this.boilerStateDiv.innerHTML = state;
    }

    showSevenSegVal(name, val) {
        var parts = this.sevenSegs[name];
        var div = parts[0];
        var digits = parts[1];
        var color = parts[2];

        div.sevenSegArray({
            value: val,
            digits:digits,
            segmentOptions: {
                colorOff: "#003500",
                colorOn: color,
                slant: 10
            }
        });

    }

    uiReset() {
        this.showBoilerState('-');

        for (var name in this.sevenSegs)
            this.showSevenSegVal(name, "XXXXX");

        this.setContentPageStatistics('')
    }

    logErr(msg) {
        this.ui.logErr("Boiler: " + msg)
    }

    logInfo(msg) {
        this.ui.logInfo("Boiler: " + msg)
    }

    restartEventTimeoutWatcher() {
        if (this.watcherTimeoutHandler) {
            clearTimeout(this.watcherTimeoutHandler);
            this.watcherTimeoutHandler = NaN;
        }

        var handler = function() {
            this.uiReset();
            this.logErr('UI does not receive a signal from boiler more then 3 second');
        }
        this.watcherTimeoutHandler = setTimeout(handler.bind(this), 3000);
    }

    eventHandler(source, type, data) {
        switch (type) {
        case 'boilerStatus':
            this.restartEventTimeoutWatcher();
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

    actualizeSevenSeg(segName, data, field) {
        if (field in data)
            this.showSevenSegVal(segName, data[field].toString());
    }

    updateStatus(data) {
        if (typeof data !== 'object') {
            this.logErr("Incorrect event status")
            return;
        }

        if ('state' in data)
            this.showBoilerState(data['state']);

        this.leds['led_power'].actualize(data, 'power', 'True');
        this.leds['led_power'].actualize(data, 'power', 'True');
        this.leds['led_air_fun'].actualize(data, 'air_fun', 'True');
        this.leds['led_fuel_pump'].actualize(data, 'fuel_pump', 'True');
        this.leds['led_ignition'].actualize(data, 'ignition', 'True');
        this.leds['led_water_pump'].actualize(data, 'water_pump', 'True');
        this.leds['led_flame'].actualize(data, 'flame', 'True');
        this.leds['led_heater'].actualize(data, 'heater', 'True');
        this.leds['led_no_pressure'].actualize(data, 'no_pressure', 'True');
        this.leds['led_overheat'].actualize(data, 'overheat', 'True');

        this.actualizeSevenSeg('ss_target_t', data, 'target_t');
        this.actualizeSevenSeg('ss_room_t', data, 'room_t');
        this.actualizeSevenSeg('ss_boiler_box_t', data, 'boiler_box_t');
        this.actualizeSevenSeg('ss_boiler_t', data, 'boiler_t');
        this.actualizeSevenSeg('ss_return_t', data, 'return_t');
        this.actualizeSevenSeg('ss_ignition_counter', data, 'ignition_counter');
        this.actualizeSevenSeg('ss_fuel_consumption', data, 'fuel_consumption');
        this.actualizeSevenSeg('ss_fuel_consumption_month', data, 'fuel_consumption_month');
        this.actualizeSevenSeg('ss_fuel_consumption_year', data, 'fuel_consumption_year');
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
                                      [['t', 't°', 2, 30, 'lime']]);
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




