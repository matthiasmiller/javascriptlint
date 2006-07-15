/*jsl:option explicit*/

function SpiderMonkey() {
    function duplicate_formal(duplicate, duplicate) {
        return;
    }

    function equal_as_assign() {
        var a, b;
        while (a = b) {
            a++;
        }
    }

    function var_hides_arg(duplicate) {
        var duplicate;
    }

    function invalid_backref() {
        /* illegal - \0 is not a valid regex backreference */
        var re = /\0/;
    }

    function bad_backref() {
        /* illegal - one 1 backreference */
        var re = /(.)\2/;
    }

    function redeclared_var() {
        var duplicate;
        var duplicate;

        function myFunction() {
            return;
        }
        var myFunction;
    }

    function deprecated_usage() {
        var o = {};

        /* illegal - with is deprecated */
        with (o) {
            this.x = this.y;
        }

        with (o) {
            /* should not warn about undeclared identifier */
            some_variable = another_variable;
            if (o) {
                second_value = first_variable;
            }
        }

        /* illegal - getter/setter is deprecated */
        Array.bogon getter = function () {
            return "";
        };
        Array.bogon setter = function (o) {
            this.push(o);
        };
    }

    function trailing_comma() {
        /* illegal - trailing comma */
        return { name: 'value', };
    }
}

var g;
function option_explicit(parm) {
    /* legal - j is declared */
    g = j;
    var j;

    var s;

    /* legal - function referencing parameter in parent */
    var fn = function() { return parm; };

    /* legal - function referening variable in parent */
    var fn2 = function() { return s; };

    /* legal - defined below */
    var o = new Child();

    /* legal - function referencing variable in grandparent */
    function Child() {
        function Grandchild() {
            if (parm) {
                return s;
            }
            return null;
        }
    }

    /* legal - catch variable */
    try {
        throw null;
    }
    catch (err) {
        return err;
    }

    /* legal - recursion */
    option_explicit(parm);

    /* legal - this is a property, not a variable */
    this.q = -1;

    /* legal - global */
    g++;

    /* legal - ignore undeclared identifier */
    /*jsl:ignore*/
    g = undefined_var;
    /*jsl:end*/

    /* illegal - undeclared global */
    z--;

    /* illegal - undeclared global */
    y();

    /* illegal */
    x = 14;

    /* illegal */
    y();

    return "";
}





function no_return_value() {
    function error1(b) {
        if (b)
            return true;
        else
            return;
    }
    
    function error2(b) {
        if (b) {
            return;
        }
        else {
            return "";
        }
    }
    
    function correct(b) {
        if (b)
            return;
        else
            return;
    }
}

function anon_no_return_value() {
    var error1 = function(b) {
        if (b)
            return true;
        else
            return;
    };

    var error2 = function(b) {
        if (b) {
            return;
        }
        else {
            return "";
        }
    };


    var correct = function(b) {
        if (b)
            return;
        else
            return;
    };
}

function invalid_fallthru() {
    /* mistake - invalid use of fallthru */
    /*jsl:fallthru*/
	var i;
    switch (i) {
      /*jsl:fallthru*/
      case /*jsl:fallthru*/1:
        break;
      default /*jsl:fallthru*/:
		break;    
    }
}

function missing_semicolon() {
	/* missing semicolon after return */
    function MissingSemicolonOnReturnStatement() {
        return 0
    }

	/* missing semicolon after return */
	/* missing semicolon after lambda */
	function x() {
		this.y = function() { return 0 }
	}

	/* missing semicolon after return */
	/* missing semicolon after lambda */
	x.prototype.z = function() {
		return 1
	}
}

function meaningless_block() {
    var i;

    /* meaningless block */
    {
        var s;
        s = i + "%";
    }

    return s;
}

function comma_separated_stmts() {
    var b, i, j;

    /* comma (legit) */
    for (i = 0, j = 0; i < 10; i += 2, j += 4) {
        b = ((i + j) / 2 == i - j);
    }

    /* comma (unclear) */
    for (i = 0; i < 10, j > 20; i++) {
        j = i;
    }

    /* comma (unclear) */
    b = false, i = 0, j = 0;
}

function unreachable_code() {
    var i;
    i = 0;

    /* unreachable because of break */
    while (i < 100) {
        break;
        i += 1;
    }

    /* unreachable because of continue */
    while (i > 100) {
        continue;
        i += 1;
    }

    /* unreachable because of return */
    if (i + i < 0) {
        return;
        i = -i;
    }

    /* unreachable because of throw */
    if (i == 14) {
        throw i;
        i -= 1;
    }
}

