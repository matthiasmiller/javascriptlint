---
layout: page
title: Documentation
permalink: /docs/
---

> **NOTE**: This documentation may be out-of-date.
> [Corrections are welcome](https://github.com/matthiasmiller/javascriptlint).

## Disable Warnings with Control Comment
JavaScript Lint has limited support for control comments. To disable warnings in part of your
JavaScript file, you can add the following comments:

```
/*jsl:ignore*/
(code that fires warnings)
/*jsl:end*/
```

To ignore all warnings in a file, simply place `/*jsl:ignoreall*/` at the top of the file.

Note that this should only be used as a short-term solution for code that you maintain. If this is
caused by a bug or missing feature in JavaScript Lint, please report the problem to info(at)JavaScriptLint.com.

## Option Explicit
JavaScript Lint can optionally check for variables, functions, and objects that don't exist, much
like Visual Basic's "option explicit." In the interest of making JavaScript Lint accessible to the
average programmer, this powerful feature is disabled by default. Although this feature requires more
work to understand and implement, it provides a higher level of protection against coding errors.

A variable that is not explicitly declared has a global scope. For example, if a function uses a
counter variable and calls another function that uses a counter variable by the same name, unless
these functions use the var keyword to declare the variable, the two functions will be accessing
and modifying the same variable. This almost never produces the expected behavior.

Here's what it takes to set up this feature:

* The check for undeclared identifiers is enabled on a per-file basis with a
`/*jsl:option explicit*/` comment within a script. To enforce the use of option explicit, you
can modify your configuration file to warn against scripts that do not use this feature.
 
* If a script references a variable, function, or object from another script, you will need to add
a `/*jsl:import PathToOtherScript*/` comment in your script. This tells JavaScript Lint to check for
items declared in the other script. Relative paths are resolved based on the path of the current script.
 
* Your script may also reference global objects that are provided by the runtime (e.g. Firefox or
Windows Scripting Host). For example, the script in a web page may reference the global window object.
Add the line `+define window` to your configuration file to tell JavaScript Lint about this global.

JavaScript Lint does not validate object properties. They do not use the `var` keyword and cannot be
validated without executing the script.

The warnings for undeclared identifiers will appear after other warnings that may occur in the script.
This is by design, since the entire script must be examined before identifiers can be called undefined.

## Switches and Breaks
By default, JavaScript Lint warns against missing `break`'s in switch statements. Sometimes, however,
`break` statements are intentionally excluded. To indicate this, use the `/*jsl:fallthru*/` control comment:

```
switch (i) {
  case 1:
    break;
  case 2:
    /*jsl:fallthru*/
  case 3:
    break;
}
```

## Empty Statements
By default, JavaScript Lint warns against empty statements. However, empty statements are sometimes
intentional. To indicate this, use the `/*jsl:pass*/` control comment:

```
while (!hasResponse()) {
    /*jsl:pass*/
}
```

## Advanced Output Format
The following output formats may also be used:

* `__ERROR_PREFIX__` indicates the type of message
* `__ERROR_MSG__` indicates the message contents
* `__ERROR__` indicates the full error including the error type and the message.

If the output format is prefixed with `encode:`, all backslashes, single and double quotes, tabs,
carriage returns, and line breaks will be escaped as \\, \' and \", \t, \r, and \n (respectively).

> **Syntax Note**: In addition to the `/*jsl:keyword*/` syntax, control comments can also use the traditional
`/*@keyword@*/` syntax. However, the jsl syntax is recommended for interoperability with JScript conditional
compilation.

