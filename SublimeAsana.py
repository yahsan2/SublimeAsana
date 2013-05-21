import os

import sublime
import sublime_plugin

import threading
import subprocess
import functools
import os.path

from asana import asana

from pprint import pprint


AsanaProjects = sublime.load_settings('AsanaProjects.sublime-settings')

class GetAsanaTasksCommand(sublime_plugin.TextCommand):

    def run(self,edit,archive = False):
        self.path = self.view.window().folders()[0]
        self.archive = archive
        if AsanaProjects.has(self.path):
            project_id = AsanaProjects.get(self.path).get('id')
            project_name = AsanaProjects.get(self.path).get('name')

            self.task_ids = [project_id]
            self.task_names = ['### '+project_name+' ###']

            thread = AsanaApiCall('get_project_tasks', int(project_id), self.show_quick_panel_task)
            thread.start()
        else:
            self.view.window().run_command('set_asana_project')


    def show_quick_panel_task(self,tasks):
        if tasks != 'cache':
            for task in tasks:
                if (self.archive or task[u'completed'] == False) and task[u'name'][-1:] != ':':
                    self.task_ids.append(task[u'id'])
                    self.task_names.append(task[u'name'])
        if len(self.task_ids) > 0 :
            self.view.window().show_quick_panel(self.task_names, self.show_quick_panel_select)
        else:
            sublime.status_message('Not exist tasks')

    def show_quick_panel_select(self,index):
        if index == 0:
            self.view.window().run_command('get_current_project')
            return
        self.current_task_id = self.task_ids[index]
        self.current_task_name = self.task_names[index]
        command = ['0: Back','1: Done','2: Done & Commit','3: Update','4: Cancel']
        self.view.window().show_quick_panel(command, self.command_task)

    def command_task(self,index):
        if index == 0 :
            self.show_quick_panel_task('cache')
        elif index == 1 or index == 2:
            thread = AsanaApiCall('done_task', int(self.current_task_id), self.on_done)
            thread.start()
            if index == 2:
                self.view.window().show_input_panel('Commit -am: ', self.current_task_name+' #'+str(self.current_task_id), self.git_commit, None, None)
        elif index == 3 :
            self.view.window().show_input_panel('Change name: ', self.current_task_name, self.update_task, None, None)
        elif index == 4 :
            self.on_done()

    def update_task(self,name):
        thread = AsanaApiCall('update_task', [int(self.current_task_id),name], self.on_done)
        thread.start()


    def git_commit(self,message):
        thread = CommandThread(['git', 'commit', '-am',message], self.repo_name)
        thread.start()

    def repo_name(self,message):
        self.story = message
        thread = CommandThread(['git', 'remote', '-v'], self.git_log)
        thread.start()
        return

    def git_log(self,repo):
        repo = repo.split(':')
        repo = repo[1].split('.git')
        format = '%an, %ad \n https://github.com/'+repo[0]+'/commit/%H'
        thread = CommandThread(['git', 'log', '--pretty=format:'+format,'-1'], self.add_story)
        thread.start()

    def add_story(self,message):
        self.story = '.\n'+ self.story + '\n'+ message
        thread = AsanaApiCall('add_story', [int(self.current_task_id),self.story], self.on_done)
        thread.start()

    def on_done(self,name=False):
        if name :
            sublime.status_message('Done '+ name)

class getCurrentProjectCommand(sublime_plugin.TextCommand):
    def run(self,edit):
        command = ['0: Create New Task','1: Show Tasks','2: Show Archive Tasks','3: Change Project','4: Update Project','5: Cancel']
        self.view.window().show_quick_panel(command, self.command_task)

    def command_task(self,index):
        if index == 0 :
            self.view.window().run_command('add_asana_task')
        elif index == 1:
            self.view.window().run_command('get_asana_tasks')
        elif index == 2:
            self.view.window().run_command('get_asana_tasks',{"archive": True})
        elif index == 3 :
            self.view.window().run_command('set_asana_project')
        elif index == 4 :
            sublime.message_dialog('Now under development')
        elif index == 5 :
            self.on_done()

    def on_done(self,name=False):
        if name :
            sublime.status_message('Done '+ name)



class SetAsanaProjectCommand(sublime_plugin.TextCommand):
    def run(self,edit):
        thread = AsanaApiCall('get_project_id', None, self.show_quick_panel)
        thread.start()

    def show_quick_panel(self,projects):
        self.project_ids = []
        self.project_names = []

        for project in projects:
            self.project_names.append(project[u'name'])
            self.project_ids.append(project[u'id'])

        self.view.window().show_quick_panel(self.project_names, self.save_project_id)

    def save_project_id(self,index):
        self.path = self.view.window().folders()[0]

        AsanaProjects.set(self.path, {
            'id':str(self.project_ids[index]),
            'name':str(self.project_names[index]),
        })
        sublime.save_settings('AsanaProjects.sublime-settings')
        self.view.window().run_command('get_asana_tasks')

