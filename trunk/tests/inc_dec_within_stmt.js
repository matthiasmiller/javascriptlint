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
    for(i = 0; i < 5; ) {
      i++;
    }

    /* illegal */
    switch (i--) 
    {
    default:
        break;
    } /*warning:inc_dec_within_stmt*/

    /* illegal */
    s = new String(i++); /*warning:inc_dec_within_stmt*/

    /* illegal */
    s = --i; /*warning:inc_dec_within_stmt*/
}
