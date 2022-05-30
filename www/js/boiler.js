
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

    init() {
        super.init();
        this.boilerStateDiv = $$('bolier_state');
        this.fuelConsumptionTableDiv = $$('boiler_fuel_consumption_table');

        this.leds = {'led_power': $$('led_power'),
                     'led_air_fun': $$('led_air_fun'),
                     'led_fuel_pump': $$('led_fuel_pump'),
                     'led_ignition': $$('led_ignition'),
                     'led_water_pump': $$('led_water_pump'),
                     'led_flame': $$('led_flame'),
                     'led_heater': $$('led_heater'),
                     'led_no_pressure': $$('led_no_pressure'),
                     'led_overheat': $$('led_overheat')};

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


    html(pageNum) {
        var tpl = this.ui.teamplates.openTpl('mod_' + this.name() + '_' + pageNum);
        tpl.assign();
        return tpl.result();
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

        for (var ledName in this.leds)
            this.ledSet(ledName, 'undefined');

        for (var name in this.sevenSegs)
            this.showSevenSegVal(name, "XXXXX");

        this.fuelConsumptionTableDiv.innerHTML = '';
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

    ledByName(name) {
        for (var itemName in this.leds) {
            if (itemName == name)
                return this.leds[itemName];
        }
        return NaN;
    }

    ledSet(ledName, mode) {
        var led = this.ledByName(ledName);
        led.className = 'led_big-' + mode;
    }

    eventHandler(type, data) {
        switch (type) {
        case 'status':
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

    actualizeLed(ledName, data, field, value, ledTrueMode) {
        if (field in data) {
            if (data[field] == value)
                this.ledSet(ledName, ledTrueMode);
            else
                this.ledSet(ledName, 'off');
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

        this.actualizeLed('led_power', data, 'power', 'True', 'green');
        this.actualizeLed('led_air_fun', data, 'air_fun', 'True', 'green');
        this.actualizeLed('led_fuel_pump', data, 'fuel_pump', 'True', 'green');
        this.actualizeLed('led_ignition', data, 'ignition', 'True', 'red');
        this.actualizeLed('led_water_pump', data, 'water_pump', 'True', 'green');
        this.actualizeLed('led_flame', data, 'flame', 'True', 'red');
        this.actualizeLed('led_heater', data, 'heater', 'True', 'red');
        this.actualizeLed('led_no_pressure', data, 'no_pressure', 'True', 'red');
        this.actualizeLed('led_overheat', data, 'overheat', 'True', 'red');

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
                this.logErr("boiler method '" + method + "'" +
                               "return error: " + resp.reason)
                return;
            }
            this.logInfo("to boiler '" + method + "' success finished")
        }

        var error = function(reason, errCode) {
            this.logErr('Can`t send request "' + method + '" to boiler: ' + reason)
        }
        asyncAjaxReq('boiler/' + method, args,
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

    boilerEnableHeater() {
        this.ui.logInfo('Request to enable heater');
        this.boilerRequest('heater_enable')
    }

    boilerDisableHeater() {
        this.ui.logInfo('Request to disable heater');
        this.boilerRequest('heater_disable')
    }

    updateBoilerFuelConsumption(data) {
        var div = this.fuelConsumptionTableDiv
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

        var tpl = this.ui.teamplates.openTpl('boiler_consumption');

        if (!data.length) {
            tpl.assign('no_data');
            div.innerHTML = tpl.result();
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
        div.innerHTML = tpl.result();
    }

    requestBoilerFuelConsumption() {
        this.logInfo('Request to sr90 to obtain fuel consumption report')
        this.sr90Request('boiler/request_fuel_compsumption_stat')
    }
}




