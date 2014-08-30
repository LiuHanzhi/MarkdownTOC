import sublime
import sublime_plugin
import re
import os.path
import distutils.util

pattern_anchor = re.compile(r'\[.+?\]')
pattern_tag = re.compile(r'<.*?>')

pattern_h1_h2_equal_dash = "^.*?(?:(?:\r\n)|\n|\r)(?:-+|=+)$"

TOCTAG_START = "<!-- MarkdownTOC -->"
TOCTAG_END = "<!-- /MarkdownTOC -->"


class MarkdowntocInsert(sublime_plugin.TextCommand):

    def run(self, edit):

        if not self.find_tag_and_insert(edit):
            sels = self.view.sel()
            for sel in sels:
                attrs = {
                    "depth":    self.get_setting('default_depth'),
                    "autolink": self.get_setting('default_autolink'),
                    "bracket":  self.get_setting('default_bracket')
                }
                # add TOCTAG
                toc = TOCTAG_START + "\n"
                toc += "\n"
                toc += self.get_toc(attrs, sel.end())
                toc += "\n"
                toc += TOCTAG_END + "\n"

                self.view.insert(edit, sel.begin(), toc)
                log('inserted TOC')

        # TODO: process to add another toc when tag exists

    def get_toc_open_tag(self):
        search_results = self.view.find_all(
            "^<!-- MarkdownTOC .*-->\n",
            sublime.IGNORECASE)
        search_results = self.remove_items_in_codeblock(search_results)

        toc_open_tags = []
        for toc_open in search_results:
            if 0 < len(toc_open):
                
                tag_str = self.view.substr(toc_open)

                depth_val = self.get_setting('default_depth')
                depth_search = re.search(" depth=(\w+) ", tag_str)
                if depth_search != None:
                    depth_val = int(depth_search.group(1))

                autolink_val = self.get_setting('default_autolink')
                autolink_search = re.search(" autolink=(\w+) ", tag_str)
                if autolink_search != None:
                    autolink_val = distutils.util.strtobool(autolink_search.group(1)) # cast to bool

                bracket_val = self.get_setting('default_bracket')
                bracket_search = re.search(" bracket=(\w+) ", tag_str)
                if bracket_search != None:
                    bracket_val = str(bracket_search.group(1))
                
                toc_open_tag = {
                    "region":   toc_open,
                    "depth":    depth_val,
                    "autolink": autolink_val,
                    "bracket":  bracket_val
                }
                toc_open_tags.append(toc_open_tag)

        return toc_open_tags

    def get_toc_close_tag(self, start):
        close_tags = self.view.find_all(
            "^" + TOCTAG_END + "\n")
        close_tags = self.remove_items_in_codeblock(close_tags)
        for close_tag in close_tags:
            if start < close_tag.begin():
                return close_tag

    # Search MarkdownTOC comments in document
    def find_tag_and_insert(self, edit):
        toc_starts = self.get_toc_open_tag()
        for dic in toc_starts:
            
            toc_start = dic["region"]
            if 0 < len(toc_start):
                
                toc_close = self.get_toc_close_tag(toc_start.end())
                
                if toc_close:
                    toc = self.get_toc(dic, toc_close.end())
                    tocRegion = sublime.Region(
                        toc_start.end(), toc_close.begin())
                    if toc:
                        self.view.replace(edit, tocRegion, "\n" + toc + "\n")
                        log('refresh TOC content')
                        return True
                    else:
                        self.view.replace(edit, tocRegion, "\n")
                        log('TOC is empty')
                        return False
        log('cannot find TOC tags')
        return False

    # TODO: add "end" parameter
    def get_toc(self, attrs, begin):

        # Search headings in docment
        if attrs['depth'] == 0:
            pattern_hash = "^#+?[^#]"
        else:
            pattern_hash = "^#{1," + str(attrs['depth']) + "}[^#]"
        headings = self.view.find_all(
            "%s|%s" % (pattern_h1_h2_equal_dash, pattern_hash))

        headings = self.remove_items_in_codeblock(headings)

        if len(headings) < 1:
            return False

        items = []  # [[headingNum,text],...]
        for heading in headings:
            if begin < heading.end():
                lines = self.view.lines(heading)
                if len(lines) == 1:
                    # handle hash headings, ### chapter 1
                    r = sublime.Region(
                        heading.end(), self.view.line(heading).end())
                    heading_text = self.view.substr(r)
                    heading_num = heading.size() - 1
                    items.append([heading_num, heading_text])
                elif len(lines) == 2:
                    # handle - or + headings, Title 1==== section1----
                    heading_text = self.view.substr(lines[0])
                    if heading_text.strip():
                        heading_num = 1 if (
                            self.view.substr(lines[1])[0] == '=') else 2
                        items.append([heading_num, heading_text])
        
        if len(items) < 1:
            return

        # Shape TOC  ------------------
        items = format(items)

        # Create TOC  ------------------
        toc = ''
        id_texts = []
        for item in items:
            heading_num = item[0] - 1
            heading_text = item[1]
            heading_text = pattern_tag.sub('', heading_text) # remove html tags
            heading_text = heading_text.rstrip() # remove end space

            # add indent by heading_num
            for i in range(heading_num):
                toc += '\t'
            
            # Handling anchors ("Reference-style links")
            matchObj = pattern_anchor.search(heading_text)
            if matchObj:
                heading_text = heading_text[0:matchObj.start()]
                heading_text = heading_text.rstrip()
                id_text = matchObj.group().replace('[','').replace(']','')
                if attrs['bracket'] == 'round':
                    toc += '- [' + heading_text + '](#' + id_text + ')\n'
                else:
                    toc += '- [' + heading_text + '][' + id_text + ']\n'
            elif attrs['autolink']:
                id_text = remove_reserved_chars(heading_text.lower().replace(" ", "-"))
                id_texts.append(id_text)
                n = id_texts.count(id_text)
                if 1 < n:
                    id_text += '-' + str(n-1)
                if attrs['bracket'] == 'round':
                    toc += '- [' + heading_text + '](#' + id_text + ')\n'
                else:
                    toc += '- [' + heading_text + '][' + id_text + ']\n'
            else:
                toc += '- ' + heading_text + '\n'

        return toc
    
    def get_setting(self, attr):
        settings = sublime.load_settings('MarkdownTOC.sublime-settings')
        return settings.get(attr)

    def remove_items_in_codeblock(self, items):

        codeblocks = self.view.find_all("^`{3,}[^`]*$")
        codeblockAreas = [] # [[area_begin, area_end], ..]
        i = 0
        while i < len(codeblocks)-1:
            area_begin = codeblocks[i].begin()
            area_end   = codeblocks[i+1].begin()
            if area_begin and area_end:
                codeblockAreas.append([area_begin, area_end])
            i += 2

        items = [h for h in items if is_out_of_areas(h.begin(), codeblockAreas)]
        return items


