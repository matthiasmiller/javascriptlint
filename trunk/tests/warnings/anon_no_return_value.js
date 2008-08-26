/*jsl:option explicit*/
/*conf:-unreferenced_identifier*/
function anon_no_return_value() {
    var error1 = function(b) {
        if (b)
            return true;
        else
            return; /*warning:anon_no_return_value*/
    };

    var error2 = function(b) {
        if (b) {
            return;
        }
        else {
            return ""; /*warning:anon_no_return_value*/
        }
    };


    var correct = function(b) {
        if (b)
            return;
        else
            return;
    };
}
