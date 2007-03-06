/*conf:-lambda_assign_requires_semicolon*/


/* Test with a simple variable. */
var x = function() {
    return {};
}
x();

var a, b = function() { }, c
b(); /*warning:missing_semicolon*/
var d, e = function() { }
e();

var y;
y = function() {
    return [];
}
y();

global = function() {
    return null;
}
global();

function Foo()
{
    this.bar = 10;

    /* Test an assignment to a member. */
    this.setBar = function(bar) {
        this.bar = bar;
    }

    this.setBar(this.bar * 2);
}

/* Test an assignment to a prototype. */
Foo.prototype.getBar = function() {
    return this.bar;
}

var foo = new Foo();
