class StringBuilder:

    def __init__(self, linebreak="\n"):
        self.string = ""
        self.level = 0
        self.line_break = linebreak
        self.current_indent = ""
        self.new_line_flag = True

    def push_indent(self):
        self.level += 1
        self.current_indent = " " * (4 * self.level)

    def pop_indent(self):
        if self.level > 0:
            self.level -= 1

        self.current_indent = " " * (4 * self.level)

    def append_indent_if_necessary(self):
        if self.new_line_flag:
            self.new_line_flag = False
            self.string += self.current_indent

    def append_line(self, text=None):
        self.append((text or '') + self.line_break)

    def append(self, text):
        pieces = text.split(self.line_break)
        for i in range(len(pieces)):
            if pieces[i] != "" and pieces[i] is not None:
                self.append_indent_if_necessary()
                self.string += pieces[i]
            if i < len(pieces) - 1:
                self.string += self.line_break
                self.new_line_flag = True

    def __str__(self):
        return self.string
