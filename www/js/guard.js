
class Guard extends ModuleBase {
    constructor(ui) {
        super(ui, 'guard');
        this.pagesNumber = 2;
        this.confGuard = ui.configs['guard'];
        this.confPowerSockets = ui.configs['powerSockets'];
        this.confDoorLocks = ui.configs['doorLocks'];
        this.sensorLeds = {};
        this.startGuardPowerSocketSwitches = {};
        this.startGuardDoorLocksSwitches = {};
        this.stopGuardDoorLocksSwitches = {};
    }

    title() {
        return 'Охрана';
    }

    description() {
        return 'Панель управления системой охраны';
    }

    eventSources() {
        return ['guard'];
    }

    setContentPagePrimary(content) {
        this.setPageContent(1, content)
    }

    setContentZoneList(content) {
        this.setPageContent(2, content)
    }

    init() {
        super.init();
        var tpl = this.tplOpen('mod_guard_1')
        for (var name in this.confPowerSockets) {
            var inf = this.confPowerSockets[name];
            tpl.assign('guard_starting_power_zone',
                       {'name': name,
                        'description': inf['description']})
        }

        for (var name in this.confDoorLocks) {
            var inf = this.confDoorLocks[name];
            var data = {'name': name, 'description': inf['description']};
            tpl.assign('guard_starting_doorlock_power', data);
            tpl.assign('guard_stopping_doorlock_power', data);
        }
        this.setContentPagePrimary(tpl.result());

        tpl = this.tplOpen('mod_guard_2')
        let cnt = 0
        for (let zName in this.confGuard['zones']) {
            let zInfo = this.confGuard['zones'][zName];
            if (cnt % 2 == 0)
                tpl.assign('row')
            cnt ++;

            tpl.assign('zone', {'name': zName,
                                'description': zInfo['desc']})

            for (var sName in zInfo['io_sensors'])
                tpl.assign('sensor', {'sensor_name': sName})
        }

        this.setContentZoneList(tpl.result());

        for (var zName in this.confGuard['zones']) {
            var zInfo = this.confGuard['zones'][zName];
            this.ui.ledRegister('ledGuardZoneReady_' + zName, 'green');
            this.ui.ledRegister('ledGuardZoneBlocked_' + zName, 'red', 'mini');
            for (var sName in zInfo['io_sensors']) {
                this.ui.ledRegister('ledGuardSensorState_' + sName, 'green');
                this.ui.ledRegister('ledGuardSensorBlocked_' + sName, 'green', 'mini');
            }
        }

        for (var name in this.confPowerSockets)
            this.ui.switchRegister('swGuardStartingPowerZone_' + name);

        for (var name in this.confDoorLocks) {
            this.ui.switchRegister('swGuardStartingDoorlockPower_' + name);
            this.ui.switchRegister('swGuardStoppingDoorlockPower_' + name);
        }

        this.ui.ledRegister('ledGuardState', 'green');
        this.ui.ledRegister('ledGuardNotWatchedZones', 'red');
        this.ui.ledRegister('ledGuardBlockedZones', 'red');
        this.ui.ledRegister('ledGuardAllZonesReady', 'green');
        this.ui.ledRegister('ledGuardPublicAudio', 'red');

        this.ui.switchRegister('swGuardStartingNoWatchWorkshop');
        this.ui.switchRegister('swGuardAlarmSoundEnabled');
        this.ui.switchRegister('swGuardAlarmSmsEnabled');
        this.ui.switchRegister('swGuardAlarmSkynetEnabled');
        this.ui.switchRegister('swGuardStartingWaterSupply');
        this.ui.switchRegister('swGuardStoppingOpenGates');
        this.ui.switchRegister('swGuardStoppingStopDvr');

        this.requestToObtainGuardSettings();
    }

    eventHandler(source, type, data) {
        this.ledAct();
    }

    onPageChanged(pageNum) {
        this.requestToObtainGuardSettings();
    }


    logErr(msg) {
        this.ui.logErr("Guard: " + msg)
    }

    logInfo(msg) {
        this.ui.logInfo("Guard: " + msg)
    }

    requestZoneLockUnlock(zoneName) {
        this.logInfo('Request to switch lock/unlock zone ' + zoneName);
        this.skynetGetRequest('guard/zone_lock_unlock', {'zone_name': zoneName});
    }

    requestSensorLockUnlock(sName) {
        this.logInfo('Request to switch lock/unlock sensor ' + sName);
        this.skynetGetRequest('guard/sensor_lock_unlock', {'sensor_name': sName});
    }

    requestToObtainGuardSettings() {
        this.logInfo('Request to obtaining guard settings');
        this.skynetGetRequest('guard/obtain_settings');
    }

    startSettings() {
        var data = {};
        data['swGuardStartingNoWatchWorkshop'] = this.ui.switchByName('swGuardStartingNoWatchWorkshop').state()
        data['swGuardAlarmSoundEnabled'] = this.ui.switchByName('swGuardAlarmSoundEnabled').state()
        data['swGuardAlarmSmsEnabled'] = this.ui.switchByName('swGuardAlarmSmsEnabled').state()
        data['swGuardAlarmSkynetEnabled'] = this.ui.switchByName('swGuardAlarmSkynetEnabled').state()
        data['swGuardStartingWaterSupply'] = this.ui.switchByName('swGuardStartingWaterSupply').state()

        for (var name in this.confPowerSockets)
            data['swGuardStartingPowerZone_' + name] = this.ui.switchByName('swGuardStartingPowerZone_' + name).state()

        for (var name in this.confDoorLocks)
            data['swGuardStartingDoorlockPower_' + name] = this.ui.switchByName('swGuardStartingDoorlockPower_' + name).state()

        return data;
    }

    stopSettings() {
        var data = {};
        data['swGuardStoppingOpenGates'] = this.ui.switchByName('swGuardStoppingOpenGates').state()
        data['swGuardStoppingStopDvr'] = this.ui.switchByName('swGuardStoppingStopDvr').state()

        for (var name in this.confDoorLocks)
            data['swGuardStoppingDoorlockPower_' + name] = this.ui.switchByName('swGuardStoppingDoorlockPower_' + name).state()

        return data;
    }

    requestToStartGuard() {
        let data = this.startSettings();
        this.logInfo('Post guard start settings and starting');
        this.skynetPostRequest('guard/start_with_settings', JSON.stringify(data));
    }

    requestToStopGuard() {
        let data = this.stopSettings();
        this.logInfo('Post guard stop settings and stopping');
        this.skynetPostRequest('guard/stop_with_settings', JSON.stringify(data));
    }

    requestToSaveStartSettings() {
        let data = this.startSettings();
        this.logInfo('Save guard start settings');
        this.skynetPostRequest('guard/save_start_settings', JSON.stringify(data));
    }

    requestToSaveStopSettings() {
        let data = this.stopSettings();
        this.logInfo('Save guard stop settings');
        this.skynetPostRequest('guard/save_stop_settings', JSON.stringify(data));
    }

    requestToCancelPublicSound() {
        this.logInfo('Request to public sound cancellation');
        this.skynetGetRequest('guard/stop_public_sound');
    }

}

