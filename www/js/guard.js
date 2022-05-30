
class Guard extends ModuleBase {
    constructor(ui) {
        super(ui, 'guard');
        this.pagesNumber = 1;
    }

    title() {
        return 'Охрана';
    }

    description() {
        return 'Панель управления системой охраны';
    }

    init() {
        super.init();
    }

    eventHandler(type, data) {
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
        this.ui.logErr("IO: " + msg)
    }


    logInfo(msg) {
        this.ui.logInfo("IO: " + msg)
    }

    onPageChanged(pageNum) {
    }


}