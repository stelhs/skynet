
function $$(id)
{
    return document.getElementById(id);
}

function asyncAjaxReq(httpMethod, method, data = {}, successCb = NaN, errCb = NaN)
{
    var error = function(jqXHR, exception) {
        var reason = '';
        var errCode = 0;
        if (jqXHR.status === 0) {
            reason = 'Not connect.\n Verify Network.';
            errCode = 1;
        } else if (jqXHR.status == 404) {
            reason = 'Requested page not found. [404]';
            errCode = 404;
        } else if (jqXHR.status == 500) {
            reason = 'Internal Server Error [500].';
            errCode = 500;
        } else if (exception === 'parsererror') {
            reason = 'Requested JSON parse failed.';
            errCode = 2;
        } else if (exception === 'timeout') {
            reason = 'Time out error.';
            errCode = 3;
        } else if (exception === 'abort') {
            reason = 'Ajax request aborted.';
            errCode = 4;
        } else {
            reason = 'Uncaught Error.\n' + jqXHR.responseText;
            errCode = 5;
        }

        errCb(reason, errCode)
    }

    return $.ajax({
          type: httpMethod,
          url: "/" + method,
          data: data,
          success: successCb,
          error: error,
          async: true,
          timeout: 70000,
              }).responseText;
}


function syncAjaxReq(method, args = {})
{
    return $.ajax({
          type: "GET",
          url: "/" + method,
          data: args,
          async: false
              }).responseText;
}

class Teamplates {
    constructor() {
        this.tplList = NaN;
        var d = syncAjaxReq('ui/get_teamplates');
        eval('this.tplList = ' + d);
        this.defMarks = {'img_dir': '/img/'};
    }

    byName(name) {
        if (name in this.tplList)
            return this.tplList[name];
        return NaN;
    }

    openTpl(name) {
        var tpl = new StrontiumTpl(this.defMarks);
        var c = this.byName(name);
        if (!c)
            return NaN;
        tpl.openTpl(c);
        return tpl;
    }
}


class Ui {
    constructor(modules) {
        this.teamplates = new Teamplates();
        this.logBox = new LogBox(this.teamplates);
        this.obtainConfigs();

        this.boiler = new Boiler(this)
        this.io = new Io(this)
        this.guard = new Guard(this)
        this.power = new Power(this)
        this.modules = [this.power, this.boiler, this.io, this.guard];
//        this.modules = [this.boiler];

//        this.noSleep = new NoSleep('no_sleep_video');
        this.errorBoxDiv = $$('errorBox');
        this.dialogBoxDiv = $$('dialogBox');
        this.dialogBox = NaN;
        this.hidingPageDiv = $$('hidingPage');
        this.isErrBoxDisplayed = false

        this.leds = [];
        this.sevenSegs = [];
        this.statusBars = [];
        this.labelBars = [];
        this.switches = [];
//        this.noSleep.run();
        this.register();
        this.eventReceiver();

        var menuTpl = this.teamplates.openTpl('menu')
        var modulesTpl = this.teamplates.openTpl('modules')
        for (var i in this.modules) {
            var mod = this.modules[i];

            modulesTpl.assign('module',
                              {'name': mod.name(),
                               'description': mod.description()});

            if (mod.pagesNumber > 1)
                modulesTpl.assign('page_selector', {'name': mod.name()});

            for (var n = 1; n <= mod.pagesNumber; n++) {
                modulesTpl.assign('page',
                                   {'name': mod.name(),
                                    'pageNum': n})
            }

            menuTpl.assign('menu_item',
                       {'name': mod.name(),
                        'title': mod.title()});
        }
        $$('menu_panel').innerHTML = menuTpl.result();
        $$('modules').innerHTML = modulesTpl.result();

        this.ledsAct = [];
        for (var i in this.modules) {
            var mod = this.modules[i];
            mod.init()
            let led = this.ledRegister('ledActivity_'+mod.name(), 'red');
            led.setLostSignalStyle('off')
            led.setActualizeTimeoutMsec(100);
            this.ledsAct[mod.name()] = led;
        }

        this.switchModule('power');
    }

