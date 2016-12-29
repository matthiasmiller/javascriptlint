/*conf:-useless_quotes*/
/*conf:-ambiguous_numeric_prop*/
function duplicate_property() {
    var o = {
        a: '',
        "a": '', /*warning:duplicate_property*/
        2.00: '',
        2: '', /*warning:duplicate_property*/
        3.00: '',
        '3': '', /*warning:duplicate_property*/
        'other': ''
    };
}
