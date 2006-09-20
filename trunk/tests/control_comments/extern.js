/*jsl:option explicit*/
function extern() {
    window.alert('http://www.javascriptlint.com/');
    /*jsl:extern window*/

    /* redeclaration only at local scope */
    var window;/*warning:redeclared_var*/
    var document;
    /*jsl:extern document*//*warning:redeclared_var*/
}

var i = 10
/*jsl:extern sample*//*warning:missing_semicolon*/

/* extern was scoped */
window.alert('JavaScript Lint');/*warning:undeclared_identifier*/

document.write('<a href="http://www.javascriptlint.com/">JavaScript Lint</a>');

/*jsl:extern document*/
function document()/*warning:redeclared_var*/
{
}

/*jsl:extern*//*warning:jsl_cc_not_understood*/
/*jsl:extern variable?*//*warning:jsl_cc_not_understood*/
