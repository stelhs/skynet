
class Power extends ModuleBase {
    constructor(ui) {
        super(ui, 'power');
        this.pagesNumber = 2;
        this.confPowerSockets = ui.configs['powerSockets'];
        this.confLighters = ui.configs['lighters'];
        this.confDoorlocks = ui.configs['doorlocks'];

        this.ledsPowerSockets = {};
        this.ledsLighters = {};
        this.ledsDoorlocks = {};
        this.ledsGates = {};
        this.ledsWaterSupply = {};

        this.ledsUps = {};
        this.textBars = {};
    }

    title() {
        return 'Питание';
    }

    description() {
        return 'Управление питанием';
    }

    eventSources() {
        return ['door_locks', 'power_sockets', 'lighters', 'gates', 'water_supply', 'ups'];
    }

    setContentPagePrimary(content) {
        this.setPageContent(1, content)
    }

    setContentUPS(content) {
        this.setPageContent(2, content)
    }

    init() {
        super.init();
        var tpl = this.tplOpen('mod_power_1')
        for (var name in this.confPowerSockets) {
            var inf = this.confPowerSockets[name];
            tpl.assign('power_zone',
                       {'name': name,
                        'description': inf['description']})
        }

        for (var name in this.confLighters['lighters']) {
            var inf = this.confLighters['lighters'][name];
            tpl.assign('lighter',
                       {'name': name,
                        'description': inf['description']})
        }

        for (var name in this.confDoorlocks) {
            var inf = this.confDoorlocks[name];
            tpl.assign('doorlock',
                       {'name': name,
                        'description': inf['description']})
        }

        this.setContentPagePrimary(tpl.result());

        var tpl = this.tplOpen('mod_power_2')
        tpl.assign()
        this.setContentUPS(tpl.result());


        for (var name in this.confPowerSockets)
            this.ledsPowerSockets[name] = new Led('led_power_zone_' + name, 'green', 3);

        for (var name in this.confLighters['lighters'])
            this.ledsLighters[name] = new Led('led_lighter_' + name, 'red', 3);
        this.ledsLighters['automatic'] = new Led('led_auto_lighter_enabled', 'green', 3, 'mini');

        for (var name in this.confDoorlocks)
            this.ledsDoorlocks[name] = new Led('led_doorlock_' + name, 'green', 3);

        this.ledsGates['gatesClosed'] = new Led('led_gates_closed', 'green', 3);
        this.ledsGates['gatesPower'] = new Led('led_gates_power', 'green', 3);

        this.ledsWaterSupply['waterPumpEnabled'] = new Led('led_water_pump_enabled', 'red', 3);
        this.ledsWaterSupply['watersupplyAutomaticEnabled'] = new Led('led_watersupply_automatic_enabled', 'green', 3, 'mini');
        this.ledsWaterSupply['watersupplyLowPressure'] = new Led('led_watersupply_low_pressure', 'red', 3);
        this.ledsWaterSupply['watersupplyPumpIsLocked'] = new Led('led_watersupply_pump_is_locked', 'red', 3, 'mini');

        this.ledsUps['ledPowerExtExist'] = new Led('led_power2_ext', 'green', 3);
        this.ledsUps['ledPowerInUps'] = new Led('led_power2_ups_in', 'green', 3);
        this.ledsUps['ledPowerOutUpsIsAbsent'] = new Led('led_power_no_output_power', 'red', 3);
        this.ledsUps['ledPower14vdcUpsAbsent'] = new Led('led_power_no_14vdc', 'red', 3);
        this.ledsUps['ledAutomaticCharhing'] = new Led('led_charger_automatic_enabled', 'green', 3, 'mini');
        this.ledsUps['ledCharging'] = new Led('led_charger_status_activated', 'green', 3);
        this.ledsUps['ledChargerEnPort'] = new Led('led_charger_power_enabled', 'green', 3);
        this.ledsUps['ledHighCurrent'] = new Led('led_charger_current_max_enabled', 'green', 3);
        this.ledsUps['ledMiddleCurrent'] = new Led('led_charger_current_middle_enabled', 'green', 3);
        this.ledsUps['ledChargeDischarge'] = new Led('led_charge_discharge', 'red', 3);
        this.ledsUps['ledBatteryRelayPort'] = new Led('led_main_relay_enabled', 'red', 3);
        this.ledsUps['ledUpsBreakPowerPort'] = new Led('led_power_ups_disabled', 'red', 3);
        this.ledsUps['ledDischarging'] = new Led('led_discharge_status_activated', 'red', 3);

        this.textBars['upsState'] = new StatusBar('power2_ups_state', 3);
        this.textBars['battVoltage'] = new StatusBar('battery_voltage', 3);
        this.textBars['chargeCurrent'] = new StatusBar('charger_current', 3);

        this.textBars['chargingReason'] = new StatusBar('charger_status_reason_started', 3);
        this.textBars['chargerStartTime'] = new StatusBar('charger_status_start_time', 3);
        this.textBars['chargerStopTime'] = new StatusBar('charger_status_end_time', 3);
        this.textBars['chargeStartVoltage'] = new StatusBar('charger_status_start_voltage', 3);
        this.textBars['chargeDuration_stage1'] = new StatusBar('charger_status_max_current_duration', 3);
        this.textBars['chargeDuration_stage2'] = new StatusBar('charger_status_middle_current_duration', 3);
        this.textBars['chargeDuration_stage3'] = new StatusBar('charger_status_min_current_duration', 3);
        this.textBars['chargeTotalDuration'] = new StatusBar('charger_status_duration', 3);
        this.textBars['dischargeReason'] = new StatusBar('discharge_status_reason_started', 3);
        this.textBars['dischargeStartTime'] = new StatusBar('discharge_status_start_time', 3);
        this.textBars['dischargeStopTime'] = new StatusBar('discharge_status_end_time', 3);
        this.textBars['dischargeStartVoltage'] = new StatusBar('discharge_status_start_voltage', 3);
        this.textBars['dischargeStopVoltage'] = new StatusBar('discharge_status_finished_voltage', 3);
        this.textBars['dischargeDuration'] = new StatusBar('discharge_status_duration', 3);
    }

