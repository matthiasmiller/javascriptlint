function trailing_comma() {
    var o = {
        outer: {
            inner: 1
        }, /*warning:trailing_comma*/
    };
}