function missing_break() {
    var i, o, s;

    switch (i) {
      /* okay because of return */
      default:
        return "";
    }

    switch (i) {
      /* okay because of throw */
      default:
        throw s;
    }

    switch (i) {
      case 1:
        s += ".";
        /*missing break*/

      case 2:
        /*okay because of return*/
        s += ",";
        return s;

      case 3:
        /*okay because of throw*/
        s += ";";
        throw s;

      case 4:
        /*okay because of break/throw*/
        if (s) {
            break;
        }
        else {
            throw i;
        }

      case 5:
        /*missing break in catch*/
        try {
            i--;
            break;
        }
        catch (err) {
            s = null;
        }
        finally {
            i++;
        }

      case 6:
        /*ok; finally statement never called*/
        try {
            i--;
            break;
        }
        catch (err) {
            s = null;
            break;
        }
        finally {
            i++;
        }

      case 7:
        /*ok; break statement in catch and finally*/
        try {
            i--;
        }
        catch (err) {
            s = null;
            break;
        }
        finally {
            i++;
            break;
        }

      default:
        break;
    }

    return "";
}

function missing_break_for_last_case(i) {
    switch (i) {
      default:
        /*missing break at end of switch (without code)*/
    }

	/*missing break at end of switch (with code)*/
	switch (i) {
	  default:
	     i++;
	}

	/*ok because of fallthru*/
	switch (i) {
	  default:
	     /*jsl:fallthru*/
	}
}

function comparison_type_conv() {
    var a, b, c;

    /* wrong - comparison against null */
    if (a == null || b < c) {
        a = b;
    }
    /* ok - comparison against null */
    if (a === null || b < c) {
        a = b;
    }

    /* wrong - comparison against zero */
    if (c > a && a + b == 0) {
        c = -c;
    }
    /* ok - comparison against zero */
    if (c > a && a + b === 0) {
        c = -c;
    }

    /* wrong - comparison against blank string */
    if (a == "") {
        b = c;
    }
    /* ok - comparison against blank string */
    if (a === "") {
        b = c;
    }
}

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
    }

    /* illegal */
    s = new String(i++);

    /* illegal */
    s = --i;
}

function useless_void() {
    var z;
    /* check use of void */
    z = void 0;
    z();
}

function multiple_plus_minus() {
    var i, j;
    i = 0;
    j = 0;

    /* disallow confusing +/- */
    i+++j;
    j---i;
}

function use_of_label() {
    var o;

    /* label disallowed */
    MyWhile:
    while (true) {
        /* label disallowed */
        MyFor:
        for (var x in o) {
            if (x) {
                break MyWhile;
            }
            else {
                continue MyWhile;
            }
        }
    }
}

function block_without_braces() {
    var i;
    if (i)
        i++;

    do i--;
    while (i);

    for (i = 0; i < 10; i++)
        i *= 2;
}

function leading_decimal_point() {
    var i;

    /* leading decimal point; should have zero */
    i = .12;
}

function trailing_decimal_point() {
    var i;

    /* trailing decimal point; should have zero or no decimal*/
    i = 12.0.floor();
}

function octal_number() {
    var i;
    i = 010;
}

function nested_comment() {
    /* nested comment */
    /* /* */
    return "";
}

function misplaced_regex() {
    var i, re;

    /* legal usage: regex in assignment */
    re = /\/\./;

    /* legal usage: regex in object definition */
    var o = { test : /\/\./ };

    /* legal usage: regex as first parameter */
    new String().replace(/\/\./, "<smile>");

    /* legal usage: regex as parameter (besides first) */
    misplaced_regex(re, /\/\./);

    /* illegal usage: anything else */
    i += /\/\./;
    i = -/.*/;
}

