/* The tests disable this warning by default becaues of noise. Enable it. */
/*conf:+unreferenced_identifier*/

/* outer-level functions shouldn't warn */
var unreferenced_global;
function unreferenced_identifier() {
    /* Test an unreferenced function. */
    function unreferenced_func() { /*warning:unreferenced_identifier*/
        return true;
    }
    function referenced_func() {
    }
    var referenced_var = referenced_func;
    referenced_var();

    /* Test an unreferenced parameter. */
    var z = new function(unreferenced_parm) { /*warning:unreferenced_identifier*/
    }
    z.prop = 42;

    /* Test an unreferenced variable. */
    var unreferenced_variable = 100; /*warning:unreferenced_identifier*/
    
    /* An unreferenced duplicate parameter should give one warning. */
    function func_with_dup(unref_dup_parm, unref_dup_parm) { /*warning:unreferenced_identifier*/ /*warning:duplicate_formal*/
    }
    func_with_dup();

    /* An unreferenced duplicate variable should give one warning. */
    var unref_dup_var; /*warning:unreferenced_identifier*/
    var unref_dup_var; /*warning:redeclared_var*/

    /* Test a try/catch. The error doesn't need to be referenced. */
    var can;
    try {
        can = true; /* we think we can... */
    }
    catch(err) {
        can = false; /* ...but maybe not! */
    }
    can = !can;

    /* Test a with statement. */
    var withobj = {};
    var withval = 42;
    with (withobj) /*warning:with_statement*/
    {
        prop_a = withval;
        var innerval = '42';
        prop_b = innerval;
    }

    /* Test assignments. */
    var assigned_but_unref; /*warning:unreferenced_identifier*/
    assigned_but_unref = 42;

    function callback() {
    }
    var assigned_but_ref;
    (assigned_but_ref = callback)();

    /* Test nested scopes. */
    function get_callback(parm) {
        return function() {
            return parm;
        }
    }
    return get_callback(42);
}
