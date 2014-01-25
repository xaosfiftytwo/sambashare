#! /usr/bin/env python3

import os
import re
import gettext
from execcmd import ExecCmd
from os.path import exists, expanduser

# i18n: http://docs.python.org/2/library/gettext.html
gettext.install("sambashare", "/usr/share/locale")
#t = gettext.translation("sambashare", "/usr/share/locale")
#_ = t.lgettext


class UserShare(object):

    def __init__(self):
        self.ec = ExecCmd()
        self.home = expanduser("~/")

    def getShares(self, inclInfo=False, inclInfoAsDict=False):
        shares = None
        lst = self.ec.run("net usershare list -l")
        if inclInfo:
            if inclInfoAsDict:
                shares = {}
                for share in lst:
                    if not 'info_fn:' in share:
                        shares[share] = self.getShareInfo(share)
                    else:
                        self.removeCorruptShare(share)
            else:
                shares = []
                for share in lst:
                    if not 'info_fn:' in share:
                        shares.append([share, self.getShareInfo(share)])
                    else:
                        self.removeCorruptShare(share)
        else:
            shares = lst
        return shares

    def getShareInfo(self, share):
        ret = []
        if share is not None and share.strip() != "":
            ret = self.ec.run("net usershare info -l '%s'" % share)
        return ret

    def removeCorruptShare(self, info_fn_line):
        matchObj = re.search("(/.*)\s+is\s+not", info_fn_line)
        if matchObj:
            path = matchObj.group(1)
            if exists(path):
                try:
                    os.remove(path)
                except:
                    # Best effort
                    pass

    def doesShareExist(self, share):
        info = self.getShareInfo(share)
        if info:
            return True
        else:
            return False

    def needRoot(self, path):
        writable = os.access(path, os.W_OK)
        if writable:
            return False
        else:
            return True

    def getPathFromName(self, name):
        path = None
        info = self.getShareInfo(name)
        for line in info:
            if line.startswith("path="):
                path = line.replace("path=", "")
        return path

    def createShare(self, path, name, comment=None, public=True, readonly=True):
        ret = []
        if self.doesShareExist(name):
            ret.append(_("Cannot create share.\nShare already exists: %(share)s") % { "share": name })
        elif not exists(path):
            ret.append(_("Cannot create share.\nPath does not exist: %(path)s") % { "path": path })
        else:
            if comment is None:
                comment = ""
            guest_ok = "y"
            if not public:
                guest_ok = "n"
            read_only = "R"
            if not readonly:
                read_only = "F"

            if self.needRoot(path):
                ret.append(_("You do not have sufficient permission to create a share on:\n%(path)s") % { "path": path })
            else:
                cmd = "net usershare add '%(name)s' '%(path)s' '%(comment)s' Everyone:%(read_only)s guest_ok=%(guest_ok)s" % { "name": name, "path": path, "comment": comment, "read_only": read_only, "guest_ok": guest_ok }
                print(cmd)
                ret = self.ec.run(cmd, False)

                if not readonly:
                    cmd = "chmod 777 %(path)s" % { "path": path }
                    print(cmd)
                    ret = self.ec.run(cmd, False)

        return ret

    def removeShare(self, name):
        ret = []
        if self.doesShareExist(name):
            path = self.getPathFromName(name)
            if self.needRoot(path):
                ret.append(_("You do not have sufficient permission on path: %(path)s") % { "path": path })
            else:
                cmd = "net usershare delete '%(name)s'" % { "name": name }
                print(cmd)
                ret = self.ec.run(cmd, False)

                if exists(path):
                    cmd = "chmod 755 %(path)s" % { "path": path }
                    print(cmd)
                    ret = self.ec.run(cmd, False)

        return ret
