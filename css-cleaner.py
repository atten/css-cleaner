import sys, os.path, re
from lxml import etree

class CssMetaBlock:
    def __init__(self):
        self.blocks = []
        self.title = ""


class CssBlock:
    def __init__(self):
        self.rules = []
        self.text = ""


class CssRule:
    AllDescendants = 0
    OnlyChildren = 1
    Follows = 2
    Sibling = 3

    def init(self):
        self.tag = None
        self.classes = []
        self.id = None
        self.bracket_content = ''
        self.state = None
        self.parent = None
        self.relation = self.AllDescendants
        self.after_whitespace = None


    def __init__(self):
        self.init()


    def __init__(self, str, parent, relation):
        self.init()
        pattern = re.compile("^[\w\-_*%]*")
        self.parent = parent
        self.relation = relation

        while len(str):
            c = str[0]
            if c == '.':
                classname = pattern.search(str[1:]).group(0)
                if not classname:
                    return
                if not classname in self.classes:
                    self.classes.append(classname)
                str = str[len(classname)+1:]
            elif c == '#':
                self.id = pattern.search(str[1:]).group(0)
                if not self.id:
                    return
                str = str[len(self.id)+1:]
            elif c == ':':
                self.state = str
                return
            elif c == '[':
                i = str.find(']')
                if i < 0:
                    return
                elif i > 1:
                    self.bracket_content += str[:i+1]
                str = str[i+1:]
            elif c == '(':
                i = str.find(')')
                if i < 0:
                    return
                str = str[i+1:]
            else:
                self.tag = pattern.search(str).group(0)
                if self.tag:
                    str = str[len(self.tag):]


    def is_empty(self):
        return not(self.tag or len(self.classes) or self.id or self.state or self.bracket_content)


    def __str__(self):
        return self.tostring()


    def tostring(self, with_parents = True, sort_classes = False, whitespace = False):
        str = ""
        if self.parent and with_parents:
            str += self.parent.tostring()
            if self.relation == self.AllDescendants:
                str += ' '
            elif self.relation == self.OnlyChildren:
                str += " > "
            elif self.relation == self.Follows:
                str += " + "
            elif self.relation == self.Sibling:
                str += ' ~ '

        str += self.tag if self.tag else ''
        if len(self.classes):
            str += '.'
            if sort_classes:
                sorted = list(self.classes)
                sorted.sort()
                str += '.'.join(sorted)
            else:
                str += '.'.join(self.classes)
        str += self.bracket_content
        str += '#' + self.id if self.id else ''
        str += self.state if self.state else ''
        str += ',' + self.after_whitespace if whitespace and self.after_whitespace else ''
        return str



class HtmlElement:
    def __init__(self):
        self.parent = None
        self.previous = None
        self.tag = None
        self.id = None
        self.classes = []

    def is_satisfy_rule(self, rule):
        if not(self.tag or len(self.classes) or self.id):     # TODO: bracket_content always satisfy, not processed
            return True
        if rule.id and rule.id != self.id:
            return False
        if not(set(rule.classes) <= set(self.classes)):
            return False
        if rule.tag and rule.tag != self.tag:
            return False
        if rule.parent:
            if rule.relation == CssRule.Follows:
                return self.previous and self.previous.is_satisfy_rule(rule.parent)
            if rule.relation == CssRule.OnlyChildren:
                return self.parent and self.parent.is_satisfy_rule(rule.parent)
            if rule.relation == CssRule.Sibling:
                p = self.previous
                while p:
                    if p.is_satisfy_rule(rule.parent):
                        return True
                    p = p.previous
                return False
            if rule.relation == CssRule.AllDescendants:
                p = self.parent
                while p:
                    if p.is_satisfy_rule(rule.parent):
                        if not rule.parent.parent:
                            return True
                        if not p.parent:
                            return False
                        return p.parent.is_satisfy_rule(rule.parent.parent)
                    else:
                        p = p.parent
                return False
        return True


    def __str__(self):
        s = ""
        if self.tag:
            s += self.tag
        if self.classes:
            s += '.' + '.'.join(self.classes)
        if self.id:
            s += '#' + self.id
        return s


class HtmlProcessor:
    ActionEnd = 0
    ActionStart = 1

    def __init__(self):
        self.parent = None
        self.previous = None
        self.last_action = None

    def start(self, tag, attrib):
        e = HtmlElement()
        e.tag = tag
        e.parent = self.parent
        e.previous = self.previous
        if 'class' in attrib:
            e.classes = attrib['class'].split(' ')
            e.classes.sort()

        if 'id' in attrib:
            e.id = attrib['id']

        self.parent = e
        self.add(e)

        if self.last_action == self.ActionStart:
            self.previous = None
        else:
            self.previous = e

        self.last_action = self.ActionStart

    def end(self, tag):
        if self.last_action == self.ActionEnd:
            self.previous = self.parent

        if self.parent:
            self.parent = self.parent.parent

        self.last_action = self.ActionEnd

    def data(self, data):
        pass

    def comment(self, text):
        pass

    def close(self):
        pass

    def add(self, element):
        key = element.__str__()
        if not key in html_tags:
            html_tags[key] = element



css_meta_blocks = []
css_rules = {}
html_tags = {}


def print_usage():
    print "Usage: %s [css_path] [html_path]" % os.path.basename(sys.argv[0])


def print_help():
    print_usage()
    print "Generates [css_path].fixed cleaned from unused styles"


