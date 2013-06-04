SublimeAsana
=================


### What is Sublime Asana?

It's task management plugin using asana api at sublime text 2.

You can

- get asana task each projects
- create new task
- complete task
- complete and git commit
- update task name

#### Installation

To install this plugin:

- Clone source code to Sublime Text 2 app folder, eg. ~/Library/Application Support/Sublime Text 2/SublimeAsana.

#### Set up
you must have Asana account.

So at fist, set up the `API Key` in the Preferences.sublime-settings.

like this:

<pre>
{ "asana_api_key" : "YOUR_API KEY" }
</pre>

you can get it , following:
[http://developer.asana.com/documentation/](http://developer.asana.com/documentation/)


#### How to use

- use `Ctrl+Shift+P` then `Asana: Get Tasks`
- type `Ctrl + t ` and `Ctrl + t`

example key bind :
<pre>
  { "keys": ["ctrl+t","ctrl+t"], "command": "get_asana_tasks" }
</pre>

## Licence

The code is available at
[GitHub](https://github.com/michfield/StrapdownPreview) under MIT licence.

