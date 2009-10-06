<!--
@template=__template__
@title=News
-->

Project News
============

## [IDE Integration](http://www.javascriptlint.com/news.php?id=23)
_Sat, 29 Sep 2007 22:08:21 +0000_

The [documentation page](http://www.javascriptlint.com/docs/running_from_your_ide.htm) now contains instructions for integrating JavaScript Lint with TextMate, vim, and emacs.

Improvements to the documentation are welcome.


## [JavaScript Lint 0.3.0 Released](http://www.javascriptlint.com/news.php?id=22)
_Fri, 03 Nov 2006 20:32:42 +0000_

This version has also been released for Intel Macs.

__Enhancements:__

* Add support for JScript's function extensions, such as `function window.onload() {}` and `function window::onload()`. (This is disabled by default.)
* Add a `/*jsl:pass*/` control comment to suppress warnings about empty statementss.
* Add a `/*jsl:declare*/` control comment to suppress warnings about undeclared identifiers.
* Warn against trailing comments in array initializers.
* Warn against assignments to function calls (for example, `alert() = 10`).
* Warn against calls to `parseInt` without a radix parameter.
* Warn against implicit type conversion when comparing against `true` or `false`.
* Clarify the warning against `with` statements.

__Bug Fixes:__

* Fix syntax error on nested comments.
* Fix duplicate case warning.
* Fix insuppressible increment/decrement warning.
* Fix incorrect warning against invalid `/*jsl:fallthru*/` comment.
* Fix undeclared identifiers in `with` statements.
		
_Update:_ Corrected post title.


## [JavaScript Lint SourceForge Project](http://www.javascriptlint.com/news.php?id=21)
_Fri, 26 May 2006 05:15:10 +0000_

JavaScript Lint now has its own [SourceForge project](http://sourceforge.net/projects/javascriptlint) with [discussion forums](http://sourceforge.net/forum/?group_id=168518), [bug/feature trackers](http://sourceforge.net/tracker/?group_id=168518), and a publicly-available [Subversion repository](http://sourceforge.net/svn/?group_id=168518).


## [JavaScript Lint 0.2.6 Released](http://www.javascriptlint.com/news.php?id=20)
_Sat, 29 Apr 2006 15:07:13 +0000_

JavaScript Lint now has a `/*jsl:ignoreall*\` keyword to allow entire files to easily be ignored.  Additionally, it no longer complains about blank JavaScript files.

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.2.5 Released](http://www.javascriptlint.com/news.php?id=19)
_Sat, 08 Apr 2006 04:29:38 +0000_

To facilitate integration into other applications, the output format can now be passed on the command line and the results can be encoded. The source package contains source files that can be used to easily [integrate JavaScript Lint into a Windows program](http://www.javascriptlint.com/docs/running_from_your_windows_program.htm).

The [documentation](http://www.javascriptlint.com/docs/) on the website has been updated.

The "Unicode (UTF-8 with signature) - Codepage 65001" encoding is now supported for configuration files.

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.2.4 Released](http://www.javascriptlint.com/news.php?id=18)
_Sat, 11 Mar 2006 02:55:51 +0000_

JavaScript within HTML files can now contain `</script>` in string literals and comments.

When referencing an external script, the _script_ start and end tags no longer need to be on the same line.

JavaScript files using "Unicode (UTF-8 with signature) - Codepage 65001" encoding, such as those created in Microsoft Visual Studio, no longer generate errors.

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.2.3 Released](http://www.javascriptlint.com/news.php?id=17)
_Thu, 16 Feb 2006 01:11:07 +0000_

Syntax errors in imported scripts were not being reported.
Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.2.2 Released](http://www.javascriptlint.com/news.php?id=16)
_Tue, 24 Jan 2006 14:16:24 +0000_

This release includes a __FILENAME__ keyword for the output format.

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.2.1 Released](http://www.javascriptlint.com/news.php?id=15)
_Mon, 09 Jan 2006 14:18:24 +0000_

This release includes a configuration setting to completely disable legacy control comments.

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.2.0 Released](http://www.javascriptlint.com/news.php?id=14)
_Wed, 04 Jan 2006 02:20:01 +0000_

This release includes cumulative changes through version 0.1m.

This release has a command-line parameter to disable the file listing in the output.

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.1m Released](http://www.javascriptlint.com/news.php?id=13)
_Tue, 03 Jan 2006 17:31:25 +0000_

This release fixes a bug with the "undeclared identifier" warnings when using the import control comment.

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.1l Released](http://www.javascriptlint.com/news.php?id=12)
_Mon, 02 Jan 2006 22:05:25 +0000_

This release includes a new warning for useless comparisons (for example, x == x).

This release also improves the use of the _fallthru_ control comment when used in the final case in a switch statement. The "undeclared identifier" fix in the 0.1k release is now applied to both global and local variables declarations.

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.1k Released](http://www.javascriptlint.com/news.php?id=11)
_Sat, 24 Dec 2005 18:56:35 +0000_

This release includes a number changes.

__Enhancements:__

* JavaScript Lint warns if the default case is not at the end of the switch statement.

* Control comments can now use the `/*jsl:keyword*/` syntax in addition to the `/*@keyword@*/` syntax. The new syntax is recommended for interoperability with JScript conditional compilation, although the traditional syntax is still supported.

* The "missing break" warning can be disabled for the last case in a switch statement. The presence of this _break_ is merely stylistic preference.

* The "missing semicolon" warning can be disabled when anonymous functions are assigned to variables and properties (such as function prototypes). Code such as the following can optionally be allowed:

>
    function Coord() {  
        this.x = function() {  
            return 1;  
        }  
	}
	Coord.prototype.y = function() {
	    return 0;
	}

__Bug Fixes:__

* The "undeclared identifier" warning for variables has been updated to reflect the ECMA specification. The following code no longer issues a warning:
  > 
	function getX() { return x; }
	var x;

* Scripts with circular _import_ directives no longer incorrectly report undeclared identifiers.

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.1j Released](http://www.javascriptlint.com/news.php?id=10)
_Mon, 05 Dec 2005 20:19:35 +0000_

This release fixes a bug in the "duplicate case" warning for numbers. Certain numbers were incorrectly reported as duplicates.  (This bug is more likely to affect JavaScript programmers using big-endian processors.)

The [Online Lint](http://www.javascriptlint.com/online_lint.php) has also been updated to use a local CGI, making the script much more responsive. PHP source code for the Online Lint is included in the source package.

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.1i Released](http://www.javascriptlint.com/news.php?id=9)
_Wed, 16 Nov 2005 14:28:54 +0000_

This release has a more specific warning for _else_ statements that may be intended for one of multiple _if_ statements (it previously warned that nested statements should use curly braces to resolve ambiguity):

>
	`if (i)`
	`if (j) func1();`
	`else func2();`

The warning against duplicate case statements now correctly handles case statements with string literals.

This release fixes a bug that caused a "Bus error" on Mac OS X and a segmentation fault on Solaris 5.9; JavaScript Lint has now been compiled and run on those operating systems. If Mac users are interested in precompiled binaries, I will consider making them available for download on the website.

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.1h Released](http://www.javascriptlint.com/news.php?id=8)
_Tue, 25 Oct 2005 19:16:04 +0000_

This release upgrades the SpiderMonkey JavaScript engine from a release candidate to the latest stable branch (version 1.5).
Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint 0.1g Released](http://www.javascriptlint.com/news.php?id=7)
_Sat, 08 Oct 2005 16:37:29 +0000_

This release includes a warning if the default case is missing from switch, a warning if a case is duplicated within a switch, better intelligence when checking for missing break statements, and a `/*@fallthru*@/` control comment (must always come at the very end of a case).

Available from the [download page](http://www.javascriptlint.com/download.htm).


## [JavaScript Lint Source Package Available](http://www.javascriptlint.com/news.php?id=6)
_Sat, 01 Oct 2005 17:06:22 +0000_

JavaScript Lint source is now [available for download](http://www.javascriptlint.com/download.htm) as a single package.


## [JavaScript Lint 0.1f Released](http://www.javascriptlint.com/download.htm)
_Sat, 10 Sep 2005 14:59:43 +0000_

This release adds a separate warning for nested statements that don't use curly braces (nested _if_, _for_, _while_, etc.), a warning for useless assignments (x = x), and a configuration option to enable option-explicit across all files.


## [JavaScript Lint 0.1e Released](http://www.javascriptlint.com/download.htm)
_Tue, 31 Aug 2005 02:40:49 +0000_

This release fixes a crash triggered by the following statement: _for(i = 0; i < 5; )_. (The Linux binary is not currently available for this release.)


## [JavaScript Lint 0.1d Released](http://www.javascriptlint.com/download.htm)
_Tue, 30 Aug 2005 22:28:35 +0000_

This release fixes a crash caused by an incorrectly formed control comment.


## [JavaScript Lint 0.1c Released](http://www.javascriptlint.com/download.htm)
_Tue, 30 Aug 2005 18:54:06 +0000_

This release corrects problems with the wildcard feature.


## [JavaScript Lint 0.1b Released](http://www.javascriptlint.com/download.htm)
_Tue, 30 Aug 2005 15:37:08 +0000_

This release fixes a crash caused by certain syntax errors. For example: _if (a !=== b)_.


