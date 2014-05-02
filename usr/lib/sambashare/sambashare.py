#! /usr/bin/env python3

# http://stackoverflow.com/questions/4112737/how-to-gain-root-privileges-in-python-via-a-graphical-sudo/4118244#4118244
# http://stackoverflow.com/questions/567542/running-a-command-as-a-super-user-from-a-python-script
# http://stackoverflow.com/questions/230845/make-python-enter-password-when-running-a-csh-script
# http://stackoverflow.com/questions/17959589/sudo-command-in-popen

# sudo apt-get install python3-gi
# from gi.repository import Gtk, GdkPixbuf, GObject, Pango, Gdk
from gi.repository import Gtk
import sys
import os
import gettext
# abspath, dirname, join, expanduser, exists
from os.path import join, abspath, dirname, basename
from execcmd import ExecCmd
from treeview import TreeViewHandler
from dialogs import MessageDialogSafe, QuestionDialog, SelectDirectoryDialog
from usershare import UserShare

# i18n: http://docs.python.org/2/library/gettext.html
gettext.install("sambashare", "/usr/share/locale")
#t = gettext.translation("sambashare", "/usr/share/locale")
#_ = t.lgettext


#class for the main window
class SambaShare(object):

    def __init__(self):
        self.scriptDir = abspath(dirname(__file__))

        # Load window and widgets
        self.builder = Gtk.Builder()
        self.builder.add_from_file(join(self.scriptDir, '../../share/sambashare/sambashare.glade'))

        go = self.builder.get_object
        self.window = go('sambashareWindow')
        self.windowAdd = go('sambashareWindowAdd')
        self.lblTitle = go('lblTitle')
        self.tvShares = go('tvShares')
        self.btnAdd = go('btnAdd')
        self.btnRemove = go('btnRemove')
        self.txtShareDetails = go('txtShareDetails')
        self.lblName = go('lblName')
        self.lblPath = go('lblPath')
        self.lblComment = go('lblComment')
        self.lblPublic = go('lblPublic')
        self.lblReadOnly = go('lblReadOnly')
        self.txtName = go('txtName')
        self.txtPath = go('txtPath')
        self.txtComment = go('txtComment')
        self.chkPublic = go('chkPublic')
        self.chkReadOnly = go('chkReadOnly')
        self.btnOk = go('btnOk')
        self.btnCancel = go('btnCancel')

        # Translations
        self.window.set_title(_("Samba share"))
        self.windowAdd.set_title(_("Create samba share"))
        self.lblTitle.set_text(self.window.get_title())
        self.lblName.set_text(_("Name"))
        self.lblPath.set_text(_("Path"))
        self.lblComment.set_text(_("Comment"))
        self.lblReadOnly.set_text(_("Read only"))
        self.lblPublic.set_text(_("Public"))

        # Init
        self.ec = ExecCmd()
        self.us = UserShare()
        self.shareName = None
        self.sharePath = None
        self.startAddNow = False

        # Fill treeview with shares
        self.tvHandler = TreeViewHandler(self.tvShares)
        self.refreshShares()

        # Command arguments
        args = sys.argv[1:]
        for arg in args:
            if "/" in arg:
                self.sharePath = arg
                self.startAddNow = True
            else:
                self.shareName = arg

        # Connect the signals and show the window
        self.builder.connect_signals(self)
        self.window.show_all()
        if self.startAddNow:
            self.on_btnAdd_clicked(None)



    # ===============================================
    # Menu section functions
    # ===============================================

    def on_tvShares_cursor_changed(self, widget, event=None):
        # Show share details
        self.setDetailText()

    def on_btnAdd_clicked(self, widget):
        # Show add share window
        if self.sharePath is None:
            self.sharePath = os.getcwd()
            self.shareName = basename(self.sharePath)
        if self.sharePath is None:
            self.sharePath = ""
        if self.shareName is None:
            self.shareName = ""
        self.txtName.set_text(self.shareName)
        self.txtPath.set_text(self.sharePath)
        self.windowAdd.show_all()

    def on_btnBrowse_clicked(self, widget):
        directory = SelectDirectoryDialog(_('Select directory to share'), self.txtPath.get_text(), self.window).show()
        if directory is not None:
            self.sharePath = directory
            self.txtPath.set_text(self.sharePath)
        self.shareName = basename(self.sharePath)
        self.txtName.set_text(self.shareName)

    def on_btnRemove_clicked(self, widget):
        # TODO: remove selected share
        title = _("Remove share")
        qd = QuestionDialog(title, _("Are you sure you want to remove the following share:\n\n'%(share)s'") % { "share": self.shareName }, self.window)
        answer = qd.show()
        if answer:
            ret = self.us.removeShare(self.shareName)
            self.showUserFeedback(ret, title, "remove", self.window)
            self.refreshShares()

    def on_btnOk_clicked(self, widget):
        # Create network share, and close add share window
        title = _("Create share")
        self.shareName = self.txtName.get_text()
        comment = self.txtComment.get_text()
        public = self.chkPublic.get_active()
        readonly = self.chkReadOnly.get_active()
        ret = self.us.createShare(self.sharePath, self.shareName, comment, public, readonly)
        closeWin = self.showUserFeedback(ret, title, "create", self.windowAdd)
        if closeWin:
            self.windowAdd.hide()
            self.refreshShares()

    def showUserFeedback(self, returnList, title, action, parent):
        msg = ""
        closeWin = False
        for line in returnList:
            msg += "%s\n" % line
        if msg != "":
            MessageDialogSafe(title, msg, Gtk.MessageType.ERROR, parent).show()
        else:
            shareExists = self.us.doesShareExist(self.shareName)
            if action == "removed" and shareExists:
                msg = _("Could not remove share: '%(share)s'") % { "share": self.shareName }
            elif action == "created" and not shareExists:
                msg = _("Could not create share: '%(share)s'") % { "share": self.shareName }
            else:
                msg = _("Share successfully %(action)s:\n\n'%(share)s' on %(path)s") % { "action": action, "share": self.shareName, "path": self.sharePath }
                closeWin = True
            MessageDialogSafe(title, msg, Gtk.MessageType.INFO, parent).show()
        return closeWin

    def refreshShares(self):
        self.shareName = None
        self.sharePath = None
        self.shares = self.us.getShares()
        self.shareDetail = self.us.getShares(True, True)
        self.fillTreeView()
        self.setDetailText()
        print("Refresh done")

    def on_btnCancel_clicked(self, widget):
        # Close add share window without saving
        self.windowAdd.hide()

    def on_sambashareWindowAdd_delete_event(self, widget, data=None):
        self.windowAdd.hide()
        return True

    def fillTreeView(self):
        # Very dirty hack: add and remove a dummy row to the treeview when treeview is empty
        # GtkTreeView has a problem refreshing when there's no data present
        if self.tvHandler.getRowCount() == 0:
            self.tvHandler.fillTreeview('-', ['str'])
            self.tvHandler.clearTreeView()
        self.tvHandler.fillTreeview(self.shares, ['str'])

    def setDetailText(self):
        buf = Gtk.TextBuffer()
        txt = ""
        try:
            self.shareName = self.tvHandler.getSelectedValue()
            if self.shareName is not None:
                if self.shareDetail[self.shareName]:
                    txt = "Name:\t\t%s\n" % self.shareName
                    for line in self.shareDetail[self.shareName]:
                        line = line.strip()
                        if line != "" and line != "[%s]" % self.shareName:
                            if line.startswith("path="):
                                self.sharePath = line.replace("path=", "")
                                txt += "Path:\t\t%s\n" % self.sharePath
                            elif line.startswith("comment="):
                                txt += "Comment:\t%s\n" % line.replace("comment=", "")
                            elif ':R' in line:
                                txt += "Share:\t\tRead permission"
                            elif ':F' in line:
                                txt += "Share:\t\tRead/write permission"
                            elif line == "guest_ok=y":
                                txt += ", public\n"
                            elif line == "guest_ok=n":
                                txt += ", private\n"
                else:
                    self.sharePath = None
        except:
            # Best effort
            pass

        buf.set_text(txt)
        self.txtShareDetails.set_buffer(buf)

    # Close the gui
    def on_sambashareWindow_destroy(self, widget):
        # Close the app
        Gtk.main_quit()

if __name__ == '__main__':
    # Create an instance of our GTK application
    try:
        gui = SambaShare()
        Gtk.main()
    except KeyboardInterrupt:
        pass
