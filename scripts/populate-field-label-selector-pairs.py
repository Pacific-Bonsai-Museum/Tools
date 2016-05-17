#!/usr/bin/env python

from argparse import ArgumentParser
from collections import OrderedDict
import json
import re
import os
import sys

# From Jack Kelly
# http://stackoverflow.com/a/3663505
def rchop(thestring, ending):
  if thestring.endswith(ending):
    return thestring[:-len(ending)]
  return thestring

# From Bryukhanov Valentin
# http://stackoverflow.com/a/12507546
# (renamed and with minor changes to variable names)
def list_generator_from_dict(current_dict, prefix=None):
    prefix = prefix[:] if prefix else []
    if isinstance(current_dict, dict):
        for key, value in current_dict.items():
            if isinstance(value, dict):
                for d in list_generator_from_dict(value, [key] + prefix):
                    yield d
            elif isinstance(value, list) or isinstance(value, tuple):
                for v in value:
                    for d in list_generator_from_dict(v, [key] + prefix):
                        yield d
            else:
                yield prefix + [key, value]
    else:
        yield current_dict
        
# http://stackoverflow.com/q/2436607
def filterPick(list,filter):
    return [ ( l, m.group(1) ) for l in list for m in (filter(l),) if m]
        
FIELD_PATTERN = re.compile("^\$\{fields\.(\w+)\}$", re.IGNORECASE)
def get_field_name(value):
    # 'basestring' -> 'str' here in Python 3
    if isinstance(value, basestring):
        match = FIELD_PATTERN.match(value)
        if match is not None:
            return str(match.group(1))
    # TODO:
    # Many fields are in repeatable structures, and
    # code MUST be added here to match those.
    # 
    # if isinstance(value, dict):
    #     for v in value.values():
            # stub
            # print "\nisdict\n"
            # print v

MESSAGEKEY_KEY = 'messagekey'
UNICODE_MESSAGEKEY_KEY = unicode(MESSAGEKEY_KEY)
def get_messagekey_from_item(item):
    # 'basestring' -> 'str' here in Python 3
    if isinstance(item, dict):
        try:
            messagekey = item[MESSAGEKEY_KEY]
            return messagekey
        except KeyError, e:
            return None
    else:
        return None

LABEL_SUFFIX = '-label'
def get_label_name_from_field_name(field_name):
    # TODO:
    # This may be wildly too simplistic and may miss many fields;
    # we might instead need to get all items that have 'messagekey' children
    return '.' + field_name + LABEL_SUFFIX

# Given the name of a label entry in the uispec file,
# get its 'messagekey' value
def get_messagekey_from_label_name(label_name, items):
    label_value = items[label_name]
    messagekey = label_value[MESSAGEKEY_KEY]
    return messagekey

# Get the selector prefix for the current record type (e.g. "acquisition-")
RECORD_TYPE_PREFIX = None
SELECTOR_PATTERN = re.compile("^\.(csc-\w+\-)?.*$", re.IGNORECASE)
def get_record_type_selector_prefix(selector):
    global RECORD_TYPE_PREFIX
    if RECORD_TYPE_PREFIX is not None:
        return RECORD_TYPE_PREFIX
    else:
        match = SELECTOR_PATTERN.match(selector)
        if match is not None:
            RECORD_TYPE_PREFIX = str(match.group(1))       
            return RECORD_TYPE_PREFIX

# Per Stack Overflow member 'Roberto' in http://stackoverflow.com/a/31852401
def load_properties(filepath, sep=':', comment_char='#'):
    props = {}
    with open(filepath, "rt") as f:
        for line in f:
            l = line.strip()
            # Added check that each line to be processed also contains the separator 
            if l and not l.startswith(comment_char) and sep in l:
                key_value = l.split(sep)
                props[key_value[0].strip()] = key_value[1].strip('" \t') 
    return props

