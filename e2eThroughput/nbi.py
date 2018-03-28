#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
#############################################################
# Northbound Interface helper
#
# (c) 2016 Airspan Ltd
# Author: Simon Brusch sbrusch@airspan.com
#############################################################
# 1) Query the webservice to get an empty soap request
# 2) optionally replace fields with user supplied values,
#      either from a file or command line options
# 3) POST the resulting request back to the web service
# 4) Display the response
##############################################################
import sys, re, urllib2, os, cgi, json
import argparse, ConfigParser, pprint, hashlib, StringIO
from xml.dom import minidom as ET
from HTMLParser import HTMLParser
import logging

class VersionParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self._versions=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower()=='a':
            attrs_dict = dict(attrs)
            if 'class' in attrs_dict and attrs_dict['class'] == 'webservice':
                    self._versions.append(attrs_dict['href'][:-1])
    def getVersions(self):
        return self._versions

class CategoryParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self._categories=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower()=='a':
            attrs_dict = dict(attrs)
            if 'href' in attrs_dict:
                full_href=attrs_dict['href']
                self._categories.append(full_href.split(".")[0])
    def getCategories(self):
        return self._categories

class WebServiceParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self._webservices=[]
        self._in_li=False
        self._in_a=False
        self._li_content = {}
    def handle_starttag(self, tag, attrs):
        if tag.lower()=='li':
            self._in_li = True
            return
        if self._in_li and tag.lower()=='a':
            self._in_a = True
            return
    def handle_data(self,data):
        if self._in_li and self._in_a and self._li_content=={}:
            self._li_content['name'] = data
    def handle_endtag(self,tag):
        if self._in_li and tag.lower()=='a':
            self._in_a = False
            return
        if tag.lower()=='li':
            self._in_li=False
            self._webservices.append(self._li_content['name'])
            self._li_content={}
    def getWebservices(self):
        return self._webservices

class GetChildParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self._children={}
    def handle_starttag(self, tag, attrs):
        if tag.lower()=='object':
            attrs_dict = dict(attrs)
            self._objId = attrs_dict['id']
        elif tag.lower()=='field':
            attrs_dict = dict(attrs)
            if 'name' in attrs_dict and attrs_dict['name'].lower()=='type':
                self._fieldType=attrs_dict['name']
            else:
                self._fieldType=None
        else:
            self._fieldType=None

    def handle_data(self,data):
        if self._fieldType!=None:
            self._children[self._objId]=data

    def getChildren(self):
        return self._children

# help to convert Dict into argparse-like object
class Argstruct(object):
    def __init__(self,dictOfValues={}):
        for key in dictOfValues:
            setattr(self, key, dictOfValues[key])
    def __contains__(self,item):
        return item in self.__dict__
    def __getattr__(self,key):
        if key in self.__dict__:
            return self.__dict__[key]
        else:
            return None
    def __repr__(self):
        return "<Argstuct: {}>".format(self.__dict__)

class nbi:
    def __init__(self, addr, version, username=None, password=None):
        self.addr = addr
        self.version = version
        if username == None:
            self.username = "svgauto"
        else:
            self.username = username
        if password == None:
            self.password = hashlib.md5('svg_auto\n').hexdigest()[:16]
        else:
            self.password = password

