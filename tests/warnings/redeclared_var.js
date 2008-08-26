/*jsl:option explicit*/
/*conf:-unreferenced_identifier*/
function redeclared_var() {
    var duplicate;
    var duplicate; /*warning:redeclared_var*/

    function myFunction() {
        return;
    }
    var myFunction; /*warning:redeclared_var*/
}