    eventHandler(source, type, data) {
        switch (source) {
        case 'door_locks':
            if (type == 'statusUpdate')
                return this.updateDoorLooksStatus(data);

        case 'power_sockets':
            if (type == 'statusUpdate')
                return this.updatePowerSocketsStatus(data);

        case 'lighters':
            if (type == 'statusUpdate')
                return this.updateLightersStatus(data);

        case 'gates':
            if (type == 'statusUpdate')
                return this.updateGatesStatus(data);

        case 'water_supply':
            if (type == 'statusUpdate')
                return this.updateWaterSupplyStatus(data);

        case 'ups':
            if (type == 'statusUpdate')
                return this.updateUpsStatus(data);
        }

        switch (type) {
        case 'error':
            this.logErr(data)
            return

        case 'info':
            this.logInfo(data)
            return

        default:
            this.logErr("Incorrect event type: " + type)
        }
    }

    logErr(msg) {
        this.ui.logErr("Guard: " + msg)
    }

    logInfo(msg) {
        this.ui.logInfo("Guard: " + msg)
    }

    updateDoorLooksStatus(data) {
        for (var name in this.ledsDoorlocks) {
            var led = this.ledsDoorlocks[name]
            if (name in data)
                led.light(data[name])
        }
    }

    updatePowerSocketsStatus(data) {
        for (var name in this.ledsPowerSockets) {
            var led = this.ledsPowerSockets[name]
            if (name in data)
                led.light(data[name])
        }
    }

    updateLightersStatus(data) {
        for (var name in this.ledsLighters) {
            var led = this.ledsLighters[name]
            if (name in data)
                led.light(data[name])
        }
    }

    updateGatesStatus(data) {
        for (var name in this.ledsGates) {
            var led = this.ledsGates[name]
            if (name in data)
                led.light(data[name])
        }
    }

    updateWaterSupplyStatus(data) {
        for (var name in this.ledsWaterSupply) {
            var led = this.ledsWaterSupply[name]
            if (name in data)
                led.light(data[name])
        }
    }

    updateUpsStatus(data) {
        for (var name in this.ledsUps) {
            var led = this.ledsUps[name]
            if (name in data)
                led.light(data[name])
        }

        for (var name in this.textBars) {
            var led = this.textBars[name]
            if (name in data)
                led.set(data[name])
        }
    }

    requestToPowerSocketOn(name) {
        this.logInfo('Request to turn on power socket ' + name);
        this.skynetGetRequest('power_sockets/on', {'name': name});
    }

