
class Guard extends ModuleBase {
    constructor(ui) {
        super(ui, 'guard');
        this.pagesNumber = 1;
        this.confGuard = ui.configs['guard'];
        this.confPowerSockets = ui.configs['powerSockets'];
        this.confDoorLocks = ui.configs['doorLocks'];
        this.sensorLeds = {};
        this.readyZoneLeds = {};
        this.blockedZoneLeds = {};
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

    init() {
        super.init();
        var tpl = this.tplOpen('mod_guard_1')
        for (var zName in this.confGuard['zones']) {
            var zInfo = this.confGuard['zones'][zName];
            tpl.assign('zone', {'name': zName,
                                'description': zInfo['desc']})

            for (var sName in zInfo['io_sensors'])
                tpl.assign('sensor', {'sensor_name': sName})
        }

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

        for (var zName in this.confGuard['zones']) {
            var zInfo = this.confGuard['zones'][zName];
            var led = new Led('led_zone_' + zName + '_ready', 'red', 3);
            this.readyZoneLeds[zName] = led;

            led = new Led('led_zone_' + zName + '_blocked', 'green', 3, 'mini');
            this.blockedZoneLeds[zName] = led;

            for (var sName in zInfo['io_sensors']) {
                var led = new Led('led_sensor_' + sName + '_state', 'red', 3);
                this.sensorLeds[sName] = led;
            }
        }

        for (var name in this.confPowerSockets)
            this.startGuardPowerSocketSwitches[name] = $$('guard_starting_power_zone_' + name);

        for (var name in this.confDoorLocks) {
            this.startGuardDoorLocksSwitches[name] = $$('guard_starting_doorlock_power_' + name);
            this.stopGuardDoorLocksSwitches[name] = $$('guard_stopping_doorlock_power_' + name);
        }

        this.guardStartedLed = new Led('led_guard_state', 'green', 3);
        this.notReadyZonesLed = new Led('led_not_watched_zones', 'red', 3);
        this.blockedZonesLed = new Led('led_blocked_zones', 'red', 3);
        this.allZonesReadyLed = new Led('led_all_zones_ready', 'red', 3);
        this.publicAudioLed = new Led('led_public_audio', 'red', 3);


        this.enabledAlarmSoundSwitch = $$('guard_alarm_sound_enabled');
        this.enabledSMSSwitch = $$('guard_alarm_sms_enabled');
        this.enabledSkynetGroupNotifySwitch = $$('guard_alarm_skynet_enabled');
        this.waterSupplySwitch = $$('guard_starting_water_supply');

        this.openGatesSwitch = $$('guard_stopping_open_gates');
        this.stopDvrSwitch = $$('guard_stopping_stop_dvr');

        this.requestToObtainGuardSettings();
    }

    eventHandler(source, type, data) {
        switch (type) {
        case 'statusUpdate':
            return this.updateStatus(data)

        case 'guardSettings':
            return this.updateGuardSettings(data)

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

    updateStatus(data) {
        if ('sensorsLeds' in data) {
            for (var sName in data['sensorsLeds']) {
                var mode = data['sensorsLeds'][sName];
                this.sensorLeds[sName].light(mode);
            }
        }

        if ('readyZoneLeds' in data) {
            for (var zName in data['readyZoneLeds']) {
                var mode = data['readyZoneLeds'][zName];
                this.readyZoneLeds[zName].light(mode);
            }
        }

        if ('blockedZoneLeds' in data) {
            for (var zName in data['blockedZoneLeds']) {
                var mode = data['blockedZoneLeds'][zName];
                this.blockedZoneLeds[zName].light(mode);
            }
        }

        if ('notAllReady' in data) {
            this.notReadyZonesLed.light(data['notAllReady'])
            this.allZonesReadyLed.light(!data['notAllReady'])
        }

        if ('isStarted' in data)
            this.guardStartedLed.light(data['isStarted'])

        if ('blockedZonesExisted' in data)
            this.blockedZonesLed.light(data['blockedZonesExisted'])

        if ('publicSound' in data)
            this.publicAudioLed.light(data['publicSound'])
    }

    updateGuardSettings(data) {
        var startSettings = data['startSettings'];
        var stopSettings = data['stopSettings'];

        for (name in startSettings['powerSockets']) {
            var val = Boolean(startSettings['powerSockets'][name]);
            this.startGuardPowerSocketSwitches[name].checked = val;
        }

        for (name in startSettings['doorLocks']) {
            var val = Boolean(startSettings['doorLocks'][name]);
            this.startGuardDoorLocksSwitches[name].checked = val;
        }

        this.enabledAlarmSoundSwitch.checked = Boolean(startSettings['enabledAlarmSound']);
        this.enabledSMSSwitch.checked = Boolean(startSettings['enabledSMS']);
        this.enabledSkynetGroupNotifySwitch.checked = Boolean(startSettings['enabledSkynetGroupNotify']);
        this.waterSupplySwitch.selected = Boolean(startSettings['waterSupply']);
        //this.watchModeSwitch.selected =

        for (name in stopSettings['doorLocks']) {
            var val = Boolean(stopSettings['doorLocks'][name]);
            this.stopGuardDoorLocksSwitches[name].checked = val;
        }

        this.openGatesSwitch.checked = Boolean(stopSettings['openGates']);
        this.stopDvrSwitch.checked = Boolean(stopSettings['stopDvr']);
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

    requestToObtainGuardSettings() {
        this.logInfo('Request to obtaining guard settings');
        this.skynetGetRequest('guard/obtain_settings');
    }

    requestToStartGuard() {
        var data = {};
        data['enabledAlarmSound'] = this.enabledAlarmSoundSwitch.checked;
        data['enabledSMS'] = this.enabledSMSSwitch.checked;
        data['enabledSkynetGroupNotify'] = this.enabledSkynetGroupNotifySwitch.checked;

        //data['watchMode'] =
        data['waterSupply'] = this.waterSupplySwitch.selected;

        data['powerSockets'] = {};
        for (var name in this.confPowerSockets)
            data['powerSockets'][name] = this.startGuardPowerSocketSwitches[name].checked;

        data['doorLocks'] = {};
        for (var name in this.confDoorLocks)
            data['doorLocks'][name] = this.startGuardDoorLocksSwitches[name].checked;

        this.logInfo('Post guard start settings and starting');
        this.skynetPostRequest('guard/start_with_settings', JSON.stringify(data));
    }

    requestToStopGuard() {
        var data = {};

        data['openGates'] = this.openGatesSwitch.checked;
        data['stopDvr'] = this.stopDvrSwitch.checked;

        data['doorLocks'] = {};
        for (var name in this.confDoorLocks)
            data['doorLocks'][name] = this.startGuardDoorLocksSwitches[name].checked;

        this.logInfo('Post guard stop settings and stopping');
        this.skynetPostRequest('guard/stop_with_settings', JSON.stringify(data));
    }

}

