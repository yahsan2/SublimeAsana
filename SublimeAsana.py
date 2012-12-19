import sublime
import sublime_plugin
from asana import asana


class GetAsanaTaskCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        asana_api_key = self.view.settings().get('asana_api_key')
        asana_api = asana.AsanaAPI( asana_api_key , debug=False)

        window = self.view.window()
        new_window = window.new_file()
        new_window.set_name('Asana todo')

        myspaces = asana_api.get_project_tasks(2128400497714) #Result: [{u'id': 123456789, u'name': u'asanapy'}]
        for myspace in myspaces:
            new_window.insert(edit, 0, str(myspace[u'id'])+': '+myspace[u'name']+'\n')