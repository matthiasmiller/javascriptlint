/*conf:-duplicate_property*/
function ambiguous_numeric_prop() {
    var a = {
        1: '',
        2.0: '', /*warning:ambiguous_numeric_prop*/
        2.1: '',
        2.2: '',
        0x3: '' /*warning:ambiguous_numeric_prop*/
    };

    a[1] = '';
    a[2.0] = ''; /*warning:ambiguous_numeric_prop*/
    a[2.1] = '';
    a[0x3] = ''; /*warning:ambiguous_numeric_prop*/
}