# the following methods replace BASH shell helpers found in nbiHelpers.sh
    def getNmsVersion(self):
        cliArgs = Argstruct()
        response = self.applyAndPost('Server', 'NmsInfoGet', cliArgs)
        return self.getField(response, 'NMSSoftwareVersion')[0]
        
    def nodeDelete(self, nodeName):
        cliArgs = Argstruct({'values':['NodeName='+nodeName],'novalues':['NodeId']})
        response = self.applyAndPost('Inventory', 'NodeDelete', cliArgs)
        result = self.getField(response, 'NodeResultString') 
        return True if result == [] else result[0]

    def makeUnmanaged(self, nodeName):
        cliArgs = Argstruct({'values':['NodeName='+nodeName,'ManagedMode=Unmanaged'],'delEmpty':True,
            'deleteSections':['Pdcl=Delete','AllowedBands=Delete']})
        response = self.applyAndPost('Backhaul', 'RelayConfigSet', cliArgs)
        result = self.getField(response, 'ErrorString') 
        return True if result == [] else result[0]

    def deletePnpConfig(self, nodeName):
        cliArgs = Argstruct({'values':['NodeName='+nodeName],'delEmpty':True})
        response = self.applyAndPost('Backhaul', 'RelayPnpConfigDelete', cliArgs)
        result = self.getField(response, 'NodeResultString') 
        return True if result == [] else result[0]

    def forceRescan(self, nodeName):
        cliArgs = Argstruct({'values':['NodeName='+nodeName],'delEmpty':True})
        response = self.applyAndPost('Backhaul', 'RelayForceScan', cliArgs)
        result = self.getField(response, 'NodeResultString') 
        return True if result == [] else result[0]

    def getNodeByName(self, nodeName):
        cliArgs = Argstruct({'values':['NodeName='+nodeName],'delEmpty':True})
        return self.applyAndPost('Inventory', 'NodeInfoGet', cliArgs)

    def getNodeById(self, nodeId):
        cliArgs = Argstruct({'values':['NodeId='+nodeId],'delEmpty':True})
        return self.applyAndPost('Inventory', 'NodeInfoGet', cliArgs)

    def getNodeNameById(self, nodeId):
        nodeInfo = self.getNodeById(nodeId)
        return self.getField(nodeInfo, "Name")[0]

    def getStatusByName(self, nodeName, device='Gps'):
        cliArgs = Argstruct({'values':['NodeNameOrId='+nodeName],'delEmpty':True})
        return self.applyAndPost('Status', "Node{}Get".format(device), cliArgs)

    def isNodeOnline(self, nodeName):
        cliArgs = Argstruct({'values':['NodeName='+nodeName],'delEmpty':True})
        connectionState = self.getField(self.applyAndPost('Inventory', 'NodeInfoGet', cliArgs), 'ConnectionState')
        # print connectionState
        if connectionState == []:
            return False
        for state in connectionState:
            if state != "Online": 
                return False
        return True

