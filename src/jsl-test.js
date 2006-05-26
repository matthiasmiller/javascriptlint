/*jsl:option explicit*/

/* legal - j is declared */
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

function AmbiguousElse() {
    var i,j;

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

function SwitchStatements() {
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
        /*missing break at end of switch (without code)*/
    }

	/*missing break at end of switch (with code)*/
	switch (i) {
	  case i:
	     i++;
	}

    /*missing default case*/
    switch (i) {
      case 1:
        return 1;
    }

    /*default case at top*/
    switch (i) {
	  default:
		i++;
		break;
      case 1:
        return 1;
    }

    /* mistake - invalid use of fallthru */
    /*jsl:fallthru*/
    switch (i) {
      /*jsl:fallthru*/
      case /*jsl:fallthru*/1:
        break;
      default:
        /*jsl:fallthru*/
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

    switch (i) {
      case i:
        s += "...";
        break;
      case -1:
        s = "";
        break;
      case SwitchStatements():
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
      case SwitchStatements():
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

    return "";
}

function SemicolonOnReturnStatement() {
    return
}

function MissingSemicolon() {
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
    default:
        break;
    }

    /* illegal */
    s = new String(i++);

    /* illegal */
    s = --i;
}

function Assign() {
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

function FunctionWithNoReturn() {
    var i, o;

    /* illegal */
    var s = FunctionWithNoReturn();

    /* illegal */
    o = FunctionWithNoReturn();

    /* illegal */
    for (i = FunctionWithNoReturn(); ; ) {
        i++;
    }

    /* illegal */
    if (FunctionWithNoReturn()) {
        i--;
    }
}

/* illegal */
g = FunctionWithNoReturn();

/* legal */
FunctionWithNoReturn();

/*jsl:ignore*/
g = FunctionWithNoReturn();
/*jsl:end*/

function FunctionWithReturn() {
    var i, o;

    /* legal */
    var s = FunctionWithReturn();

    /* legal */
    o = FunctionWithReturn();

    /* legal */
    for (i = FunctionWithReturn(); ; ) {
        i++;
    }

    /* legal */
    if (FunctionWithReturn()) {
        i--;
    }

    return "";
}

/* legal */
FunctionWithReturn();

/* legal */
g = FunctionWithReturn();

function Comparisons() {
    var i, j;

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
    if (Comparisons() == Comparisons()) {
        return;
    }
}

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

/* illegal - missing end */
/*@control comment starts but doesn't end*/

/* illegal - unrecognized */
/*@bogon@*/
/*jsl:bogon*/

/* illegal - not ending anything */
/*jsl:end*/

/* illegal - can't start twice */
/*jsl:ignore*/
/*jsl:ignore*/
/*jsl:end*/

/* illegal - don't forget to end */
/*jsl:ignore*/
