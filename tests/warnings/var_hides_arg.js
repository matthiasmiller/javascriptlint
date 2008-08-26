/*jsl:option explicit*/
/*conf:-unreferenced_identifier*/
function var_hides_arg(duplicate1, duplicate2) {
    var duplicate1; /*warning:var_hides_arg*/
    function inner() {
        var duplicate2; /*warning:var_hides_arg*/
    }
}