function ambiguous_newline() {
    /* the EOL test is based on JSLint's documentation */
    var a, b, i, o, s;

    /* legal: , */
    s = s.substr(0,
        1);

    /* legal: . */
    s = s.
        substr(0, 1);

    /* legal: ; */
    s = s.substr(0, 1);

    /* legal: : */
    o = { test :
        'works' };

    /* legal: { */
    /* legal: } */
    if (s) {
        s = i;
    }

    /* legal: ( */
    s = s.substr(
        0, 1);

    /* legal: [ */
    s = o[
        'test'];

    /* legal: = */
    s =
        '?';

    /* legal: < */
    b = (i <
        14);

    /* legal: > */
    b = (i >
        93);

    /* legal: ? */
    i = (b ?
        1 : 0);

    /* legal: ! */
    b = (!
        false);

    /* legal: + */
    i = 55 +
        i;

    /* legal: - */
    i = 101 -
        i;

    /* legal: * */
    i = i *
        2;

    /* legal: / */
    i = i /
        43;

    /* legal: % */
    i = i %
        16;

    /* legal: ~ */
    i = ~
        16;

    /* legal: ^ */
    i = i ^
        32;

    /* legal: | */
    i = i |
        64;

    /* legal: & */
    i = i &
        2;

    /* legal: == */
    b = (i ==
        99);

    /* legal: != */
    b = (i !=
        -1);

    /* legal: <= */
    b = (i <=
        4);

    /* legal: >= */
    b = (i >=
        3.14);

    /* legal: += */
    i +=
        1;

    /* legal: -= */
    i -=
        1;

    /* legal: *= */
    i *=
        19;

    /* legal: /= */
    i /=
        17;

    /* legal: %= */
    i %=
        15;

    /* legal: ^= */
    i ^=
        1024;

    /* legal: |= */
    i ^=
        512;

    /* legal: &= */
    i ^=
        256;

    /* legal: << */
    i = i <<
        2;

    /* legal: >> */
    i = i >>
        1;

    /* legal: || */
    b = (b ||
        false);

    /* legal: && */
    b = (b &&
        true);

    /* legal: === */
    b = (i ===
        0);

    /* legal: !== */
    b = (i !==
        0);

    /* legal: <<= */
    i <<=
        1;

    /* legal: >>= */
    i >>=
        2;

    /* legal: >>> */
    i = i >>>
        4;

    /* legal: >>>= */
    i >>>=
        2;

    /* legal */
    o =
    {
        'component one': 1,
        'component two': 2
    };

    /* legal */
    o = {
        'one': 1,
        'two': 2
    };

    /* legal */
    i = o['one'
        ];

    /* illegal */
    i = o
        ['one'];

    /* illegal: identifier */
    s = i
        + "?";

    /* illegal: string */
    s = "this "
        + i;

    /* illegal: number */
    i = 14
        / 2;

    /* illegal: ) */
    b = (i == 7)
        || false;

    /* illegal: ) */
    s = o['test']
        + "!";

    /* illegal: ++ */
    b = i++
        || true;

    /* illegal: -- */
    s = i--
        + " = i";

    /* legal */
    if (true)
    {
        i++;
    }
    else
    {
        i--;
    }
    while (false)
    {
        i--;
    }
    switch (1)
    {
    default:
        break;
    }
    for (i = 0; i < 1; i++)
    {
        s = i + "";
    }
    function Test()
    {
        return "";
    }
    try
    {
        s = null;
    }
    catch (err)
    {
    }
}

function empty_statement() {
    var i;
    i = 0;

    /* empty statement within while; useless expression */
    while (false);
    while (false) {}

    /* empty block within for; useless expression */
    for (i = 0; i < 2; i += 1) {
    }

    /* legal: empty catch statement */
    try {
        i++;
    }
    catch (err) {
    }
}

function missing_option_explicit() {
    /* nothing to see here; move along */
    return null;
}

function partial_option_explicit() {
    /* nothing to see here; move along */
    return null;
}

function dup_option_explicit() {
    /*@option explicit@*/
    return null;
}

function useless_assign() {
    var i, o;

    /* illegal */
    var s = s;

    /* illegal */
    o = o;

    /* illegal */
    for (i = i; ; ) {
        i++;
    }
    /* illegal */
    for (; i = i; ) {
        i++;
    }
    /* illegal */
    for (; ; i = i) {
        i++;
    }
}

function ambiguous_nested_stmt() {
    var a, i, s;
    a = new Array(1, 2, 3);

    /* legal: else if */
    if (s == "false") {
        i = 0;
    }
    else if (s == "true") {
        i = 1;
    }

    /* if, else */
    if (true)
        s = "A";
    else
        s = "B";

    /* skip with */

    /* try, catch, finally always require braces */

    /* do...while */
    do s += ".";
    while (false);

    /* for */
    for (i = 0; i < 20; i += 1)
        s += i;

    /* for...in */
    for (i in a)
        s += a[i];

    /* while */
    while (i > 0)
        s += "~";

    /* illegal */
    if (i)
        if (s) {
            i = s;
        }
        else {
            s = i;
        }

    /* illegal */
    if (i)
        while (s) {
            i = s;
        }

    /* illegal */
    if (i)
        do {
            i = s;
        } while (s);

    /* illegal */
    if (i)
        for (i = 0; i < 1; i++) {
            i++;
        }
}