    register(login=NaN, password=NaN) {
        var args = {}
        if (login && password)
            args = {'login': login,
                    'password': password}
        var c = syncAjaxReq('ui/subscribe', args);
        var resp = JSON.parse(c)
        this.subscriberId = resp.subscriber_id;
    }

    obtainConfigs() {
        var c = syncAjaxReq('ui/configs');
        this.configs = JSON.parse(c)
    }

    moduleByName(name) {
        for (var mod of this.modules) {
            if (mod.name() == name)
                return mod;
        }
        return NaN;
    }

    eventHandler(source, type, data) {
        switch (type) {
        case 'ledsUpdate':
            this.ledsUpdateState(data);
            break;

        case 'sevenSegsUpdate':
            this.sevenSegsUpdateState(data);
            break;

        case 'statusBarsUpdate':
            this.statusBarsUpdateState(data);
            break;

        case 'labelsBarsUpdate':
            this.labelBarsUpdateState(data);
            break;

        case 'switchesUpdate':
            this.switchesUpdateState(data);
            break;

        case 'error':
            this.logErr(source + ': ' + data)
            return

        case 'info':
            this.logInfo(source + ': ' + data)
            return
        }

        for (var mod of this.modules) {
            if (mod.eventSources().includes(source)) {
                mod.eventHandler(source, type, data);
            }
        }
    }

    eventReceiver() {
        var success = function(responceText) {
            this.errorBoxHide();
            var resp = JSON.parse(responceText)
            if (resp.status == 'error') {
                if (resp.errCode == 'subscriberNotRegistred') {
                    this.register();
                    this.eventReceiver();
                    return;
                }

                if (resp.errCode == 'subscriberAbsent') {
                    this.loginDialog();
                    return;
                }

                this.errorBoxShow('Ошибка',
                                  'Ошибка сервера ' + resp.errCode + ': status: ' + resp.status + '<br>' +
                                  'Причина: ' + resp.reason.replace('\n', '<br>'));
                var retry = function () {
                    this.eventReceiver();
                }
                setTimeout(retry.bind(this), 3000);
                return;
            }

            var events = resp.events;
            if (events.length) {
                for (var i in events) {
                    event = events[i];
                    this.eventHandler(event.source,
                                 event.type,
                                 event.data);
                }
            }

            this.eventReceiver();
        }

        var error = function(reason, errCode) {
            this.errorBoxShow('Гавнище', 'Ошибшка связи с сервером: ' + reason);
            var retry = function () {
                this.eventReceiver();
            }
            setTimeout(retry.bind(this), 3000);
        }

        asyncAjaxReq('GET', 'ui/get_events',
                     {'subscriber_id': this.subscriberId},
                      success.bind(this), error.bind(this))
    }

    switchModule(name) {
//        this.noSleep.run()
        for (var i in this.modules) {
            var mod = this.modules[i];
            var menuDiv = $$('menu_item_' + mod.name());
            var moduleDiv = $$('module_' + mod.name());
            menuDiv.className = 'menu_item';
            moduleDiv.style.display = 'none';
            if (mod.name() != name)
                continue;
            menuDiv.className = 'menu_item_active';
            moduleDiv.style.display = 'block';
            mod.update();
        }
    }

    errorBoxShow(header, msg, timeout = 0) {
        this.isErrBoxDisplayed = true
        var tpl = this.teamplates.openTpl('message_box');
        tpl.assign(NaN, {'header': header,
                         'msg': msg});
        this.errorBoxDiv.innerHTML = tpl.result();
        this.errorBoxDiv.style.display = 'block';
        this.hidingPageDiv.style.display = 'block';
        if (!timeout)
            return;

        var autohide = function () {
            this.errorBoxHide();
        }
        setTimeout(autohide.bind(this), timeout);
    }

    errorBoxHide() {
        if (!this.isErrBoxDisplayed)
            return;
        console.log("call errorBoxHide")
        this.errorBoxDiv.style.display = 'none';
        this.hidingPageDiv.style.display = 'none';
        this.isErrBoxDisplayed = false
    }

    logErr(msg) {
        this.logBox.insert('err', msg);
        this.logBox.redraw();
    }

    logInfo(msg) {
        this.logBox.insert('info', msg);
        this.logBox.redraw();
    }

