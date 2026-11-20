# Multillviewer

An extention of the LiveLanguage Lexicon Viewer meant to work on multilingual lexicons and allows modification.

*As this is a version 0 there is likely to be bugs*

To run the program execute this command in the console:

C:\my\path\> python multillviewer.py .\multi-lit-eng-ita-scn-pms-nap.xml

With the xml file being replacable with another multilingual lexicon that must be in the same folder.

If you want to start fresh delete the "_modified" file and "obj_ids.txt"

# LiveLanguage Lexicon Viewer

A simple, multi-platform tool for viewing the contents of monolingual lexicons.

*Note that this is a beta release. The tool is under development.*

On Windows, you can run the EXE file directly, but you have to provide it with an input lexicon as argument. For example, the example Quechua lexicon included in the distribution can be loaded as follows:

```console
C:\my\path\> llview.exe que.xml
```

If you wish to build the tool directly from the Python source (which is what you have to do under Linux), you will need Python 3 and PySimpleGui installed.

```console
$ pip install pysimplegui
```

Then the tool is run as follows (loading the Quechua lexicon):

```console
$ python3 llview.py que.xml
```
