
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

        for (var i in this.modules) {
            var mod = this.modules[i];
            mod.init()
        }

        this.switchModule('power');
    }

    register() {
        var c = syncAjaxReq('ui/subscribe');
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

                this.errorBoxShow('Ошибка',
                                  'Ошибка сервера: status: ' + resp.status + '<br>' +
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

}

class Led {
    constructor(divName, color, actualizeTimeoutSec=0, size="big") {
        this.divName = divName;
        this.div = $$(divName);
        this.color = color
        this.size = size
        this.actualizeTimeout = actualizeTimeoutSec
        this.wrkId = NaN;
        this.set('undefined');
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
                this.set('undefined')
                this.wrkId = NaN;
            }
            this.wrkId = setTimeout(cb.bind(this), this.actualizeTimeout * 1000)
        }
    }

    light(mode) {
        if (mode)
            this.set('on');
        else
            this.set('off');
    }

    actualize(data, field, value) {
        if (field in data) {
            if (data[field] == value)
                this.set('on');
            else
                this.set('off');
        }
    }
}

class SevenSeg {
    constructor(divName, color, digits=3, actualizeTimeoutSec=0) {
        this.divName = divName;
        this.div = $("#" + divName);
        this.color = color
        this.digits = digits
        this.actualizeTimeout = actualizeTimeoutSec
        this.wrkId = NaN;
        this.set('');
    }

    set(val) {
        this.div.sevenSegArray({
            value: val,
            digits: this.digits,
            segmentOptions: {
                colorOff: "#003500",
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
            this.wrkId = setTimeout(cb.bind(this), this.actualizeTimeout * 1000)
        }
    }
}

class StatusBar {
    constructor(divName, actualizeTimeoutSec=0) {
        this.divName = divName;
        this.div = $$(divName);
        this.actualizeTimeout = actualizeTimeoutSec
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
            this.wrkId = setTimeout(cb.bind(this), this.actualizeTimeout * 1000)
        }
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

