/*jsl:option explicit*/
/*conf:-unreferenced_identifier*/
function trailing_decimal_point() {
    var i;

    /* trailing decimal point; should have zero or no decimal*/
    i = 12.0.floor(); /*warning:trailing_decimal_point*/
}