function ambiguous_else_stmt() {
    var i, j, y;

    if (i)
        if (j) {
            j++;
        }
    /* error - where does the else go? */
    else if (j) {
        i--;
    }

    if (j)
        if (i)
            for (;;)
                while (j)
                    if (y)
                        y--;
        /* error - where does the else go? */
        else
            y++;
}

function missing_default_case() {
    var i, s;

    /*missing default case*/
    switch (i) {
      case 1:
        return 1;
    }

    /* ambivalence - allow fallthru but don't enforce it */
    switch (i) {
      case 2:
        /*jsl:fallthru*/
      case 3:
        s += 1;
        break;
      default:
        break;
    }

    /* ok - intended use of fallthru */
    switch (i) {
      case 0:
        s += "?";
        /*jsl:fallthru*/
      case 1:
        s += "!";
        break;
      default:
        break;
    }

    return "";
}

function duplicate_case_in_switch() {
    var i, o, s;

    switch (i) {
      case i:
        s += "...";
        break;
      case -1:
        s = "";
        break;
      case duplicate_case_in_switch():
        s = "0";
        break;
      case o.prop:
        i = 4;
        break;
      case "\"str1'":
      case "str2":
        i = null;
        break;

      /* mistake - duplicated */
      case i:
        s = "~";
        break;

      /* mistake - duplicated */
      case -1:
        s = "!";
        break;

      /* mistake - duplicated */
      case duplicate_case_in_switch():
        s = "";
        break;

      /* mistake - duplicated */
      case o['prop']:
        s = i;
        break;

      /* mistake - duplicated */
      case '"str1\'':
        s = 0;
        break;

      /* ok - not duplicated */
      case 100000000:
      case 100000001:
        s = 1;
        break;

      /* mistake - duplicated */
      case 100000000:
        s = -1;
        break;

      default:
        break;
    }
}

function default_not_at_end() {
    var i;

    /*default case at top*/
    switch (i) {
	  default:
		i++;
		break;
      case 1:
        return 1;
    }

    return 0;
}

function legacy_cc_not_understood() {
    /* illegal - missing end */
    /*@control comment starts but doesn't end*/

    /* illegal - unrecognized */
    /*@bogon@*/
   return;
}

function jsl_cc_not_understood() {
    /*jsl:bogon*/
    return;
}

function useless_comparison() {
    var i, j, o;

    /* illegal -- always false */
    if (i+2 < i+2) {
        return;
    }
    /* illegal - always false */
    if (j != j) {
        i++;
    }
    /* illegal - always true */
    if ((14 * i) / (j - 2) >= (14 * i) / (j - 2)) {
        return;
    }
    /* illegal - same properties */
    if (o.left == o.left) {
        return;
    }
    /* illegal - same properties */
    if (o.left == o['left']) {
        return;
    }
    /* illegal - same properties */
    if (o['left'] == o['left']) {
        return;
    }
    /* illegal - same properties */
    if (o[i] == o[i]) {
        return;
    }

    /* legal - different properties */
    if (o.left == o.right) {
        return;
    }
    /* legal - different properties */
    if (o['left'] == o.right) {
        return;
    }
    /* legal - different properties */
    if (o['left'] == o['right']) {
        return;
    }
    /* legal - different properties */
    if (o[i] == o[j]) {
        return;
    }
    /* legal - different properties */
    if (o[i] == o.right) {
        return;
    }

    /* "legal" (not caught because of slight differences) */
    if ((14 * i) / (j - 2) == (i * 14) / (j - 2)) {
        return;
    }

    /* legal - does function have side affects? */
    if (useless_comparison() == useless_comparison()) {
        return;
    }
}


function control_comments() {
    /* "legal" - can do anything */
    /*jsl:ignore*/
    var a;
    if (a);
       var b = a = b+++a;
       var a = b;
    /*jsl:end*/
    /*@ignore@*/
    var a;
    if (a);
       var b = a = b+++a;
       var a = b;
    /*@end@*/

    /* legal - case doesn't matter */
    /*Jsl:IGNORE*/
    asdf = asdf;
    /*JSL:End*/

    /* illegal - not ending anything */
    /*jsl:end*/

    /* illegal - can't start twice */
    /*jsl:ignore*/
    /*jsl:ignore*/
    /*jsl:end*/

    /* illegal - don't forget to end */
    /*jsl:ignore*/
}
