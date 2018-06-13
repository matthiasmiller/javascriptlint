function unexpected_not_comparison() {
    var i, j;
    var b, f, s, o;

    if (!i == -1) { /*warning:unexpected_not_comparison*/
        return false;
    }

    if (!f() < -1) { /*warning:unexpected_not_comparison*/
        return false;
    }

    if (!i != -1) { /*warning:unexpected_not_comparison*/
        return false;
    }

    if (i != -1 || !j == -1) { /*warning:unexpected_not_comparison*/
        return false;
    }

    // Allow ! and !!
    if (!!i == b) {
        return false;
    }
    if (b == !!i) {
        return false;
    }
    if (b === !i) { /*warning:unexpected_not_comparison*/
        return false;
    }
    if (!i === b) { /*warning:unexpected_not_comparison*/
        return false;
    }
    if (!!b === !i) {
        return false;
    }
    if (!i === !!b) {
        return false;
    }

    // Do not allow !! for relative comparison
    if (!!i <= b) { /*warning:unexpected_not_comparison*/
        return false;
    }

    return true;
}
