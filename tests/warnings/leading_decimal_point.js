/*jsl:option explicit*/
/*conf:-unreferenced_identifier*/
function leading_decimal_point() {
    var i;

    /* leading decimal point; should have zero */
    i = .12; /*warning:leading_decimal_point*/
}
