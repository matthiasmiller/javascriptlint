/*jsl:option explicit*/
function inc_dec_within_stmt() {
    var i, s;

    /* legal */
    i++;
    i--;
    ++i;
    --i;
    for (i = 0; i < 10; i++) {
        s = i;
    }
    for (i = 10; i > 0; i--) {
        s = i;
    }
    for(i = 0; i < 5; i++, i--) {
        i++;
    }
    for(i = 0; i < 5; ) {
        i++;
    }

    for (i = 0; i < 5; i = ++i) { /*warning:inc_dec_within_stmt*/
        /*jsl:pass*/
    }

    /* illegal */
    switch (i--) /*warning:inc_dec_within_stmt*/ 
    {
    default:
        break;
    }

    /* illegal */
    s = new String(i++); /*warning:inc_dec_within_stmt*/

    /* illegal */
    s = --i; /*warning:inc_dec_within_stmt*/
}
