function unexpected_not() {
    var i, j;
    var f, s, o;

    if (!i == -1) { /*warning:unexpected_not*/
        return false;
    }

    if (!f() < -1) { /*warning:unexpected_not*/
        return false;
    }

    if (!i != -1) { /*warning:unexpected_not*/
        return false;
    }

    if (i != -1 || !j == -1) { /*warning:unexpected_not*/
        return false;
    }

    if (!s in o) { /*warning:unexpected_not*/
        return false;
    }

    return true;
}
