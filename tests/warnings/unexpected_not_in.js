function unexpected_not_in() {
    var s, o;

    if (!s in o) { /*warning:unexpected_not_in*/
        return false;
    }

    if (!(s in o)) {
        return false;
    }

    // Strange, but...if you really want to...
    if ((!s) in o) {
        return false;
    }

    return true;
}
