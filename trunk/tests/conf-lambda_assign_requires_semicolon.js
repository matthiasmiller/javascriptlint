/*conf:-lambda_assign_requires_semicolon*/


/* Test with a simple variable. *
var x = function() {
    return {};
} /*warning:missing_semicolon*/


/* Test an assignment to a prototype. */
function Foo()
{
    this.bar = 10;
}
Foo.prototype.getBar = function() {
    return this.bar;
}
