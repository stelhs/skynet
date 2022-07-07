
class LoginBox {
    constructor(ui, resultCb) {
        this.ui = ui;
        this.resultCb = resultCb
    }

    html() {
        var tpl = this.ui.teamplates.openTpl('login_box');
        tpl.assign();
        return tpl.result();
    }

    show() {
        this.loginInput = $$("login_input");
        this.passwordInput = $$("password_input");
    }

    onEnter() {
        var login = this.loginInput.value
        var password = this.passwordInput.value
        this.ui.hideDialogBox();
        this.resultCb(login, password);
    }
}