if __name__ == '__main__':
    
    parser = ArgumentParser(description='Populate field label/selector associations')
    parser.add_argument('-b', '--bundle_file',
        help='file with text labels (defaults to \'core-messages.properties\' in current directory)', default = 'core-messages.properties')
    parser.add_argument('-u', '--uispec_file',
        help='file with data used to generate the page (defaults to \'uispec\' in current directory)', default = 'uispec')
    args = parser.parse_args()
    
    # ##################################################
    # Open and read the message bundle (text label) file
    # ##################################################
    
    bundle_path = args.bundle_file.strip()
    if not os.path.isfile(bundle_path):
        sys.exit("Could not find file \'%s\'" % bundle_path)
        
    text_labels = load_properties(bundle_path)
    text_labels_lowercase = {k.lower():v for k,v in text_labels.items()}
    
    # For debugging
    # for key,value in text_labels_lowercase.items():
    #     # Change the following hard-coded record type value as needed, for debugging
    #     if key.startswith('acquisition-'):
    #         print "%s: %s" % (key, str(value))
    
    # ##################################################
    # Open and read the uispec file
    # ##################################################

    uispec_path = args.uispec_file.strip()
    if not os.path.isfile(uispec_path):
        sys.exit("Could not find file \'%s\'" % uispec_path)
        
    with open(uispec_path) as uispec_file:    
        uispec = json.load(uispec_file)
    
    # From the uispec file ...
    
    # Get the list of items below the top level item
    
    # Check for presence of the expected top-level item
    TOP_LEVEL_KEY='recordEditor'
    try:
        uispec_items = uispec[TOP_LEVEL_KEY]
    except KeyError, e:
        sys.exit("Could not find expected top level item \'%s\' in uispec file" % TOP_LEVEL_KEY)
    
    # Check that at least one item was returned
    if not uispec_items:
        sys.exit("Could not find expected items in uispec file")
    
    # ##################################################
    # Iterate through the list of selectors in the
    # uispec file
    # ##################################################
    
    messagekeys = {}
    messagekeys_not_found_msgs = []
    text_labels_not_found_msgs = []
    for selector, value in uispec_items.iteritems():
        
        # For debugging
        # print "%s %s\n" % (selector, value)
        
        messagekey = get_messagekey_from_item(value)
        if messagekey is not None:
            try:
                text_label = text_labels_lowercase[messagekey.lower()]
                if not text_label.strip():
                    text_labels_not_found_msgs.append("// Not found: text label for message key '%s'" % messagekey)
                else:
                    # Strip leading '.' from selector
                    selector = selector.replace(selector[:1], '')
                    messagekeys[selector] = text_label
            except KeyError, e:
                messagekeys_not_found_msgs.append("// Not found: message key '%s'" % messagekey)

    # For debugging
    # for key, value in messagekeys.iteritems():
    #     print 'fieldSelectorByLabel.put("%s", "%s");' % (value, key)
            
    generator = list_generator_from_dict(uispec[TOP_LEVEL_KEY])

    selector_items = []
    for uispec_item in generator:
        # TODO: There may be more elegant and/or faster ways to do this
        # with list comprehensions and/or fiters
        if isinstance(uispec_item, list):
            for u_item in uispec_item:
                # TODO: Replace with regex to avoid unintentional matches
                if str(u_item).startswith(".cs"):
                    selector_items.append(uispec_item)
    
    # For debugging
    # for s_item in selector_items:
    #     print s_item
    
    field_items = []
    field_regex = re.compile(".*fields\.", re.IGNORECASE)
    for selector_item in selector_items:
        for entry in selector_item:
            if field_regex.match(entry):
                field_items.append(selector_item)
               
    # For debugging
    # for f_item in field_items:
    #     print f_item
                    
    LABEL_SUFFIX = "-label"
    #########
    CSC_PREFIX = "csc-"
    CSC_RECORD_TYPE_PREFIX = CSC_PREFIX + "acquisition-" # HARD_CODED!!! get_record_type_selector_prefix('any')
    #########
    CSC_RECORD_TYPE_PREFIX_LENGTH = len(CSC_RECORD_TYPE_PREFIX)
    fields = {}
    fields_not_found_msgs = []
    for key, value in messagekeys.iteritems():
        messagekey_fieldname = rchop(key, LABEL_SUFFIX)
        if messagekey_fieldname.startswith(CSC_RECORD_TYPE_PREFIX):
            messagekey_fieldname = messagekey_fieldname[CSC_RECORD_TYPE_PREFIX_LENGTH:]
        found = False
        print messagekey_fieldname
        num_found = 0
        for field_item in field_items:
            for item in field_item:
                messagekey_fieldname_regex = re.compile(".*fields\." + messagekey_fieldname, re.IGNORECASE)
                if messagekey_fieldname_regex.match(str(item)):
                    # The following needs work; the first item may not hold a selector
                    # We need to find the item in a list that contains the 
                    for possible_selector_item in field_item:
                        if str(possible_selector_item).startswith("." + CSC_PREFIX):
                            # For debugging
                            # print "=> %s" % possible_selector_item
                            fieldkey = possible_selector_item.replace(possible_selector_item[:1], '')
                            fields[fieldkey] = value
                            found = True
        if not found:
            fields_not_found_msgs.append("// Not found: field for label %s" % rchop(key, LABEL_SUFFIX))
        
    for key, value in sorted(fields.iteritems(), key=lambda (k,v): (v,k)):
        print 'fieldSelectorByLabel.put("%s", "%s");' % (value, key)

    for msg in sorted(fields_not_found_msgs):
        print msg

    for msg in sorted(messagekeys_not_found_msgs):
        print msg

    for msg in sorted(text_labels_not_found_msgs):
        print msg
    
        
        # Get selectors that are specifically for fields. (There are some
        # selectors in uispec files that are for other entity types)
        #
        # From those selectors, get their actual field names, as these
        # may not always match even a part of the selector.
        #
        # E.g. for selector '.csc-acquisition-acquisition-provisos'
        # its actual field name, following the initial '.csc-recordtype-...'
        # prefix, is 'acquisitionProvisos' (i.e. ${fields.acquisitionProvisos})

        # field_name = get_field_name(value)
        # if field_name is not None:
        #     prefix = get_record_type_selector_prefix(selector)
        #     field_name = prefix + field_name
        #     label = get_label_name_from_field_name(field_name)
        #     messagekey = get_messagekey_from_label_name(label, uispec_items)
        #     try:
        #         text_label = text_labels_lowercase[messagekey.lower()]
        #         if not text_label.strip():
        #             print "// Could not find text label for message key '%s'" % messagekey
        #         else:
        #             # Strip leading '.' from selector
        #             print 'fieldSelectorByLabel.put("%s", "%s");' % (text_label, selector.replace(selector[:1], ''))
        #     except KeyError, e:
        #         print "// Could not find message key '%s'" % messagekey

            
        
    