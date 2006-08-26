/*jsl:option explicit*/
function comparison_type_conv() {
    var a, b, c;

    /* wrong - comparison against null */
    if (a == null || b < c) { /*warning:comparison_type_conv*/
        a = b;
    }
    /* ok - comparison against null */
    if (a === null || b < c) {
        a = b;
    }

    /* wrong - comparison against zero */
    if (c > a && a + b == 0) { /*warning:comparison_type_conv*/
        c = -c;
    }
    /* ok - comparison against zero */
    if (c > a && a + b === 0) {
        c = -c;
    }

    /* wrong - comparison against blank string */
    if (a == "") { /*warning:comparison_type_conv*/
        b = c;
    }
    /* ok - comparison against blank string */
    if (a === "") {
        b = c;
    }
}
