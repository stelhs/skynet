
class Power extends ModuleBase {
    constructor(ui) {
        super(ui, 'power');
        this.pagesNumber = 2;
        this.confPowerSockets = ui.configs['powerSockets'];
        this.confLighters = ui.configs['lighters'];
        this.confDoorlocks = ui.configs['doorlocks'];
        this.confUi = ui.configs['ui'];
    }

    title() {
        return 'Питание';
    }

    description() {
        return 'Управление питанием';
    }

    eventSources() {
        return ['water_supply', 'lighters', 'gates', 'door_looks', 'power_sockets'];
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
            this.ui.ledRegister('ledPowerZone_' + name, 'green');

        for (var name in this.confLighters['lighters'])
            this.ui.ledRegister('ledLighter_' + name, 'red');
        this.ui.ledRegister('ledLighter_automatic', 'green', 'mini');

        for (var name in this.confDoorlocks)
            this.ui.ledRegister('ledDoorlock_' + name, 'green');

        this.ui.ledRegister('ledGatesNotClosed', 'red');
        this.ui.ledRegister('ledGatesNoPower', 'red');
        this.ui.ledRegister('ledWaterPumpEnabled', 'red');
        this.ui.ledRegister('ledWatersupplyAutomaticEnabled', 'green', 'mini');
        this.ui.ledRegister('ledWatersupplyLowPressure', 'red');
        this.ui.ledRegister('ledWatersupplyPumpIsLocked', 'red', 'mini');
        this.ui.ledRegister('ledPowerExtExist', 'green');
        this.ui.ledRegister('ledPowerInUps', 'green');
        this.ui.ledRegister('ledPowerOutUpsIsAbsent', 'red');
        this.ui.ledRegister('ledPower14vdcUpsAbsent', 'red');
        this.ui.ledRegister('ledAutomaticCharhing', 'green', 'mini');
        this.ui.ledRegister('ledCharging', 'green');
        this.ui.ledRegister('ledChargerEnPort', 'green');
        this.ui.ledRegister('ledHighCurrent', 'green');
        this.ui.ledRegister('ledMiddleCurrent', 'green');
        this.ui.ledRegister('ledChargeDischarge', 'red');
        this.ui.ledRegister('ledBatteryRelayPort', 'red');
        this.ui.ledRegister('ledUpsBreakPowerPort', 'red');
        this.ui.ledRegister('ledDischarging', 'red');

        this.ui.statusBarRegister('sbUpsState');
        this.ui.statusBarRegister('sbBattVoltage');
        this.ui.statusBarRegister('sbChargeCurrent');
        this.ui.statusBarRegister('sbChargingReason');
        this.ui.statusBarRegister('sbChargerStartTime');
        this.ui.statusBarRegister('sbChargerStopTime');
        this.ui.statusBarRegister('sbChargeStartVoltage');
        this.ui.statusBarRegister('sbChargeDuration_stage1');
        this.ui.statusBarRegister('sbChargeDuration_stage2');
        this.ui.statusBarRegister('sbChargeDuration_stage3');
        this.ui.statusBarRegister('sbChargeTotalDuration');
        this.ui.statusBarRegister('sbDischargeReason');
        this.ui.statusBarRegister('sbDischargeStartTime');
        this.ui.statusBarRegister('sbDischargeStopTime');
        this.ui.statusBarRegister('sbDischargeStartVoltage');
        this.ui.statusBarRegister('sbDischargeStopVoltage');
        this.ui.statusBarRegister('sbDischargeDuration');
    }

    eventHandler(source, type, data) {
        this.ledAct();
    }

    logErr(msg) {
        this.ui.logErr("Guard: " + msg)
    }

    logInfo(msg) {
        this.ui.logInfo("Guard: " + msg)
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

    requestToGatesPowerOn() {
        this.logInfo('Request to gates power on');
        this.skynetGetRequest('gates/power_on');
    }

    requestToGatesPowerOff() {
        this.logInfo('Request to gates power off');
        this.skynetGetRequest('gates/power_off');
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

    requestToSetZeroChargerCurrent() {
        this.logInfo('Request to set zero charger current');
        this.skynetGetRequest('ups/set_zero_charger_current');
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