class AddAsanaTaskCommand(sublime_plugin.TextCommand):
    def run(self,edit):
        self.path = self.view.window().folders()[0]
        self.view.window().show_input_panel('New Task: ', '', self.create_task, None, None)

    def create_task(self,name):
        project_id = AsanaProjects.get(self.path).get('id')
        thread = AsanaApiCall('create_task', [name,project_id], self.show_quick_panel)
        thread.start()

    def show_quick_panel(self,name):
        sublime.status_message('Created: '+ name)
        self.view.window().run_command('get_asana_tasks')




def main_thread(callback, *args, **kwargs):
    # sublime.set_timeout gets used to send things onto the main thread
    # most sublime.[something] calls need to be on the main thread
    sublime.set_timeout(functools.partial(callback, *args, **kwargs), 0)

def _make_text_safeish(text, fallback_encoding, method='decode'):
    # The unicode decode here is because sublime converts to unicode inside
    # insert in such a way that unknown characters will cause errors, which is
    # distinctly non-ideal... and there's no way to tell what's coming out of
    # git in output. So...
    try:
        unitext = getattr(text, method)('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        unitext = getattr(text, method)(fallback_encoding)
    return unitext

class AsanaApiCall(threading.Thread):
    def __init__(self,command,args,callback):
        asana_api_key = sublime.active_window().active_view().settings().get('asana_api_key')
        self.AsanaApi = asana.AsanaAPI( asana_api_key , debug=True)
        self.command = command
        self.args = args
        self.callback = callback
        threading.Thread.__init__(self)

    def run(self):
        # try:
            if self.command == 'get_project_tasks':
                tasks = self.AsanaApi.get_project_tasks(self.args)
                main_thread(self.callback, tasks)

            elif self.command == 'get_task':
                projects = self.AsanaApi.get_task(self.args)
                main_thread(self.callback,projects)

            elif self.command == 'get_project_id':
                projects = self.AsanaApi.list_projects()
                main_thread(self.callback,projects)

            elif self.command == 'create_task':
                myspaces = self.AsanaApi.list_workspaces()
                task = self.AsanaApi.create_task(self.args[0], myspaces[1]['id'])
                self.AsanaApi.add_project_task(task[u'id'], self.args[1])
                main_thread(self.callback,self.args[0])

            elif self.command == 'update_task':
                task = self.AsanaApi.update_task(self.args[0], self.args[1])
                main_thread(self.callback,task[u'name'])

            elif self.command == 'add_story':
                task = self.AsanaApi.add_story(self.args[0], self.args[1])
                main_thread(self.callback,self.args[1])

            elif self.command == 'done_task':
                task = self.AsanaApi.update_task(self.args, None, None, None, True)
                main_thread(self.callback,task[u'name'])

            return
        # except:
        #     err = 'error'
        #     sublime.error_message(err)
        #     self.result = False

            # self.view.window().run_command('exec', {'cmd': ['sh', 'script.sh'], 'quiet': False})

class CommandThread(threading.Thread):
    def __init__(self, command, on_done, working_dir="", fallback_encoding="", **kwargs):
        threading.Thread.__init__(self)
        self.command = command
        self.on_done = on_done
        self.working_dir = working_dir
        if "stdin" in kwargs:
            self.stdin = kwargs["stdin"]
        else:
            self.stdin = None
        if "stdout" in kwargs:
            self.stdout = kwargs["stdout"]
        else:
            self.stdout = subprocess.PIPE
        self.fallback_encoding = fallback_encoding
        self.kwargs = kwargs

    def run(self):
        try:
            # Per http://bugs.python.org/issue8557 shell=True is required to
            # get $PATH on Windows. Yay portable code.
            shell = os.name == 'nt'
            if self.working_dir != "":
                os.chdir(self.working_dir)

            proc = subprocess.Popen(self.command,
                stdout=self.stdout, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                shell=shell, universal_newlines=True)
            output = proc.communicate(self.stdin)[0]
            if not output:
                output = ''
            # if sublime's python gets bumped to 2.7 we can just do:
            # output = subprocess.check_output(self.command)
            main_thread(self.on_done,
                _make_text_safeish(output, self.fallback_encoding), **self.kwargs)
        except subprocess.CalledProcessError, e:
            main_thread(self.on_done, e.returncode)
        except OSError, e:
            if e.errno == 2:
                main_thread(sublime.error_message, "Git binary could not be found in PATH\n\nConsider using the git_command setting for the Git plugin\n\nPATH is: %s" % os.environ['PATH'])
            else:
                raise e