    showDialogBox(box) {
        this.dialogBoxDiv.innerHTML = box.html();
        this.dialogBoxDiv.style.display = 'block';
        this.hidingPageDiv.style.display = 'block';
        this.dialogBox = box;
        box.show()
    }

    hideDialogBox() {
        this.dialogBoxDiv.style.display = 'none';
        this.hidingPageDiv.style.display = 'none';
        this.dialogBox = NaN;
        this.dialogBoxDiv.innerHTML = "";
    }

    setPageContent(modName, pageNum, content) {
        var page = $$('module_' + modName + '_page_' + pageNum + '_content');
        page.innerHTML = content
    }


    pinCodeDialog() {
        var cb = function(results) {
            var success = function(responceText) {
                var resp = JSON.parse(responceText)
                if (resp.status == 'error') {
                    this.logErr("send PIN code error: " + resp.reason)
                    return;
                }
                this.logInfo("PIN code success")
            }

            var error = function(reason, errCode) {
                this.logErr('Can`t send PIN code: ' + reason)
            }

            var pin = results['pin'];
            asyncAjaxReq('GET', 'ui/pin_code',
                         {'pin': pin},
                          success.bind(this), error.bind(this))
        }

        var numberBox = new NumberBox(this, cb.bind(this),
                                      'PIN код',
                                      [['pin', '', 0, 9999, 'lime', true]]);
        this.showDialogBox(numberBox)
    }

    logout() {
        var success = function(responceText) {
            var resp = JSON.parse(responceText)
            if (resp.status == 'error') {
                this.logErr("Logout error: " + resp.reason)
                return;
            }
            $.cookie("auth", null, { path: '/' });
            this.logInfo("Logout success")
        }

        var error = function(reason, errCode) {
            this.logErr('Logout error: ' + reason)
        }

        asyncAjaxReq('GET', 'ui/logout', {'subscriber_id': this.subscriberId},
                      success.bind(this), error.bind(this))
    }

    loginDialog() {
        var cb = function(login, password) {
            this.register(login, password)
            this.eventReceiver();
        }

        var loginBox = new LoginBox(this, cb.bind(this));
        this.showDialogBox(loginBox)
    }

    ledRegister(name, color, type='big', timeout='default') {
        let led = new Led(this, name, color, type);
        if (timeout != 'default')
            led.setActualizeTimeoutMsec()
        this.leds[name] = led;
        return led;
    }

    ledByName(name) {
        return this.leds[name];
    }

    ledsUpdateState(listStates) {
        for (var name in listStates) {
            var led = this.ledByName(name);
            if (!led) {
                console.log("Led "+name+" is not registred")
                return;
            }
            var state = listStates[name]
            led.light(state)
        }
    }

    sevenSegRegister(name, color, digits=3) {
        let sevenSeg = new SevenSeg(this, name, color, digits);
        this.sevenSegs[name] = sevenSeg;
    }

    sevenSegByName(name) {
        return this.sevenSegs[name];
    }

    sevenSegsUpdateState(listStates) {
        for (var name in listStates) {
            var ss = this.sevenSegByName(name);
            if (!ss) {
                console.log("SevenSeg "+name+" is not registred");
                return;
            }
            var state = listStates[name]
            ss.set(state)
        }
    }

    statusBarRegister(name) {
        let sb = new StatusBar(this, name);
        this.statusBars[name] = sb;
    }

    statusBarByName(name) {
        return this.statusBars[name];
    }

    statusBarsUpdateState(listStates) {
        for (var name in listStates) {
            var sb = this.statusBarByName(name);
            if (!sb) {
                console.log("StatusBar "+name+" is not registred");
                return;
            }
            var state = listStates[name]
            sb.set(state)
        }
    }

    labelBarRegister(name) {
        let lb = new LabelBar(this, name);
        this.labelBars[name] = lb;
    }

    labelBarByName(name) {
        return this.labelBars[name];
    }

    labelBarsUpdateState(listStates) {
        for (var name in listStates) {
            var lb = this.labelBarByName(name);
            if (!lb) {
                console.log("LabelBar "+name+" is not registred");
                return;
            }
            var state = listStates[name];
            lb.set(state);
        }
    }