#moje zmiany
    def getNodeHardwareCategory(self, nodeName):
        cliArgs = Argstruct({'values': ['NodeName=' + nodeName], 'delEmpty': True})
        #sprawdzenie gdzie znajduje si? odpowiedni obiekt
        xml = self.action('Inventory', 'NodeInfoGet', cliArgs)
        # print xml
        image_record = self.getFieldList(xml, ['HardwareCategory'])
        return image_record

    def deleteAuPnpConfig(self, nodeName):
        cliArgs = Argstruct({'values':['NodeName='+nodeName],'delEmpty':True})
        response = self.applyAndPost('Lte', 'UnityPnpConfigDelete', cliArgs)
        result = self.getField(response, 'NodeResultString') 
        return True if result == [] else result[0]

    def resetNode(self, nodeName, resetType="NodeReset"):
        cliArgs = Argstruct({'values':['NodeName='+nodeName],'delEmpty':True})
        response = self.applyAndPost('Inventory', resetType, cliArgs)
        result = self.getField(response, 'NodeResultCode') 
        return True if result == 'OK' else self.getField(response,'NodeResultString')

    def run(self, cliArgs=None):
        if cliArgs == None:
            cliArgs=nbi.parseargs()
        elif type(cliArgs) == type({}):    # Dict
            cliArgs = Argstruct(cliArgs)
        elif type(cliArgs) == type([]):
            cliArgs=nbi.parseargs(cliArgs)
        # for name in cliArgs.__dict__:
        #     print "    {0} = {1!s}".format(name, cliArgs.__dict__[name])
        if cliArgs.qpack:
            if not cliArgs.server:
                if 'AUTOMATION_QPACK_SERVER' in os.environ:
                    cliArgs.server = os.environ['AUTOMATION_QPACK_SERVER']
                else:
                    cliArgs.server='10.3.10.28'
        elif cliArgs.server == None:
            if self.addr != None:
                cliArgs.server = self.addr
            elif 'AUTOMATION_NETSPAN_NBI_ADDR' in os.environ:
                cliArgs.server = os.environ['AUTOMATION_NETSPAN_NBI_ADDR']
            else:
                print "need a value for --server (Netspan IP address)"
                sys.exit(0)
        if not cliArgs.qpack:
            if cliArgs.version == None:
                if self.version != None:
                    cliArgs.version = self.version
                elif 'AUTOMATION_NETSPAN_NBI_VERSION' in os.environ:
                    cliArgs.version = os.environ['AUTOMATION_NETSPAN_NBI_VERSION']
                else:
                    print "need a value for --version=..., one of:"
                    print self.get_version_list(cliArgs.server)
                    sys.exit(0)
            if cliArgs.category == None or cliArgs.category_list:
                if not cliArgs.category_list: print "need a value for --category=..., one of:"
                print self.get_category_list(cliArgs.server, cliArgs.version)
                sys.exit(0)
            if cliArgs.webservice == None or cliArgs.webservice_list:
                if not cliArgs.webservice_list: print "need a value for --webservice=..., one of:"
                print self.get_webservice_list(cliArgs.server, cliArgs.version, cliArgs.category)
                sys.exit(0)
            url = "http://{server}/ws/{version}/{category}.asmx?op={webservice}".format(**cliArgs.__dict__)
        else:
            if cliArgs.webservice == None:
                print "need a value for --webservice=..., one of:"
                print self.get_webservice_list(cliArgs.server)
                sys.exit(0)
            url="http://{server}/qpack/qpackserv/qpackserv.asmx?op={webservice}".format(**cliArgs.__dict__)
        if cliArgs.values == None and cliArgs.valuesfilenames == None and not cliArgs.makeini:
            ufh = urllib2.urlopen(url)
            print "".join(self.get_webservice_raw(ufh))
            sys.exit(1)
    #     else:
    #         url = "http://{server}/ws/{version}/{category}.asmx".format(**cliArgs.__dict__)
        template_doc = self.get_webservice_raw(urllib2.urlopen(url))
        if cliArgs.makeini:
            ini_name = "{category}_{webservice}".format(**cliArgs.__dict__)
            self.make_ini(ini_name, template_doc)
            sys.exit(0)
        # template_doc = get_webservice_raw(urllib2.urlopen(url+'?op={}'.format(cliArgs.webservice)))
        post_args, doc = self.apply_values(template_doc, cliArgs)
        if cliArgs.verbose:
            print "POST {}".format(url)
            print "\n".join(doc)
        if cliArgs.dryrun or 'dryrun' in post_args:
            print "Not trying POST --dry-run is set"
            sys.exit(0)
        post = urllib2.Request(url,"\n".join(doc))
        self.add_post_header(post, post_args['Content-Type'])
        self.add_post_header(post, post_args['SOAPAction'])
        # open URL and process returned XML, this is performed in a try ... except
        # to catch URL or parsing errors
        try:
            urlFh=urllib2.urlopen(post)
            xmldoc = ET.parse(urlFh)
        except urllib2.HTTPError, e:
            print "{}".format(e.reason)
        else:
            if cliArgs.field == None:
                print xmldoc.getElementsByTagName("soap:Body")[0].toprettyxml(indent="  ")
            else:
                if cliArgs.webservice=="Get_Children" and cliArgs.field=="Get_ChildrenResult":
                    gcparser = GetChildParser()
                    gcparser.feed(xmldoc.getElementsByTagName(cliArgs.field)[0].firstChild.nodeValue)
                    response = gcparser.getChildren()
                    return response
                elif cliArgs.all_occ:
                    fieldList="{}".format(";".join([node.firstChild.nodeValue for node in xmldoc.getElementsByTagName(cliArgs.field)]))
                    if fieldList == "":
                        print "{} not found".format(cliArgs.field)
                    else:
                        print fieldList
                else:
                    try:
                        response="{}".format(xmldoc.getElementsByTagName(cliArgs.field)[0].firstChild.nodeValue)
                    except IndexError:
                        print "{} not found".format(cliArgs.field)
                    if cliArgs.return_val:
                        return response
                    else:
                        print response

    def action(self, category, webservice, cliArgs=Argstruct({}), ini=None):
        return self.applyAndPost(category, webservice, cliArgs, ini)

    def getXml(self, url, doc, post_args=None):
        if post_args == None:
            post_args = self._post_args
        post = urllib2.Request(url,"\n".join(doc))
        self.add_post_header(post, post_args['Content-Type'])
        self.add_post_header(post, post_args['SOAPAction'])
        # open URL and process returned XML, this is performed in a try ... except
        # to catch URL or parsing errors
        try:
            urlFh=urllib2.urlopen(post)
            xmldoc = ET.parse(urlFh)
        except urllib2.HTTPError, e:
            print "{}".format(e.reason)
            sys.exit(2)
        return xmldoc

    def formatXmlResponse(self, xmldoc):
        return xmldoc.getElementsByTagName("soap:Body")[0].toprettyxml(indent="  ")

    def getField(self, xmldoc, field):
        try:
            return [node.firstChild.nodeValue for node in xmldoc.getElementsByTagName(field)]
        except AttributeError:
            logging.warning('AttributeError')
            logging.warning('No info from node about %s' % field)

    def getFieldList(self, xmldoc, fields):
        output = {}
        for field in fields:
            try:
                output[field] = ["{}".format(node.firstChild.nodeValue) for node in xmldoc.getElementsByTagName(field)]
            except AttributeError:
                logging.warning('AttributeError')
                logging.warning('No info from node about %s' % field)
                output[field] = []
        return output

    def add_post_header(self, post, header):
        first_colon_index = header.index(":")
        key = header[:first_colon_index]
        value = header[first_colon_index+1:]
        post.add_header(key,value)

    def applyAndPost(self, category, webservice, cliArgs={}, ini=None):
        url, templateDoc = self.getTemplateDoc(category, webservice, withUrl=True)
        doc = self.applyValues(templateDoc, cliArgs, ini)
        if cliArgs.verbose:
            print doc
        xml = self.getXml(url, doc)
        return xml

    def applyValues(self, template, cliArgs={}, ini=None):
        # print cliArgs
        post_args, doc = self.apply_values(template, cliArgs, ini)
        self._post_args = post_args
        return doc

    def apply_values(self, doc, cliArgs={}, ini=None):
        headers = self.extract_headers(doc)
        if 'headerlength' not in headers:
            print "could not find xml doc in server response"
            sys.exit(2)
        replacement_data = self.gather_replacements(cliArgs, ini)
        if 'options' in replacement_data:
            if 'dryrun' in replacement_data['options']:
                headers['dryrun'] = True
            for n,v in replacement_data['options'].iteritems():
                cliArgs.__setattr__(n,v)
        doc_changes_applied = []
        for line in doc[headers['headerlength']+1:]:
            doc_changes_applied.extend(self.apply_values_to_line(line.rstrip(), replacement_data, cliArgs))
        if 'delEmptySections' in cliArgs:
            doc_changes_applied = self.removeEmptySections(doc_changes_applied)
        return headers, doc_changes_applied

    def removeEmptySections(self, doc):
        """take an xml doc as an array of lines, remove any section tags which do not contain any assigned value tags.
        Returns the xml doc as an array of lines."""
        newDoc = []
        currentDepth = 0; tagByDepth = []; includeClose = {}; notAddedLines = []
        valueTag = re.compile("\s+<(\w+)>(.*)</\\1>")
        endSection = re.compile("\s*</")
        sectionName = re.compile("\s*<([:\w]+)(\s.*)?>")
        for line in doc:
            if line[:5] == "<?xml":
                newDoc.append(line)
                continue
            if valueTag.match(line):
                # add all so far and this value
                for depth, tag in enumerate(tagByDepth):
                    includeClose[depth+1] = tag
                while len(notAddedLines) > 0:
                    newDoc.append(notAddedLines.pop(0))