def add_rule(rule):
    if not rule:
        return
    key = rule.tostring(sort_classes = True)
    if not key in css_rules:
        css_rules[key] = rule


def process_css_block(str, css_path, line_counter, column_counter):
    block = CssBlock()
    rule_name_pattern = re.compile("^[\w\-_.#()\[\]=:*\"\'%]*")
    relation = CssRule.AllDescendants
    parent = None

    while len(str):
        rule = rule_name_pattern.search(str).group(0)
        if rule:
            r = CssRule(rule, parent, relation)
            parent = r if not r.is_empty() else None
            str = str[len(rule):]
            relation = CssRule.AllDescendants
        elif parent:
            c = str[0]
            str = str[1:]
            column_counter += 1
            if c == '>':
                relation = CssRule.OnlyChildren
            elif c == '+':
                relation = CssRule.Follows
            elif c == '~':
                relation = CssRule.Sibling
            elif c == ',':
                stripped = str.lstrip()
                parent.after_whitespace = str[:len(str)-len(stripped)]
                str = stripped
                add_rule(parent)
                block.rules.append(parent)
                relation = CssRule.AllDescendants
                parent = None
            elif c == '\n':
                line_counter += 1
                column_counter = 0
            elif c == '{':
                add_rule(parent)
                block.rules.append(parent)
                block.text = str[:-1]
                if len(block.text.strip()):
                    return block
                else:
                    return None
        elif str.startswith('@'):       # meta block
            start = str.find('{')
            end = str.rfind('}')
            if 0 < start < end:
                meta = CssMetaBlock()
                meta.title = str[:start]
                for s, line_counter, column_counter in get_css_blocks(str[start+1:end]):
                    b = process_css_block(s, css_path, line_counter, column_counter)
                    if b:
                        meta.blocks.append(b)
                css_meta_blocks.append(meta)
            return None
        else:
            #print "Warning: unexpected symbol '%s' (file %s, line %d, column %d)" % (str[0], css_path, line_counter, column_counter)
            return None


def get_css_blocks(css_path_or_str):
    iterable = open(css_path_or_str) if os.path.isfile(css_path_or_str) else ['%s\n' % s for s in css_path_or_str.split('\n')]
    buffer = ""
    nested = 0
    line_counter = 0
    comment = False

    for line in iterable:
        line_counter += 1

        while not nested:         # keep comments inside blocks
            comment_start = line.find("/*")
            comment_end = line.find("*/")

            if comment and comment_end < 0:
                line = ""         # entire line belongs to comment
                break
            elif comment_start == comment_end:
                break
            elif comment_end >= 0 and (comment_start > comment_end or comment_start < 0):
                line = line[comment_end+2:]
                comment = False
            elif 0 <= comment_start < comment_end:
                line = line[:comment_start] + line[comment_end+2:]
                comment = False
            elif comment_end < 0 <= comment_start and not comment:
                line = line[:comment_start]
                comment = True
                break

        column_counter = 0
        for c in line:
            column_counter += 1
            if not(not nested and not buffer and c.isspace()):
                buffer += c

            if c == '{':
                nested += 1
            elif c == '}':
                nested -= 1
                if not nested:
                    yield buffer, line_counter, column_counter
                    buffer = ""
                elif nested < 0:
                    print "Warning: excessive '}' (file %s, line %d, column %d)" % (css_path, line_counter, column_counter)
                    nested = 0
                    buffer = ""


def analyze_css(css_path, html_path):
    for s, line_counter, column_counter in get_css_blocks(css_path):
        b = process_css_block(s, css_path, line_counter, column_counter)
        if b:
            if not len(css_meta_blocks) or css_meta_blocks[-1].title:   # create untitled meta block
                meta = CssMetaBlock()
                css_meta_blocks.append(meta)
            css_meta_blocks[-1].blocks.append(b)

    print "css rules: %d " % len(css_rules)

    parser = etree.HTMLParser(target = HtmlProcessor())
    etree.parse(html_path, parser)

    unused = 0
    for k, rule in css_rules.items():
        satisfied = False
        for element in html_tags.values():
            if element.is_satisfy_rule(rule):
                satisfied = True
                break

        if not satisfied:
            del css_rules[k]
            unused += 1

    print "unused rules: %d" % unused

    newfile = open(css_path + '.fixed', 'w')

    for m in css_meta_blocks:
        title_printed = False
        for b in m.blocks:
            rules = []
            for r in b.rules:
                if r.tostring(sort_classes = True) in css_rules:
                    rules.append(r)
            if len(rules):
                if m.title and not title_printed:
                    newfile.write(m.title + '{\n')
                    title_printed = True
                if m.title:
                    newfile.write('  ')     # intend for block headers inside metablock
                newfile.write(''.join([r.tostring(sort_classes = False, whitespace = r != rules[-1]) for r in rules]))
                newfile.write(' {' + b.text + '}\n')

        if title_printed:
            newfile.write('}\n')

    print "written optimized css: %s" % newfile.name



if len(sys.argv) == 3:
    css_path = sys.argv[1]
    html_path = sys.argv[2]

    if not os.path.isfile(css_path):
        print "Error: wrong CSS file path: %s" % css_path
        print_usage()
        exit(2)
    elif not os.path.isfile(html_path):
        print "Error: wrong HTML file path: %s" % html_path
        print_usage()
        exit(2)
    else:
        analyze_css(css_path, html_path)
else:
    print_help()
    exit(2)