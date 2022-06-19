

class Led() {
    constructor(divName, size="big") {
        this.div = $$(divName);
        this.size = size
    }

    set(mode) {
        this.div.className = 'led_' + this.size + '-' + mode;
    }

    actualize(data, field, value, ledTrueMode) {
        if (field in data) {
            if (data[field] == value)
                this.set(ledTrueMode);
            else
                this.ledSet(ledName, 'off');
        }
    }
}