#                     print "**DEBUG** valueTag adding cached header {}".format(newDoc[-1])
                newDoc.append(line)
#                 print "**DEBUG** valueTag adding value {}".format(newDoc[-1])
            elif endSection.match(line):
                if currentDepth in includeClose:
#                     print "**DEBUG** including section end depth={}: {}".format(currentDepth, line)
                    newDoc.append(line)
                    del includeClose[currentDepth]
#                     print "**DEBUG** endSection includeClose keys are:{}".format(",".join([str(x) for x in includeClose.keys()]))
                tagByDepth.pop()
#                 print "**DEBUG** endSection popping tagByDepth, now len={}".format(len(tagByDepth))
                if len(notAddedLines) > 0:
#                     print "**DEBUG** popping one notAddedLine: {}".format(notAddedLines[-1])
                    notAddedLines.pop()
                currentDepth -= 1
#                 print "**DEBUG** endSection currentDepth now {}".format(currentDepth)
            elif sectionName.match(line):
                currentDepth += 1
                tagByDepth.append(line)
#                 print "**DEBUG** startSection appending tagByDepth, now len={}".format(len(tagByDepth))
                notAddedLines.append(line)
#                 print "**DEBUG** startSection caching header {}".format(line)
#                 print "**DEBUG** startSection currentDepth now {}".format(currentDepth)
        return newDoc

    def gather_replacements(self, cliArgs={}, ini=None):
        if cliArgs == {}:
            cliArgs = ArgStruct({'valuesfilenames':[]})
        try:
            repl_data = self.get_file_values(cliArgs.valuesfilenames, ini)
        except:
            repl_data = {'once':{}, 'eachtime':{}, 'inturn':{}, 'changekeys':{}, 'novalue':{}, 'deleteSections':{}, 'options':{} }
        try:
            for kv in cliArgs.eachtime:
                k,v = kv.split('=')
                if k not in repl_data['eachtime']:
                    repl_data['eachtime'][k] = [v]
                else:
                    repl_data['eachtime'][k].append(v)
                if k not in repl_data['changekeys']:
                    repl_data['changekeys'][k]=True
        except:
            pass
        try:
            for kv in cliArgs.valuesinturn:
                k,v = kv.split('=')
                sep = v[0]
                repl_data['inturn'][k] = v[1:].split(sep)
                if k not in repl_data['changekeys']:
                    repl_data['changekeys'][k]=True
        except:
            pass
        try:
            for kv in cliArgs.values:
                # split on the first =, the ,1 means perform one split only
                k,v = kv.split('=',1)
                if k not in repl_data['once']:
                    repl_data['once'][k] = [v]
                else:
                    repl_data['once'][k].append(v)
                if k not in repl_data['changekeys']:
                    repl_data['changekeys'][k]=True
        except:
            pass
        try:
            for key in cliArgs.novalues:
                repl_data['novalue'][key]=True
        except:
            pass
        try:
            for kv in cliArgs.deleteSections:
                k,v = kv.split('=',1)
                repl_data['deleteSections'][k]=v
        except:
            pass
        if 'Username' not in repl_data['once']:
            repl_data['once']['Username'] = [self.username]
            repl_data['changekeys']['Username']=True
        if 'Password' not in repl_data['once']:
            repl_data['once']['Password'] = [self.password]
            repl_data['changekeys']['Password']=True
        # finally add 'global' command-line arguments to options 
        for flag in ['delEmpty','delEmptySections','dryrun']:
            try:
                if cliArgs.hasattr(flag):
                    repl_data['options'][flag] = True
            except:
                pass
        return repl_data

    def apply_values_to_line(self, line, changes, cliArgs):
    #    if 'test propertytest propertytest propertytest propertytest propertytest property' in line:
    #        line='<?xml version="1.0" encoding="utf-8"?>'
        # first see if we are in a section to skip
        if 'InSectionNow' in changes['deleteSections']:
            if "</{}>".format(changes['deleteSections']['InSectionNow']) in line:
                # we have reached the end of the section to skip
                del changes['deleteSections']['InSectionNow']
            return []

        # next check if line contains a 'no value' tag, if True to return empty set
        for key in changes['novalue']:
            if "<{}>".format(key) in line:
                return []

        # check to see if we are at the start of the section to delete
        for section,disposition in changes['deleteSections'].iteritems():
            if "<{}>".format(section) in line:
                # yes this is a section to potentially delete
                if disposition=='Delete':
                    # mark we are in a section to delete and return empty set
                    changes['deleteSections']['InSectionNow']=section
                    return []
                elif disposition=='KeepFirst':
                    # we are in a section to use this time and delete next time, so mark as delete and continue
                    changes['deleteSections'][section]='Delete'
                    break

        # keep the current line, unless it is a single value and --del-empty is TRUE, then apply the changes
        if re.match("\s+<(\w+)>.*</\\1>",line) and hasattr(cliArgs,'delEmpty') and cliArgs.delEmpty:
            newlines = []
        else:
            newlines = [line]
        for key in changes['changekeys']:
            if "<{}>".format(key) in line:
                newlines = []  # key found so remove unchanged line
                indent = line.index("<{}>".format(key))
                # and add a line for each value gathered
                if key in changes['once']:
                    for value in changes['once'][key]:
                        newlines.append(line[:indent] + "<{0}>{1}</{0}>".format(key,value))
                    changes['once'][key] = {}   # if change was in 'once' then make the changelist empty, so they will not be applied again
                elif key in changes['eachtime']:
                    # change in eachtime
                    for value in changes['eachtime'][key]:
                        newlines.append(line[:indent] + "<{0}>{1}</{0}>".format(key,value))
                elif key in changes['inturn']:
                    value =  changes['inturn'][key][0]
                    if len(value) > 0:
                        newlines.append(line[:indent] + "<{0}>{1}</{0}>".format(key,value))
                    if len(changes['inturn'][key]) > 1:
                        changes['inturn'][key]=changes['inturn'][key][1:]
                    else:
                        del changes['inturn'][key]
                else:
                    print "Do not know what to do with {}, not in any list, so stopisNodeOnline".format(key)
                    sys.exit(1)
        return newlines

    def extract_headers(self, doc):
        headers = {}
        for linenum, line in enumerate(doc):
            if len(line) == 0:
                continue
            if line[:5] == '<?xml':
                headers['headerlength'] = linenum-1
                break
            fieldname = line.split(" ")[0]
            if fieldname[-1] == ':': fieldname = fieldname[:-1]  # remove trailing colon
            if fieldname == 'POST':
                headers['path'] = line.split(" ")[1]
                continue
            if fieldname in ['Content-Type', 'SOAPAction']:
                headers[fieldname] = line.rstrip()
        return headers

    def get_file_values(self, fnames, buffer=None):
        values={'once':{}, 'eachtime':{}, 'inturn':{}, 'changekeys':{}, 'deleteSections':{}, 'novalue':{}, 'options':{}}
        cfgParser = ConfigParser.ConfigParser(allow_no_value=True)
        cfgParser.optionxform = str  # prevent options been converted to lower case
        if fnames == None: fnames = []
        heredoc = True if '-' in fnames else False
        if heredoc: fnames.remove('-')
        filesread = cfgParser.read(fnames)
        if len(filesread) < len(fnames):
            print "** ERROR unable to read all value files - only read: '{}'".format("','".join(filesread))
        if heredoc:
            cfgParser.readfp(sys.stdin, 'heredoc')
        if buffer != None:
            bufferObj = StringIO.StringIO(buffer)
            cfgParser.readfp(bufferObj, 'string')
        if cfgParser.has_section('valueseachtime'):
            for (name, value) in cfgParser.items('valueseachtime'):
                values['eachtime'][name] = [value]
                values['changekeys'][name] = True
        if cfgParser.has_section('values'):
            for (name, value) in cfgParser.items('values'):
                values['once'][name] = [value]
                values['changekeys'][name] = True
        if cfgParser.has_section('escapevalues'):
            for (name, value) in cfgParser.items('escapevalues'):
                values['once'][name] = [cgi.escape(value)]
                values['changekeys'][name] = True
        if cfgParser.has_section('deletesections'):
            for (name, value) in cfgParser.items('deletesections'):
                values['deleteSections'][name] = value
        if cfgParser.has_section('valuesinturn'):
            for (name, value) in cfgParser.items('valuesinturn'):
                sep = value[0]
                values['inturn'][name] = value[1:].split(sep)
                values['changekeys'][name] = True
        if cfgParser.has_section('multivalues'):
            for (name, value) in cfgParser.items('multivalues'):
                sep = value[0]
                values['once'][name] = value[1:].split(sep)
                values['changekeys'][name] = True
        if cfgParser.has_section('multivalueseach'):
            for (name, value) in cfgParser.items('multivalueseach'):
                sep = value[0]
                values['eachtime'][name] = value[1:].split(sep)
                values['changekeys'][name] = True
        if cfgParser.has_section('novalues'):
            for (name, value) in cfgParser.items('novalues'):
                values['novalue'][name]=True
        if cfgParser.has_section('options'):
            for (name, value) in cfgParser.items('options'):
                values['options'][name]=value
        return values

    def clean_webservice_line(self, line):
        hp = HTMLParser()
        # print ('line before: %s'%line)
        line = re.sub("°","#deg;",line)
        # print ('line after: %s' % line)
        try:
            line = hp.unescape(line)
        except:
            print "<!-- unusual chars in {}".format(line)
        line = re.sub("<font[^>]+>","",line)
        line = re.sub("</font>","",line)
        return line

    def getTemplateDoc(self, category, webservice, withUrl=False):
        url = "http://{0}/ws/{1}/{2}.asmx?op={3}".format(self.addr, self.version, category, webservice)
        fh = urllib2.urlopen(url)
        # print type(fh)
        if withUrl:
            return url, self.get_webservice_raw(fh)
        else:
            return self.get_webservice_raw(fh)

    def get_webservice_raw(self, fh):
        output = []
        in_pre_block = 'never'
        for line in fh:
            # print line
            if in_pre_block == 'never' and "<pre>" in line:
                in_pre_block = 'first'
                output.append(self.clean_webservice_line(line.split("<pre>")[-1]))
            elif in_pre_block == 'first' and "</pre>" in line:
                in_pre_block = 'no'
                output.append(self.clean_webservice_line(line.split("</pre>")[0]))
            elif in_pre_block == 'first':
                output.append(self.clean_webservice_line(line))
        fh.close()
        # print output
        return output

    def getVersionList(self):
        return self.get_version_list(self.addr).splitlines()

    def get_version_list(self, server):
        pp = pprint.PrettyPrinter(indent=4)
        url = "http://{}/ws/".format(server)
        ufh = urllib2.urlopen(url)
        vparser = VersionParser()
        vparser.feed(ufh.read())
        versions = vparser.getVersions()

        return "\n".join(versions)

    def getCategoryList(self):
        return self.get_category_list(self.addr, self.version).splitlines()

    def get_category_list(self, server, version):
        pp = pprint.PrettyPrinter(indent=4)
        url = "http://{}/ws/{}".format(server, version)
        ufh = urllib2.urlopen(url)
        cparser = CategoryParser()
        cparser.feed(ufh.read())
        categories = cparser.getCategories()

        return "\n".join(categories)

    def getWebserviceList(self, category):
        url = "http://{}/ws/{}/{}.asmx".format(self.addr, self.version, category)
        ufh = urllib2.urlopen(url)
        wsparser = WebServiceParser()
        wsparser.feed(ufh.read())
        webservices = wsparser.getWebservices()
        return webservices

    def get_webservice_list(self, server, version=None, category=None):
        pp = pprint.PrettyPrinter(indent=4)
        if version==None and category==None:
            url="http://{}/qpack/qpackserv/qpackserv.asmx".format(server)
        else:
            url = "http://{}/ws/{}/{}.asmx".format(server, version, category)
        print "URL = "+url
        ufh = urllib2.urlopen(url)
        wsparser = WebServiceParser()
        wsparser.feed(ufh.read())
        webservices = wsparser.getWebservices()

        return "\n".join(webservices)

    def make_ini(self, name, template):
        print "# Making template for {}".format(name)
        in_header = True
        sections = []
        singleOccurences = { 'Username': [ 'string', 'Credentials'],  'Password': [ 'string', 'Credentials'] }
        multipleOccurences = {}
        eoHeader = re.compile("\s+<soap:Body")
        valueTag = re.compile("\s+<(\w+)>(.*)</\\1>")
        endSection = re.compile("\s+</")
        sectionName = re.compile("\s+<(\w+)>")
        for line in template:
            if in_header and eoHeader.match(line):
                in_header = False
                continue
            if in_header:
                continue
            if valueTag.match(line):
                name, values = valueTag.match(line).groups()
                sectionsName = "/".join(sections) if len(sections) > 0 else 'soap:Body root'
                if name in multipleOccurences:
                    newEntry = json.dumps([values, sectionsName])
                    if newEntry in multipleOccurences[name]:
                        multipleOccurences[name][newEntry] += 1
                    else:
                        multipleOccurences[name][newEntry] = 1
                elif name in singleOccurences:
                    multipleOccurences[name] = {}
                    multipleOccurences[name][json.dumps(singleOccurences[name])] = 1
                    newEntry = json.dumps([values, sectionsName])
                    if newEntry in multipleOccurences[name]:
                        multipleOccurences[name][newEntry] += 1
                    else:
                        multipleOccurences[name][newEntry] = 1
                    del singleOccurences[name]
                else:
                    singleOccurences[name] = [values, sectionsName]
            elif endSection.match(line):
                if len(sections) > 0:
                    sections.pop()
            elif sectionName.match(line):
                sections.append(sectionName.match(line).group(1))

        print "[values]"
        for name, values in singleOccurences.iteritems():
            print "{} # {}: possible values {}".format(name, values[1], values[0])
        print "[valueseachtime]"
        for name, valueList in multipleOccurences.iteritems():
            print name
            for valueJson, countUses in valueList.iteritems():
                values = json.loads(valueJson)
                print "# {} used {} times in {}: possible values {}".format(name, countUses, values[1], values[0])

    def parseargs(self, cliArgs=None):
        parser = argparse.ArgumentParser(description='Get/ set objects using NBI.',
                        epilog='Call without arguments (or just --server=..), to build command')
        parser.add_argument('--server', dest="server", default=None,
           help='name or IP address of Netspan server')
        parser.add_argument('--version', dest="version", default=None,
           help='version string')
        parser.add_argument('--category', dest="category", default=None,
           help='category within SOAP interface, typically Backhaul for iRelay')
        parser.add_argument('--category-list', dest="category_list", default=False, action='store_true',
           help='generate category list for command line completion')
        parser.add_argument('--list-webservice', dest="webservice_list", default=False, action='store_true',
           help='generate webservice list for command line completion, category must be specified')
        parser.add_argument('--webservice', dest="webservice", default=None,
           help='webservice within SOAP interface, e.g. IRelayPnpConfigCreate')
        parser.add_argument('--value', dest="values", default=None, action='append',
                help='name=value pairs to set')
        parser.add_argument('--eachtime', dest="eachtime", default=None, action='append',
                help='name=value pairs to set, each time they occur')
        parser.add_argument('--inturn', dest="valuesinturn", default=None, action='append',
                help='name=value pairs to set, to be used in turn, the first char is the separator.')
        parser.add_argument('--novalue', dest="novalues", default=None, action='append',
                            help='name of key to be removed')
        parser.add_argument('--vfile', dest='valuesfilenames', action='append', default=None,
                help='filename of values file, must contain name=value pairs, values in value file are overridden by --value. A filename of \'-\' will read from stdin, useful for reading HEREDOCs')
        parser.add_argument('--field', dest="field", default=None,
           help='if specified, only the value of this single field is output (first occurrence only unless --all-occurrences specified)')
        parser.add_argument('--all-occurrences', dest="all_occ", action='store_true',
           help="if specified, al values of --field will be output (';' separated)")
        parser.add_argument('--qpack', action='store_true',
            help="specify QPack SOAP method, switch to QPack not Netspan methods")
        parser.add_argument('--del-empty', dest='delEmpty', action='store_true', default=False,
                            help='remove any unspecified fields, useful for updates')
        parser.add_argument('--del-empty-sections', dest='delEmptySections', action='store_true', default=False,
                            help='remove sections which no do contain specified fields, useful for updates')
        parser.add_argument('--dry-run', dest='dryrun', action='store_true', default=False,
                            help='produce output POST to screen, do not send to NMS')
        parser.add_argument('--verbose', dest='verbose', action='store_true', default=False,
                            help='print out the SOAP Request before sending to NMS')
        parser.add_argument('--make-ini', dest='makeini', action='store_true', default=False,
                            help='make a template ini file for use with this SOAP action, overrides any values')
        parser.add_argument('--return-val',action="store_true")
        if cliArgs==None:
            return parser.parse_args()
        else:
            return parser.parse_args(cliArgs)
        
if __name__ == '__main__':
    nbi = nbi(None,None)
    response=nbi.run()
    if response!=None:
        print "{}".format(response)