    requestToPowerSocketOff(name) {
        this.logInfo('Request to turn off power socket ' + name);
        this.skynetGetRequest('power_sockets/off', {'name': name});
    }

    requestToLighterOn(name) {
        this.logInfo('Request to turn on lighter ' + name);
        this.skynetGetRequest('lighters/on', {'name': name});
    }

    requestToLighterOff(name) {
        this.logInfo('Request to turn off lighter ' + name);
        this.skynetGetRequest('lighters/off', {'name': name});
    }

    requestToSwitchLightersAutomatic() {
        this.logInfo('Request to switch lighter automatics');
        this.skynetGetRequest('lighters/switch_automatic_control');
    }

    requestToDoorLocksOn(name) {
        this.logInfo('Request to turn on door lock ' + name);
        this.skynetGetRequest('doorlooks/on', {'name': name});
    }

    requestToDoorLocksOff(name) {
        this.logInfo('Request to turn off door lock ' + name);
        this.skynetGetRequest('doorlooks/off', {'name': name});
    }

    requestToGatesOpen() {
        this.logInfo('Request to gates open');
        this.skynetGetRequest('gates/open');
    }

    requestToGatesOpenPedestrian() {
        this.logInfo('Request to gates open for pedestrian');
        this.skynetGetRequest('gates/open_pedestrian');
    }

    requestToGatesClose() {
        this.logInfo('Request to gates close');
        this.skynetGetRequest('gates/close');
    }

    requestToWaterPumpOn() {
        this.logInfo('Request to water pump on');
        this.skynetGetRequest('water_supply/pump_on');
    }

    requestToWaterPumpOff() {
        this.logInfo('Request to water pump off');
        this.skynetGetRequest('water_supply/pump_off');
    }

    requestToSwitchWaterSupplyAutomatic() {
        this.logInfo('Request to switch water supply automatic control');
        this.skynetGetRequest('water_supply/switch_automatic_control');
    }

    requestToSwitchWaterSupplyBlocking() {
        this.logInfo('Request to switch blocking water pump');
        this.skynetGetRequest('water_supply/switch_lock_unlock');
    }

    requestToStartCharger() {
        this.logInfo('Request to start charger');
        this.skynetGetRequest('ups/start_charger');
    }

    requestToStopCharger() {
        this.logInfo('Request to stop charger');
        this.skynetGetRequest('ups/stop_charger');
    }

    requestToSwitchAutomatic() {
        this.logInfo('Request to switch automatic charging');
        this.skynetGetRequest('ups/switch_automatic');
    }

    requestToEnableHwCharger() {
        this.logInfo('Request to enable hardware charger');
        this.skynetGetRequest('ups/charger_hw_on');
    }

    requestToDisableHwCharger() {
        this.logInfo('Request to disable hardware charger');
        this.skynetGetRequest('ups/charger_hw_off');
    }

    requestToTurnOnHighCurrent() {
        this.logInfo('Request to turn on high current');
        this.skynetGetRequest('ups/high_current_on');
    }

    requestToTurnOffHighCurrent() {
        this.logInfo('Request to turn off high current');
        this.skynetGetRequest('ups/high_current_off');
    }

    requestToTurnOnMiddleCurrent() {
        this.logInfo('Request to turn on middle current');
        this.skynetGetRequest('ups/middle_current_on');
    }

    requestToTurnOffMiddleCurrent() {
        this.logInfo('Request to turn off middle current');
        this.skynetGetRequest('ups/middle_current_off');
    }

    requestToSwitchToCharge() {
        this.logInfo('Request to switch to charge mode');
        this.skynetGetRequest('ups/switch_to_charge');
    }

    requestToSwitchToDischarge() {
        this.logInfo('Request to switch to discharge mode');
        this.skynetGetRequest('ups/switch_to_discharge');
    }

    requestToBatteryRelayOn() {
        this.logInfo('Request to turn on battery relay');
        this.skynetGetRequest('ups/battery_relay_on');
    }

    requestToBatteryRelayOff() {
        this.logInfo('Request to turn off battery relay');
        this.skynetGetRequest('ups/battery_relay_off');
    }

    requestToInputPowerOff() {
        this.logInfo('Request to turn off input power');
        this.skynetGetRequest('ups/input_power_off');
    }

    requestToInputPowerOn() {
        this.logInfo('Request to turn on input power');
        this.skynetGetRequest('ups/input_power_on');
    }


}






