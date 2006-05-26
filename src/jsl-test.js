/*@option explicit@*/

/* illegal - j is not declared */
var g = j;
var j;

/* illegal - undeclared global */
z--;

/* illegal - undeclared global */
y();

/* legal */
UndeclaredIdentifier(true);

function UndeclaredIdentifier(parm) {
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
    UndeclaredIdentifier(parm);

    /* legal - this is a property, not a variable */
    this.q = -1;

    /* legal - global */
    g++;

    /* illegal */
    x = 14;

    /* illegal */
    y();

    /* illegal - z is not yet declared */
    s = z;
    var z;

    return "";
}

function SpiderMonkey(duplicate, duplicate) {
    /* illegal - duplicate formal parameters above */

    /* illegal - variable hiding argument */
    var duplicate;

    /* illegal - with is deprecated */
    with (duplicate) {
        this.x = this.y;
    }

    /* illegal - getter/setter is deprecated */
    Array.bogon getter = function () {
        return "";
    };
    Array.bogon setter = function (o) {
        this.push(o);
    };

    /* illegal - named function missing return value */
    function Check(b) {
        if (b) {
            return;
        }
        else {
            return "";
        }
    }

    /* illegal - anon function missing return value */
    var fn = function(b) {
        if (b) {
            return;
        }
        else {
            return "";
        }
    };

    /* illegal - redeclaration (see above) */
    function Check() {
        return "";
    }
    /* illegal - see above */
    var Check;

    /* illegal - assignment in condition */
    var a, b;
    while (a = b) {
        a++;
    }

    /* illegal - \0 is not a valid regex backreference */
    var re = /\0/;

    /* illegal - one 1 backreference */
    re = /(.)\2/;

    /* illegal - trailing comma */
    var o = { name: 'value', };
}

/* the EOL test is based on JSLint's documentation */
function EndOfLine() {
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
    case 1:
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

function UnreachableCode() {
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

function UselessExpression() {
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

function BlockWithoutBraces() {
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
}

function MissingBreak() {
    var i, s;

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

      default:
        /*missing break*/
    }

    return "";
}

function SemicolonOnReturnStatement() {
    return
}

function MeaninglessBlock() {
    var i;

    /* meaningless block */
    {
        var s;
        s = i + "%";
    }

    return s;
}

function Comma() {
    var b, i, j;

    /* comma (arguably legit) */
    for (i = 0, j = 0; i < 10; i += 2, j += 4) {
        b = ((i + j) / 2 == i - j);
    }

    /* comma (unclear) */
    b = false, i = 0, j = 0;
}

function ImplicitConversions() {
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

function UseOfVoid() {
    var z;
    /* check use of void */
    z = void 0;
    z();
}

function PlusMinus() {
    var i, j;
    i = 0;
    j = 0;

    /* disallow confusing +/- */
    i+++j;
    j---i;
}

function Numbers() {
    var i;

    /* leading decimal point; should have zero */
    i = .12;

    /* trailing decimal point; should have zero or no decimal*/
    i = 12.0.floor();
}

function Comments() {
    // line-continuation not supported \

    /* nested comment */
    /* /* */
    return "";
}

function RegEx() {
    var i, re;

    /* legal usage: regex in assignment */
    re = /\/\./;

    /* legal usage: regex in object definition */
    var o = { test : /\/\./ };

    /* legal usage: regex as first parameter */
    new String().replace(/\/\./, "<smile>");

    /* legal usage: regex as parameter (besides first) */
    RegEx(re, /\/\./);

    /* illegal usage: anything else */
    i += /\/\./;
}

function Label() {
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

function IncDec() {
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
    }

    /* illegal */
    s = new String(i++);

    /* illegal */
    s = --i;
}

/* "legal" - can do anything */
/*@ignore@*/
var a;
if (a);
   var b = a = b+++a;
   var a = b;
/*@end@*/

/* illegal - missing start/end */
/*control comment ends but doesn't start@*/
/*@control comment starts but doesn't end*/

/* illegal - unrecognized */
/*@bogon@*/

/* illegal - not ending anything */
/*@end@*/

/* illegal - can't start twice */
/*@ignore@*/
/*@ignore@*/
/*@end@*/

/* illegal - don't forget to end */
/*@ignore@*/
