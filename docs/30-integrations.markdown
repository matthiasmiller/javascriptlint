---
layout: page
title: Integrations
permalink: /integrations/
---

> **NOTE**: This documentation may be out-of-date.
> [Corrections are welcome](https://github.com/matthiasmiller/javascriptlint).

You can run JavaScript Lint several ways:

* You can integrate it into your IDE, such as Visual Studio, SciTE, or any other IDE supporting
external tools. When JavaScript Lint finds an error, your IDE takes you directly to the line containing the error.

* You can run it through Windows Explorer, which Windows programmers may prefer.

* You can use the command line to integrate into your build system, or maybe you're a Linux programmer
and simply prefer the command line!

Additionally, if you are a software developer, you may want to integrate into your Windows program or
run it from your PHP website to take advantage of the full power of JavaScript Lint.

## Visual Studio
If you use Microsoft Visual Studio to edit JavaScript or HTML, you may want to integrate this tool into Visual Studio. This will let you lint the file that is currently open. You can double-click on error messages or use keyboard shortcuts to look at the line of code that triggered a warning.

In Visual Studio 2003/2005, go to Tools, External Tools... and create a tool with these settings:

**Command**: `c:\path\to\jsl.exe` <br/>
**Arguments**: `-conf c:\path\to\configuration\file -process $(ItemPath)` <br/>
**Initial directory**:<br/>
[x] Use output window; [_] Prompt for arguments

In Visual C++ 6.0, go to Tools, Customize, Tools and create a new tool with the following settings.

**Command**: `c:\path\to\jsl.exe` <br/>
**Arguments**: `-conf c:\path\to\configuration\file -process $(FilePath)` <br/>
**Initial directory**: <br/>
[x] Use output window; [_] Prompt for arguments

If you wish to disable warnings, you can simply modify configuration file that is passed through the command line.

You may also want to create a second tool to lint all of your JavaScript files. To do this, you can create a
copy of the configuration and specify specific folders to lint. (Instructions are included in the default
configuration file.)

## TextMate
See [JavaScript Tools TextMate Bundle](https://andrewdupont.net/2006/10/01/javascript-tools-textmate-bundle/).

## SciTE
You can also integrate JavaScript Lint into [SciTE](https://scintilla.sourceforge.io/SciTE.html).
Open `~/.SciteUser.properties` (choose Options, Open User Options File). Add the following to the following lines:

```
file.patterns.js=*.js;*.es
command.compile.$(file.patterns.js)=/path/to/jsl conf /path/to/configuration/file process $(FileNameExt)
```

You will also need to change your JavaScript Lint configuration so that SciTE will correctly place a
yellow dot at the beginning of the line corresponding to the current error (see screenshot). Change the "output-format" setting to:

```
+output-format __FILE__:__LINE__: __ERROR__
```

Like Visual Studio, you can press F4 to go to the next error.

## vim (Cygwin)
This configuration is for vim on Cygwin. There may be some differences with vim directly on Windows.

* Copy jsl.exe to /usr/bin
* Copy jsl.default.conf to /etc/jsl.conf
* Edit /etc/jsl.conf:
  * Comment out the line containing "+process"
  * Comment out the line containing "+pauseatend"
  * Set the line containing "+context" to "-context"

Add one of the following configurations to vimrc.

To process the current file:
```
autocmd FileType javascript set makeprg=jsl\ -nologo\ -nofilelisting\ -nosummary\ -nocontext\ -conf\ '/cygwin/etc/jsl.conf'\ -process\ %
autocmd FileType javascript set errorformat=%f(%l):\ %m^M
```

To process ALL files in the directory instead of just the current file:

```
autocmd FileType javascript set makeprg=jsl\ -nologo\ -nofilelisting\ -nosummary\ -nocontext\ -conf\ '/cygwin/etc/jsl.conf'\ -process\ '*.js'
autocmd FileType javascript set errorformat=%f(%l):\ %m^M
```

If you want to process ALL files recursively, use these lines instead:

```
autocmd FileType javascript set makeprg=jsl\ -nologo\ -nofilelisting\ -nosummary\ -nocontext\ -conf\ '/cygwin/etc/jsl.conf'\ -process\ '*.js'\ -recurse
autocmd FileType javascript set errorformat=%f(%l):\ %m^M
```

Note that ^M should be a control character! To enter it, Press {Ctrl-V}{Ctrl-M}. If this doesn't work for you,
just leave out ^M. Note also that if using method 2 or 3 and vim on cygwin, you will probably get vim errors
about "unable to open swap file...". I have no way around this, but if you are ok with not having a swap file
in vim (no recovery on crash), then that's fine.

## emacs
To integrate JavaScript Lint to emacs, add the following to your emacs init file (~/.emacs). It assumes you
are using a javascript-mode with a hook support. You can use Karl Landström's mode.

```
;; javascript lint
(defun jslint-thisfile ()
  (interactive)
  (compile (format "jsl -process %s" (buffer-file-name))))

(add-hook 'javascript-mode-hook
  '(lambda ()
  (local-set-key [f8] 'jslint-thisfile)))
```

Just press 'F8' and it will execute JavaScript Lint in the current buffer.
 
## Other IDEs
Many IDEs can launch a third-party tool and show the results in a window in the IDE. If the tool correctly
formats its output, the IDE will read the file names and line numbers from the tool and provide a way of
finding the corresponding location in the code.

If you use an IDE other than Visual Studio, you may need to customize the format of JavaScript Lint's
outputted error messages. The sample configuration file (jsl.default.conf) demonstrates this feature.

## Running from Windows Explorer
The easiest way to run JavaScript lint is by adding it to the right-click menu on .htm and .js files.
To do so, open Windows Explorer and choose Tools | Folder Options | File Types. Select the .js file type.
Click Advanced, then click New. Enter these settings (paths will vary):

**Action**: `Lint` <br/>
**Application used to perform action**: `c:\path\to\jsl.exe -conf c:\path\to\configuration\file -process "%1" -pauseatend`

Repeat these steps for all the file types that you wish to lint (e.g. .htm, .hta, and .wsf).

## Running from the Command Line
Running JavaScript Lint from the command line allows integration with build and source control systems.
It also allows batching lint jobs.

You can run JavaScript Lint in two modes: using built-in default settings or using settings from a
configuration file. For the latter, the name of the configuration file is passed on the command line.
The sample configuration file (jsl.default.conf) documents how to enable or disable warnings.

The names of the files to process can be specified on the command line, in the configuration file, or
both. The sample configuration file demonstrates how to use wildcards and recursion to specify which files to lint.

Run jsl without parameters for usage.
