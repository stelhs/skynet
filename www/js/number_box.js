
class NumberBox {
    constructor(ui, resultCb, header, inputs) {
        // inputs = [name, header, min, max]
        this.ui = ui;
        this.resultCb = resultCb
        this.header = header;
        this.inputs = inputs;
        this.digits = {};
        this.dispDiv = {};
        this.dispFrameDiv = {};
        this.selectedInput = "";
    }

    html() {
        var tpl = this.ui.teamplates.openTpl('number_box');
        tpl.assign(NaN, {'header': this.header});
        for (var i in this.inputs) {
            var input = this.inputs[i];
            var name = input[0];
            var header = input[1];
            tpl.assign('display',
                       {'name': name,
                        'header': header});
        }
        return tpl.result();
    }

    show() {
        for (var i in this.inputs) {
            var input = this.inputs[i];
            var name = input[0];
            this.dispDiv[name] = $("#ss_number_win_" + name);
            this.dispFrameDiv[name] = $$('number_win_disp_frame_' + name);
            this.digits[name] = [];
        }
        this.selectedInput = this.inputs[0][0];
        this.dispFrameDiv[this.selectedInput].style.border = 'solid 2px lime';

        for (var i in this.inputs) {
            var input = this.inputs[i];
            var name = input[0];
            this.erase(name);
        }
    }

    onSelectInput(name) {
        this.selectedInput = name;
        this.updateDisplays();

        for (var i in this.inputs) {
            var input = this.inputs[i];
            var name = input[0];
            if (name == this.selectedInput)
                this.dispFrameDiv[name].style.border = 'solid 2px lime';
            else
                this.dispFrameDiv[name].style.border = 'solid 2px #557799';
        }
    }

    onClickDigit(digit) {
        this.digits[this.selectedInput].push(digit);

        if (this.digits[this.selectedInput].length > 4)
            this.digits[this.selectedInput].shift();
        console.log(this.digits);
        this.updateDisplays();
    }

    value(name) {
        if (!this.digits[name].length)
            return 0.0;

        var str = "";
        for (var i in this.digits[name]) {
            var digit = this.digits[name][i];
            str += digit;
        }

        return parseFloat(str);
    }

    onEnter() {
        var result = {};
        for (var i in this.inputs) {
            var input = this.inputs[i];
            var name = input[0];
            var header = input[1];
            var div = this.dispDiv[name];
            var min = input[2];
            var max = input[3];
            var color = input[4];

            var val = this.value(name);
            if (val < min) {
                this.ui.logErr("Error: Entered value of " + header + ": " + val + " less then " + min);
                this.erase(name);
                return;
            }

            if (val > max) {
                this.ui.logErr("Error: Entered value of " + header + ": " + val + " more then " + max);
                this.erase(name);
                return;
            }
            result[name] = val;
        }

        this.ui.hideDialogBox();
        this.resultCb(result);
    }

    updateDisplays() {
        for (var i in this.inputs) {
            var input = this.inputs[i];
            var name = input[0];
            var header = input[1];
            var div = this.dispDiv[name];
            var min = input[2];
            var max = input[3];
            var color = input[4];

            var str = "";
            for (var i in this.digits[name]) {
                var digit = this.digits[name][i];
                str += digit;
            }

            console.log(color);
            div.sevenSegArray({
                value: str,
                digits: 4,
                segmentOptions: {
                    colorOff: "#003500",
                    colorOn: color,
                    slant: 10
                }
            });
        }
    }

    erase(name) {
        this.digits[name] = [];
        this.updateDisplays();
    }

    eraseSelected() {
        this.erase(this.selectedInput);
    }


}