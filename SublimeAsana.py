import sublime
import sublime_plugin
from asana import asana

# import urllib
# import urllib2
import threading
import functools


AsanaProjects = sublime.load_settings('AsanaProjects.sublime-settings')


class GetAsanaTasksCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        self.path = self.view.window().folders()[0]
        self.task_names = []
        self.task_ids = []

        if AsanaProjects.has(self.path):
            project_id = AsanaProjects.get(self.path)
            AsanaApiCall('get_project_tasks', int(project_id), self.show_quick_panel_task)

            thread = AsanaApiCall('get_project_tasks', int(project_id), self.show_quick_panel_task)
            thread.start()
        else:
            sublime.message_dialog('setproject')
            self.view.window().run_command('set_asana_project')

    def show_quick_panel_task(self,tasks):
        if tasks != 'cache':
            for task in tasks:
                self.task_names.append(task[u'name'])
                self.task_ids.append(task[u'id'])
        self.view.window().show_quick_panel(self.task_names, self.show_quick_panel_select)


    def show_quick_panel_select(self,index):
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
        self.view.window().run_command('exec', {'cmd': ['git', 'commit', '-am', message], 'quiet': False})
        sublime.status_message('Commit: '+message)


    def on_done(self,name=False):
        if name :
            sublime.status_message('done '+ name)


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
        AsanaProjects.set(self.path, str(self.project_ids[index]))
        sublime.save_settings('AsanaProjects.sublime-settings')

        self.view.window().run_command('get_asana_task')

class AddAsanaTaskCommand(sublime_plugin.TextCommand):
    def run(self,edit):
        self.path = self.view.window().folders()[0]
        self.view.window().show_input_panel('New Task: ', '', self.create_task, None, None)

    def create_task(self,name):
        project_id = AsanaProjects.get(self.path)
        thread = AsanaApiCall('create_task', [name,project_id], self.show_quick_panel)
        thread.start()

    def show_quick_panel(self,name):
        sublime.status_message('created: '+ name)
        # self.view.window().run_command('get_asana_tasks')


class AsanaApiCall(threading.Thread):
    def __init__(self,command,args,callback):
        self.command = command
        self.args = args
        self.callback = callback
        threading.Thread.__init__(self)

    def main_thread(self,callback, args=False):
        # sublime.set_timeout gets used to send things onto the main thread
        # most sublime.[something] calls need to be on the main thread
        sublime.set_timeout(functools.partial(callback, args), 10)


    def run(self):
        self.main_thread(self.api_command,10)

    def api_command(self,na):
            asana_api_key = sublime.active_window().active_view().settings().get('asana_api_key')
            self.AsanaApi = asana.AsanaAPI( asana_api_key , debug=True)
        # try:
            if self.command == 'get_project_tasks':
                tasks = self.AsanaApi.get_project_tasks(self.args)
                self.main_thread(self.callback, tasks)

            elif self.command == 'get_project_id':
                projects = self.AsanaApi.list_projects()
                self.main_thread(self.callback,projects)

            elif self.command == 'create_task':
                myspaces = self.AsanaApi.list_workspaces()
                task = self.AsanaApi.create_task(self.args[0], myspaces[1]['id'])
                self.AsanaApi.add_project_task(task[u'id'], self.args[1])
                self.main_thread(self.callback,self.args[0])

            elif self.command == 'update_task':
                task = self.AsanaApi.update_task(self.args[0], self.args[1])
                self.main_thread(self.callback,task[u'name'])

            elif self.command == 'done_task':
                task = self.AsanaApi.update_task(self.args, None, None, None, True)
                self.main_thread(self.callback,task[u'name'])

            return
        # except:
        #     err = 'error'
        #     sublime.error_message(err)
        #     self.result = False


            # self.view.window().run_command('exec', {'cmd': ['sh', 'script.sh'], 'quiet': False})
