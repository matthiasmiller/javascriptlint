---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: page
title: Overview
permalink: /

---

## What It Is

Many JavaScript implementations do not warn against questionable coding practices. Yes, that's nice for the site that "works best with Internet Explorer" (designed with templates, scripted with snippets copied from forums). But it's a nightmare when you actually want to write quality, maintainable code.

That's where JavaScript Lint comes in. With JavaScript Lint, you can check all your JavaScript source code for common mistakes without actually running the script or opening the web page.

## What It Does
Here are some common mistakes that JavaScript Lint looks for:

* Missing semicolons at the end of a line.
* Curly braces without an *if, for, while,* etc.
* Code that is never run because of a *return, throw, continue,* or *break*.
* Case statements in a switch that do not have a break statement.
* Leading and trailing decimal points on a number.
* A leading zero that turns a number into octal (base 8).
* Comments within comments.
* Ambiguity whether two adjacent lines are part of the same statement.
* Statements that don't do anything.

JavaScript Lint also looks for the following less common mistakes:

* Regular expressions that are not preceded by a left parenthesis, assignment, colon, or comma.
* Statements that are separated by commas instead of semicolons.
* Use of increment (++) and decrement (--) except for simple statements such as "i++;" or "--i;".
* Use of the void type.
* Successive plus (e.g. x+++y) or minus (e.g. x---y) signs.
* Use of labeled *for* and *while* loops.
* *if, for, while,* etc. without curly braces. (This check is disabled by default.)

Advanced users can also configure JavaScript Lint to check for undeclared identifiers.