    switchRegister(name) {
        let sw = new Switch(this, name);
        this.switches[name] = sw;
    }

    switchByName(name) {
        return this.switches[name];
    }

    switchesUpdateState(listStates) {
        for (var name in listStates) {
            var sw = this.switchByName(name);
            if (!sw) {
                console.log("Switch "+name+" is not registred");
                return;
            }
            var state = listStates[name];
            sw.set(state);
        }
    }
}


class LogBox {
    constructor(teamplates) {
        this.teamplates = teamplates
        this.logs = [];
        this.div = $$('log_box');
    }

    insert(type, message) {
        var now = new Date();
        this.logs.unshift([now, type, message]);
        if (this.logs.length > 30)
            this.logs.pop();
    }

    redraw() {
        var tpl = this.teamplates.openTpl('log_box')

        for (var i in this.logs) {
            var row = this.logs[i];
            var date = row[0];
            var type = row[1];
            var msg = row[2];

            var t = {'day': date.getDate().pad(),
                     'month': (date.getMonth() + 1).pad(),
                     'hour': date.getHours().pad(),
                     'min': date.getMinutes().pad(),
                     'sec': date.getSeconds().pad()};

            tpl.assign('row', t);
            if (type == 'err')
                tpl.assign('row_error', {'message': msg});
            else
                tpl.assign('row_info', {'message': msg});
        }

        this.div.innerHTML = tpl.result();
    }
}

class ModuleBase {
    constructor(ui, name) {
        this.ui = ui;
        this._name = name;
        this.pagesNumber = 1;
        this.currentPage = 1;
        this.pages = {};
        this.pagesNav = NaN;
    }

    init() {
        for (var i = 1; i <= this.pagesNumber; i++)
            this.pages[i] = $$('module_' + this.name() + '_page_' + i + '_block');
        if (this.pagesNumber > 1)
            this.pagesNav = $$('module_' + this.name() + '_page_selector');
    }

    name() {
        return this._name;
    }

    eventSources() {
        return [];
    }

    switchNextPage() {
        if (this.currentPage >= this.pagesNumber)
            return;
        this.currentPage ++;
        this.update()
        this.onPageChanged(this.currentPage);
    }

    switchPrevPage() {
        if (this.currentPage <= 1)
            return;
        this.currentPage --;
        this.update()
        this.onPageChanged(this.currentPage);
    }

    update() {
        for (var i = 1; i <= this.pagesNumber; i++) {
            var div = this.pages[i];
            if (i == this.currentPage)
                div.style.display = 'block';
            else
                div.style.display = 'none';
        }

        if (this.pagesNav)
            this.pagesNav.innerHTML = "(" + this.currentPage + " / " + this.pagesNumber + ")"
        this.onPageChanged()
    }

    tplOpen(tplName) {
        return this.ui.teamplates.openTpl(tplName);
    }

    setPageContent(pageNum, content) {
        this.ui.setPageContent(this.name(), pageNum, content)
    }

    onPageChanged(pageNum) {
    }

    skynetGetRequest(method, args) {
        var success = function(responceText) {
            var resp = JSON.parse(responceText)

            if (resp.status == 'error') {
                this.logErr("skynet GET method '" + method + "'" +
                               "return error: " + resp.reason)
                return;
            }
            this.logInfo("to skynet GET '" + method + "' success finished")
        }

        var error = function(reason, errCode) {
            this.logErr('Can`t send GET request "' + method + '" to skynet: ' + reason)
        }
        asyncAjaxReq('GET', method, args,
                     success.bind(this), error.bind(this))
    }

    skynetPostRequest(method, data) {
        var success = function(responceText) {
            var resp = JSON.parse(responceText)

            if (resp.status != 'ok') {
                this.logErr("skynet POST method '" + method + "'" +
                               "return error: " + resp.reason)
                return;
            }
            this.logInfo("to skynet POST '" + method + "' success finished")
        }

        var error = function(reason, errCode) {
            this.logErr('Can`t send POST request "' + method + '" to skynet: ' + reason)
        }
        asyncAjaxReq('POST', method, data,
                     success.bind(this), error.bind(this))
    }

    ledAct() {
        this.ui.ledsAct[this.name()].set('on');
    }
}