def remove_reserved_chars(str):
    # Percent-encoding reserved characters
    delete = {
        ord(u"!"): None,
        ord(u"#"): None,
        ord(u"$"): None,
        ord(u"&"): None,
        ord(u"'"): None,
        ord(u"("): None,
        ord(u")"): None,
        ord(u"*"): None,
        ord(u"+"): None,
        ord(u","): None,
        ord(u"/"): None,
        ord(u":"): None,
        ord(u";"): None,
        ord(u"="): None,
        ord(u"?"): None,
        ord(u"@"): None,
        ord(u"["): None,
        ord(u"]"): None,
        ord(u"`"): None
    }
    return str.translate(delete)

def is_out_of_areas(num, areas):
    for area in areas:
        if area[0] < num and num < area[1]:
            return False
    return True

def format(items):
    headings = []
    for item in items:
        headings.append(item[0])
    # ----------

    # set root to 1
    min_heading = min(headings)
    if 1 < min_heading:
        for i, item in enumerate(headings):
            headings[i] -= min_heading - 1
    headings[0] = 1  # first item must be 1

    # minimize "jump width"
    for i, item in enumerate(headings):
        if 0 < i and 1 < item - headings[i - 1]:
            before = headings[i]
            after = headings[i - 1] + 1
            headings[i] = after
            for n in range(i + 1, len(headings)):
                if(headings[n] == before):
                    headings[n] = after
                else:
                    break

    # ----------
    for i, item in enumerate(items):
        item[0] = headings[i]
    return items

def log(arg):
    sublime.status_message(arg)
    print(arg)

# Search and refresh if it's exist


class MarkdowntocUpdate(MarkdowntocInsert):

    def run(self, edit):
        MarkdowntocInsert.find_tag_and_insert(self, edit)


class AutoRunner(sublime_plugin.EventListener):

    def on_pre_save(self, view):
        # limit scope
        root, ext = os.path.splitext(view.file_name())
        ext = ext.lower()
        if ext in [".md", ".markdown", ".mdown", ".mdwn", ".mkdn", ".mkd", ".mark"]:
            view.run_command('markdowntoc_update')