class Led {
    constructor(ui, divName, color, size="big") {
        this.divName = divName;
        this.div = $$(divName);

        this.color = color
        this.size = size
        this.ui = ui

        this.actualizeTimeout = ui.configs['ui']['updateTimeout']

        this.wrkId = NaN;
        this.lostState = 'undefined'
        this.set(this.lostState);
    }

    setLostSignalStyle(style) {
        this.lostState = style
    }

    setActualizeTimeoutMsec(intervalMsec) {
        this.actualizeTimeout = intervalMsec
    }

    set(mode) {
        var style
        switch (mode) {
        case 'on':
            style = this.color;
            break;
        case 'off':
            style = 'off';
            break;
        case 'undefined':
            style = 'undefined';
            break;
        }

        this.div.className = 'led_' + this.size + '-' + style;

        if (this.actualizeTimeout && style != 'undefined') {
            if (this.wrkId) {
                clearTimeout(this.wrkId)
                this.wrkId = NaN;
            }

            var cb = function() {
                this.set(this.lostState)
                this.wrkId = NaN;
            }
            this.wrkId = setTimeout(cb.bind(this), this.actualizeTimeout)
        }
    }

    light(mode) {
        if (mode)
            this.set('on');
        else
            this.set('off');
    }

/*    actualize(data, field, value) {
        if (field in data) {
            if (data[field] == value)
                this.set('on');
            else
                this.set('off');
        }
    }*/
}

class SevenSeg {
    constructor(ui, divName, color, digits=3) {
        this.divName = divName;
        this.div = $("#" + divName);
        this.color = color
        this.digits = digits
        this.actualizeTimeout = ui.configs['ui']['updateTimeout'];
        this.wrkId = NaN;
        this.set('');
    }

    set(val) {
        this.div.sevenSegArray({
            value: val.toString(),
            digits: this.digits,
            segmentOptions: {
                colorOff: "#002700",
                colorOn: this.color,
                slant: 10
            }
        });

        if (this.actualizeTimeout && val != '') {
            if (this.wrkId) {
                clearTimeout(this.wrkId)
                this.wrkId = NaN;
            }

            var cb = function() {
                this.set('')
                this.wrkId = NaN;
            }
            this.wrkId = setTimeout(cb.bind(this), this.actualizeTimeout)
        }
    }
}

class StatusBar {
    constructor(ui, divName) {
        this.divName = divName;
        this.div = $$(divName);
        this.actualizeTimeout = ui.configs['ui']['updateTimeout'];
        this.wrkId = NaN;
        this.set('---');
    }

    set(val) {
        this.div.innerHTML = val;

        if (this.actualizeTimeout && val != '---') {
            if (this.wrkId) {
                clearTimeout(this.wrkId)
                this.wrkId = NaN;
            }

            var cb = function() {
                this.set('---')
                this.wrkId = NaN;
            }
            this.wrkId = setTimeout(cb.bind(this), this.actualizeTimeout)
        }
    }
}

class LabelBar {
    constructor(ui, divName) {
        this.divName = divName;
        this.div = $$(divName);
        this.actualizeTimeout = ui.configs['ui']['updateTimeout'];
        this.wrkId = NaN;
        this.set('');
    }

    set(val) {
        this.div.innerHTML = val;
        this.show();

        if (this.actualizeTimeout && val != '') {
            if (this.wrkId) {
                clearTimeout(this.wrkId)
                this.wrkId = NaN;
            }

            var cb = function() {
                this.set('')
                this.wrkId = NaN;
                this.hide();
            }
            this.wrkId = setTimeout(cb.bind(this), this.actualizeTimeout)
        }
    }

    show() {
        this.div.style.display = "block";
    }

    hide() {
        this.div.style.display = "none";
    }
}

class Switch {
    constructor(ui, divName) {
        this.divName = divName;
        this.div = $$(divName);
        this.set(false);
    }

    set(val) {
        this.div.checked = val;
    }

    state() {
        return this.div.checked;
    }
}


function init() {
    Number.prototype.pad = function(size) {
        var s = String(this);
        while (s.length < (size || 2)) {s = "0" + s;}
        return s;
    }

    ui = new Ui();
}

